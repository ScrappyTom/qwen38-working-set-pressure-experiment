import json
from pathlib import Path
from contextlib import contextmanager
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import parser_roundtrip as task
import run_uncoached_contribution as run
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_session import ContributionSession
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


class UncoachedContributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="uncoached-host-test-")
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.session = ContributionSession(Candidate.create({"app.py": b"value = 1\n"}),
            b"from app import value\nassert value == 2\n", "Save checked work.", call_limit=12)
        self.module = SimpleNamespace(**{k: getattr(task, k) for k in dir(task) if not k.startswith("_")})
        self.adapter = run.Adapter(self.module)
        self.sent = []

    def render(self, request, stem):
        native = self.adapter.expected_native(request)
        count = len(native) // 4 + 100
        return canonical_json_bytes(dict(prompt=native.decode())), native, canonical_json_bytes(dict(tokens=[0] * count)), count

    def loop(self, choose, finish="stop", render=None):
        def post(url, route, raw, timeout):
            self.assertEqual(route, "/v1/chat/completions")
            index = len(self.sent) + 1
            self.assertEqual((self.output/f"calls/C{index:02d}-wire-request.json").read_bytes(), raw)
            request = json.loads(raw)
            self.sent.append(request)
            state = json.loads(request["messages"][1]["content"])
            self.assertEqual(set(state), {"workspace", "preceding_operation_feedback"})
            self.assertNotIn("PRIVATE_REASONING", raw.decode())
            self.assertNotIn("MODEL_EXPLANATION", raw.decode())
            self.assertEqual(list(request["response_format"]["json_schema"]["schema"]["oneOf"][2]["properties"]),
                             ["discussion", "operation", "check_after"])
            reply = choose(state, index)
            count = self.render(request, "")[-1]
            return canonical_json_bytes(dict(choices=[dict(finish_reason=finish, message=dict(
                reasoning_content="PRIVATE_REASONING", content=json.dumps(reply)))],
                usage=dict(prompt_tokens=count, completion_tokens=100, total_tokens=count + 100,
                           prompt_tokens_details=dict(cached_tokens=0)), timings=dict(cache_n=0)))
        return run.Loop(self.output, ArtifactStore(self.output), run.RunLog(self.output/"records.jsonl", "offline-test"),
                        task_module=self.adapter, post=post, render=render or self.render, health=lambda: {}, source_check=lambda: None)

    def edit(self, state, old, new):
        workspace = state["workspace"]
        return dict(discussion="MODEL_EXPLANATION", operation=dict(action="patch", path="app.py", old=old, new=new,
                    expected_candidate_id=workspace["candidate_id"], expected_file_sha256=self.session.candidate.file_sha256("app.py")),
                    check_after="public")

    def test_read_edit_check_submit_without_coaching_or_lost_receipt(self):
        def choose(state, index):
            w = state["workspace"]
            if index == 1:
                return dict(discussion="MODEL_EXPLANATION", operation=dict(action="read", path="app.py", start_line=1, end_line=0))
            if index == 2:
                return self.edit(state, "value = 1\n", "value = 2\n")
            edit = state["preceding_operation_feedback"][0]["result"]
            check = w["latest_feedback"]["result"]
            self.assertEqual(edit["candidate_id"], check["checked_candidate_id"])
            self.assertEqual(check["check_definition_sha256"], sha256_bytes(self.session.checker))
            self.assertEqual(w["working_set"]["sources"][0]["content"], "value = 2\n")
            self.assertTrue(w["current_check"]["applies_to_current"])
            return dict(discussion="MODEL_EXPLANATION", operation=dict(action="submit", expected_candidate_id=w["candidate_id"]))
        outcome = self.loop(choose).execute(self.session)
        self.assertEqual(outcome["disposition"], "checked_submission")
        self.assertEqual((outcome["sent_requests"], outcome["actual_operations"]), (3, 4))
        self.assertEqual(len(self.sent), 3)
        self.assertTrue((self.output/"after/C02-O01-state.json").exists())
        self.assertTrue((self.output/"after/C02-O02-state.json").exists())
        verify_records(self.output/"records.jsonl", self.output)

    def test_failed_check_is_delivered_and_correction_preserves_actual_work(self):
        self.session.add_source(self.session.source(dict(path="app.py", start_line=1, end_line=0)))
        def choose(state, index):
            w = state["workspace"]
            if index == 1:
                return self.edit(state, "value = 1\n", "value = 3\n")
            if index == 2:
                self.assertFalse(w["latest_feedback"]["result"]["passed"])
                self.assertEqual(w["working_set"]["sources"][0]["content"], "value = 3\n")
                return self.edit(state, "value = 3\n", "value = 2\n")
            return dict(discussion="MODEL_EXPLANATION", operation=dict(action="submit", expected_candidate_id=w["candidate_id"]))
        outcome = self.loop(choose).execute(self.session)
        self.assertEqual(outcome["disposition"], "checked_submission")
        self.assertEqual(outcome["actual_operations"], 5)

    def test_rejected_stale_patch_does_not_check_or_mutate(self):
        def choose(state, index):
            reply = self.edit(state, "value = 1\n", "value = 2\n")
            reply["operation"]["expected_candidate_id"] = "0" * 64
            return reply
        self.loop(choose).invoke(self.session)
        result = task.read(self.output/"calls/C01-host-result.json")
        self.assertEqual(len(result["operations"]), 1)
        self.assertFalse(result["operations"][0]["result"]["accepted"])
        self.assertFalse(result["check_after"]["executed"])
        self.assertEqual(self.session.candidate.file_map["app.py"], b"value = 1\n")

    def test_discussion_only_closes_without_a_coaching_reply(self):
        outcome = self.loop(lambda s, n: dict(discussion="I cannot continue with these tools.")).execute(self.session)
        self.assertEqual(outcome["disposition"], "actor_stopped_without_operation")
        self.assertEqual((len(self.sent), self.session.calls_used), (1, 0))

    def test_request_and_action_allowances_are_distinct(self):
        self.module.MAX_REQUESTS = 1
        self.session.add_source(self.session.source(dict(path="app.py", start_line=1, end_line=0)))
        outcome = self.loop(lambda s, n: self.edit(s, "value = 1\n", "value = 2\n")).execute(self.session)
        self.assertEqual(outcome["disposition"], "request_allowance_exhausted")
        self.assertEqual((outcome["sent_requests"], outcome["actual_operations"]), (1, 2))

    def test_combined_allowance_failure_happens_before_mutation(self):
        self.session.call_limit = 1
        self.session.add_source(self.session.source(dict(path="app.py", start_line=1, end_line=0)))
        with self.assertRaisesRegex(ValueError, "insufficient action allowance"):
            self.loop(lambda s, n: self.edit(s, "value = 1\n", "value = 2\n")).invoke(self.session)
        self.assertEqual(self.session.calls_used, 0)
        self.assertTrue((self.output/"calls/C01-endpoint-response.json").exists())

    def test_stop_during_response_drains_requested_bundle(self):
        self.session.add_source(self.session.source(dict(path="app.py", start_line=1, end_line=0)))
        def choose(state, index):
            (self.output/"STOP_REQUEST.txt").write_text("Offline operator stop", encoding="utf-8")
            return self.edit(state, "value = 1\n", "value = 2\n")
        outcome = self.loop(choose).execute(self.session)
        self.assertEqual(outcome["disposition"], "operator_stopped")
        self.assertEqual((len(self.sent), self.session.calls_used), (1, 2))
        self.assertTrue(self.session.check_state()["passed"])

    def test_stop_during_render_does_not_mark_unsent_input_delivered(self):
        def render(request, stem):
            (self.output/"STOP_REQUEST.txt").write_text("Stop during preparation", encoding="utf-8")
            return self.render(request, stem)
        with patch.object(self.session, "mark_delivered", wraps=self.session.mark_delivered) as delivered:
            result = self.loop(lambda s, n: {}, render=render).execute(self.session)
        self.assertEqual(result["disposition"], "operator_stopped")
        delivered.assert_not_called()
        self.assertEqual(self.sent, [])

    def test_incomplete_response_is_preserved_without_action_or_retry(self):
        with self.assertRaisesRegex(ValueError, "incomplete response"):
            self.loop(lambda s, n: dict(discussion="unfinished"), finish="length").execute(self.session)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.session.calls_used, 0)
        self.assertEqual((self.output/"calls/C01-assistant-reasoning.txt").read_text(), "PRIVATE_REASONING")

    def test_first_wire_mismatch_prevents_sending(self):
        loop = self.loop(lambda s, n: {})
        loop.measure(self.session.view())
        row = next(iter(loop.cache.values()))
        loop.initial = {**row, "wire_request_sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "first input differs"):
            loop.execute(self.session)
        self.assertEqual(self.sent, [])

    def test_prior_candidate_check_does_not_verify_a_different_contract(self):
        old = ContributionSession(self.session.candidate, b"pass\n", "old work")
        old.execute(dict(action="check", check_id="public", expected_candidate_id=old.candidate.candidate_id), lambda v: 500)
        changed = ContributionSession(old.candidate, self.session.checker, "new work", pairs=old.pairs)
        self.assertTrue(changed.check_state()["candidate_matches"])
        self.assertFalse(changed.check_state()["check_definition_matches"])
        result = changed.execute(dict(action="submit", expected_candidate_id=changed.candidate.candidate_id), lambda v: 500)
        self.assertFalse(result["accepted"])
        same = ContributionSession(old.candidate, old.checker, "same contract", pairs=old.pairs)
        self.assertTrue(same.check_state()["applies_to_current"])

    def test_legacy_unbound_check_is_retrievable_but_not_current_verification(self):
        s = task.initial_session()
        self.assertTrue(s.check_state()["passed"])
        self.assertFalse(s.check_state()["applies_to_current"])
        self.assertTrue(json.loads(s.payload(s.check_state()["handle"]))["passed"])
        self.assertEqual(s.sources(), [])
        self.assertEqual(s.calls_used, 0)
        request = self.adapter.request_for(s.view())
        self.assertEqual(request["chat_template_kwargs"], dict(enable_thinking=True, reasoning_effort="xhigh"))

    def test_normal_operator_stop_closes_runtime_and_seals(self):
        folder = self.output / "attempt"
        manifest = dict(source_sha256={}, initial={})
        manifest_path = self.output / "manifest.json"
        manifest_path.write_bytes(canonical_json_bytes(manifest))
        self.module.MANIFEST, self.module.RUN = manifest_path, folder
        self.module.initial_session = lambda: self.session
        self.module.runtime_paths = lambda: (Path("server"), Path("model"), Path("tokenizer"))
        closed = []
        @contextmanager
        def runtime(args, store, log):
            (args.output / "STOP_REQUEST.txt").write_text("Offline closure qualification", encoding="utf-8")
            try:
                yield "mock://runtime"
            finally:
                closed.append(True)
                log.append("runtime_closed", dict(owned_server_shutdown_verified=True, dedicated_port_free=True), [])
        with patch.object(run, "verify_package", return_value=manifest), \
             patch.object(task.base.base, "owned_runtime", runtime), \
             patch.object(task.base.pilot, "health", return_value={}):
            run.run_once(SimpleNamespace(owner_direction="Offline lifecycle", manifest_sha256=sha256_file(manifest_path)), self.module)
        seal = task.read(folder / "RESPONSE_SEAL.json")
        self.assertEqual(seal["disposition"], "operator_stopped")
        self.assertEqual(seal["sent_requests"], 0)
        self.assertEqual(closed, [True])
        self.assertTrue((folder/"final-candidate.json").exists())
        verify_records(folder / "records.jsonl", folder)

    def test_status_only_check_keeps_definition_binding_in_current_state(self):
        self.session.checker = b"print('x' * 2500)\n"
        def meter(view):
            feedback = view["latest_feedback"]
            return 999_999 if feedback and len(feedback["result"].get("stdout", "")) > 1000 else 500
        result = self.session.execute(dict(action="check", check_id="public",
            expected_candidate_id=self.session.candidate.candidate_id), meter)
        self.assertTrue(result["passed"])
        self.assertEqual(self.session.last["output_scope"], "status_only_full_result_archived")
        self.assertTrue(self.session.check_state()["applies_to_current"])
        archived = json.loads(self.session.payload(self.session.last["full_result_handle"]))
        self.assertEqual(archived["check_definition_sha256"], sha256_bytes(self.session.checker))


if __name__ == "__main__":
    unittest.main()
