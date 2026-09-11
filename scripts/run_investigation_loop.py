"""Execute the prepared two-run loop only after its separate owner decision."""
from __future__ import annotations

import argparse
from pathlib import Path
import time

import prepare_investigation_loop as prep
import run_interface_comparison as shared
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.event_frame_v3 import resident_pair_v3
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.measurement import check_opportunity

RUN = prep.AREA / "run-001"
require, base = prep.require, prep.base


def validate_package(folder, expected_sha):
    require(sha256_file(folder / "PACKAGE_MANIFEST.json") == expected_sha, "approved package identity differs")
    plan = load_json_strict((folder / "PACKAGE_MANIFEST.json").read_bytes())
    require(plan["completion_calls"] == 0 and plan["execution_authorized"] is False, "preparation status differs")
    require(plan["actor"] == prep.ACTOR and plan["memory_policy"] == prep.cont.POLICY, "actor or memory policy differs")
    require(plan["call_limit"] == prep.CALL_LIMIT and plan["maximum_completion_calls"] == 40
            and plan["input_ceiling"] == prep.INPUT_CEILING, "allowance differs")
    require(plan["source_sha256"] == prep.source_identities(), "prepared source closure differs")
    require((folder / "SPEC.md").read_bytes() == prep.SPEC.read_bytes(), "specification differs")
    require(plan["history_policy"] == "all ordered events resident; private thinking omitted; no externalization", "history policy differs")
    require(len(plan["schedule"]) == 2, "run count differs")
    for actual, expected in zip(plan["schedule"], prep.schedule()):
        require(all(actual[k] == v for k, v in expected.items()), "schedule differs")
        require(actual["stem"] == "initial/" + actual["id"], "initial address differs")
    for row in plan["files"]:
        path = folder / row["path"]
        require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"], "prepared artifact differs: " + row["path"])
    seal = load_json_strict((folder / "PREPARATION_SEAL.json").read_bytes())
    require(seal["disposition"] == "prepared_without_completion" and seal["completion_calls"] == 0, "preparation not complete")
    require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "preparation seal aggregate differs")
    for row in seal["files"]:
        path = folder / row["path"]
        require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"], "sealed artifact differs")
    require(len(verify_records(folder / "records.jsonl", folder)) == seal["record_count"], "preparation record count differs")
    require([(q["path"],q["required_to_fit"]) for q in plan["qualification_paths"]] ==
            [("direct",True),("focused_correction",True),("explore_and_correct",False)], "qualification scope differs")
    require(all(q["all_inputs_admitted"] for q in plan["qualification_paths"] if q["required_to_fit"]), "required offline route not qualified")
    return plan


def save_payloads(value, run_id, store):
    artifacts = []
    for mapping in (value.result_payloads, value.event_payloads):
        for handle, raw in mapping.items():
            relative = "payloads/" + run_id + "/" + handle + ".json"
            target = store.root / relative
            if target.exists():
                require(target.read_bytes() == raw, "canonical historical payload changed")
            else:
                artifacts.append(store.put(relative, raw))
    return artifacts


def execute(plan, folder, url, output, store, log, *, post=base.post, render=prep.render_only, health=None):
    health = health or (lambda: prep.health(output))
    selected = prep.load_fixture(folder)
    visible_reference = (folder / "TOOL_REFERENCE.txt").read_text(encoding="utf-8")
    require(visible_reference == prep.tool_reference(prep.grammar_for(new_state("verify", selected))), "tool reference differs")
    # Validate both first inputs before exposing either independent run.
    for run in plan["schedule"]:
        value = new_state(run["id"], selected)
        raw = canonical_json_bytes(prep.request_for(value, run["seed"], visible_reference))
        require(raw == (folder / (run["stem"] + "-request.json")).read_bytes(), "initial request reconstruction differs")
    summaries = []
    for run in plan["schedule"]:
        value = new_state(run["id"], selected)
        started, sent, disposition = time.monotonic(), 0, "action_allowance_exhausted"
        log.append("run_started", run, [])
        for index in range(1, prep.CALL_LIMIT + 1):
            require(plan["source_sha256"] == prep.source_identities(), "source changed before dispatch")
            request = prep.request_for(value, run["seed"], visible_reference)
            raw = canonical_json_bytes(request)
            state = load_json_strict(request["messages"][1]["content"].encode())
            events = state["active_phase_event_frame"]["events"]
            require([resident_pair_v3(event) for event in events] == value.pairs, "next-input result delivery differs")
            require(len(value.pairs) == index - 1 and state["resource_state"]["calls_remaining"] == prep.CALL_LIMIT-index+1,
                    "remaining action allowance differs")
            health()
            template, rendered, tokenized, count = render(url, request)
            if index == 1:
                require(sha256_bytes(rendered) == run["rendered_sha256"] and count == run["prompt_tokens"], "first native input differs")
            tag = f"{run['id']}-{index:03d}"
            row = {"id":tag,"run_id":run["id"],"seed":run["seed"],"sequence":index,"prompt_tokens":count,
                   "calls_remaining_before":prep.CALL_LIMIT-index+1,"native_input_sha256":sha256_bytes(rendered)}
            artifacts = [store.put("calls/"+tag+suffix, data) for suffix, data in (
                ("-endpoint-request.json",raw),("-rendered-prompt.txt",rendered),("-template-response.json",template),
                ("-tokenization.json",tokenized),("-candidate-before.json",prep.reference.candidate_bytes(value.state.candidate)),
                ("-state-before.json",prep.reference.session_bytes(value.state)))]
            log.append("invocation_prepared", {**row,"completion_sent":False,"resident_results":len(events)}, artifacts)
            if count > prep.INPUT_CEILING:
                disposition = "native_input_capacity_denied"
                log.append("invocation_withheld", {**row,"disposition":disposition,"completion_sent":False}, [])
                break
            require(plan["source_sha256"] == prep.source_identities(), "source changed after rendering")
            checked_health = health()
            log.append("invocation_started", {**row,"completion_sent":True,**checked_health}, [])
            print(f"Starting {tag}: {count} input; {row['calls_remaining_before']} actions remaining", flush=True)
            before = time.monotonic()
            try:
                response = post(url, "/v1/chat/completions", raw, base.HTTP_TIMEOUT_SECONDS)
            except base.ResponseFailure as error:
                log.append("transport_stopped", {**row,"error":str(error),"status":error.status,"received_prefix_not_asserted_complete":True},
                           [store.put("calls/"+tag+"-transport-body.bin",error.data)])
                raise
            sent += 1
            elapsed = time.monotonic() - before
            processing_started = time.monotonic()
            outcome = shared.receive_and_execute(value, row, response, elapsed, store, log, health)
            require(len(value.pairs) == index, "response did not execute exactly one action")
            action, result = value.pairs[-1]["response"], value.pairs[-1]["result"]
            opportunity = check_opportunity(calls_used=index-1,call_limit=prep.CALL_LIMIT,result=result) if action["action"] == "check" else None
            terminal = value.state.submitted
            log.append("next_turn_decision", {**row,"calls_remaining_after":prep.CALL_LIMIT-index,
                "response_processing_seconds":time.monotonic()-processing_started,"check_opportunity":opportunity,
                "submitted":terminal,"next_step":"terminal" if terminal else "reconstruct_then_check_admission",
                "next_request_sent":False}, save_payloads(value, run["id"], store))
            print(f"Completed {tag}: {outcome['usage']['completion_tokens']} output; {action['action']}; accepted={result.get('accepted')}", flush=True)
            if terminal:
                disposition = "submitted_with_current_public_check" if value.state.public_check_passed else "submitted_without_current_public_check"
                break
        summary = {**run,"disposition":disposition,"completed_requests":sent,"actions":len(value.pairs),
                   "task_wall_seconds":time.monotonic()-started,"submitted":value.state.submitted,
                   "public_check_passed":value.state.public_check_passed,"final_candidate_id":value.state.candidate.candidate_id}
        log.append("run_completed",summary,[store.put("runs/"+run["id"]+"-pairs.json",canonical_json_bytes(value.pairs))])
        summaries.append(summary)
    return summaries


