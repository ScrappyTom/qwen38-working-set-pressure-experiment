"""Execute the frozen single-run shift investigation after its owner decision."""
from __future__ import annotations

import argparse
from pathlib import Path
import time

import prepare_shift_investigation as prep
import run_investigation_loop as legacy
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.event_frame_v3 import resident_pair_v3
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.measurement import check_opportunity

RUN=prep.AREA / "run-001"
base, require = prep.base, prep.require


def validate_package(folder, expected_sha):
    require(sha256_file(folder / "PACKAGE_MANIFEST.json")==expected_sha, "approved package differs")
    plan=load_json_strict((folder / "PACKAGE_MANIFEST.json").read_bytes())
    require(plan["schema"]=="shift-investigation-preparation-v1" and plan["completion_calls"]==0 and plan["execution_authorized"] is False, "preparation status differs")
    require(plan["source_sha256"]==prep.source_identities(), "source closure differs")
    require(plan["actor"]==prep.ACTOR and plan["memory_policy"]==prep.pilot.cont.POLICY, "actor or memory policy differs")
    require(plan["call_limit"]==plan["maximum_completion_calls"]==prep.CALL_LIMIT and plan["input_ceiling"]==prep.INPUT_CEILING, "allowance differs")
    require(plan["seed"]==prep.SEED and plan["run_id"]=="S01" and plan["initial"]["stem"]=="initial/S01", "schedule differs")
    require(plan["history_policy"]==prep.HISTORY and plan["episode_annotation"]==prep.EPISODE_ANNOTATION, "presentation differs")
    require((folder / "SPEC.md").read_bytes()==prep.SPEC.read_bytes(), "specification differs")
    seal=load_json_strict((folder / "PREPARATION_SEAL.json").read_bytes())
    require(seal["disposition"]=="prepared_without_completion" and seal["completion_calls"]==0, "preparation incomplete")
    require(sha256_bytes(canonical_json_bytes(seal["files"]))==seal["aggregate_sha256"], "inventory differs")
    public={p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and "private-runtime" not in p.relative_to(folder).parts}
    require(public=={r["path"] for r in seal["files"]}|{"PREPARATION_SEAL.json"}, "unsealed public preparation")
    for row in [*plan["files"],*seal["files"]]:
        path=folder / row["path"]
        require(path.stat().st_size==row["size_bytes"] and sha256_file(path)==row["sha256"], "prepared bytes differ")
    require(len(verify_records(folder / "records.jsonl",folder))==seal["record_count"], "record count differs")
    require([q["path"] for q in plan["qualification_paths"]]==["direct","correction"] and all(q["all_inputs_admitted"] for q in plan["qualification_paths"]), "oracle capacity not qualified")
    return plan


def execute(plan,folder,url,output,store,log,*,post=base.post,render=prep.pilot.render_only,health=None):
    health=health or (lambda:prep.pilot.health(output))
    value=new_state("S01",prep.load_fixture(folder))
    reference=(folder / "TOOL_REFERENCE.txt").read_text(encoding="utf-8")
    require(reference==prep.pilot.tool_reference(prep.pilot.grammar_for(value)), "tool reference differs")
    require(canonical_json_bytes(prep.request_for(value,reference))==(folder / "initial/S01-request.json").read_bytes(), "first request differs")
    began=time.monotonic()
    disposition="action_allowance_exhausted"
    log.append("run_started",dict(id="S01",seed=prep.SEED,call_limit=prep.CALL_LIMIT),[])
    for index in range(1,prep.CALL_LIMIT+1):
        require(plan["source_sha256"]==prep.source_identities(), "source changed before dispatch")
        request=prep.request_for(value,reference)
        state=load_json_strict(request["messages"][1]["content"].encode())
        require(state["active_user_authored_step"]["episode_annotation"]==prep.EPISODE_ANNOTATION, "annotation absent")
        require([resident_pair_v3(e) for e in state["active_phase_event_frame"]["events"]]==value.pairs, "result feedback differs")
        require(len(value.pairs)==index-1 and state["resource_state"]["calls_remaining"]==prep.CALL_LIMIT-index+1, "action accounting differs")
        health()
        template,native,tokens,count=render(url,request)
        if index==1:
            require(sha256_bytes(native)==plan["initial"]["rendered_sha256"] and count==plan["initial"]["prompt_tokens"], "first native input differs")
        tag=f"S01-{index:03d}"
        row=dict(id=tag,run_id="S01",seed=prep.SEED,sequence=index,prompt_tokens=count,
                 calls_remaining_before=prep.CALL_LIMIT-index+1,native_input_sha256=sha256_bytes(native))
        log.append("invocation_prepared",{**row,"completion_sent":False},[store.put("calls/"+tag+suffix,raw) for suffix,raw in (
            ("-endpoint-request.json",canonical_json_bytes(request)),("-rendered-prompt.txt",native),("-template-response.json",template),
            ("-tokenization.json",tokens),("-candidate-before.json",prep.pilot.reference.candidate_bytes(value.state.candidate)),
            ("-state-before.json",prep.pilot.reference.session_bytes(value.state)))])
        if count>prep.INPUT_CEILING:
            disposition="native_input_capacity_denied"
            log.append("invocation_withheld",{**row,"disposition":disposition,"completion_sent":False},[])
            break
        require(plan["source_sha256"]==prep.source_identities(), "source changed after rendering")
        log.append("invocation_started",{**row,"completion_sent":True,**health()},[])
        print(f"Starting {tag}: {count} input; {row['calls_remaining_before']} actions remaining",flush=True)
        before=time.monotonic()
        try:
            raw=post(url,"/v1/chat/completions",canonical_json_bytes(request),base.HTTP_TIMEOUT_SECONDS)
        except base.ResponseFailure as error:
            log.append("transport_stopped",{**row,"error":str(error),"status":error.status,"received_prefix_not_asserted_complete":True},
                       [store.put("calls/"+tag+"-transport-body.bin",error.data)])
            raise
        elapsed=time.monotonic()-before
        processing=time.monotonic()
        outcome=legacy.shared.receive_and_execute(value,row,raw,elapsed,store,log,health)
        require(len(value.pairs)==index,"response did not execute one action")
        action,result=value.pairs[-1]["response"],value.pairs[-1]["result"]
        opportunity=check_opportunity(calls_used=index-1,call_limit=prep.CALL_LIMIT,result=result) if action["action"]=="check" else None
        log.append("next_turn_decision",{**row,"calls_remaining_after":prep.CALL_LIMIT-index,
            "response_processing_seconds":time.monotonic()-processing,"check_opportunity":opportunity,
            "submitted":value.state.submitted,"next_step":"terminal" if value.state.submitted else "reconstruct_then_check_admission",
            "next_request_sent":False},legacy.save_payloads(value,"S01",store))
        print(f"Completed {tag}: {outcome['usage']['completion_tokens']} output; {action['action']}; accepted={result.get('accepted')}",flush=True)
        if value.state.submitted:
            disposition="submitted_with_current_public_check" if value.state.public_check_passed else "submitted_without_current_public_check"
            break
    summary=dict(id="S01",seed=prep.SEED,disposition=disposition,actions=len(value.pairs),task_wall_seconds=time.monotonic()-began,
                 submitted=value.state.submitted,public_check_passed=value.state.public_check_passed,final_candidate_id=value.state.candidate.candidate_id)
    log.append("run_completed",summary,[store.put("runs/S01-pairs.json",canonical_json_bytes(value.pairs))])
    return summary


