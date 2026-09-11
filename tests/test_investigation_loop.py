"""Bounded multi-turn delivery and failure handling using mocked model endpoints."""
import argparse
from contextlib import nullcontext
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_investigation_loop as prep
import run_investigation_loop as run
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes


def mocked_render(url, request):
    native = canonical_json_bytes(request["messages"])
    return canonical_json_bytes({"prompt":native.decode()}), native, canonical_json_bytes({"tokens":[1]*11}), 11


def package(folder):
    selected = prep.constructed_fixture()
    value = new_state("initial", selected)
    text = prep.tool_reference(prep.grammar_for(value))
    folder.mkdir()
    for name, raw in (("candidate.json",prep.reference.candidate_bytes(selected.initial)),
                      ("TASK.txt",selected.task.encode()),("PUBLIC_CHECK.py",selected.public_checker),
                      ("TOOL_REFERENCE.txt",text.encode())):
        (folder / name).write_bytes(raw)
    rows = []
    for row in prep.schedule():
        req = prep.request_for(value,row["seed"],text)
        _,native,_,count = mocked_render("mock",req)
        stem = "initial/"+row["id"]
        (folder/"initial").mkdir(exist_ok=True)
        (folder/(stem+"-request.json")).write_bytes(canonical_json_bytes(req))
        rows.append({**row,"stem":stem,"prompt_tokens":count,"rendered_sha256":sha256_bytes(native)})
    return {"schedule":rows,"source_sha256":prep.source_identities()}


def model_reply(request, action, *, count=11, finish="stop", content=None):
    return canonical_json_bytes({"choices":[{"finish_reason":finish,"message":{"role":"assistant",
        "reasoning_content":"PRIVATE_THINKING_SENTINEL","content":content if content is not None else canonical_json_bytes(action).decode()}}],
        "usage":{"prompt_tokens":count,"completion_tokens":17,"total_tokens":count+17,"prompt_tokens_details":{"cached_tokens":0}},
        "timings":{"cache_n":0,"prompt_n":count,"predicted_n":17}})


def repair_action(state):
    events = state["active_phase_event_frame"]["events"]
    index = len(events)
    candidate = state["candidate_id"]
    if index == 0:
        return {"action":"read","path":prep.TARGET,"start_line":1}
    if index in (1,3):
        return {"action":"check","check_id":"public","expected_candidate_id":candidate}
    if index == 2:
        return {"action":"patch","path":prep.TARGET,"old":prep.BAD,"new":prep.GOOD,
                "expected_candidate_id":candidate,"expected_file_sha256":events[0]["result"]["file_sha256"]}
    return {"action":"submit","expected_candidate_id":candidate}


class InvestigationLoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / "package"
        self.plan = package(self.folder)
        self.output = self.root / "run"
        self.output.mkdir()
        self.store = ArtifactStore(self.output)
        self.log = prep.PilotLog(self.output/"records.jsonl","mock-pilot")

    def execute(self, post, render=mocked_render):
        return run.execute(self.plan,self.folder,"mock://no-network",self.output,self.store,self.log,
                           post=post,render=render,health=lambda:{"mocked":True})

    def records(self):
        return verify_records(self.output/"records.jsonl",self.output)

    def test_complete_loop_delivers_actual_results_and_isolates_runs_and_thinking(self):
        inputs = []
        def post(url,route,raw,timeout):
            self.assertEqual(route,"/v1/chat/completions")
            self.assertNotIn(b"PRIVATE_THINKING_SENTINEL",raw)
            request = load_json_strict(raw)
            state = load_json_strict(request["messages"][1]["content"].encode())
            inputs.append((request["seed"],state))
            events = state["active_phase_event_frame"]["events"]
            if len(events) == 2:
                self.assertTrue(events[-1]["result"]["accepted"])
                self.assertFalse(events[-1]["result"]["passed"])
            if len(events) == 3:
                self.assertEqual(events[-1]["result"]["candidate_id"],state["candidate_id"])
            return model_reply(request,repair_action(state))
        summaries = self.execute(post)
        self.assertEqual([r["actions"] for r in summaries],[5,5])
        self.assertTrue(all(r["submitted"] and r["public_check_passed"] for r in summaries))
        self.assertEqual(inputs[0][1],inputs[5][1])
        self.assertNotEqual(inputs[0][0],inputs[5][0])
        self.assertEqual([len(state["active_phase_event_frame"]["events"]) for _,state in inputs],list(range(5))*2)
        self.assertEqual((self.output/"calls/L01-001-assistant-reasoning.txt").read_text(),"PRIVATE_THINKING_SENTINEL")
        decisions = [r["payload"] for r in self.records() if r["record_type"]=="next_turn_decision"]
        self.assertEqual(decisions[1]["check_opportunity"]["calls_remaining_after"],18)
        self.assertEqual(len(list((self.output/"payloads/L01").glob("RES-*.json"))),5)

    def test_tool_rejections_consume_budget_and_cannot_extend_twenty_actions(self):
        requests = []
        def post(url,route,raw,timeout):
            request = load_json_strict(raw)
            requests.append(request)
            return model_reply(request,{"action":"read","path":"missing.py","start_line":1})
        summaries = self.execute(post)
        self.assertEqual(len(requests),40)
        self.assertEqual([r["disposition"] for r in summaries],["action_allowance_exhausted"]*2)
        final_state = load_json_strict(requests[19]["messages"][1]["content"].encode())
        self.assertEqual(final_state["resource_state"]["calls_remaining"],1)
        self.assertTrue(all(not e["result"]["accepted"] for e in final_state["active_phase_event_frame"]["events"]))

    def test_capacity_denial_saves_unsent_input_without_externalization(self):
        calls = []
        def render(url,request):
            result = mocked_render(url,request)
            state = load_json_strict(request["messages"][1]["content"].encode())
            if state["active_phase_event_frame"]["events"]:
                return (*result[:3],prep.INPUT_CEILING+1)
            return result
        def post(url,route,raw,timeout):
            request = load_json_strict(raw); calls.append(request)
            return model_reply(request,{"action":"read","path":prep.TARGET,"start_line":1})
        summaries = self.execute(post,render)
        self.assertEqual(len(calls),2)
        self.assertTrue(all(r["disposition"]=="native_input_capacity_denied" for r in summaries))
        blocked = load_json_strict((self.output/"calls/L01-002-endpoint-request.json").read_bytes())
        state = load_json_strict(blocked["messages"][1]["content"].encode())
        self.assertEqual(state["active_phase_event_frame"]["externalized_payload_through_sequence"],0)
        self.assertIn(prep.BAD,state["active_phase_event_frame"]["events"][0]["result_body"]["fields"]["content"])
        self.assertEqual(sum(r["record_type"]=="invocation_withheld" for r in self.records()),2)

    def test_unchecked_submission_ends_run_without_forced_check(self):
        def post(url,route,raw,timeout):
            request = load_json_strict(raw)
            state = load_json_strict(request["messages"][1]["content"].encode())
            return model_reply(request,{"action":"submit","expected_candidate_id":state["candidate_id"]})
        summaries = self.execute(post)
        self.assertEqual([r["actions"] for r in summaries],[1,1])
        self.assertTrue(all(r["disposition"]=="submitted_without_current_public_check" for r in summaries))

    def test_invalid_usage_preserves_response_without_executing_action(self):
        def post(url,route,raw,timeout):
            request = load_json_strict(raw)
            return model_reply(request,{"action":"read","path":prep.TARGET,"start_line":1},count=12)
        with self.assertRaisesRegex(ValueError,"prompt accounting mismatch"):
            self.execute(post)
        result = load_json_strict((self.output/"calls/L01-001-host-result.json").read_bytes())
        self.assertFalse(result["execution_attempted"])
        self.assertTrue((self.output/"calls/L01-001-endpoint-response.json").exists())
        self.assertFalse(any(r["record_type"]=="invocation_completed" for r in self.records()))

    def test_incomplete_output_is_preserved_and_not_executed(self):
        def post(url,route,raw,timeout):
            request = load_json_strict(raw)
            return model_reply(request,{"action":"read","path":prep.TARGET,"start_line":1},finish="length")
        with self.assertRaisesRegex(ValueError,"incomplete output"):
            self.execute(post)
        result = load_json_strict((self.output/"calls/L01-001-host-result.json").read_bytes())
        self.assertFalse(result["execution_attempted"])
        self.assertEqual(sum(r["record_type"]=="invocation_started" for r in self.records()),1)

    def test_partial_transport_is_preserved_and_second_run_is_withheld(self):
        def post(*args):
            raise prep.base.ResponseFailure("interrupted",b'{"partial":')
        with self.assertRaises(prep.base.ResponseFailure):
            self.execute(post)
        self.assertEqual((self.output/"calls/L01-001-transport-body.bin").read_bytes(),b'{"partial":')
        self.assertEqual(sum(r["record_type"]=="run_started" for r in self.records()),1)

    def test_source_drift_after_rendering_blocks_completion(self):
        post = mock.Mock(side_effect=AssertionError("must not dispatch"))
        with mock.patch.object(prep,"source_identities",side_effect=[self.plan["source_sha256"],{}]):
            with self.assertRaisesRegex(ValueError,"source changed after rendering"):
                self.execute(post)
        post.assert_not_called()

    def test_render_preparation_uses_only_template_and_tokenization_routes(self):
        routes = []
        def post(url,route,raw,timeout):
            routes.append(route)
            return canonical_json_bytes({"prompt":"native"}) if route=="/apply-template" else canonical_json_bytes({"tokens":[1,2]})
        self.assertEqual(prep.render_only("mock",{},post)[3],2)
        self.assertEqual(routes,["/apply-template","/tokenize"])

    def test_reference_and_request_keep_actual_bounds_and_no_procedural_example(self):
        value = new_state("check",prep.load_fixture(self.folder))
        grammar = prep.grammar_for(value)
        reference = prep.tool_reference(grammar)
        request = prep.request_for(value,prep.SEEDS[0],reference)
        state = load_json_strict(request["messages"][1]["content"].encode())
        self.assertNotIn(prep.wording.RESOURCE_KEY,state["resource_state"])
        self.assertEqual(state["resource_state"]["call_limit"],20)
        self.assertIn(prep.wording.NEW_NAVIGATION,request["messages"][0]["content"])
        self.assertIn("exact saved-result wrapper",reference)
        self.assertIn("signature above 240",reference)
        for option in grammar["json_schema"]["schema"]["oneOf"]:
            for key in option["required"]:
                self.assertIn("  "+key+": "+prep.reference.argument_form(option["properties"][key]),reference)
        self.assertTrue(all(request[k]==-1 for k in ("max_tokens","n_predict","thinking_budget_tokens","reasoning_budget_tokens")))

    def test_offline_discovery_and_correction_path_closes_with_remaining_actions(self):
        paths = list(prep.qualification_paths(prep.constructed_fixture()))
        self.assertEqual([len(p[1]) for p in paths],[10,17,18])
        checks = paths[1][2]
        self.assertEqual([c["sequence"] for c in checks],[11,13,16])
        self.assertEqual(checks[1]["calls_remaining_after"],7)
        self.assertTrue(checks[1]["patch_recheck_submit_fits_after_failure"])

    def test_missing_approval_and_existing_attempt_prevent_runtime_launch(self):
        args = argparse.Namespace(owner_approval="",package=self.folder,package_sha256="unused")
        with mock.patch.object(run.base,"owned_runtime") as runtime:
            with self.assertRaisesRegex(ValueError,"owner execution approval"):
                run.run_once(args)
            args.owner_approval = "test-only authorization for mocked endpoints"
            with mock.patch.object(run,"validate_package",return_value=self.plan),mock.patch.object(run,"RUN",self.output):
                with self.assertRaisesRegex(ValueError,"already reserved"):
                    run.run_once(args)
            runtime.assert_not_called()

    def test_package_hash_and_mutated_artifacts_are_rejected(self):
        (self.folder/"SPEC.md").write_bytes(prep.SPEC.read_bytes())
        log = prep.PilotLog(self.folder/"records.jsonl","mock-preparation")
        log.append("preparation_completed",{"completion_calls":0},[])
        plan = {**self.plan,"completion_calls":0,"execution_authorized":False,"actor":prep.ACTOR,
                "memory_policy":prep.cont.POLICY,"call_limit":prep.CALL_LIMIT,"maximum_completion_calls":40,
                "input_ceiling":prep.INPUT_CEILING,
                "history_policy":"all ordered events resident; private thinking omitted; no externalization",
                "qualification_paths":[{"path":name,"required_to_fit":required,"all_inputs_admitted":required}
                    for name,required in (("direct",True),("focused_correction",True),("explore_and_correct",False))],
                "files":[r for r in prep.base.file_inventory(self.folder) if r["path"] != "records.jsonl"]}
        raw = canonical_json_bytes(plan)
        (self.folder/"PACKAGE_MANIFEST.json").write_bytes(raw)
        files = prep.base.file_inventory(self.folder)
        seal = {"disposition":"prepared_without_completion","completion_calls":0,"files":files,
                "aggregate_sha256":sha256_bytes(canonical_json_bytes(files)),"record_count":1}
        (self.folder/"PREPARATION_SEAL.json").write_bytes(canonical_json_bytes(seal))
        self.assertEqual(run.validate_package(self.folder,sha256_bytes(raw)),plan)
        with self.assertRaisesRegex(ValueError,"approved package identity"):
            run.validate_package(self.folder,"0"*64)
        (self.folder/"TASK.txt").write_text("changed",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"artifact differs"):
            run.validate_package(self.folder,sha256_bytes(raw))

    def test_run_failure_is_sealed_and_does_not_reserve_a_replacement(self):
        target = self.root/"reserved"
        args = argparse.Namespace(owner_approval="test-only authorization for mocked endpoints",package=self.folder,
                                  package_sha256="mock",model=Path("mock.gguf"),server=Path("mock.exe"))
        (self.folder/"PACKAGE_MANIFEST.json").write_bytes(canonical_json_bytes(self.plan))
        with mock.patch.object(run,"RUN",target),mock.patch.object(run,"validate_package",return_value=self.plan),\
             mock.patch.object(run.base,"owned_runtime",return_value=nullcontext("mock")),\
             mock.patch.object(run,"execute",side_effect=RuntimeError("mock failure")),\
             mock.patch.object(run.base,"running_process_ids",return_value=()),mock.patch.object(run.base,"port_free",return_value=True):
            with self.assertRaisesRegex(RuntimeError,"mock failure"):
                run.run_once(args)
        seal = load_json_strict((target/"RESPONSE_SEAL.json").read_bytes())
        self.assertEqual(seal["disposition"],"stopped_without_retry")
        self.assertEqual(seal["sent_requests"],0)
        self.assertTrue((target/"records.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
