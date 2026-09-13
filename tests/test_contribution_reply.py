import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import parser_documentation_session as task
from run_bounded_parser import Loop, RunLog
from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes
from working_set_exp.working_session import WorkingSession
from working_set_exp.working_view import validate


class ContributionReplyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="assisted-parser-test-")
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.session = WorkingSession(Candidate.create({"app.py": b"value = 1\n"}),
            b"from app import value\nassert value == 2\n", "one checked change", call_limit=6)
        self.session.add_source(self.session.source(dict(path="app.py", start_line=1, end_line=0)))
        self.adapter = task.Adapter([dict(speaker="reviewer", text="Save the change or ask what is missing.")])
        self.sent = []

    def make_loop(self, reply, finish="stop"):
        def render(request, stem):
            native = task.base.expected_native(request)
            return canonical_json_bytes(dict(prompt=native.decode())), native, canonical_json_bytes(dict(tokens=[1]*500)), 500
        def post(url, route, raw, timeout):
            self.assertEqual(route, "/v1/chat/completions")
            request = json.loads(raw)
            self.assertNotIn("PRIVATE_EXPLANATION", raw.decode())
            self.sent.append(request)
            return canonical_json_bytes(dict(choices=[dict(finish_reason=finish, message=dict(
                reasoning_content="PRIVATE_EXPLANATION", content=canonical_json_bytes(reply).decode()))],
                usage=dict(prompt_tokens=500, completion_tokens=100, total_tokens=600,
                           prompt_tokens_details=dict(cached_tokens=0)), timings=dict(cache_n=0)))
        return Loop(self.output, ArtifactStore(self.output), RunLog(self.output/"records.jsonl", "mock-assistance"),
            task_module=self.adapter, post=post, render=render, health=lambda: {}, source_check=lambda: None)

    def invoke(self, loop, tag="T01"):
        loop.measure(self.session.view())
        key = sha256_bytes(canonical_json_bytes(self.adapter.request_for(self.session.view())))
        return task.receive(loop, self.session, tag, loop.cache[key])

    def operation(self):
        return dict(action="patch", path="app.py", old="value = 1\n", new="value = 2\n",
            expected_candidate_id=self.session.candidate.candidate_id,
            expected_file_sha256=self.session.candidate.file_sha256("app.py"))

    def test_exact_operation_feedback_public_discussion_and_source_refresh(self):
        operation = self.operation()
        reply = dict(discussion="I can save this change now.", operation=operation)
        loop = self.make_loop(reply)
        self.invoke(loop)
        host = task.base.read(self.output/"calls/T01-host-result.json")
        self.assertEqual(host["operations"][0]["action"], operation)
        self.assertTrue(host["operations"][0]["result"]["accepted"])
        self.assertEqual(self.session.candidate.file_map["app.py"], b"value = 2\n")
        following = self.adapter.request_for(self.session.view())
        value = json.loads(following["messages"][1]["content"])
        self.assertEqual(value["dialogue"][-1]["text"], reply["discussion"])
        self.assertEqual(value["workspace"]["latest_feedback"]["result"], host["operations"][0]["result"])
        self.assertEqual(value["workspace"]["working_set"]["sources"][0]["content"], "value = 2\n")
        self.assertNotIn("PRIVATE_EXPLANATION", canonical_json_bytes(following).decode())
        self.assertEqual((self.output/"calls/T01-assistant-reasoning.txt").read_text(), "PRIVATE_EXPLANATION")

    def test_question_is_recorded_without_operation_or_mutation(self):
        before = self.session.candidate
        loop = self.make_loop(dict(discussion="Which documented input should this handle?"))
        self.invoke(loop)
        self.assertEqual(self.session.candidate, before)
        self.assertEqual(self.session.pairs, [])
        self.assertEqual(task.base.read(self.output/"calls/T01-host-result.json"), dict(executed=False, discussion_only=True, operations=[]))

    def test_incomplete_or_invalid_reply_is_preserved_without_execution(self):
        loop = self.make_loop(dict(discussion="Ready.", operation=self.operation()), finish="length")
        with self.assertRaisesRegex(ValueError, "incomplete reply"):
            self.invoke(loop)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.session.pairs, [])
        self.assertTrue((self.output/"calls/T01-endpoint-response.json").is_file())
        self.assertEqual(len(self.adapter.dialogue), 1)
        rule = task.reply_schema()["json_schema"]["schema"]
        for invalid in (dict(discussion="x", operation={}), dict(operation=self.operation()),
                        dict(discussion="x", operation=self.operation(), invented=True)):
            with self.assertRaises(ValueError):
                validate(invalid, rule)

    def test_guards_are_enforced_by_existing_host(self):
        operation = self.operation()
        operation["expected_candidate_id"] = "0"*64
        loop = self.make_loop(dict(discussion="This guarded proposal must be checked.", operation=operation))
        self.invoke(loop)
        self.assertFalse(task.base.read(self.output/"calls/T01-host-result.json")["operations"][0]["result"]["accepted"])
        self.assertEqual(self.session.candidate.file_map["app.py"], b"value = 1\n")

    def test_settings_and_operation_requirements_are_preserved(self):
        request = self.adapter.request_for(self.session.view())
        original = task.base.request_for(self.session.view())
        self.assertEqual({k:v for k,v in request.items() if k not in ("messages", "response_format")},
                         {k:v for k,v in original.items() if k not in ("messages", "response_format")})
        reference = task.working_view.system_prompt().split("\n\n", 1)[1]
        self.assertIn(reference, request["messages"][0]["content"])
        self.assertIn("operation", request["messages"][0]["content"])

    def test_requested_check_binds_successor_and_both_receipts_reach_input(self):
        operation = self.operation()
        before = self.session.candidate.candidate_id
        loop = self.make_loop(dict(discussion="Save and check this contribution.",
                                   operation=operation, check_after="public"))
        self.invoke(loop)
        host = task.base.read(self.output/"calls/T01-host-result.json")
        edit, check = host["operations"]
        self.assertEqual(edit["action"], operation)
        self.assertNotEqual(before, self.session.candidate.candidate_id)
        self.assertEqual(check["action"]["expected_candidate_id"], edit["result"]["candidate_id"])
        self.assertTrue(check["result"]["passed"])
        self.assertEqual(self.session.calls_used, 2)
        self.assertEqual(len(self.sent), 1)
        current = json.loads(self.adapter.request_for(self.session.view())["messages"][1]["content"])
        self.assertEqual(current["preceding_operation_feedback"][0]["result"], edit["result"])
        self.assertEqual(current["workspace"]["latest_feedback"]["result"], check["result"])
        self.assertEqual(self.session.delivered_sources[0]["candidate_id"], before)
        self.assertTrue((self.output/"after/T01-O01-state.json").exists())
        self.assertTrue((self.output/"after/T01-O02-state.json").exists())
        self.assertFalse(self.session.submitted)

    def test_rejected_edit_skips_requested_check(self):
        action = self.operation()
        action["expected_candidate_id"] = "0"*64
        loop = self.make_loop(dict(discussion="Guarded edit with validation.", operation=action, check_after="public"))
        self.invoke(loop)
        host = task.base.read(self.output/"calls/T01-host-result.json")
        self.assertEqual(len(host["operations"]), 1)
        self.assertFalse(host["operations"][0]["result"]["accepted"])
        self.assertFalse(host["check_after"]["executed"])
        self.assertEqual(self.session.candidate.file_map["app.py"], b"value = 1\n")
        self.assertEqual(self.adapter.preceding_feedback, [])

    def test_failed_check_keeps_edit_for_actual_correction(self):
        self.session.checker = b"from app import value\nassert value == 3\n"
        loop = self.make_loop(dict(discussion="A proposed change to test.", operation=self.operation(), check_after="public"))
        self.invoke(loop)
        host = task.base.read(self.output/"calls/T01-host-result.json")
        self.assertTrue(host["operations"][1]["result"]["accepted"])
        self.assertFalse(host["operations"][1]["result"]["passed"])
        self.assertEqual(self.session.candidate.file_map["app.py"], b"value = 2\n")
        self.assertFalse(self.session.submitted)

    def test_action_allowance_is_checked_before_mutation(self):
        self.session.call_limit = 1
        self.session.mark_delivered(self.session.view())
        with self.assertRaisesRegex(ValueError, "insufficient action allowance"):
            task.process_reply(self.session, dict(discussion="Save and check.",
                operation=self.operation(), check_after="public"), lambda view: 100, [])
        self.assertEqual(self.session.pairs, [])
        self.assertEqual(self.session.candidate.file_map["app.py"], b"value = 1\n")

    def test_following_request_restore_preserves_actual_combined_feedback(self):
        loop = self.make_loop(dict(discussion="Save and check.", operation=self.operation(), check_after="public"))
        self.invoke(loop)
        for name, value in (("final-state.json", task.base.snapshot(self.session)),
                            ("final-candidate.json", task.base.candidate_bytes(self.session.candidate))):
            task.base.save(self.output, name, value)
        restored = task.restore(self.output, "final")
        restored.task = self.session.task
        adapter = task.Adapter(self.adapter.dialogue, self.adapter.preceding_feedback)
        self.assertEqual(adapter.request_for(restored.view()), self.adapter.request_for(self.session.view()))

    def test_combined_receipt_is_counted_when_check_output_requires_historical_access(self):
        self.session.mark_delivered(self.session.view())
        self.session.checker = b"print('x' * 2000)\n"
        observed = []
        def measure(view):
            request = json.loads(self.adapter.request_for(view)["messages"][1]["content"])
            observed.append(request)
            if request["preceding_operation_feedback"] and len(view["latest_feedback"]["result"].get("stdout", "")) > 1000:
                return task.INPUT_LIMIT + 1
            return 500
        host = task.process_reply(self.session, dict(discussion="Save and check.",
            operation=self.operation(), check_after="public"), measure, self.adapter.preceding_feedback)
        self.assertTrue(host["operations"][1]["result"]["passed"])
        self.assertEqual(self.session.last["output_scope"], "status_only_full_result_archived")
        self.assertNotIn("stdout", self.session.last["result"])
        self.assertEqual(json.loads(self.session.payload(self.session.last["full_result_handle"])), host["operations"][1]["result"])
        self.assertTrue(any(r["preceding_operation_feedback"] for r in observed))
        self.assertFalse(self.session.delivery_blocked)

    def test_combined_form_rejects_nonpatch_and_unrecognized_check(self):
        rule = task.reply_schema()["json_schema"]["schema"]
        for operation, check in ((dict(action="check", check_id="public",
            expected_candidate_id=self.session.candidate.candidate_id), "public"),
            (self.operation(), "invented")):
            with self.assertRaises(ValueError):
                validate(dict(discussion="Invalid combination.", operation=operation, check_after=check), rule)

    def test_saved_edit_receipt_survives_failure_before_check_returns(self):
        self.session.mark_delivered(self.session.view())
        original = self.session.execute
        recorded = []
        def execute(action, measure):
            if action["action"] == "check":
                raise RuntimeError("simulated interruption before check execution")
            return original(action, measure)
        with patch.object(self.session, "execute", execute):
            with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
                task.process_reply(self.session, dict(discussion="Save and check.",
                    operation=self.operation(), check_after="public"), lambda view: 500,
                    self.adapter.preceding_feedback, lambda n, op: recorded.append((n, op)))
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0][1]["result"]["candidate_id"], self.session.candidate.candidate_id)
        self.assertEqual(self.session.candidate.file_map["app.py"], b"value = 2\n")

    def test_one_reply_closes_runtime_and_seals_without_automatic_continuation(self):
        area = self.output / "session"
        area.mkdir()
        for name in ("SPEC.md", "SYSTEM.txt", "OPENING.txt"):
            (area/name).write_bytes((task.AREA/name).read_bytes())
        (area/"TASK.txt").write_text(self.session.task, encoding="utf-8")
        package = area / "preparation-01"
        package.mkdir()
        closed, requests = [], []
        @contextmanager
        def runtime(args, store, log):
            log.append("runtime_prepared", dict(actor=task.base.ACTOR), [])
            try:
                yield "mock://local"
            finally:
                closed.append(True)
                log.append("runtime_closed", dict(owned_server_shutdown_verified=True, dedicated_port_free=True), [])
        def factory(output, store, log, **kwargs):
            def render(request, stem):
                native = task.base.expected_native(request)
                return canonical_json_bytes(dict(prompt=native.decode())), native, canonical_json_bytes(dict(tokens=[1]*500)), 500
            def post(url, route, raw, timeout):
                self.assertEqual(route, "/v1/chat/completions")
                requests.append(raw)
                return canonical_json_bytes(dict(choices=[dict(finish_reason="stop", message=dict(
                    reasoning_content="PRIVATE_EXPLANATION", content='{"discussion":"One reply is complete."}'))],
                    usage=dict(prompt_tokens=500, completion_tokens=100, total_tokens=600,
                               prompt_tokens_details=dict(cached_tokens=0)), timings=dict(cache_n=0)))
            return Loop(output, store, log, task_module=kwargs["task_module"], source_check=kwargs["source_check"],
                        post=post, render=render, health=lambda: {})
        with patch.object(task, "AREA", area), patch.object(task, "identities", return_value={}), \
             patch.object(task.base, "runtime_paths", return_value=(Path("server"), Path("model"), Path("tokenizer"))), \
             patch.object(task.base.base, "owned_runtime", runtime), patch.object(task, "Loop", factory), \
             patch.object(task.base.base, "memory_stats", return_value={}), \
             patch.object(task.base.base, "runtime_evidence", return_value={}), \
             patch.object(task.base.base, "port_free", return_value=True):
            request = self.adapter.request_for(self.session.view())
            initial = dict(prompt_tokens=500, request_sha256=sha256_bytes(canonical_json_bytes(request)),
                           native_sha256=sha256_bytes(task.base.expected_native(request)))
            for name, value in (("starting-state.json", task.base.snapshot(self.session)),
                ("starting-candidate.json", task.base.candidate_bytes(self.session.candidate)),
                ("dialogue.json", self.adapter.dialogue), ("preceding-feedback.json", []),
                ("reviewer-message.txt", b"A reviewed operator message"),
                ("PLAN.json", dict(status="qualified", source_sha256={}, initial=initial))):
                task.base.save(package, name, value)
            files = task.base.base.file_inventory(package)
            task.base.save(package, "SEAL.json", dict(files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files))))
            task.run_turn(1, "Execute this mocked assisted reply.")
        self.assertEqual(len(requests), 1)
        self.assertEqual(closed, [True])
        sealed = task.base.base.verify_seal(area/"turn-01")
        self.assertEqual(sealed["disposition"], "completed_assisted_turn")
        self.assertEqual(sealed["sent_requests"], 1)
        self.assertEqual(task.base.read(area/"turn-01/final-dialogue.json")[-1]["text"], "One reply is complete.")


if __name__ == "__main__":
    unittest.main()