def run_once(args):
    require(isinstance(args.owner_approval,str) and bool(args.owner_approval.strip()), "separate owner execution approval is required")
    plan = validate_package(args.package,args.package_sha256)
    require(not RUN.exists(), "pilot attempt already reserved; no resume, retry or replacement")
    args.output = RUN
    RUN.mkdir(parents=True,exist_ok=False)
    store = ArtifactStore(RUN)
    log = prep.PilotLog(RUN / "records.jsonl","investigation-loop-run-001")
    log.append("stage_prepared", {"owner_approval":args.owner_approval,"package_sha256":args.package_sha256,
        "maximum_completion_calls":40,"schedule":prep.schedule()},
        [store.put("PACKAGE_MANIFEST.json",(args.package / "PACKAGE_MANIFEST.json").read_bytes()),store.put("SPEC.md",prep.SPEC.read_bytes())])
    disposition, failure = "completed_two_run_pilot", None
    try:
        with base.owned_runtime(args,store,log) as url:
            execute(plan,args.package,url,RUN,store,log)
            require(plan["source_sha256"] == prep.source_identities(), "source changed during execution")
            prep.health(RUN)
    except BaseException as error:
        disposition, failure = "stopped_without_retry", error
        detail = str(error)
        for path in (args.model,args.server,RUN):
            detail = detail.replace(str(path),"<local path>")
        log.append("stage_stopped",{"error_type":type(error).__name__,"error":detail},[])
    finally:
        log.append("stage_closed",{"disposition":disposition,"owned_server_shutdown_verified":not base.running_process_ids(args.server.name),
                                   "dedicated_port_free":base.port_free(base.PORT)},[])
        records = verify_records(RUN / "records.jsonl",RUN)
        files = base.file_inventory(RUN)
        seal = {"disposition":disposition,"package_sha256":args.package_sha256,"actor":prep.ACTOR,"memory_policy":prep.cont.POLICY,
                "sent_requests":sum(r["record_type"]=="invocation_started" for r in records),
                "received_responses":sum(r["record_type"]=="response_received" for r in records),
                "completed_responses":sum(r["record_type"]=="invocation_completed" for r in records),
                "runs":[r["payload"] for r in records if r["record_type"]=="run_completed"],
                "record_count":len(records),"files":files,"aggregate_sha256":sha256_bytes(canonical_json_bytes(files)),
                "memory":base.memory_stats(RUN / "memory.csv"),"effective_runtime":base.runtime_evidence(RUN / "private-runtime/server.stderr.log"),
                "private_runtime_files_local_only":{p.name:sha256_file(p) for p in (RUN / "private-runtime").glob("*") if p.is_file()}}
        base.write_json(RUN / "RESPONSE_SEAL.json",seal)
    if failure:
        raise failure
    return seal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package",type=Path,default=prep.PACKAGE)
    parser.add_argument("--package-sha256",required=True)
    parser.add_argument("--owner-approval",required=True)
    parser.add_argument("--model",type=Path,required=True)
    parser.add_argument("--server",type=Path,required=True)
    run_once(parser.parse_args())


if __name__ == "__main__":
    main()
