import copy
import json
from pathlib import Path
import tempfile
from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import compare
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.contribution_session import ContributionSession
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes


class EffortComparisonTests(unittest.TestCase):
    def test_paired_inputs_only_change_effort_and_its_exact_native_paragraph(self):
        view = compare.task.initial_session().view()
        for x, m in ((0, 1), (3, 2)):
            control, variant = compare.Adapter(compare.SCHEDULE[x]), compare.Adapter(compare.SCHEDULE[m])
            old, new = control.request_for(view), variant.request_for(view)
            expected = copy.deepcopy(old)
            expected["chat_template_kwargs"]["reasoning_effort"] = "medium"
            self.assertEqual(new, expected)
            self.assertEqual(new["messages"], old["messages"])
            self.assertEqual(new["response_format"], old["response_format"])
            self.assertEqual(control.expected_native(old).replace((compare.XHIGH+"\n\n").encode(), b"", 1),
                             variant.expected_native(new))
            self.assertTrue(variant.expected_native(new).endswith(b"<|im_start|>assistant\n<think>\n"))
            self.assertTrue(all(new[k] == -1 for k in ("max_tokens", "n_predict", "thinking_budget_tokens", "reasoning_budget_tokens")))

    def test_undeclared_effort_seed_or_output_cap_is_rejected(self):
        for effort in ("high", "low", "max"):
            with self.assertRaisesRegex(ValueError, "undeclared"):
                compare.Adapter(dict(id="A01", seed=961208, effort=effort))
        adapter = compare.Adapter(compare.SCHEDULE[1])
        request = adapter.request_for(compare.task.initial_session().view())
        request["max_tokens"] = 512
        with self.assertRaisesRegex(ValueError, "drift"):
            adapter.expected_native(request)
        request = adapter.request_for(compare.task.initial_session().view())
        request["seed"] += 1
        with self.assertRaisesRegex(ValueError, "drift"):
            adapter.expected_native(request)

    def test_fresh_sessions_share_saved_start_but_not_working_state(self):
        one, two = compare.task.initial_session(), compare.task.initial_session()
        self.assertEqual(one.candidate, two.candidate)
        self.assertEqual(one.pairs, two.pairs)
        one.add_source(one.source(dict(path="Lib/configparser.py", start_line=299, end_line=341)))
        self.assertEqual(two.sources(), [])
        self.assertFalse(two.check_state()["applies_to_current"])
        self.assertEqual(two.calls_used, 0)
        self.assertEqual(two.call_limit, 24)
        self.assertEqual(compare.Adapter(compare.SCHEDULE[0]).MAX_REQUESTS, 16)

    def test_both_efforts_deliver_paired_results_without_thinking_or_coaching(self):
        for row in compare.SCHEDULE[:2]:
            with self.subTest(effort=row["effort"]), tempfile.TemporaryDirectory() as name:
                folder = Path(name)
                adapter = compare.Adapter(row)
                session = ContributionSession(Candidate.create({"app.py": b"value = 1\n"}),
                    b"from app import value\nassert value == 2\n", "Save checked work.", call_limit=24)
                sent = []
                def render(request, stem):
                    raw = adapter.expected_native(request)
                    return canonical_json_bytes(dict(prompt=raw.decode())), raw, canonical_json_bytes(dict(tokens=[0]*1000)), 1000
                def post(url, route, wire, timeout):
                    self.assertEqual(route, "/v1/chat/completions")
                    self.assertNotIn(b"PRIVATE_REASONING", wire)
                    self.assertNotIn(b"MODEL_DISCUSSION", wire)
                    request = json.loads(wire)
                    self.assertEqual(wire, completion_request_bytes(adapter.request_for(session.view())))
                    self.assertEqual(request["chat_template_kwargs"]["reasoning_effort"], row["effort"])
                    state = json.loads(request["messages"][1]["content"])
                    self.assertEqual(set(state), {"workspace", "preceding_operation_feedback"})
                    sent.append(request)
                    if len(sent) == 1:
                        reply = dict(discussion="MODEL_DISCUSSION", operation=dict(action="read", path="app.py", start_line=1, end_line=0))
                    elif len(sent) == 2:
                        reply = dict(discussion="MODEL_DISCUSSION", operation=dict(action="patch", path="app.py",
                            old="value = 1\n", new="value = 2\n", expected_candidate_id=session.candidate.candidate_id,
                            expected_file_sha256=session.candidate.file_sha256("app.py")), check_after="public")
                    else:
                        edit = state["preceding_operation_feedback"][0]["result"]
                        checked = state["workspace"]["latest_feedback"]["result"]
                        self.assertTrue(checked["passed"])
                        self.assertEqual(edit["candidate_id"], checked["checked_candidate_id"])
                        self.assertEqual(state["workspace"]["working_set"]["sources"][0]["content"], "value = 2\n")
                        reply = dict(discussion="MODEL_DISCUSSION", operation=dict(action="submit", expected_candidate_id=session.candidate.candidate_id))
                    return canonical_json_bytes(dict(choices=[dict(finish_reason="stop", message=dict(
                        content=json.dumps(reply), reasoning_content="PRIVATE_REASONING"))],
                        usage=dict(prompt_tokens=1000, completion_tokens=100, total_tokens=1100,
                                   prompt_tokens_details=dict(cached_tokens=0)), timings=dict(cache_n=0)))
                loop = compare.prior.Loop(folder, ArtifactStore(folder), compare.Log(folder/"records.jsonl", "offline", row, scripted=True),
                    task_module=adapter, render=render, post=post, health=lambda: {}, source_check=lambda: None)
                outcome = loop.execute(session)
                self.assertTrue(outcome["submitted"])
                self.assertEqual((len(sent), outcome["actual_operations"]), (3, 4))
                self.assertTrue(all(not r["payload"].get("completion_sent") for r in verify_records(folder/"records.jsonl", folder)))

    def test_native_preparation_only_routes_to_rendering_and_tokenization(self):
        with tempfile.TemporaryDirectory() as name:
            adapter = compare.Adapter(compare.SCHEDULE[1])
            folder, routes = Path(name), []
            request = adapter.request_for(compare.task.initial_session().view())
            def post(url, route, raw, timeout):
                routes.append(route)
                if route == "/apply-template":
                    return canonical_json_bytes(dict(prompt=adapter.expected_native(json.loads(raw)).decode()))
                self.assertEqual(route, "/tokenize")
                return canonical_json_bytes(dict(tokens=[0]*1000))
            with patch.object(compare.RUNTIME, "post", post):
                loop = compare.prior.Loop(folder, ArtifactStore(folder), compare.Log(folder/"records.jsonl", "render", compare.SCHEDULE[1], scripted=True),
                    task_module=adapter, health=lambda: {}, source_check=lambda: None)
                self.assertEqual(loop.measure(compare.task.initial_session().view()), 1000)
            self.assertEqual(routes, ["/apply-template", "/tokenize"])

    def test_schedule_is_counterbalanced_and_existing_comparison_is_not_retried(self):
        self.assertEqual([r["effort"] for r in compare.SCHEDULE], ["xhigh", "medium", "medium", "xhigh"])
        self.assertEqual([r["seed"] for r in compare.SCHEDULE], [961208, 961208, 961209, 961209])
        with tempfile.TemporaryDirectory() as name, patch.object(compare, "RUN", Path(name)), \
             patch.object(compare, "verify_package", return_value={}):
            with self.assertRaisesRegex(ValueError, "no retry"):
                compare.execute()

    def test_operator_stop_with_final_submission_does_not_start_another_attempt(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)/"run"
            manifest = Path(name)/"manifest.json"
            manifest.write_text("{}")
            def run(folder, row, manifest):
                folder.mkdir()
                (folder/"STOP_REQUEST.txt").write_text("Stop after this response")
                return dict(disposition="checked_submission")
            with patch.object(compare, "RUN", root), patch.object(compare, "MANIFEST", manifest), \
                 patch.object(compare, "verify_package", return_value=dict(source_sha256={})), \
                 patch.object(compare, "run_attempt", side_effect=run) as invoked:
                compare.execute()
                self.assertEqual(invoked.call_count, 1)
                self.assertEqual(compare.task.read(root/"SEAL.json")["status"], "stopped")

    def test_incomplete_response_closes_and_preserves_without_an_operation(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            manifest_path = root/"manifest.json"
            manifest_path.write_text("{}")
            row = compare.SCHEDULE[1]
            @contextmanager
            def runtime(args, store, log):
                try:
                    yield "offline"
                finally:
                    log.append("runtime_closed", dict(owned_server_shutdown_verified=True), [])
            def render(loop, request, stem):
                raw = loop.task.expected_native(request)
                return canonical_json_bytes(dict(prompt=raw.decode())), raw, canonical_json_bytes(dict(tokens=[0]*1000)), 1000
            def post(url, route, raw, timeout):
                self.assertEqual(route, "/v1/chat/completions")
                return canonical_json_bytes(dict(choices=[dict(finish_reason="length", message=dict(
                    reasoning_content="Unfinished", content=""))],
                    usage=dict(prompt_tokens=1000, completion_tokens=55576, total_tokens=56576)))
            manifest = dict(source_sha256={}, cases=[dict(id=row["id"], initial={})])
            with patch.object(compare, "MANIFEST", manifest_path), \
                 patch.object(compare.task, "runtime_paths", return_value=(Path("server"), Path("model"), None)), \
                 patch.object(compare.RUNTIME, "owned_runtime", runtime), patch.object(compare.RUNTIME, "post", post), \
                 patch.object(compare.task.base.pilot, "health", return_value={}), \
                 patch.object(compare.prior.Loop, "native_render", render):
                result = compare.run_attempt(root/"attempt", row, manifest)
            self.assertEqual(result["disposition"], "model_or_allowance_boundary")
            self.assertEqual((result["sent_requests"], result["returned_responses"], result["actual_operations"]), (1, 1, 0))
            self.assertTrue((root/"attempt/calls/C01-assistant-reasoning.txt").is_file())
            self.assertTrue((root/"attempt/stopped-candidate.json").is_file())
            self.assertEqual(compare.verify_seal(root/"attempt")["record_count"], len(verify_records(root/"attempt/records.jsonl", root/"attempt")))


if __name__ == "__main__":
    unittest.main()
