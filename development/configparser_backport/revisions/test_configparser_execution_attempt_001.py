import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import configparser_backport as task
import configparser_work as work
import prepare_configparser_inputs as prep
import run_configparser_backport as run
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes


def fake_render(url, request, count=1000):
    native = ("mock-native:" + sha256_bytes(canonical_json_bytes(request))).encode()
    return canonical_json_bytes({"prompt": native.decode()}), native, canonical_json_bytes({"tokens": [0]*count}), count


def answer(request, action, *, count=1000, generated=100, finish="stop"):
    return canonical_json_bytes(dict(choices=[dict(finish_reason=finish,
        message=dict(reasoning_content="Mock private explanation never carried forward.",
                     content=canonical_json_bytes(action).decode()))],
        usage=dict(prompt_tokens=count, completion_tokens=generated, total_tokens=count+generated,
                   prompt_tokens_details=dict(cached_tokens=0)), timings=dict(cache_n=0)))


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="configparser-runner-test-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def loop(self, *, post=None, render=fake_render, source_check=lambda: None):
        value = new_state("initial", task.fixture())
        request = work.request_for(value)
        _, native, _, count = render("offline", request)
        plan = dict(initial_request_sha256=sha256_bytes(canonical_json_bytes(request)),
                    initial_native_sha256=sha256_bytes(native), initial_prompt_tokens=count)
        self.requests = []
        def send(url, route, raw, timeout):
            self.assertEqual(route, "/v1/chat/completions")
            req = load_json_strict(raw)
            self.requests.append(req)
            if post:
                return post(req)
            state = load_json_strict(req["messages"][1]["content"].encode())
            return answer(req, dict(action="submit", expected_candidate_id=state["candidate_id"]))
        store, log = ArtifactStore(self.folder), run.RunLog(self.folder / "records.jsonl", "mock-configparser")
        loop = run.Loop(plan, self.folder, store, log, post=send, render=render,
                        health=lambda: {}, source_check=source_check)
        return value, loop

    def records(self):
        return verify_records(self.folder / "records.jsonl", self.folder)

    def test_exact_initial_task_and_settings_without_oracle(self):
        value, loop = self.loop()
        request = work.request_for(value)
        self.assertEqual(canonical_json_bytes(request), (run.PACKAGE / "initial-request.json").read_bytes())
        self.assertEqual([m["role"] for m in request["messages"]], ["system", "user"])
        self.assertEqual(request["seed"], 961207)
        for name in ("max_tokens", "n_predict", "thinking_budget_tokens", "reasoning_budget_tokens"):
            self.assertEqual(request[name], -1)
        self.assertEqual(request["chat_template_kwargs"], dict(enable_thinking=True, reasoning_effort="xhigh"))
        self.assertEqual(len(value.state.candidate.files), 10)
        self.assertEqual(value.state.candidate.max_file_bytes, 1_048_576)
        self.assertEqual(sum(len(b) for _, b in value.state.candidate.files), 337239)
        state = load_json_strict(request["messages"][1]["content"].encode())
        self.assertEqual(state["resource_state"], dict(call_limit=40, calls_used=0, calls_remaining=40, reasoning_budget_tokens=-1))
        self.assertEqual(state["active_phase_event_frame"]["events"], [])
        self.assertIn("1,048,576 bytes", request["messages"][0]["content"])
        for edit in task.read(task.AREA / "REFERENCE_EDITS.json")["rows"]:
            self.assertNotIn(edit["new"], request["messages"][1]["content"])

    def test_real_grammar_rejects_old_reference_and_accepts_split_route(self):
        value, _ = self.loop()
        request = work.request_for(value)
        edits = task.read(task.AREA / "REFERENCE_EDITS.json")["rows"]
        old = edits[1]
        action = dict(action="patch", **old, expected_candidate_id=value.state.candidate.candidate_id,
                      expected_file_sha256=value.state.candidate.file_sha256(old["path"]))
        with self.assertRaisesRegex(ValueError, "supplied bound"):
            run.host.validate_action(action, request)
        for _, _, edit in prep.schema_edits(edits):
            action.update(edit)
            run.host.validate_action(action, request)

    def test_complete_runner_uses_all_qualified_native_inputs_and_actual_tools(self):
        q = task.read(run.PACKAGE / "QUALIFICATION.json")
        route = next(r for r in q["routes"] if r["kind"] == "focused")
        rendered = {}
        for row in [q["initial"], *route["native_attempts"]]:
            native = (run.PACKAGE / (row["stem"] + "-native.txt")).read_bytes()
            rendered[row["request_sha256"]] = native, row["prompt_tokens"]
        def render(url, request):
            native, count = rendered[sha256_bytes(canonical_json_bytes(request))]
            return canonical_json_bytes({"prompt": native.decode()}), native, canonical_json_bytes({"tokens": [0]*count}), count
        def post(request):
            index = len(self.requests)-1
            row = route["rows"][index]
            self.assertEqual(sha256_bytes(canonical_json_bytes(request)), row["selected_request_sha256"])
            self.assertNotIn("Mock private explanation", canonical_json_bytes(request).decode())
            return answer(request, row["action"], count=row["prompt_tokens"])
        _, loop = self.loop(post=post, render=render)
        result = loop.execute()
        self.assertEqual(result["sent_requests"], route["operations"])
        self.assertTrue(result["submitted"] and result["current_public_check_passed"])
        self.assertEqual(result["final_candidate"], route["final_candidate"])
        original_pairs = task.read(run.PACKAGE / "routes/focused/pairs.json")
        self.assertEqual(task.read(self.folder / "final-snapshot.json")["pairs"], original_pairs)
        records = self.records()
        self.assertEqual(sum(r["record_type"] == "invocation_started" for r in records), route["operations"])
        self.assertTrue(all(r["payload"]["latest_result_delivered"] for r in records if r["record_type"] == "delivery_assessed"))
        self.assertGreater(loop.prefix, 0)

    def test_submission_without_pass_is_recorded_without_new_stopping_policy(self):
        _, loop = self.loop()
        result = loop.execute()
        self.assertEqual(result["disposition"], "submitted_without_current_public_check")
        self.assertEqual(len(self.requests), 1)

    def test_rejected_guard_is_actual_next_input_feedback(self):
        def post(request):
            state = load_json_strict(request["messages"][1]["content"].encode())
            if len(self.requests) == 1:
                action = dict(action="check", check_id="public", expected_candidate_id="0"*64)
            else:
                event = state["active_phase_event_frame"]["events"][-1]
                self.assertFalse(event["result"]["accepted"])
                self.assertEqual(state["resource_state"]["calls_remaining"], 39)
                action = dict(action="submit", expected_candidate_id=state["candidate_id"])
            return answer(request, action)
        _, loop = self.loop(post=post)
        result = loop.execute()
        self.assertEqual(result["sent_requests"], 2)

    def test_forty_call_allowance_does_not_silently_expand(self):
        _, loop = self.loop(post=lambda req: answer(req, dict(action="tree", path=".", offset=0, limit=1)))
        result = loop.execute()
        self.assertEqual(result["disposition"], "action_allowance_exhausted")
        self.assertEqual(len(self.requests), 40)
        self.assertFalse(result["submitted"])

    def test_incomplete_output_is_preserved_without_execution_or_retry(self):
        _, loop = self.loop(post=lambda req: answer(req, dict(action="tree", path=".", offset=0, limit=1), finish="length"))
        with self.assertRaisesRegex(ValueError, "incomplete output"):
            loop.execute()
        self.assertEqual(len(self.requests), 1)
        self.assertTrue((self.folder / "calls/C01-endpoint-response.json").is_file())
        self.assertIn("Mock private explanation", (self.folder / "calls/C01-assistant-reasoning.txt").read_text())
        self.assertFalse(task.read(self.folder / "calls/C01-host-result.json")["executed"])

    def test_out_of_grammar_output_executes_no_action(self):
        _, loop = self.loop(post=lambda req: answer(req, dict(action="read", path="Lib/configparser.py", start_line=1, line_count=10)))
        with self.assertRaisesRegex(ValueError, "action keys differ"):
            loop.execute()
        self.assertEqual(len(self.requests), 1)
        self.assertFalse(task.read(self.folder / "calls/C01-host-result.json")["executed"])
        self.assertTrue(any(r["record_type"] == "action_schema_stop" for r in self.records()))

    def test_native_drift_prevents_first_completion(self):
        _, loop = self.loop()
        loop.plan["initial_native_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "initial input differs"):
            loop.execute()
        self.assertEqual(self.requests, [])

    def test_source_change_after_response_preserves_output_without_execution(self):
        changed = False
        def source_check():
            if changed:
                raise ValueError("mock source drift")
        def post(req):
            nonlocal changed
            changed = True
            return answer(req, dict(action="tree", path=".", offset=0, limit=1))
        _, loop = self.loop(post=post, source_check=source_check)
        with self.assertRaisesRegex(ValueError, "source drift"):
            loop.execute()
        self.assertEqual(len(self.requests), 1)
        self.assertTrue((self.folder / "calls/C01-assistant-reasoning.txt").is_file())
        self.assertFalse(task.read(self.folder / "calls/C01-host-result.json")["executed"])

    def test_transport_failure_preserves_received_prefix_and_stops(self):
        def post(req):
            raise run.base.ResponseFailure("mock disconnect", b"partial-response", 503)
        _, loop = self.loop(post=post)
        with self.assertRaises(run.base.ResponseFailure):
            loop.execute()
        self.assertEqual(len(self.requests), 1)
        self.assertEqual((self.folder / "calls/C01-transport-body.bin").read_bytes(), b"partial-response")

    def test_withheld_latest_read_is_a_capacity_stop_not_a_next_decision(self):
        value, loop = self.loop()
        self.assertTrue(value.execute(dict(action="read", path="Lib/configparser.py", start_line=1))["accepted"])
        loop.sent = 1
        def render(url, request):
            state = load_json_strict(request["messages"][1]["content"].encode())
            prefix = state["active_phase_event_frame"]["externalized_payload_through_sequence"]
            return fake_render(url, request, count=1000 if prefix else work.INPUT_CEILING+1)
        loop.render = render
        self.assertIsNone(loop.prepare(value))
        self.assertEqual(self.requests, [])
        self.assertTrue(any(r["record_type"] == "immediate_feedback_withheld" for r in self.records()))

    def test_generation_reserve_is_selected_policy_not_inherited_helper(self):
        _, loop = self.loop(post=lambda req: answer(req,
            dict(action="submit", expected_candidate_id=load_json_strict(req["messages"][1]["content"].encode())["candidate_id"]),
            generated=25000))
        loop.execute()
        row = next(r["payload"] for r in self.records() if r["record_type"] == "invocation_completed")
        self.assertEqual(row["selected_generation_reserve"], 32768)
        self.assertTrue(row["within_proposed_generation_reserve"])
        self.assertFalse(row["runtime_helper_within_proposed_generation_reserve"])


if __name__ == "__main__":
    unittest.main()
