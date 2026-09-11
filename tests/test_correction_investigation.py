"""Qualify episode framing across actual tool feedback with mocked inference."""
import argparse
from contextlib import contextmanager, nullcontext
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "scripts"))
import prepare_correction_investigation as prep
import run_correction_investigation as run
from test_investigation_loop import mocked_render, model_reply
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.interface_consultation import new_state
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import canonical_json_bytes,load_json_strict,sha256_bytes


class CorrectionInvestigationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.folder,self.output=self.root / "package",self.root / "run"
        self.folder.mkdir(); self.output.mkdir()
        self.selected=prep.constructed_fixture()
        value=new_state("R01",self.selected)
        self.reference=prep.pilot.tool_reference(prep.pilot.grammar_for(value))
        request=prep.request_for(value,self.reference)
        _,native,_,count=mocked_render("mock",request)
        (self.folder / "initial").mkdir()
        for name,raw in (("candidate.json",prep.pilot.reference.candidate_bytes(self.selected.initial)),("TASK.txt",self.selected.task.encode()),
                         ("PUBLIC_CHECK.py",self.selected.public_checker),("TOOL_REFERENCE.txt",self.reference.encode()),
                         ("initial/R01-request.json",canonical_json_bytes(request))):
            (self.folder / name).write_bytes(raw)
        self.plan=dict(source_sha256=prep.source_identities(),initial=dict(stem="initial/R01",prompt_tokens=count,rendered_sha256=sha256_bytes(native)))
        self.store=ArtifactStore(self.output)
        self.log=prep.pilot.PilotLog(self.output / "records.jsonl","mock-correction")

    def execute(self,post,render=mocked_render):
        return run.execute(self.plan,self.folder,"mock",self.output,self.store,self.log,post=post,render=render,health=lambda:{"mock":True})

    def records(self):
        return verify_records(self.output / "records.jsonl",self.output)

    def test_complete_correction_loop_delivers_failures_successor_checks_and_annotation(self):
        paths=list(prep.qualification_paths(self.selected))
        self.assertEqual([len(p[1]) for p in paths],[17,20])
        snapshots=paths[1][1]
        inputs=[]
        def post(url,route,raw,timeout):
            self.assertEqual(route,"/v1/chat/completions")
            self.assertNotIn(b"PRIVATE_THINKING_SENTINEL",raw)
            request=load_json_strict(raw)
            self.assertEqual(request["seed"],prep.SEED)
            state=load_json_strict(request["messages"][1]["content"].encode())
            self.assertEqual(state["active_user_authored_step"]["episode_annotation"],prep.EPISODE_ANNOTATION)
            index=len(inputs); inputs.append(state)
            self.assertEqual(request,snapshots[index]["before_request"])
            return model_reply(request,snapshots[index]["action"])
        outcome=self.execute(post)
        self.assertEqual(outcome["disposition"],"submitted_with_current_public_check")
        self.assertEqual(len(inputs),20)
        self.assertFalse(inputs[1]["active_phase_event_frame"]["events"][-1]["result"]["passed"])
        self.assertFalse(inputs[16]["active_phase_event_frame"]["events"][-1]["result"]["passed"])
        self.assertTrue(inputs[19]["active_phase_event_frame"]["events"][-1]["result"]["passed"])
        decisions=[r["payload"] for r in self.records() if r["record_type"]=="next_turn_decision"]
        self.assertEqual(decisions[15]["check_opportunity"]["calls_remaining_after"],8)
        self.assertEqual(len(list((self.output / "payloads/R01").glob("RES-*.json"))),20)

    def test_initial_state_has_no_oracle_and_no_forced_check_or_navigation(self):
        request=load_json_strict((self.folder / "initial/R01-request.json").read_bytes())
        state=load_json_strict(request["messages"][1]["content"].encode())
        self.assertFalse(state["active_phase_event_frame"]["events"])
        self.assertNotIn(prep.TARGET,request["messages"][1]["content"])
        self.assertNotIn(prep.GOOD,request["messages"][1]["content"])
        self.assertTrue(all(request[k]==-1 for k in ("max_tokens","n_predict","thinking_budget_tokens","reasoning_budget_tokens")))
        def post(url,route,raw,timeout):
            r=load_json_strict(raw); s=load_json_strict(r["messages"][1]["content"].encode())
            return model_reply(r,dict(action="submit",expected_candidate_id=s["candidate_id"]))
        outcome=self.execute(post)
        self.assertEqual(outcome["actions"],1)
        self.assertEqual(outcome["disposition"],"submitted_without_current_public_check")

    def test_rejections_do_not_extend_allowance(self):
        def post(url,route,raw,timeout):
            return model_reply(load_json_strict(raw),dict(action="read",path="missing.py",start_line=1))
        outcome=self.execute(post)
        self.assertEqual(outcome["actions"],24)
        self.assertEqual(outcome["disposition"],"action_allowance_exhausted")

    def test_capacity_denial_preserves_unsent_input_without_losing_annotation(self):
        def render(url,request):
            result=mocked_render(url,request)
            state=load_json_strict(request["messages"][1]["content"].encode())
            return (*result[:3],prep.INPUT_CEILING+1) if state["active_phase_event_frame"]["events"] else result
        def post(url,route,raw,timeout):
            return model_reply(load_json_strict(raw),dict(action="read",path="README.md",start_line=1))
        outcome=self.execute(post,render)
        self.assertEqual(outcome["actions"],1)
        self.assertEqual(outcome["disposition"],"native_input_capacity_denied")
        saved=load_json_strict((self.output / "calls/R01-002-endpoint-request.json").read_bytes())
        self.assertIn(prep.EPISODE_ANNOTATION,saved["messages"][1]["content"])
        self.assertEqual(sum(r["record_type"]=="invocation_started" for r in self.records()),1)

    def test_source_drift_and_missing_approval_block_dispatch(self):
        post=mock.Mock(side_effect=AssertionError("must not dispatch"))
        with mock.patch.object(prep,"source_identities",side_effect=[self.plan["source_sha256"],{}]):
            with self.assertRaisesRegex(ValueError,"source changed after rendering"):
                self.execute(post)
        post.assert_not_called()
        with mock.patch.object(run.base,"owned_runtime") as runtime:
            with self.assertRaisesRegex(ValueError,"owner execution instruction"):
                run.run_once(argparse.Namespace(owner_approval=""))
            runtime.assert_not_called()

    def test_partial_transport_is_preserved_without_execution(self):
        def post(*args):raise prep.base.ResponseFailure("interrupted",b'{"partial":')
        with self.assertRaises(prep.base.ResponseFailure):self.execute(post)
        self.assertEqual((self.output / "calls/R01-001-transport-body.bin").read_bytes(),b'{"partial":')
        self.assertFalse((self.output / "calls/R01-001-action.json").exists())

    def test_incomplete_output_is_saved_and_never_executed(self):
        def post(url,route,raw,timeout):
            return model_reply(load_json_strict(raw),dict(action="read",path="README.md",start_line=1),finish="length")
        with self.assertRaisesRegex(ValueError,"incomplete output"):self.execute(post)
        host=load_json_strict((self.output / "calls/R01-001-host-result.json").read_bytes())
        self.assertFalse(host["execution_attempted"])
        self.assertTrue((self.output / "calls/R01-001-endpoint-response.json").exists())
        self.assertFalse((self.output / "calls/R01-002-endpoint-request.json").exists())

    def test_failure_is_sealed_and_reserved_attempt_cannot_be_replaced(self):
        target=self.root / "reserved"
        args=argparse.Namespace(owner_approval="test-only mocked execution",package=self.folder,package_sha256="mock",
                                model=Path("mock.gguf"),server=Path("mock.exe"))
        (self.folder / "PACKAGE_MANIFEST.json").write_bytes(canonical_json_bytes(self.plan))
        with mock.patch.object(run,"RUN",target),mock.patch.object(run,"validate_package",return_value=self.plan),\
             mock.patch.object(run.base,"owned_runtime",return_value=nullcontext("mock")) as runtime,\
             mock.patch.object(run,"execute",side_effect=RuntimeError("mock failure")),\
             mock.patch.object(run.base,"running_process_ids",return_value=()),mock.patch.object(run.base,"port_free",return_value=True):
            with self.assertRaisesRegex(RuntimeError,"mock failure"):run.run_once(args)
            seal=load_json_strict((target / "RESPONSE_SEAL.json").read_bytes())
            self.assertEqual(seal["disposition"],"stopped_without_retry")
            self.assertEqual(seal["sent_requests"],0)
            with self.assertRaisesRegex(ValueError,"already reserved"):run.run_once(args)
            self.assertEqual(runtime.call_count,1)

    def test_preparation_routes_cannot_generate_and_package_tampering_is_rejected(self):
        routes=[]
        def post(url,route,raw,timeout):
            routes.append(route)
            self.assertIn(route,("/apply-template","/tokenize"))
            return canonical_json_bytes({"prompt":"mock native"}) if route=="/apply-template" else canonical_json_bytes({"tokens":[1,2]})
        real_render=prep.pilot.render_only
        args=argparse.Namespace(output=self.root / "prepared",model=Path("mock.gguf"),server=Path("mock.exe"))
        @contextmanager
        def runtime(args,store,log):
            yield "mock"
            log.append("runtime_closed",dict(owned_server_shutdown_verified=True,dedicated_port_free=True),[])
        with mock.patch.object(prep.base,"owned_runtime",side_effect=runtime),mock.patch.object(prep.pilot,"health",return_value={}),\
             mock.patch.object(prep.pilot,"render_only",side_effect=lambda url,request:real_render(url,request,post)):
            prep.prepare(args)
        self.assertEqual(len(routes),76)
        self.assertEqual(set(routes),{"/apply-template","/tokenize"})
        digest=prep.sha256_file(args.output / "PACKAGE_MANIFEST.json")
        self.assertEqual(run.validate_package(args.output,digest)["maximum_completion_calls"],24)
        (args.output / "TASK.txt").write_text("changed",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"prepared bytes differ"):run.validate_package(args.output,digest)

    def test_checker_distinguishes_decoding_selection_and_projection_and_rejects_partial_repairs(self):
        c=self.selected.initial
        original=run_checker(c,self.selected.public_checker)
        observations=[load_json_strict(line.encode()) for line in original["stdout"].splitlines()]
        cases={r["case"]:r for r in observations if "case" in r}
        self.assertFalse(original["passed"])
        for name in ("decoded sequence","selected receipts","quantity correction","older arrival"):
            self.assertTrue(cases[name]["passed"], name)
        for name in ("sequence report","depot correction","item correction","void with changed labels"):
            self.assertFalse(cases[name]["passed"], name)
        def modified(candidate,path,old,new):
            return candidate.patch(path=path,old=old,new=new,expected_candidate_id=candidate.candidate_id,
                                   expected_file_sha256=candidate.file_sha256(path))[0]
        self.assertFalse(run_checker(modified(c,prep.TARGET,prep.BAD,prep.PARTIAL),self.selected.public_checker)["passed"])
        correct=modified(c,prep.TARGET,prep.BAD,prep.GOOD)
        self.assertTrue(run_checker(correct,self.selected.public_checker)["passed"])
        clamped=modified(c,prep.TARGET,"self._units.get(destination, 0) + units","max(0, self._units.get(destination, 0) + units)")
        self.assertFalse(run_checker(clamped,self.selected.public_checker)["passed"])
        void_regression=modified(correct,"src/dispatchledger/reporting/entries.py",'if change.after.status == "active":','if True:')
        self.assertFalse(run_checker(void_regression,self.selected.public_checker)["passed"])

    def test_new_request_differs_only_in_frozen_seed_and_numerical_allowance(self):
        import copy
        from prepare_episode_framing import annotate
        value=new_state("comparison",self.selected)
        for index in range(4):
            previous=annotate(prep.pilot.request_for(value,prep.pilot.SEEDS[0],self.reference),report_precedes_session=True)
            current=prep.request_for(value,self.reference)
            expected=copy.deepcopy(previous)
            expected["seed"]=prep.SEED
            state=load_json_strict(expected["messages"][1]["content"].encode())
            state["resource_state"].update(call_limit=prep.CALL_LIMIT,calls_remaining=prep.CALL_LIMIT-index)
            expected["messages"][1]["content"]=canonical_json_bytes(state).decode()
            self.assertEqual(current,expected)
            value.execute(dict(action="read",path="README.md",start_line=1))


if __name__ == "__main__":unittest.main()