def run_once(args):
    require(isinstance(args.owner_approval,str) and bool(args.owner_approval.strip()), "separate owner execution instruction required")
    plan=validate_package(args.package,args.package_sha256)
    require(not RUN.exists(),"attempt already reserved; no retry or replacement")
    RUN.mkdir(parents=True,exist_ok=False)
    args.output=RUN
    store,log=ArtifactStore(RUN),prep.pilot.PilotLog(RUN / "records.jsonl","shift-investigation-run-001")
    log.append("stage_prepared",dict(owner_approval=args.owner_approval,package_sha256=args.package_sha256,maximum_completion_calls=prep.CALL_LIMIT),
               [store.put("PACKAGE_MANIFEST.json",(args.package / "PACKAGE_MANIFEST.json").read_bytes()),store.put("SPEC.md",prep.SPEC.read_bytes())])
    failure,disposition=None,"completed_single_run_investigation"
    try:
        with base.owned_runtime(args,store,log) as url:
            execute(plan,args.package,url,RUN,store,log)
            require(plan["source_sha256"]==prep.source_identities(),"source changed during execution")
            prep.pilot.health(RUN)
        closed=verify_records(RUN / "records.jsonl",RUN)[-1]
        require(closed["record_type"]=="runtime_closed" and closed["payload"]["owned_server_shutdown_verified"]
                and closed["payload"]["dedicated_port_free"], "execution runtime lifecycle incomplete")
    except BaseException as error:
        failure,disposition=error,"stopped_without_retry"
        detail=str(error)
        for path in (args.model,args.server,RUN):detail=detail.replace(str(path),"<local path>")
        log.append("stage_stopped",dict(error_type=type(error).__name__,error=detail),[])
    finally:
        log.append("stage_closed",dict(disposition=disposition,owned_server_shutdown_verified=not base.running_process_ids(args.server.name),dedicated_port_free=base.port_free(base.PORT)),[])
        records=verify_records(RUN / "records.jsonl",RUN)
        files=base.file_inventory(RUN)
        base.write_json(RUN / "RESPONSE_SEAL.json",dict(disposition=disposition,package_sha256=args.package_sha256,actor=prep.ACTOR,memory_policy=prep.pilot.cont.POLICY,
            sent_requests=sum(r["record_type"]=="invocation_started" for r in records),received_responses=sum(r["record_type"]=="response_received" for r in records),
            completed_responses=sum(r["record_type"]=="invocation_completed" for r in records),runs=[r["payload"] for r in records if r["record_type"]=="run_completed"],
            record_count=len(records),files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),memory=base.memory_stats(RUN / "memory.csv"),
            effective_runtime=base.runtime_evidence(RUN / "private-runtime/server.stderr.log"),
            private_runtime_files_local_only={p.name:sha256_file(p) for p in (RUN / "private-runtime").glob("*") if p.is_file()}))
    if failure:raise failure


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package",type=Path,default=prep.PACKAGE)
    parser.add_argument("--package-sha256",required=True)
    parser.add_argument("--owner-approval",required=True)
    parser.add_argument("--model",type=Path,required=True)
    parser.add_argument("--server",type=Path,required=True)
    run_once(parser.parse_args())
