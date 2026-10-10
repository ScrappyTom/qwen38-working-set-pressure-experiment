"""Opt-in host transitions, actual CPU execution, and bounded HTTP lifecycle."""
import copy
from contextlib import contextmanager
import http.server
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import parser_roundtrip
import run_contribution_cycle as runner
from working_set_exp import decision_view, working_view
from working_set_exp.accounted_contribution import process_reply
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_cycle import ContributionCycleMixin, extend_reply_schema, focus_request
from working_set_exp.contribution_limits import Limits, SpendingControl, SpendingStop
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.deadline_transport import post, TransportFailure
from working_set_exp.decision_session import DecisionSession
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes
from working_set_exp.observations import ObservationStore
from working_set_exp.working_session import INPUT_LIMIT


class Session(ContributionCycleMixin, DecisionSession):
    pass


def converter():
    path = ROOT / "development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py"
    spec = importlib.util.spec_from_file_location("cycle_test_converter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SchemaConverter


class Clock:
    value = 0.0

    def __call__(self):
        return self.value


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.checker = b"from app import value\nassert value == 2, f'actual value: {value}'\n"
        self.s = Session(Candidate.create({"app.py": b"value = 1\n"}),
            {"public": self.checker}, "Save the behavior, then verify it.", edit_checks={},
            call_limit=40, request_limit=16, observations=ObservationStore(self.folder / "obs"))

    def do(self, action, measure=lambda v: 900):
        self.s.mark_delivered(self.s.view())
        return self.s.execute(action, measure)

    def select(self, objective="Implement value 2", check_id="public", **kwargs):
        return self.do(dict(action="select_contribution", objective=objective, check_id=check_id), **kwargs)

    def read(self):
        return self.do(dict(action="read", path="app.py", start_line=1, end_line=0))

    def edit(self, value):
        return self.do(dict(action="patch", path="app.py", old=self.s.candidate.file_map["app.py"].decode(),
            new=f"value = {value}\n", expected_candidate_id=self.s.candidate.candidate_id,
            expected_file_sha256=self.s.candidate.file_sha256("app.py")))

    def check(self):
        return self.do(dict(action="check", check_id="public", expected_candidate_id=self.s.candidate.candidate_id))


class HostTests(Fixture):
    def test_purpose_does_not_grant_authority_or_certify_work(self):
        self.select("value = 1\n")
        self.assertFalse(self.edit(2)["accepted"])
        self.assertFalse(self.do(dict(action="submit", expected_candidate_id=self.s.candidate.candidate_id))["accepted"])
        self.assertEqual(self.s.current_contribution()["recorded_effects"]["accepted_edits"], 0)
        self.read()
        self.assertTrue(self.edit(3)["accepted"])
        self.assertFalse(self.check()["passed"])
        focus = self.s.current_contribution()
        self.assertEqual(focus["recorded_effects"], dict(accepted_edits=1, edited_paths=["app.py"]))
        self.assertTrue(focus["actual_selected_check"]["applies_to_current"])
        self.assertFalse(focus["actual_selected_check"]["passed"])
        self.assertTrue(self.edit(2)["accepted"])
        self.assertFalse(self.s.current_contribution()["actual_selected_check"]["applies_to_current"])
        self.assertTrue(self.check()["passed"])
        self.assertTrue(self.do(dict(action="submit", expected_candidate_id=self.s.candidate.candidate_id))["accepted"])
        self.assertEqual(self.s.current_contribution()["completion"], "not_inferred_from_objective_account_or_edit_counts")

    def test_clear_retrieve_rejected_update_and_clone_preserve_designation(self):
        self.select("First")
        first = self.s.current_contribution()["action_handle"]
        self.select("Second")
        self.do(dict(action="reopen_event", handle=first, offset=0))
        self.assertEqual(self.s.current_contribution()["objective"], "Second")
        clone = self.s.clone()
        self.assertFalse(self.select("Too big", measure=lambda v: INPUT_LIMIT + 1
            if v["current_contribution"]["objective"] == "Too big" else 900)["accepted"])
        self.assertEqual(self.s.current_contribution()["objective"], "Second")
        self.select("", "")
        self.assertIsNone(self.s.current_contribution())
        self.assertEqual(clone.current_contribution()["objective"], "Second")
        self.assertFalse(self.select(" ")["accepted"])
        self.assertFalse(self.select("", "public")["accepted"])

    def test_old_pass_and_changed_checker_are_separate_from_local_work(self):
        self.read()
        self.edit(2)
        self.check()
        self.select("Inspect existing work")
        check = self.s.current_contribution()["actual_selected_check"]
        self.assertTrue(check["applies_to_current"])
        self.assertFalse(check["recorded_after_selection"])
        self.s.checkers["public"] += b"# a different definition\n"
        self.assertFalse(self.s.current_contribution()["actual_selected_check"]["applies_to_current"])

    def test_focus_changes_neither_source_selection_nor_account(self):
        self.read()
        self.do(dict(action="record_account", text="Unresolved: behavior is untested."))
        before = copy.deepcopy(self.s.view())
        self.select("Finish bounded behavior")
        after = self.s.view()
        self.assertEqual(before["working_set"], after["working_set"])
        self.assertEqual(before["working_account"], after["working_account"])
        wire = dict(messages=[dict(role="system", content="original"), dict(role="user",
            content=canonical_json_bytes(dict(workspace=after, preceding_operation_feedback=[])).decode())],
            seed=42, temperature=0.6)
        changed = focus_request(wire)
        payload = json.loads(changed["messages"][1]["content"])
        self.assertEqual(next(iter(payload)), "current_contribution")
        focus = payload.pop("current_contribution")
        payload["workspace"]["current_contribution"] = focus
        self.assertEqual(payload, json.loads(wire["messages"][1]["content"]))
        self.assertEqual(changed["seed"], wire["seed"])
        self.assertNotIn("Finish bounded behavior", changed["messages"][0]["content"])

    def test_previous_job_objective_stays_historical(self):
        self.select("Earlier job purpose")
        self.s.starting_archive_length = len(self.s.pairs)  # Declared new-job boundary.
        self.assertIsNone(self.s.current_contribution())
        self.do(dict(action="reopen_event", handle="EVT-0001", offset=0))
        self.assertIsNone(self.s.current_contribution())
        self.select("New job purpose")
        self.assertEqual(self.s.current_contribution()["objective"], "New job purpose")


class SpendingTests(Fixture):
    def test_only_real_current_declared_checks_clear_waiting_time(self):
        clock = Clock()
        control = SpendingControl(Limits(10, 50, 12), clock=clock, wall_clock=clock)
        self.read()
        start = len(self.s.pairs)
        self.edit(3)
        control.observe_reply(self.s, start, 1)
        clock.value = 8
        start = len(self.s.pairs)
        self.select("Different objective")
        self.do(dict(action="record_account", text="The work is checked. (An unsupported claim.)"))
        control.observe_reply(self.s, start, 1)
        self.assertEqual(control.request_allowance(), (4, "unchecked_edit_elapsed_limit"))
        start = len(self.s.pairs)
        self.check()
        self.assertFalse(self.s.check_state()["passed"])
        control.observe_reply(self.s, start, 1)
        self.assertIsNone(control.unchecked_since)
        start = len(self.s.pairs)
        self.edit(2)
        control.observe_reply(self.s, start, 1)
        clock.value = 13
        saved = control.snapshot()
        restored = SpendingControl.restore(json.loads(json.dumps(saved)), clock=clock, wall_clock=clock)
        self.assertEqual(restored.snapshot(), saved)
        self.assertEqual(restored.request_allowance(), (7, "unchecked_edit_elapsed_limit"))
        clock.value = 20
        with self.assertRaisesRegex(SpendingStop, "unchecked_edit"):
            restored.remaining()

    def test_stale_definition_rejected_check_and_historical_retrieval_do_not_reset(self):
        clock = Clock()
        control = SpendingControl(Limits(10, 30, 10), clock=clock)
        self.read()
        start = len(self.s.pairs)
        self.edit(3)
        control.observe_reply(self.s, start, 1)
        start = len(self.s.pairs)
        self.check()
        self.s.checkers["public"] += b"# changed\n"
        control.observe_reply(self.s, start, 1)
        self.assertIsNotNone(control.unchecked_since)
        start = len(self.s.pairs)
        self.do(dict(action="check", check_id="public", expected_candidate_id="0" * 64))
        self.do(dict(action="reopen_result", handle=f"RES-{start:04d}", offset=0))
        control.observe_reply(self.s, start, 1)
        self.assertIsNotNone(control.unchecked_since)

    def test_invalid_and_exhausted_limits(self):
        for values in ((0, 20, 10), (30, 20, 10), (float("inf"), 20, 10), (True, 20, 10)):
            with self.assertRaises(ValueError):
                Limits(*values)
        clock = Clock()
        control = SpendingControl(Limits(5, 20, 10), clock=clock, wall_clock=clock)
        clock.value = 21
        restored = SpendingControl.restore(control.snapshot(), clock=clock, wall_clock=clock)
        with self.assertRaisesRegex(SpendingStop, "attempt_elapsed"):
            restored.remaining()

    def test_restore_does_not_refund_elapsed_time_after_checkpoint(self):
        clock = Clock()
        control = SpendingControl(Limits(5, 20, 10), clock=clock, wall_clock=clock)
        clock.value = 4
        saved = control.snapshot()
        clock.value = 19
        restored = SpendingControl.restore(saved, clock=clock, wall_clock=clock)
        self.assertEqual(restored.remaining(), (1, "attempt_elapsed_limit"))
        clock.value = 3
        with self.assertRaisesRegex(ValueError, "future"):
            SpendingControl.restore(saved, clock=clock, wall_clock=clock)


class RunnerTests(Fixture):
    def setup_loop(self, choose, limits=None, transport=None):
        self.clock = Clock()
        limits = limits or Limits(30, 120, 60)
        self.control = SpendingControl(limits, clock=self.clock)
        module = SimpleNamespace(**{k: getattr(parser_roundtrip, k) for k in dir(parser_roundtrip) if not k.startswith("_")})
        module.MAX_REQUESTS = self.s.request_limit
        module.reply_schema = lambda: decision_view.reply_schema(self.s.checkers)
        module.process_reply = process_reply
        module.response_constraints = lambda: dict(grammar="CPU stub, not native qualification")
        module.expected_native = lambda r: canonical_json_bytes(r["messages"])
        self.adapter = runner.Adapter(module, checks=self.s.checkers, converter_class=converter(), limits=limits)
        self.sent = []

        def render(request, stem):
            native = self.adapter.expected_native(request)
            count = 1200  # CPU stub. Native token admission is a later gate.
            return canonical_json_bytes(dict(prompt=native.decode())), native, canonical_json_bytes(dict(tokens=[0] * count)), count

        def fake_post(url, route, raw, timeout):
            self.sent.append(json.loads(raw))
            state = json.loads(self.sent[-1]["messages"][1]["content"])
            reply = choose(state, len(self.sent))
            return canonical_json_bytes(dict(choices=[dict(finish_reason="stop", message=dict(
                reasoning_content="PRIVATE", content=json.dumps(reply)))], usage=dict(prompt_tokens=1200,
                completion_tokens=100, total_tokens=1300, prompt_tokens_details=dict(cached_tokens=0)), timings=dict(cache_n=0)))

        loop = runner.Loop(self.folder, ArtifactStore(self.folder),
            runner.existing.RunLog(self.folder / "records.jsonl", "cycle-offline"), task_module=self.adapter,
            spending=self.control, post=transport or fake_post, render=render, health=lambda: {}, source_check=lambda: None)
        return loop

    def test_real_edit_check_submission_through_new_reply_decoder(self):
        def choose(state, n):
            if n == 1:
                return dict(discussion="Local goal", operation=dict(action="select_contribution", objective="Implement value 2", check_id="public"))
            if n == 2:
                self.assertEqual(state["current_contribution"]["objective"], "Implement value 2")
                return dict(discussion="Need exact code", operation=dict(action="read", path="app.py", start_line=1, end_line=0))
            if n == 3:
                return dict(discussion="Implement", operation=dict(action="patch", path="app.py", old="value = 1\n", new="value = 2\n",
                    expected_candidate_id=self.s.candidate.candidate_id, expected_file_sha256=self.s.candidate.file_sha256("app.py")))
            if n == 4:
                return dict(discussion="Observe", operation=dict(action="check", check_id="public", expected_candidate_id=self.s.candidate.candidate_id))
            self.assertTrue(state["current_contribution"]["actual_selected_check"]["passed"])
            return dict(discussion="Close", operation=dict(action="submit", expected_candidate_id=self.s.candidate.candidate_id))
        result = self.setup_loop(choose).execute(self.s)
        self.assertEqual(result["disposition"], "checked_submission")
        self.assertEqual((len(self.sent), self.control.requests_completed), (5, 5))
        self.assertIsNone(self.control.unchecked_since)
        verify_records(self.folder / "records.jsonl", self.folder)

    def test_deadline_preserves_raw_partial_and_does_not_execute_or_retry(self):
        calls = []
        def transport(url, route, raw, timeout):
            calls.append(timeout)
            raise SpendingStop("request_deadline", data=b'{"unfinished":"private draft')
        loop = self.setup_loop(None, transport=transport)
        before = self.s.candidate.candidate_id
        closed = []
        @contextmanager
        def owned_runtime():
            try:
                yield
            finally:
                closed.append(True)
        with owned_runtime():
            result = loop.execute(self.s)
        self.assertEqual(closed, [True])  # Real owned-runtime shutdown is a later gate.
        self.assertEqual(result["disposition"], "spending_limit")
        self.assertEqual(result["reason"], "request_elapsed_limit")
        self.assertEqual((len(calls), self.s.calls_used), (1, 0))
        self.assertEqual(self.s.candidate.candidate_id, before)
        self.assertEqual((self.folder / "calls/C01-partial-response.bin").read_bytes(), b'{"unfinished":"private draft')
        self.assertTrue((self.folder / "spending-stop-candidate.json").exists())
        verify_records(self.folder / "records.jsonl", self.folder)

    def test_total_deadline_before_dispatch(self):
        loop = self.setup_loop(lambda s, n: {})
        self.clock.value = 121
        self.assertEqual(loop.execute(self.s)["reason"], "attempt_elapsed_limit")
        self.assertEqual(self.sent, [])

    def test_checkpoint_request_count_and_first_input_guard_are_preserved(self):
        loop = self.setup_loop(lambda s, n: dict(discussion="Stop"))
        self.s.requests_used = 3
        loop.measure(self.s.view())
        entry = next(iter(loop.cache.values()))
        loop.initial = {**entry, "wire_request_sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "first input differs"):
            loop.execute(self.s)
        self.assertEqual((loop.sent, len(self.sent)), (3, 0))
        with self.assertRaisesRegex(ValueError, "already entered"):
            loop.execute(self.s)

    def test_rendered_scopes_must_match_execution_before_sending(self):
        loop = self.setup_loop(None)
        self.s.checkers["additional"] = b"pass\n"
        with self.assertRaisesRegex(ValueError, "scopes differ"):
            loop.execute(self.s)
        self.assertEqual(self.sent, [])
        with self.assertRaisesRegex(ValueError, "unavailable check"):
            runner.Adapter(self.adapter.original, checks={"public": b"pass\n"},
                converter_class=converter(), limits=self.control.limits, qualifying_check_ids=("missing",))

    def test_closure_cost_does_not_rewrite_an_already_accepted_submission(self):
        self.read()
        self.edit(2)
        self.check()
        loop = self.setup_loop(lambda s, n: dict(discussion="Use actual pass", operation=dict(
            action="submit", expected_candidate_id=self.s.candidate.candidate_id)))
        def processing(*args):
            result = process_reply(*args)
            self.clock.value += 150  # Simulated draining/custody after accepted submission.
            return result
        self.adapter.original.process_reply = processing
        result = loop.execute(self.s)
        self.assertEqual(result["disposition"], "checked_submission")
        self.assertTrue(self.s.submitted)
        self.assertEqual(len(self.sent), 1)
        self.assertGreater(self.control.snapshot()["elapsed_seconds"], self.control.limits.total_seconds)

    def test_deadline_after_saved_edit_keeps_candidate_and_scope_changes_do_not_reset(self):
        def choose(state, n):
            if n == 1:
                return dict(discussion="Read", operation=dict(action="read", path="app.py", start_line=1, end_line=0))
            if n == 2:
                return dict(discussion="Save", operation=dict(action="patch", path="app.py", old="value = 1\n", new="value = 2\n",
                    expected_candidate_id=self.s.candidate.candidate_id, expected_file_sha256=self.s.candidate.file_sha256("app.py")))
            self.clock.value += 25  # Whole response arrives after the pending-edit deadline.
            return dict(discussion="Late reply must not execute", operation=dict(action="select_contribution", objective="Reset?", check_id="public"))
        loop = self.setup_loop(choose, Limits(30, 100, 20))
        result = loop.execute(self.s)
        self.assertEqual(result["reason"], "unchecked_edit_elapsed_limit")
        self.assertEqual(self.s.candidate.file_map["app.py"], b"value = 2\n")
        self.assertEqual(self.s.calls_used, 2)
        self.assertIsNone(self.s.current_contribution())

    def test_literal_source_channel_remains_available(self):
        self.setup_loop(None)
        header = dict(discussion="exact source", operation=dict(action="replace_region", region="R-abc", expected_candidate_id="0" * 64))
        # The real source-header schema validates refs; obtain one through a read.
        self.read()
        header["operation"]["region"] = self.s.view()["working_set"]["sources"][0]["region_ref"]
        content = json.dumps(header) + "\nSOURCE\nvalue = 'literal \\n remains'\n"
        decoded = self.adapter.module.decode_reply(content)
        self.assertEqual(decoded["operation"]["new"], "value = 'literal \\n remains'\n")
        self.assertIn("select_contribution", self.adapter.constraints["grammar"])


class TransportTests(unittest.TestCase):
    def server(self, body):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                body(self)
            def log_message(self, *args):
                pass
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_port}"

    def test_trickling_output_hits_absolute_deadline_and_keeps_prefix(self):
        def body(h):
            h.send_response(200)
            h.send_header("Content-Length", "10000")
            h.end_headers()
            try:
                for _ in range(200):
                    h.wfile.write(b"x")
                    h.wfile.flush()
                    time.sleep(0.02)
            except OSError:
                pass
        url = self.server(body)
        start = time.monotonic()
        with self.assertRaises(SpendingStop) as caught:
            post(url, "/completion", b"{}", 0.18)
        self.assertLess(time.monotonic() - start, 1.5)
        self.assertTrue(caught.exception.data.startswith(b"x"))

    def test_normal_response_and_non_success_are_distinct(self):
        def body(h):
            h.send_response(422)
            h.send_header("Content-Length", "7")
            h.end_headers()
            h.wfile.write(b"invalid")
        with self.assertRaises(TransportFailure) as caught:
            post(self.server(body), "/completion", b"{}", 2)
        self.assertEqual((caught.exception.status, caught.exception.data), (422, b"invalid"))

    def test_complete_body_is_returned_unchanged(self):
        def body(h):
            h.send_response(200)
            h.send_header("Content-Length", "2")
            h.end_headers()
            h.wfile.write(b"{}")
        self.assertEqual(post(self.server(body), "/completion", b"{}", 2), b"{}")

    def test_deadline_also_applies_before_headers(self):
        def body(h):
            time.sleep(0.4)
        start = time.monotonic()
        with self.assertRaises(SpendingStop) as caught:
            post(self.server(body), "/completion", b"{}", 0.12)
        self.assertEqual(caught.exception.data, b"")
        self.assertLess(time.monotonic() - start, 1.5)


if __name__ == "__main__":
    unittest.main()
