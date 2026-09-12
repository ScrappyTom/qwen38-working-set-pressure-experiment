"""Verify a sealed compiler comparison and replay its observed actions offline.

This checks custody and execution, not whether a reviewer read the transcripts.
It neither starts inference nor changes the frozen runner or its artifacts.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime
import difflib
from pathlib import Path
from types import SimpleNamespace

import run_compiler_incident as run
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.measurement import check_opportunity
from working_set_exp.runtime import tokenizer_count
from working_set_exp.tools import strict_action

TOKENIZER_SHA = "d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c"
require = run.require


def verify(args):
    folder = run.RUN
    # Verify the immutable seal before accessing response contents.
    require(sha256_file(folder / "RESPONSE_SEAL.json") == args.seal_sha256, "reviewed seal differs")
    seal = run.base.verify_seal(folder)
    plan = run.load_manifest()
    require(seal["execution_manifest_sha256"] == sha256_file(run.MANIFEST), "execution binding differs")
    require((folder / "EXECUTION_MANIFEST.json").read_bytes() == run.MANIFEST.read_bytes(), "saved manifest differs")
    require((folder / "EXECUTION_SPEC.md").read_bytes() == run.SPEC.read_bytes(), "saved specification differs")
    require(seal["actor"] == plan["actor"] and seal["memory_policy"] == plan["memory_policy"], "sealed settings differ")
    require({p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and "private-runtime" not in p.parts}
            == {r["path"] for r in seal["files"]} | {"RESPONSE_SEAL.json"}, "unsealed public evidence")
    for name,digest in seal["private_runtime_files_local_only"].items():
        require(sha256_file(folder / "private-runtime" / name) == digest, "private evidence differs")
    for name in ("candidate.json","TASK.txt","PUBLIC_CHECK.py","observations.json","captures.json"):
        require((folder / "starting-data" / name).read_bytes() == (run.PACKAGE / name).read_bytes(), "starting data differs")
    records = verify_records(folder / "records.jsonl",folder)
    require(records[0]["record_type"] == "attempt_reserved" and records[-1]["record_type"] == "stage_closed", "attempt custody differs")
    approval = records[0]["payload"]
    require(approval["owner_approval"].startswith("I approve") and approval["schedule"] == plan["schedule"]
            and approval["maximum_completion_requests"] == 128, "approval scope differs")
    require(seal["record_count"] == len(records), "record count differs")
    launch = load_json_strict((folder / "private-runtime/launch.json").read_bytes())
    model,server = Path(launch[2]),Path(launch[0])
    require(sha256_file(model) == plan["actor"]["model_sha256"] and sha256_file(server) == plan["actor"]["server_sha256"], "runtime binaries differ")
    require(launch == run.base.launch_args(server,model), "actual runtime arguments differ")
    require(sha256_file(args.tokenizer) == TOKENIZER_SHA, "offline tokenizer differs")
    profile = SimpleNamespace(model_path=model,tokenizer_path=args.tokenizer)
    token_counts = {}

    def count(raw):
        if not raw:
            return 0
        if raw not in token_counts:
            token_counts[raw] = tokenizer_count(profile,raw)
        return token_counts[raw]

    def indexed(kind):
        values = [r["payload"] for r in records if r["record_type"] == kind]
        require(len({r["id"] for r in values}) == len(values), "duplicate "+kind)
        return {r["id"]:r for r in values}

    started,received,completed = (indexed(kind) for kind in ("invocation_started","response_received","invocation_completed"))
    decisions = indexed("next_turn_decision")
    require(set(decisions) == set(completed) and set(completed) <= set(received) <= set(started), "response custody order differs")
    for key,rows in (("sent_requests",started),("received_responses",received),("completed_responses",completed)):
        require(seal[key] == len(rows) <= 128, "sealed response count differs")
    if set(started)-set(completed):
        require(seal["disposition"] == "stopped_without_retry" and len(set(started)-set(completed)) == 1, "incomplete invocation did not stop")
    runtime = next(r["payload"] for r in records if r["record_type"] == "runtime_prepared")
    portable = list(launch)
    portable[0],portable[2] = "<pinned llama-server>","<selected GGUF>"
    require(runtime["public_launch"] == portable, "public runtime command differs")
    differences = {k:dict(runtime_prepared=runtime["actor"].get(k),active_plan=plan["actor"].get(k))
                   for k in sorted(runtime["actor"].keys() | plan["actor"].keys()) if runtime["actor"].get(k) != plan["actor"].get(k)}
    require(set(differences) <= {"generation_reserve","minimum_free_gpu_mib"}, "unexpected runtime metadata difference")
    for row in started.values():
        evidence = row["effective_runtime"]
        require(all(evidence[k] for k in ("full_offload","context_matches","q4_k_and_v","mtp_disabled")), "unqualified dispatch runtime")
        require(not evidence["truncation_observed"] and not evidence["cuda_failure_observed"], "failure present at dispatch")
        require(row["memory"]["reference_is_advisory"] is True, "memory policy changed")

    fixture = run.load_fixture()
    reference = run.pilot.tool_reference(run.pilot.grammar_for(run.new_state("reference",fixture)))
    schedule = {cell["id"]:cell for cell in plan["schedule"]}
    states,ancestors,branches,prepared = {},{},{},{}
    calls,inputs,segments,forks,payload_paths = [],[],[],[],set()
    for record in records:
        kind,payload = record["record_type"],record["payload"]
        if kind == "cell_started":
            require(payload == schedule[payload["id"]], "cell identity differs")
            states[payload["id"],"SHARED"] = run.new_state(payload["id"],fixture)
            branches[payload["id"]] = []
        elif kind == "authentic_fork":
            cell = payload["cell_id"]
            value = states[cell,"SHARED"]
            snapshot = canonical_json_bytes(run.snapshot(value))
            require((folder / ("forks/"+cell+".json")).read_bytes() == snapshot, "fork ancestor differs")
            require(len(value.pairs) == payload["prefix_actions"] > 0 and payload["input_tokens"] > 16000, "inauthentic fork")
            require(not value.state.submitted and len(value.pairs) < 32, "fork follows a terminal state")
            request = run.task.request_for(value,reference,seed=schedule[cell]["seed"])
            require(sha256_bytes(canonical_json_bytes(request)) == payload["pre_residency_request_sha256"], "fork input differs")
            ancestors[cell] = snapshot
            forks.append(payload)
        elif kind == "branch_started":
            cell,condition = payload["cell_id"],payload["condition"]
            require(canonical_json_bytes(run.snapshot(states[cell,"SHARED"])) == ancestors[cell], "ancestor changed")
            require(condition == schedule[cell]["branch_order"][len(branches[cell])], "branch order differs")
            branches[cell].append(condition)
            value = copy.deepcopy(states[cell,"SHARED"])
            require(sha256_bytes(canonical_json_bytes(run.snapshot(value))) == payload["common_snapshot_sha256"], "branch clone differs")
            states[cell,condition] = value
        elif kind == "native_input_prepared":
            cell,segment = payload["cell_id"],payload["segment"]
            value = run.new_state("preflight",fixture) if segment == "PREFLIGHT" else states[cell,segment]
            stem = folder / payload["admission_stem"]
            raw = Path(str(stem)+"-endpoint-request.json").read_bytes()
            request = load_json_strict(raw)
            require(raw == canonical_json_bytes(run.task.request_for(value,reference,
                externalized=payload["externalized_through"],seed=schedule[cell]["seed"])), "input reconstruction differs: "+payload["id"])
            require(Path(str(stem)+"-candidate.json").read_bytes() == run.pilot.reference.candidate_bytes(value.state.candidate), "input candidate differs")
            require(Path(str(stem)+"-session.json").read_bytes() == run.pilot.reference.session_bytes(value.state), "input session differs")
            native = Path(str(stem)+"-native.txt").read_bytes()
            template = load_json_strict(Path(str(stem)+"-template.json").read_bytes())
            tokens = load_json_strict(Path(str(stem)+"-tokens.json").read_bytes())["tokens"]
            require(native == template["prompt"].encode() and all(m["content"].strip().encode() in native for m in request["messages"]), "native content differs")
            require(count(native) == len(tokens) == payload["prompt_tokens"], "native token accounting differs")
            require(sha256_bytes(raw) == payload["endpoint_request_sha256"] and sha256_bytes(native) == payload["native_input_sha256"], "input hashes differ")
            require(payload["sequence"] == len(value.pairs)+1 and payload["calls_remaining_before"] == 32-len(value.pairs), "input allowance differs")
            if not value.pairs:
                require(payload["native_input_sha256"] == schedule[cell]["initial_native_sha256"] and len(tokens) == 3744, "initial input changed")
            sent = payload["id"] in started and started[payload["id"]]["admission_stem"] == payload["admission_stem"]
            entry = {**payload,"sent":sent}
            inputs.append(entry)
            prepared[payload["admission_stem"]] = (entry,request)
        elif kind == "invocation_started":
            row,request = prepared[payload["admission_stem"]]
            require(row["id"] == payload["id"] and row["sent"], "dispatch does not match preparation")
            require(row["prompt_tokens"] <= (23808 if row["segment"] == "R23808" else 16000), "unadmitted input dispatched")
        elif kind == "invocation_completed":
            cell,segment,tag = payload["cell_id"],payload["segment"],payload["id"]
            value = states[cell,segment]
            row,request = prepared[payload["admission_stem"]]
            stem = folder / ("calls/"+tag)
            response = load_json_strict(Path(str(stem)+"-endpoint-response.json").read_bytes())
            require(len(response["choices"]) == 1, "choice count differs")
            choice,usage,timings = response["choices"][0],response["usage"],response["timings"]
            message = choice["message"]
            require(choice["finish_reason"] == "stop" and set(message) == {"role","reasoning_content","content"}
                    and message["role"] == "assistant", "accepted output channel differs")
            reasoning,final = Path(str(stem)+"-assistant-reasoning.txt").read_bytes(),Path(str(stem)+"-assistant-content.txt").read_bytes()
            require(reasoning == message["reasoning_content"].encode() and final == message["content"].encode(), "saved output fields differ")
            require(usage["prompt_tokens"] == timings["prompt_n"] == row["prompt_tokens"], "prompt accounting differs")
            require(usage["completion_tokens"] == timings["predicted_n"] > 0 and usage["prompt_tokens_details"]["cached_tokens"] == timings["cache_n"] == 0, "generation or cache accounting differs")
            require(usage["total_tokens"] == usage["prompt_tokens"]+usage["completion_tokens"] <= 56576, "physical accounting differs")
            action = strict_action(final)
            run.validate_action(action,request)
            require(Path(str(stem)+"-action.json").read_bytes() == canonical_json_bytes(action), "saved action differs")
            result = value.execute(action)
            host = dict(action=action,execution_attempted=True,executed=True,finish_reason="stop",result=result)
            require(Path(str(stem)+"-host-result.json").read_bytes() == canonical_json_bytes(host) and host == payload["host_result"], "replayed result differs: "+tag)
            require(Path(str(stem)+"-candidate-after.json").read_bytes() == run.pilot.reference.candidate_bytes(value.state.candidate), "successor differs")
            require(Path(str(stem)+"-state-after.json").read_bytes() == run.pilot.reference.session_bytes(value.state), "successor session differs")
            decision = decisions[tag]
            opportunity = check_opportunity(calls_used=len(value.pairs)-1,call_limit=32,result=result) if action["action"] == "check" else None
            require(decision["check_opportunity"] == opportunity and decision["calls_remaining_after"] == 32-len(value.pairs), "opportunity differs")
            require(decision["submitted"] == value.state.submitted and decision["next_step"] == ("terminal" if value.state.submitted else "reconstruct_then_admit"), "next-turn decision differs")
            for mapping in (value.result_payloads,value.event_payloads):
                for handle,body in mapping.items():
                    path = f"payloads/{cell}-{segment}/{handle}.json"
                    require((folder / path).read_bytes() == body, "canonical payload differs")
                    payload_paths.add(path)
            calls.append(dict(id=tag,cell_id=cell,segment=segment,sequence=len(value.pairs),input_tokens=row["prompt_tokens"],
                output_tokens=usage["completion_tokens"],retokenized_reasoning_text_tokens=count(reasoning),retokenized_final_text_tokens=count(final),
                request_seconds=payload["elapsed_seconds"],response_processing_seconds=decision["response_processing_seconds"],
                physical_tokens_remaining=56576-usage["total_tokens"],action=action,accepted=result.get("accepted"),passed=result.get("passed"),
                check_opportunity=opportunity,submitted=value.state.submitted,replay_exact=True,externalized_through=row["externalized_through"]))
            print("Replayed "+tag,flush=True)
        elif kind == "segment_completed":
            value = states[payload["cell_id"],payload["segment"]]
            require((folder / ("segments/"+payload["cell_id"]+"-"+payload["segment"]+"-pairs.json")).read_bytes() == canonical_json_bytes(value.pairs), "saved segment history differs")
            require(payload["actions_total"] == len(value.pairs) and payload["final_candidate_id"] == value.state.candidate.candidate_id
                    and payload["public_check_passed"] == value.state.public_check_passed and payload["submitted"] == value.state.submitted, "segment outcome differs")
            segments.append(payload)
    require(len(calls) == len(completed), "unreplayed completed action")
    require(seal["cells"] == [r["payload"] for r in records if r["record_type"] == "cell_completed"], "cell summaries differ")

    # A received answer without an executable final still consumed real input,
    # generation and time. Verify this observed context stop without fabricating
    # an action, continuation or completed-segment record.
    unexecuted = []
    extracted, host_decisions = indexed("response_extracted"), indexed("host_decision")
    for tag in sorted(set(received) - set(completed)):
        row, request = prepared[started[tag]["admission_stem"]]
        value = states[row["cell_id"], row["segment"]]
        stem = folder / ("calls/" + tag)
        response = load_json_strict(Path(str(stem) + "-endpoint-response.json").read_bytes())
        require(len(response["choices"]) == 1, "incomplete response choice count differs")
        choice, usage, timings = response["choices"][0], response["usage"], response["timings"]
        message = choice["message"]
        require(set(message) == {"role", "reasoning_content", "content"} and message["role"] == "assistant",
                "incomplete response channels differ")
        reasoning = Path(str(stem) + "-assistant-reasoning.txt").read_bytes()
        final = Path(str(stem) + "-assistant-content.txt").read_bytes()
        require(reasoning == message["reasoning_content"].encode() and final == message["content"].encode(),
                "incomplete response extraction differs")
        require(choice["finish_reason"] == "length" and reasoning and not final, "unexpected incomplete-response cause")
        require(usage["prompt_tokens"] == timings["prompt_n"] == row["prompt_tokens"], "incomplete prompt count differs")
        require(usage["completion_tokens"] == timings["predicted_n"] > 0, "incomplete output count differs")
        require(usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"] == 56576,
                "incomplete response did not fill physical context")
        require(usage["prompt_tokens_details"]["cached_tokens"] == timings["cache_n"] == 0, "incomplete response reused cache")
        require(extracted[tag] == dict(id=tag, usage=usage, finish_reason="length"), "incomplete extraction record differs")
        expected_host = dict(execution_attempted=False, executed=False, finish_reason="length",
                             error_type="ValueError", error="incomplete output; no action executed")
        require(Path(str(stem) + "-host-result.json").read_bytes() == canonical_json_bytes(expected_host),
                "incomplete response host decision differs")
        require(host_decisions[tag] == dict(id=tag, processing_stopped=True), "incomplete response did not stop processing")
        require(not Path(str(stem) + "-action.json").exists() and tag not in decisions,
                "incomplete response acquired an action or continuation")
        require(Path(str(stem) + "-candidate-after.json").read_bytes() == run.pilot.reference.candidate_bytes(value.state.candidate)
                and Path(str(stem) + "-state-after.json").read_bytes() == run.pilot.reference.session_bytes(value.state),
                "incomplete response changed candidate or session")
        unexecuted.append(dict(id=tag, cell_id=row["cell_id"], segment=row["segment"], sequence=row["sequence"],
            input_tokens=usage["prompt_tokens"], output_tokens=usage["completion_tokens"],
            retokenized_reasoning_text_tokens=count(reasoning), retokenized_final_text_tokens=count(final),
            request_seconds=received[tag]["elapsed_seconds"], physical_tokens_remaining=0, finish_reason="length",
            action_executed=False, following_request_offered=False, calls_remaining_at_dispatch=row["calls_remaining_before"],
            final_candidate_id=value.state.candidate.candidate_id, public_check_passed=value.state.public_check_passed,
            submitted=value.state.submitted, executed_actions_including_shared=len(value.pairs),
            externalized_through=row["externalized_through"], response_processing_seconds=None))

    # Qualify the actual oldest-prefix trials, including unsuccessful admissions.
    last_prefix = {}
    trial_groups = {}
    for row in inputs:
        if row["segment"] != "PREFLIGHT":
            trial_groups.setdefault((row["cell_id"],row["segment"],row["sequence"]),[]).append(row)
    for (cell,segment,sequence),rows in trial_groups.items():
        previous = last_prefix.get((cell,segment),0)
        expected = list(range(previous,previous+len(rows))) if segment == "X16000" else [0]
        require([r["externalized_through"] for r in rows] == expected, "payload selection is not the oldest monotonic prefix")
        limit = 23808 if segment == "R23808" else 16000
        require(all(r["prompt_tokens"] > limit and not r["sent"] for r in rows[:-1]), "unnecessary admission trial")
        if rows[-1]["sent"]:
            last_prefix[cell,segment] = rows[-1]["externalized_through"]
    for call in calls:
        possible = {call["segment"]}
        if call["segment"] == "SHARED" and any(f["cell_id"] == call["cell_id"] and f["prefix_actions"] == call["sequence"] for f in forks):
            possible.update(run.CONDITIONS)
        next_rows = [r for r in inputs if r["sent"] and r["cell_id"] == call["cell_id"] and r["sequence"] == call["sequence"]+1 and r["segment"] in possible]
        call["next_sent_inputs"] = [dict(id=r["id"],result_payload_resident=r["externalized_through"] < call["sequence"]) for r in next_rows]

    totals_keys = ("input_tokens","output_tokens","retokenized_reasoning_text_tokens","retokenized_final_text_tokens","request_seconds","response_processing_seconds")
    for segment in segments:
        selected = [c for c in calls if c["cell_id"] == segment["cell_id"] and c["segment"] == segment["segment"]]
        segment["new_work_totals"] = {key:sum(c[key] for c in selected) for key in totals_keys}
        segment["new_work_peak_input"] = max((c["input_tokens"] for c in selected),default=0)
        segment["new_action_counts"] = dict(Counter(c["action"]["action"] for c in selected))
        value = states[segment["cell_id"],segment["segment"]]
        segment["final_differences"] = [dict(path=name,diff="".join(difflib.unified_diff(
            fixture.initial.file_map.get(name,b"").decode().splitlines(keepends=True),value.state.candidate.file_map.get(name,b"").decode().splitlines(keepends=True),
            fromfile="before/"+name,tofile="after/"+name))) for name in sorted(fixture.initial.file_map.keys() | value.state.candidate.file_map.keys())
            if fixture.initial.file_map.get(name) != value.state.candidate.file_map.get(name)]
    samples = [line.split(",") for line in (folder / "memory.csv").read_text().splitlines()]
    stamps = [datetime.strptime(row[0].strip(),"%Y/%m/%d %H:%M:%S.%f") for row in samples]
    free = [int(row[-1]) for row in samples]
    memory = dict(samples=len(free),min_free_mib=min(free),max_free_mib=max(free))
    require(memory == seal["memory"], "memory summary differs")
    return dict(status="sealed_observed_prefix_verified_and_replayed",scope="Offline verification; zero completion requests; does not certify direct transcript review.",
        response_seal_sha256=args.seal_sha256,execution_manifest_sha256=sha256_file(run.MANIFEST),verifier_sha256=sha256_file(Path(__file__)),
        owner_approval=approval["owner_approval"],actor=plan["actor"],disposition=seal["disposition"],source_files_verified=len(plan["execution_source_sha256"]),
        public_files_verified=len(seal["files"]),private_files_verified_local_only=len(seal["private_runtime_files_local_only"]),record_count=len(records),
        prepared_inputs=len(inputs),sent_requests=len(started),received_responses=len(received),replayed_actions=len(calls),
        incomplete_invocation_ids=sorted(set(started)-set(completed)),canonical_payload_files_verified=len(payload_paths),
        tokenizer_sha256=TOKENIZER_SHA,distinct_cli_text_recounts=len(token_counts),tokenization_note="Separate text recounts are not original generated-token segmentation.",
        first_record_utc=records[0]["created_at_utc"],last_record_utc=records[-1]["created_at_utc"],memory=memory,
        maximum_telemetry_gap_seconds=max((b-a).total_seconds() for a,b in zip(stamps,stamps[1:])),
        effective_runtime=seal["effective_runtime"],runtime_prepared_metadata_differences=differences,
        runtime_closure=[r["payload"] for r in records if r["record_type"] in ("runtime_closed","stage_closed")],
        totals_completed_actions_shared_counted_once={key:sum(c[key] for c in calls) for key in totals_keys},
        totals_all_received_responses_shared_counted_once={key:sum(c[key] for c in [*calls,*unexecuted])
            for key in totals_keys if key != "response_processing_seconds"},
        response_processing_scope="Recorded monotonic processing time covers completed actions; no such timing was recorded for the context-stopped response.",
        forks=forks,segments=segments,inputs=inputs,calls=calls,unexecuted_responses=unexecuted)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal-sha256",required=True)
    parser.add_argument("--tokenizer",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "verification output already exists")
    result = verify(args)
    run.base.write_json(args.output,result)
    print({k:result[k] for k in ("status","prepared_inputs","sent_requests","replayed_actions","memory")})
