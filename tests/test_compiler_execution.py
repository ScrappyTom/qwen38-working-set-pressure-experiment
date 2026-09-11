"""Mocked execution tests. No function in this module contacts a model endpoint."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext, redirect_stdout
from datetime import datetime
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "scripts"))
import run_compiler_incident as run
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


def request_key(request):
    normalized = dict(request)
    normalized["seed"] = run.task.SEEDS[0]
    return canonical_json_bytes(normalized)


def sealed_native_cache():
    cache = {}
    for path in run.PACKAGE.rglob("*-request.json"):
        stem = str(path).removesuffix("-request.json")
        request = load_json_strict(path.read_bytes())
        native = Path(stem+"-native.txt").read_bytes()
        template = Path(stem+"-template.json").read_bytes()
        tokenized = Path(stem+"-tokens.json").read_bytes()
        value = template,native,tokenized,len(load_json_strict(tokenized)["tokens"])
        key = request_key(request)
        if key in cache:
            assert cache[key] == value
        cache[key] = value
    return cache


def cached_renderer(cache):
    def render(url, request):
        assert url == "mock://no-network"
        return cache[request_key(request)]
    return render


def synthetic_renderer(count_for=lambda state:11):
    def render(url,request):
        state = load_json_strict(request["messages"][1]["content"].encode())
        count = count_for(state)
        native = canonical_json_bytes(request["messages"])
        return canonical_json_bytes({"prompt":native.decode()}),native,canonical_json_bytes({"tokens":[1]*count}),count
    return render


def plan_for_render(plan, fixture, render):
    plan = load_json_strict(canonical_json_bytes(plan))
    for cell in plan["schedule"]:
        request = run.initial_request(fixture,cell["seed"])
        _,native,_,count = render("mock://no-network",request)
        cell.update(initial_native_sha256=sha256_bytes(native),initial_prompt_tokens=count)
    return plan


def response(request, action, count, **changes):
    data = {"choices":[{"finish_reason":"stop","message":{"role":"assistant",
             "reasoning_content":"PRIVATE_REASONING_SENTINEL", "content":canonical_json_bytes(action).decode()}}],
            "usage":{"prompt_tokens":count,"completion_tokens":17,"total_tokens":count+17,
                     "prompt_tokens_details":{"cached_tokens":0}},
            "timings":{"cache_n":0,"prompt_n":count,"predicted_n":17}}
    for key,value in changes.items():
        if key == "finish":
            data["choices"][0]["finish_reason"] = value
        elif key == "content":
            data["choices"][0]["message"]["content"] = value
        elif key == "usage":
            data["usage"].update(value)
        else:
            data[key] = value
    return canonical_json_bytes(data)


def replay_action(request):
    """Test-only known actions from the sealed incremental-report capacity path."""
    state = load_json_strict(request["messages"][1]["content"].encode())
    frame = state["active_phase_event_frame"]
    used = len(frame["events"])
    external = frame["externalized_payload_through_sequence"] > 0
    if external and used == 6:
        return {"action":"reopen_observation","handle":"OBS-0001"}
    index = used if external else used+1
    return load_json_strict((run.PACKAGE / f"resident/report_incremental/{index:03d}-oracle.json").read_bytes())["action"]


def make_mocked_comparison(output, plan, *, render, action=replay_action, health=None, source_check=None):
    fixture = run.load_fixture()
    store = ArtifactStore(output)
    log = run.pilot.PilotLog(output / "records.jsonl","mock-compiler-comparison")
    def post(url,route,raw,timeout):
        assert url == "mock://no-network" and route == "/v1/chat/completions"
        assert b"PRIVATE_REASONING_SENTINEL" not in raw
        request = load_json_strict(raw)
        return response(request,action(request),render(url,request)[3])
    engine = run.Comparison(plan,fixture,"mock://no-network",output,store,log,post=post,render=render,
                            health=health or (lambda:{"mocked_health":True}),source_check=source_check)
    return engine,log


def rehearse(output):
    """Durable rehearsal uses real tools and saved native inputs, mocked answers."""
    plan = run.load_manifest()
    output.mkdir(parents=True,exist_ok=False)
    engine,log = make_mocked_comparison(output,plan,render=cached_renderer(sealed_native_cache()))
    results = engine.execute()
    records = verify_records(output / "records.jsonl",output)
    require = run.require
    require(engine.sent == 34 and len(results) == 2, "mocked trajectory count differs")
    require(all(cell["boundary_occurred"] and all(b["submitted"] and b["public_check_passed"] for b in cell["branches"])
                for cell in results), "mocked comparison did not finish")
    files = run.base.file_inventory(output)
    seal = dict(mocked_completion_responses=engine.sent,actual_model_completion_requests=0,runtime_launched=False,
        native_inputs="exact previously sealed render bytes matched to each reconstructed request; no new tokenization",
        execution_manifest_sha256=sha256_file(run.MANIFEST),test_source_sha256=sha256_file(Path(__file__)),
        cells=results,record_count=len(records),files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files)))
    run.base.write_json(output / "MOCK_REHEARSAL_SEAL.json",seal)
    return seal


class CompilerExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = run.proposed_manifest()
        cls.fixture = run.load_fixture()
        cls.cache = sealed_native_cache()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "output"
        self.output.mkdir()

    def engine(self, *, render=None, action=replay_action, plan=None, **kwargs):
        selected_render = render or cached_renderer(self.cache)
        selected_plan = plan or (plan_for_render(self.plan,self.fixture,selected_render) if render else self.plan)
        engine,log = make_mocked_comparison(self.output,selected_plan,render=selected_render,action=action,**kwargs)
        self.log = log
        return engine

    def execute(self, engine):
        with redirect_stdout(io.StringIO()):
            return engine.execute()

    def records(self):
        return verify_records(self.output / "records.jsonl",self.output)

    def test_real_native_replay_forks_once_per_seed_with_exact_recovery_and_current_check(self):
        engine = self.engine()
        cells = self.execute(engine)
        self.assertEqual(engine.sent,34)
        self.assertEqual([c["common"]["actions_total"] for c in cells],[6,6])
        self.assertEqual([[b["segment"] for b in c["branches"]] for c in cells],[list(run.CONDITIONS),list(reversed(run.CONDITIONS))])
        self.assertTrue(all(b["submitted"] and b["public_check_passed"] for c in cells for b in c["branches"]))
        self.assertEqual([[b["actions_total"] for b in c["branches"]] for c in cells],[[11,12],[12,11]])
        records = self.records()
        self.assertEqual(sum(r["record_type"]=="authentic_fork" for r in records),2)
        self.assertEqual(sum(r["record_type"]=="response_received" for r in records),34)
        for record in records:
            if record["record_type"] == "invocation_started":
                payload = record["payload"]
                request = load_json_strict((self.output/(payload["admission_stem"]+"-endpoint-request.json")).read_bytes())
                self.assertNotIn("PRIVATE_REASONING_SENTINEL",str(request))
                self.assertLessEqual(payload["prompt_tokens"],16000 if payload["segment"] != "R23808" else 23808)
        private = list((self.output / "calls").glob("*-assistant-reasoning.txt"))
        self.assertEqual(len(private),34)
        self.assertTrue(all(p.read_text()=="PRIVATE_REASONING_SENTINEL" for p in private))

    def test_early_unchecked_submission_creates_no_fork_or_forced_check(self):
        action = lambda request:{"action":"submit","expected_candidate_id":load_json_strict(request["messages"][1]["content"].encode())["candidate_id"]}
        engine = self.engine(render=synthetic_renderer(),action=action)
        results = self.execute(engine)
        self.assertEqual(engine.sent,2)
        self.assertTrue(all(not c["boundary_occurred"] and not c["branches"] for c in results))
        self.assertTrue(all(c["common"]["disposition"]=="submitted_without_current_public_check" for c in results))

    def test_ordinary_rejections_consume_the_full_shared_inclusive_allowance(self):
        def count(state):
            frame = state["active_phase_event_frame"]
            return 17000 if frame["events"] and frame["externalized_payload_through_sequence"] == 0 else 11
        engine = self.engine(render=synthetic_renderer(count),action=lambda _:dict(action="read",path="missing.py",start_line=1))
        results = self.execute(engine)
        self.assertEqual(engine.sent,126)
        self.assertTrue(all(c["common"]["actions_total"]==1 for c in results))
        self.assertTrue(all(b["actions_total"]==32 and b["requests_this_segment"]==31 and
                            b["disposition"]=="action_allowance_exhausted" for c in results for b in c["branches"]))
        self.assertTrue(all(r["payload"]["calls_remaining_before"]>=1 for r in self.records() if r["record_type"]=="invocation_started"))

    def test_signals_that_cannot_fit_stop_x_without_suppressing_fields(self):
        count = lambda state:17000 if state["active_phase_event_frame"]["events"] else 11
        def action(request):
            state = load_json_strict(request["messages"][1]["content"].encode())
            return dict(action="read",path="missing.py",start_line=1) if not state["active_phase_event_frame"]["events"] else dict(action="submit",expected_candidate_id=state["candidate_id"])
        engine = self.engine(render=synthetic_renderer(count),action=action)
        cells = self.execute(engine)
        self.assertEqual(engine.sent,4)
        for cell in cells:
            x = next(b for b in cell["branches"] if b["segment"]=="X16000")
            self.assertEqual(x["disposition"],"native_input_capacity_denied")
            self.assertEqual(x["requests_this_segment"],0)

    def test_resident_capacity_stop_does_not_prevent_admissible_x_branch(self):
        def count(state):
            frame = state["active_phase_event_frame"]
            return 25000 if frame["events"] and frame["externalized_payload_through_sequence"]==0 else 11
        def action(request):
            state = load_json_strict(request["messages"][1]["content"].encode())
            return dict(action="read",path="missing.py",start_line=1) if not state["active_phase_event_frame"]["events"] else dict(action="submit",expected_candidate_id=state["candidate_id"])
        engine = self.engine(render=synthetic_renderer(count),action=action)
        cells = self.execute(engine)
        self.assertEqual(engine.sent,4)
        self.assertTrue(all(next(b for b in c["branches"] if b["segment"]=="R23808")["disposition"]=="native_input_capacity_denied" for c in cells))

    def test_clone_preserves_passing_state_and_parent_independence(self):
        parent = run.new_state("parent",self.fixture)
        parent.state.public_check_passed = True
        child = run.clone(parent)
        self.assertTrue(child.state.public_check_passed)
        child.state.public_check_passed = False
        child.state.read_coverage["test.py"] = [(1,2)]
        self.assertTrue(parent.state.public_check_passed)
        self.assertNotIn("test.py",parent.state.read_coverage)

    def checked_route_engine(self, route, fork_after):
        # Synthetic sizes isolate branch state handling, not task capacity.
        def count(state):
            frame = state["active_phase_event_frame"]
            return 17000 if len(frame["events"]) >= fork_after and frame["externalized_payload_through_sequence"] == 0 else 11
        def action(request):
            state = load_json_strict(request["messages"][1]["content"].encode())
            index = len(state["active_phase_event_frame"]["events"])+1
            return load_json_strict((run.PACKAGE / f"resident/{route}/{index:03d}-oracle.json").read_bytes())["action"]
        return self.engine(render=synthetic_renderer(count),action=action)

    def test_passing_check_before_fork_remains_current_in_both_branches(self):
        engine = self.checked_route_engine("schema_informed_minimum",8)
        cells = self.execute(engine)
        self.assertEqual(engine.sent,20)
        self.assertTrue(all(c["common"]["public_check_passed"] and c["common"]["actions_total"]==8 for c in cells))
        self.assertTrue(all(b["requests_this_segment"]==1 and b["disposition"]=="submitted_with_current_public_check"
                            for c in cells for b in c["branches"]))
        checks = [r for r in self.records() if r["record_type"]=="next_turn_decision" and r["payload"]["check_opportunity"]]
        self.assertEqual(len(checks),2)  # The passing check is shared, never repeated by the runner.

    def test_failed_check_before_fork_allows_actual_repair_recheck_and_submission(self):
        engine = self.checked_route_engine("correction",9)
        cells = self.execute(engine)
        self.assertEqual(engine.sent,30)
        self.assertTrue(all(not c["common"]["public_check_passed"] and c["common"]["actions_total"]==9 for c in cells))
        self.assertTrue(all(b["requests_this_segment"]==3 and b["disposition"]=="submitted_with_current_public_check"
                            for c in cells for b in c["branches"]))
        checks = [r["payload"]["check_opportunity"] for r in self.records()
                  if r["record_type"]=="next_turn_decision" and r["payload"]["check_opportunity"]]
        failures = [c for c in checks if c["passed"] is False]
        self.assertEqual(len(failures),2)
        self.assertTrue(all(c["calls_remaining_before"]==24 and c["calls_remaining_after"]==23 and
                            c["patch_recheck_submit_fits_after_failure"] for c in failures))
        self.assertEqual(sum(c["passed"] is True for c in checks),4)

    def test_invalid_output_stops_after_exact_response_custody_without_tool_execution(self):
        engine = self.engine(render=synthetic_renderer(),action=lambda _:dict(action="read",path="compiler/unary.py",start_line=True))
        with self.assertRaisesRegex(ValueError,"argument type"):
            self.execute(engine)
        self.assertEqual(engine.sent,1)
        records = self.records()
        self.assertEqual(sum(r["record_type"]=="cell_started" for r in records),1)
        self.assertTrue(any(r["record_type"]=="action_schema_stop" for r in records))
        host = load_json_strict((self.output/"calls/C01-SHARED-001-host-result.json").read_bytes())
        self.assertFalse(host["executed"])
        self.assertTrue((self.output/"calls/C01-SHARED-001-endpoint-response.json").exists())

    def test_incomplete_output_is_never_executed_or_retried(self):
        engine = self.engine(render=synthetic_renderer())
        engine.post = lambda url,route,raw,timeout:response(load_json_strict(raw),dict(action="read",path="compiler/unary.py",start_line=1),11,finish="length")
        with self.assertRaisesRegex(ValueError,"incomplete output"):
            self.execute(engine)
        self.assertEqual(engine.sent,1)
        self.assertFalse(load_json_strict((self.output/"calls/C01-SHARED-001-host-result.json").read_bytes())["execution_attempted"])

    def test_invalid_total_usage_cannot_mutate_candidate(self):
        engine = self.engine(render=synthetic_renderer())
        engine.post = lambda url,route,raw,timeout:response(load_json_strict(raw),dict(action="read",path="compiler/unary.py",start_line=1),11,usage={"total_tokens":999})
        with self.assertRaisesRegex(ValueError,"total token accounting"):
            self.execute(engine)
        self.assertEqual(engine.sent,1)
        self.assertFalse(load_json_strict((self.output/"calls/C01-SHARED-001-host-result.json").read_bytes())["execution_attempted"])

    def test_transport_prefix_is_saved_and_later_cells_are_withheld(self):
        engine = self.engine(render=synthetic_renderer())
        def interrupted(*args):
            raise run.base.ResponseFailure("interrupted",b'{"partial":')
        engine.post = interrupted
        with self.assertRaises(run.base.ResponseFailure):
            self.execute(engine)
        self.assertEqual((self.output/"calls/C01-SHARED-001-transport-body.bin").read_bytes(),b'{"partial":')
        self.assertEqual(engine.sent,1)
        self.assertEqual(sum(r["record_type"]=="cell_started" for r in self.records()),1)

    def test_monitor_loss_after_response_preserves_it_without_executing(self):
        lost = False
        def health():
            if lost:
                raise ValueError("GPU monitoring is stale")
            return {"mocked":True}
        engine = self.engine(render=synthetic_renderer(),health=health)
        def post(url,route,raw,timeout):
            nonlocal lost
            lost = True
            return response(load_json_strict(raw),dict(action="read",path="compiler/unary.py",start_line=1),11)
        engine.post = post
        with self.assertRaisesRegex(ValueError,"monitoring is stale"):
            self.execute(engine)
        self.assertTrue((self.output/"calls/C01-SHARED-001-endpoint-response.json").exists())
        self.assertFalse(load_json_strict((self.output/"calls/C01-SHARED-001-host-result.json").read_bytes())["execution_attempted"])

    def test_source_change_during_response_stops_before_action(self):
        changed = False
        def source_check():
            if changed:
                raise ValueError("execution source changed while waiting")
        engine = self.engine(render=synthetic_renderer(),source_check=source_check)
        def post(url,route,raw,timeout):
            nonlocal changed
            changed = True
            return response(load_json_strict(raw),dict(action="read",path="compiler/unary.py",start_line=1),11)
        engine.post = post
        with self.assertRaisesRegex(ValueError,"source changed"):
            self.execute(engine)
        self.assertFalse(load_json_strict((self.output/"calls/C01-SHARED-001-host-result.json").read_bytes())["execution_attempted"])

    def test_source_change_after_render_prevents_completion(self):
        rendered = 0
        def render(url,request):
            nonlocal rendered
            rendered += 1
            return synthetic_renderer()(url,request)
        def source_check():
            if rendered >= 3:
                raise ValueError("execution source changed after rendering")
        engine = self.engine(render=render,source_check=source_check,
                             plan=plan_for_render(self.plan,self.fixture,synthetic_renderer()))
        engine.post = mock.Mock(side_effect=AssertionError("must not dispatch"))
        with self.assertRaisesRegex(ValueError,"after rendering"):
            self.execute(engine)
        engine.post.assert_not_called()

    def test_raw_invalid_native_response_is_preserved_before_parsing(self):
        engine = self.engine()
        engine.render = None
        engine.native_post = lambda *args:b'{"broken":'
        engine.post = mock.Mock(side_effect=AssertionError("must not dispatch"))
        with self.assertRaises(ValueError):
            self.execute(engine)
        self.assertEqual((self.output/"preflight/C01-PREFLIGHT-001-x000-template.json").read_bytes(),b'{"broken":')
        engine.post.assert_not_called()

    def test_native_transport_prefix_is_preserved_without_a_completion(self):
        engine = self.engine()
        engine.render = None
        def post(*args):
            raise run.base.ResponseFailure("native failure",b'partial template')
        engine.native_post = post
        with self.assertRaises(run.base.ResponseFailure):
            self.execute(engine)
        self.assertEqual(engine.sent,0)
        self.assertEqual((self.output/"preflight/C01-PREFLIGHT-001-x000-template-transport-body.bin").read_bytes(),b'partial template')

    def test_low_memory_remains_advisory_but_stale_sampling_stops(self):
        path = self.output / "memory.csv"
        sampled = datetime.now()
        path.write_text(sampled.strftime("%Y/%m/%d %H:%M:%S.%f")+",0,12000,11999,1\n")
        evidence = run.pilot.cont.monitoring(path,now=sampled.timestamp())
        self.assertTrue(evidence["reference_is_advisory"] and evidence["below_original_reference"])
        with self.assertRaisesRegex(ValueError,"stale"):
            run.pilot.cont.monitoring(path,now=sampled.timestamp()+6)

    def test_package_tampering_is_rejected_before_runtime(self):
        folder = self.output / "copied-preparation"
        shutil.copytree(run.PACKAGE,folder,ignore=shutil.ignore_patterns("private-runtime"))
        (folder/"captures.json").write_bytes(b"[]")
        with self.assertRaisesRegex(ValueError,"sealed preparation artifact"):
            run.verified_package(folder)

    def test_missing_approval_or_existing_attempt_prevents_runtime_launch(self):
        args = argparse.Namespace(owner_approval="",execution_sha256="unused",model=None,server=None)
        with mock.patch.object(run.base,"owned_runtime") as runtime:
            with self.assertRaisesRegex(ValueError,"owner execution approval"):
                run.run_once(args)
            manifest = self.output / "manifest.json"
            manifest.write_bytes(canonical_json_bytes(self.plan))
            args.owner_approval = "mock-only owner approval"
            args.execution_sha256 = sha256_file(manifest)
            with mock.patch.object(run,"MANIFEST",manifest),mock.patch.object(run,"load_manifest",return_value=self.plan),\
                 mock.patch.object(run,"RUN",self.output):
                with self.assertRaisesRegex(ValueError,"already reserved"):
                    run.run_once(args)
            runtime.assert_not_called()

    def test_failure_seals_reserved_attempt_without_retry(self):
        manifest = self.output / "manifest.json"
        manifest.write_bytes(canonical_json_bytes(self.plan))
        target = self.output / "reserved"
        args = argparse.Namespace(owner_approval="mock-only approval",execution_sha256=sha256_file(manifest),
                                  model=Path("mock.gguf"),server=Path("mock.exe"))
        with mock.patch.object(run,"MANIFEST",manifest),mock.patch.object(run,"load_manifest",return_value=self.plan),\
             mock.patch.object(run,"RUN",target),mock.patch.object(run.base,"owned_runtime",return_value=nullcontext("mock")),\
             mock.patch.object(run.Comparison,"execute",side_effect=RuntimeError("injected stop")),\
             mock.patch.object(run.base,"running_process_ids",return_value=[]),mock.patch.object(run.base,"port_free",return_value=True):
            with self.assertRaisesRegex(RuntimeError,"injected stop"):
                run.run_once(args)
        seal = load_json_strict((target/"RESPONSE_SEAL.json").read_bytes())
        self.assertEqual(seal["disposition"],"stopped_without_retry")
        self.assertEqual(seal["sent_requests"],0)
        self.assertEqual(len(list(self.output.glob("reserved*"))),1)

    def test_failed_runtime_shutdown_is_not_marked_completed(self):
        @contextmanager
        def runtime(args,store,log):
            try:
                yield "mock://no-network"
            finally:
                log.append("runtime_closed", {"owned_server_shutdown_verified":True,"dedicated_port_free":False}, [])
        manifest = self.output / "manifest.json"
        manifest.write_bytes(canonical_json_bytes(self.plan))
        target = self.output / "reserved"
        args = argparse.Namespace(owner_approval="mock-only approval",execution_sha256=sha256_file(manifest),
                                  model=Path("mock.gguf"),server=Path("mock.exe"))
        with mock.patch.object(run,"MANIFEST",manifest),mock.patch.object(run,"load_manifest",return_value=self.plan),\
             mock.patch.object(run,"RUN",target),mock.patch.object(run.base,"owned_runtime",runtime),\
             mock.patch.object(run.Comparison,"execute",return_value=[]),mock.patch.object(run.pilot,"health",return_value={}),\
             mock.patch.object(run.base,"running_process_ids",return_value=[]),mock.patch.object(run.base,"port_free",return_value=False):
            with self.assertRaisesRegex(ValueError,"lifecycle incomplete"):
                run.run_once(args)
        seal = load_json_strict((target/"RESPONSE_SEAL.json").read_bytes())
        self.assertEqual(seal["disposition"],"stopped_without_retry")
        self.assertEqual(seal["sent_requests"],0)


if __name__ == "__main__":
    unittest.main()
