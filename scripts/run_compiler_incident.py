"""Freeze or execute the separately approved compiler pressure comparison once.

The live loader reads only the sealed candidate, task, checks and observations.
It does not import the compiler task's oracle builder or expected-report helper.
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
import re
import time

import prepare_incident_pressure as task
import run_interface_comparison as shared
import run_investigation_loop as payloads
from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.ecological_pilot_v2 import EcologicalFixture
from working_set_exp.event_frame_v3 import event_from_pair_v3, resident_pair_v3
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.measurement import check_opportunity

ROOT = task.ROOT
AREA = ROOT / "development/compiler_incident"
PACKAGE = AREA / "preparation-001"
RUN = AREA / "run-001"
SPEC = AREA / "EXECUTION_SPEC.md"
MANIFEST = AREA / "EXECUTION_MANIFEST.json"
TEST = ROOT / "tests/test_compiler_execution.py"
PACKAGE_SHA = "f63ec3dcb8115df53235f85acd3e4c644c16d7e3be46c9d1d0a7c2c675e2f3b2"
SEAL_SHA = "35a53de9d8ca5a1811d842378d309f291035d11172791ead0d59b3ee99fe9480"
REVIEW_SHA = "3e25b370dfeef9dec5544920c0c0c2a7605b6c54986f4f5ff8d4b844acd3e01c"
VERIFICATION_SHA = "e46a35cd85fdb214552d73acdf39aa13f4879f3889ee1f9ad4f68cecab464bc0"
MAX_COMPLETIONS = 128
CONDITIONS = ("R23808", "X16000")
require, base, pilot = task.require, task.base, task.pilot


def load_fixture(folder=PACKAGE):
    snapshot = load_json_strict((folder / "candidate.json").read_bytes())
    files = {row["path"]:row["content_utf8"].encode("utf-8") for row in snapshot["files"]}
    require(len(files) == len(snapshot["files"]), "duplicate candidate path")
    for row in snapshot["files"]:
        require(sha256_bytes(files[row["path"]]) == row["sha256"], "candidate file hash differs")
    candidate = Candidate.create(files)
    require(candidate.candidate_id == snapshot["candidate_id"], "candidate identity differs")
    observations = tuple(load_json_strict((folder / "observations.json").read_bytes()))
    captures = load_json_strict((folder / "captures.json").read_bytes())
    bodies = tuple((f"OBS-{i:04d}", canonical_json_bytes(record)) for i,record in enumerate(captures,1))
    require(len(observations) == len(bodies) == 3, "observation inventory differs")
    for row, (handle, raw) in zip(observations, bodies):
        require(row["handle"] == handle and row["sha256"] == sha256_bytes(raw) and row["size_bytes"] == len(raw)
                and row["candidate_id"] == candidate.candidate_id, "observation binding differs")
    return EcologicalFixture("COMPILER-INCIDENT", "captured_compiler_investigation", (folder / "TASK.txt").read_bytes().decode(),
                             candidate, (folder / "PUBLIC_CHECK.py").read_bytes(), b"", observations, bodies, {}, ())


def verified_package(folder=PACKAGE):
    require(sha256_file(folder / "PACKAGE_MANIFEST.json") == PACKAGE_SHA, "prepared package hash differs")
    require(sha256_file(folder / "PREPARATION_SEAL.json") == SEAL_SHA, "preparation seal hash differs")
    seal = load_json_strict((folder / "PREPARATION_SEAL.json").read_bytes())
    require(seal["disposition"] == "qualified_without_completion" and seal["completion_calls"] == 0, "preparation status differs")
    require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "preparation aggregate differs")
    for row in seal["files"]:
        raw = (folder / row["path"]).read_bytes()
        require(len(raw) == row["size_bytes"] and sha256_bytes(raw) == row["sha256"], "sealed preparation artifact differs: " + row["path"])
    require(len(verify_records(folder / "records.jsonl", folder)) == seal["record_count"], "preparation custody count differs")
    plan = load_json_strict((folder / "PACKAGE_MANIFEST.json").read_bytes())
    require(plan["actor"] == task.ACTOR and plan["prospective_seeds"] == list(task.SEEDS) and
            plan["prospective_call_limit"] == task.CALL_LIMIT and plan["working_set"] == task.WORKING_SET and
            plan["resident_ceiling"] == task.RESIDENT_CEILING, "prepared configuration differs")
    require(plan["task_geometry_qualified"] and plan["external_continuation"]["qualified"], "task continuation is unqualified")
    require(plan["completion_calls"] == 0 and plan["execution_authorized"] is False, "unexpected prepared execution status")
    for name,digest in plan["source_sha256"].items():
        require(sha256_file(ROOT / name) == digest, "prepared source changed: " + name)
    require(sha256_file(AREA / "PREPARATION_REVIEW.md") == REVIEW_SHA and
            sha256_file(AREA / "VERIFICATION.json") == VERIFICATION_SHA, "task review or verification changed")
    return plan


def initial_request(fixture, seed):
    value = new_state("initial", fixture)
    reference = pilot.tool_reference(pilot.grammar_for(value))
    return task.request_for(value, reference, seed=seed)


def proposed_manifest():
    prepared = verified_package()
    fixture = load_fixture()
    original = load_json_strict((PACKAGE / "resident/schema_informed_minimum/001-request.json").read_bytes())
    native = (PACKAGE / "resident/schema_informed_minimum/001-native.txt").read_bytes()
    count = len(load_json_strict((PACKAGE / "resident/schema_informed_minimum/001-tokens.json").read_bytes())["tokens"])
    schedule = []
    for index,seed in enumerate(task.SEEDS,1):
        request = initial_request(fixture, seed)
        expected = copy.deepcopy(original)
        expected["seed"] = seed
        require(request == expected, "initial task input differs from preparation")
        schedule.append(dict(id=f"C{index:02d}", seed=seed, branch_order=list(CONDITIONS if index == 1 else reversed(CONDITIONS)),
                             initial_request_sha256=sha256_bytes(canonical_json_bytes(request)),
                             initial_native_sha256=sha256_bytes(native), initial_prompt_tokens=count))
    sources = {**prepared["source_sha256"], **{p.relative_to(ROOT).as_posix():sha256_file(p)
               for p in (Path(__file__), SPEC, TEST)}}
    return dict(schema="compiler-pressure-execution-v1", package_sha256=PACKAGE_SHA, preparation_seal_sha256=SEAL_SHA,
        task_review_sha256=REVIEW_SHA, verification_sha256=VERIFICATION_SHA, execution_spec_sha256=sha256_file(SPEC),
        execution_source_sha256=sources, actor=task.ACTOR, memory_policy=pilot.cont.POLICY,
        working_set=task.WORKING_SET, resident_ceiling=task.RESIDENT_CEILING, call_limit=task.CALL_LIMIT,
        maximum_completion_requests=MAX_COMPLETIONS, schedule=schedule, preparation_completion_calls=0,
        requires_separate_owner_execution_decision=True, retries=0, automatic_successors=False,
        branch_binding_in_custody_only=True, initial_prompt_tokens=count)


def check_sources(plan):
    for relative,digest in plan["execution_source_sha256"].items():
        require(sha256_file(ROOT / relative) == digest, "execution source changed: " + relative)
    require(sha256_file(PACKAGE / "PACKAGE_MANIFEST.json") == plan["package_sha256"] and
            sha256_file(PACKAGE / "PREPARATION_SEAL.json") == plan["preparation_seal_sha256"], "preparation binding changed")


def load_manifest():
    plan = load_json_strict(MANIFEST.read_bytes())
    require(plan == proposed_manifest(), "frozen execution manifest differs")
    return plan


def validate_action(action, request):
    forms = request["response_format"]["json_schema"]["schema"]["oneOf"]
    matches = [f for f in forms if f["properties"]["action"].get("const") == action.get("action")]
    require(len(matches) == 1, "action is outside the supplied schema")
    form = matches[0]
    require(form["additionalProperties"] is False and set(action) == set(form["required"]) == set(form["properties"]),
            "action keys differ from the supplied schema")
    for name,value in action.items():
        rule = form["properties"][name]
        require(set(rule) <= {"type","const","enum","pattern","minimum","maximum","minLength","maxLength"},
                "unqualified schema constraint")
        require(rule["type"] in {"string","integer"} and type(value) is (str if rule["type"] == "string" else int),
                "action argument type differs")
        if "const" in rule:
            require(value == rule["const"], "action discriminator differs")
        if "enum" in rule:
            require(value in rule["enum"], "action value is outside its enumeration")
        if "pattern" in rule:
            require(re.fullmatch(rule["pattern"],value) is not None, "action argument pattern differs")
        for key in ("minimum","maximum","minLength","maxLength"):
            if key in rule:
                actual = len(value) if key.endswith("Length") else value
                require(actual >= rule[key] if key.startswith("min") else actual <= rule[key], "action argument exceeds its supplied bound")


def snapshot(value):
    return dict(candidate_id=value.state.candidate.candidate_id,
                session=load_json_strict(pilot.reference.session_bytes(value.state)), pairs=value.pairs,
                result_payloads={h:sha256_bytes(raw) for h,raw in value.result_payloads.items()},
                event_payloads={h:sha256_bytes(raw) for h,raw in value.event_payloads.items()})


def clone(value):
    result = copy.deepcopy(value)
    require(snapshot(result) == snapshot(value) and result.state is not value.state, "branch clone changed state")
    require(result.executor.state is result.state and result.executor.result_reopenable is result.result_payloads and
            result.executor.event_reopenable is result.event_payloads, "cloned executor maps are disconnected")
    require(result.executor.reopenable == value.executor.reopenable, "cloned observations differ")
    return result


class CheckedReceiver:
    def __init__(self, value, request, log, call_id):
        self.value, self.request, self.log, self.call_id = value,request,log,call_id
        self.state = value.state

    def execute(self, action):
        try:
            validate_action(action,self.request)
        except ValueError as error:
            self.log.append("action_schema_stop", {"id":self.call_id,"tool_execution_attempted":False,"error":str(error)}, [])
            raise
        return self.value.execute(action)


class Comparison:
    def __init__(self, plan, fixture, url, output, store, log, *, post=base.post, render=None,
                 native_post=base.post, health=None, source_check=None):
        self.plan, self.fixture, self.url, self.output, self.store, self.log = plan,fixture,url,output,store,log
        self.post, self.render, self.native_post = post,render,native_post
        self.health = health or (lambda:pilot.health(output))
        self.source_check = source_check or (lambda:check_sources(plan))
        self.reference = pilot.tool_reference(pilot.grammar_for(new_state("reference",fixture)))
        self.sent = 0

    def render_with_custody(self, request, stem):
        def post(url, route, raw, timeout):
            require(route in {"/apply-template","/tokenize"}, "unexpected native preparation endpoint")
            suffix = "template" if route == "/apply-template" else "tokens"
            self.log.append("native_request_started", {"route":route,"completion_sent":False},
                            [self.store.put(stem+"-"+suffix+"-request.json",raw)])
            try:
                response = self.native_post(url,route,raw,timeout)
            except base.ResponseFailure as error:
                self.log.append("native_transport_stopped", {"route":route,"error":str(error),"status":error.status,
                    "received_prefix_not_asserted_complete":True},
                    [self.store.put(stem+"-"+suffix+"-transport-body.bin",error.data)])
                raise
            self.log.append("native_response_received", {"route":route,"completion_sent":False},
                            [self.store.put(stem+"-"+suffix+".json",response)])
            return response
        return pilot.render_only(self.url,request,post=post)

    def probe(self, value, cell, segment, externalized, *, preflight=False):
        self.source_check()
        request = task.request_for(value,self.reference,externalized=externalized,seed=cell["seed"])
        raw = canonical_json_bytes(request)
        state = load_json_strict(request["messages"][1]["content"].encode())
        events = state["active_phase_event_frame"]["events"]
        expected = [event_from_pair_v3(pair["response"],pair["result"],sequence=i,
            payload_residency="external" if i<=externalized else "resident") for i,pair in enumerate(value.pairs,1)]
        require(events == expected and state["resource_state"]["calls_remaining"] == task.CALL_LIMIT-len(value.pairs),
                "next-input event delivery or allowance differs")
        for event,pair in zip(events[externalized:],value.pairs[externalized:]):
            require(resident_pair_v3(event) == pair, "resident result delivery differs")
        index = len(value.pairs)+1
        tag = f"{cell['id']}-{segment}-{index:03d}"
        stem = ("preflight/" if preflight else "admission/")+tag+f"-x{externalized:03d}"
        self.health()
        # Save the exact request before any external rendering/tokenization.
        self.log.append("input_reconstruction", {"id":tag,"externalized_through":externalized,"completion_sent":False},
                        [self.store.put(stem+"-endpoint-request.json",raw),
                         self.store.put(stem+"-candidate.json",pilot.reference.candidate_bytes(value.state.candidate)),
                         self.store.put(stem+"-session.json",pilot.reference.session_bytes(value.state))])
        template,native,tokens,count = self.render(self.url,request) if self.render else self.render_with_custody(request,stem)
        require(canonical_json_bytes(request) == raw, "renderer changed the request")
        require(load_json_strict(template)["prompt"].encode() == native and
                len(load_json_strict(tokens)["tokens"]) == count and count > 0, "native rendering/count evidence differs")
        self.source_check()
        self.health()
        row = dict(id=tag,cell_id=cell["id"],segment=segment,seed=cell["seed"],sequence=index,
                   calls_remaining_before=task.CALL_LIMIT-len(value.pairs),externalized_through=externalized,
                   prompt_tokens=count,native_input_sha256=sha256_bytes(native),endpoint_request_sha256=sha256_bytes(raw),
                   physical_generation_space=task.ACTOR["context"]-count,admission_stem=stem)
        native_artifacts = [self.store.put(stem+"-native.txt",native)]
        if self.render:
            native_artifacts += [self.store.put(stem+suffix,data) for suffix,data in (("-template.json",template),("-tokens.json",tokens))]
        self.log.append("native_input_prepared", {**row,"completion_sent":False}, native_artifacts)
        if not value.pairs:
            require(row["endpoint_request_sha256"] == cell["initial_request_sha256"] and
                    row["native_input_sha256"] == cell["initial_native_sha256"] and count == cell["initial_prompt_tokens"],
                    "initial native input differs from sealed preparation")
        return dict(request=request,raw=raw,row=row)

    def invoke(self, value, prepared, segment_key):
        row,request,raw = prepared["row"],prepared["request"],prepared["raw"]
        require(self.sent < self.plan["maximum_completion_requests"] and len(value.pairs) < task.CALL_LIMIT
                and not value.state.submitted, "completion allowance or terminal boundary reached")
        self.source_check()
        health = self.health()
        self.log.append("invocation_started", {**row,"completion_sent":True,**health}, [])
        self.sent += 1
        print(f"Starting {row['id']}: {row['prompt_tokens']} input; {row['calls_remaining_before']} actions remain",flush=True)
        started = time.monotonic()
        try:
            raw_response = self.post(self.url,"/v1/chat/completions",raw,base.HTTP_TIMEOUT_SECONDS)
        except base.ResponseFailure as error:
            self.log.append("transport_stopped", {"id":row["id"],"error":str(error),"status":error.status,
                "received_prefix_not_asserted_complete":True},
                [self.store.put("calls/"+row["id"]+"-transport-body.bin",error.data)])
            raise

        def after_response():
            # shared.receive_and_execute has already preserved raw and extracted
            # output before calling this guard and before any action execution.
            usage = load_json_strict(raw_response)["usage"]
            require(all(type(usage[k]) is int for k in ("prompt_tokens","completion_tokens","total_tokens")) and
                    usage["total_tokens"] == usage["prompt_tokens"]+usage["completion_tokens"], "total token accounting differs")
            self.source_check()
            return self.health()

        received_at = time.monotonic()
        outcome = shared.receive_and_execute(CheckedReceiver(value,request,self.log,row["id"]),row,raw_response,
                                             received_at-started,self.store,self.log,after_response)
        require(len(value.pairs) == row["sequence"], "response did not produce exactly one action")
        action,result = value.pairs[-1]["response"],value.pairs[-1]["result"]
        opportunity = check_opportunity(calls_used=len(value.pairs)-1,call_limit=task.CALL_LIMIT,result=result) if action["action"]=="check" else None
        self.log.append("next_turn_decision", {"id":row["id"],"calls_remaining_after":task.CALL_LIMIT-len(value.pairs),
            "response_processing_seconds":time.monotonic()-received_at,"check_opportunity":opportunity,
            "submitted":value.state.submitted,"next_step":"terminal" if value.state.submitted else "reconstruct_then_admit",
            "next_request_sent":False},payloads.save_payloads(value,segment_key,self.store))
        print(f"Completed {row['id']}: {outcome['usage']['completion_tokens']} output; {action['action']}; accepted={result.get('accepted')}",flush=True)

    def segment(self, value, cell, segment, *, prefix_actions=0):
        start,time_start = self.sent,time.monotonic()
        externalized = 0
        boundary = None
        disposition = "action_allowance_exhausted"
        while len(value.pairs) < task.CALL_LIMIT and not value.state.submitted:
            selected = None
            trials = range(externalized,len(value.pairs)+1) if segment == "X16000" else (0,)
            for removed in trials:
                prepared = self.probe(value,cell,segment,removed)
                count = prepared["row"]["prompt_tokens"]
                limit = task.WORKING_SET if segment in {"SHARED","X16000"} else task.RESIDENT_CEILING
                if count <= limit:
                    selected,externalized = prepared,removed
                    break
                self.log.append("input_withheld", {**prepared["row"],"completion_sent":False,
                    "reason":"shared_boundary" if segment=="SHARED" else "input_ceiling",
                    "input_ceiling":limit}, [])
                if segment == "SHARED":
                    require(bool(value.pairs), "initial state cannot be manufactured into a pressure fork")
                    boundary = prepared
                    break
            if boundary is not None:
                disposition = "authentic_input_boundary"
                break
            if selected is None:
                disposition = "native_input_capacity_denied"
                break
            self.invoke(value,selected,cell["id"]+"-"+segment)
        if value.state.submitted:
            disposition = "submitted_with_current_public_check" if value.state.public_check_passed else "submitted_without_current_public_check"
        summary = dict(cell_id=cell["id"],seed=cell["seed"],segment=segment,disposition=disposition,
            prefix_actions=prefix_actions,actions_total=len(value.pairs),requests_this_segment=self.sent-start,
            segment_wall_seconds=time.monotonic()-time_start,submitted=value.state.submitted,
            public_check_passed=value.state.public_check_passed,final_candidate_id=value.state.candidate.candidate_id,
            externalized_through=externalized)
        self.log.append("segment_completed",summary,[self.store.put("segments/"+cell["id"]+"-"+segment+"-pairs.json",canonical_json_bytes(value.pairs))])
        return summary,boundary

    def execute(self):
        # Both independent cells must pass native initial preflight before either
        # receives a completion. This does not qualify later generation lengths.
        for cell in self.plan["schedule"]:
            self.probe(new_state("initial",self.fixture),cell,"PREFLIGHT",0,preflight=True)
        results = []
        for cell in self.plan["schedule"]:
            self.log.append("cell_started",cell,[])
            common = new_state(cell["id"],self.fixture)
            common_summary,boundary = self.segment(common,cell,"SHARED")
            branches = []
            if boundary is not None:
                frozen = canonical_json_bytes(snapshot(common))
                prefix = len(common.pairs)
                self.log.append("authentic_fork", {"cell_id":cell["id"],"prefix_actions":prefix,
                    "pre_residency_request_sha256":sha256_bytes(boundary["raw"]),"input_tokens":boundary["row"]["prompt_tokens"],
                    "branch_order":cell["branch_order"],"branch_binding_in_model_input":False},
                    [self.store.put("forks/"+cell["id"]+".json",frozen)])
                for condition in cell["branch_order"]:
                    require(canonical_json_bytes(snapshot(common)) == frozen, "common ancestor changed during another branch")
                    value = clone(common)
                    request = task.request_for(value,self.reference,seed=cell["seed"])
                    require(canonical_json_bytes(request) == boundary["raw"], "branch pre-residency request differs")
                    self.log.append("branch_started", {"cell_id":cell["id"],"condition":condition,"prefix_actions":prefix,
                        "common_snapshot_sha256":sha256_bytes(frozen),"pre_residency_request_sha256":sha256_bytes(boundary["raw"])},
                        payloads.save_payloads(value,cell["id"]+"-"+condition,self.store))
                    summary,_ = self.segment(value,cell,condition,prefix_actions=prefix)
                    branches.append(summary)
                    require(canonical_json_bytes(snapshot(common)) == frozen, "branch mutation leaked into ancestor")
            result = dict(cell_id=cell["id"],seed=cell["seed"] ,common=common_summary,branches=branches,
                          boundary_occurred=boundary is not None)
            self.log.append("cell_completed",result,[])
            results.append(result)
        return results


def run_once(args):
    require(isinstance(args.owner_approval,str) and bool(args.owner_approval.strip()), "separate owner execution approval is required")
    require(args.execution_sha256 == sha256_file(MANIFEST), "owner-approved execution manifest differs")
    plan = load_manifest()
    require(not RUN.exists(), "attempt already reserved; no resume, retry or replacement")
    require(args.model is not None and args.server is not None, "pinned model/runtime paths are required")
    RUN.mkdir(parents=True,exist_ok=False)
    args.output = RUN
    store,log = ArtifactStore(RUN),pilot.PilotLog(RUN / "records.jsonl","compiler-pressure-run-001")
    failure,disposition = None,"completed_comparison"
    log.append("attempt_reserved", {"owner_approval":args.owner_approval,"execution_manifest_sha256":args.execution_sha256,
        "maximum_completion_requests":MAX_COMPLETIONS,"schedule":plan["schedule"]},
        [store.put("EXECUTION_MANIFEST.json",MANIFEST.read_bytes()),store.put("EXECUTION_SPEC.md",SPEC.read_bytes())])
    try:
        fixture = load_fixture()
        for name in ("candidate.json","TASK.txt","PUBLIC_CHECK.py","observations.json","captures.json"):
            log.append("starting_data_saved", {"path":name}, [store.put("starting-data/"+name,(PACKAGE/name).read_bytes())])
        with base.owned_runtime(args,store,log) as url:
            Comparison(plan,fixture,url,RUN,store,log).execute()
            check_sources(plan)
            pilot.health(RUN)
        closed = verify_records(RUN / "records.jsonl",RUN)[-1]
        require(closed["record_type"] == "runtime_closed" and closed["payload"]["owned_server_shutdown_verified"]
                and closed["payload"]["dedicated_port_free"], "runtime lifecycle incomplete")
        verified_package()
    except BaseException as error:
        failure,disposition = error,"stopped_without_retry"
        detail = str(error)
        for path in (args.model,args.server,RUN):
            detail = detail.replace(str(path),"<local path>")
        log.append("stage_stopped", {"error_type":type(error).__name__,"error":detail}, [])
    finally:
        log.append("stage_closed", {"disposition":disposition,
            "owned_server_shutdown_verified":not base.running_process_ids(args.server.name),
            "dedicated_port_free":base.port_free(base.PORT)}, [])
        records = verify_records(RUN / "records.jsonl",RUN)
        files = base.file_inventory(RUN)
        seal = dict(disposition=disposition,execution_manifest_sha256=args.execution_sha256,package_sha256=PACKAGE_SHA,
            actor=task.ACTOR,memory_policy=pilot.cont.POLICY,
            sent_requests=sum(r["record_type"]=="invocation_started" for r in records),
            received_responses=sum(r["record_type"]=="response_received" for r in records),
            completed_responses=sum(r["record_type"]=="invocation_completed" for r in records),
            cells=[r["payload"] for r in records if r["record_type"]=="cell_completed"],
            record_count=len(records),files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),
            memory=base.memory_stats(RUN / "memory.csv"),
            effective_runtime=base.runtime_evidence(RUN / "private-runtime/server.stderr.log"),
            private_runtime_files_local_only={p.name:sha256_file(p) for p in (RUN/"private-runtime").glob("*") if p.is_file()})
        base.write_json(RUN / "RESPONSE_SEAL.json",seal)
    if failure:
        raise failure
    return seal


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("freeze","run"),required=True)
    parser.add_argument("--execution-sha256")
    parser.add_argument("--owner-approval",default="")
    parser.add_argument("--model",type=Path)
    parser.add_argument("--server",type=Path)
    args = parser.parse_args()
    if args.mode == "freeze":
        base.write_json(MANIFEST,proposed_manifest())
        print({"completion_calls":0,"execution_manifest_sha256":sha256_file(MANIFEST)})
    else:
        run_once(args)
