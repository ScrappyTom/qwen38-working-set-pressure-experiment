"""Verify sealed Shift Ledger evidence and replay its completed prefix without inference."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import difflib
from pathlib import Path
from types import SimpleNamespace

import run_shift_investigation as run
from working_set_exp.custody import verify_records
from working_set_exp.ecological_pilot_v2 import inspection_status
from working_set_exp.event_frame_v3 import resident_pair_v3
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.measurement import check_opportunity
from working_set_exp.runtime import tokenizer_count
from working_set_exp.tools import strict_action

PACKAGE_SHA = "f46919611cf06506d6e56a194ba0200e6b566b28fae8ec8df2c24c55951a14f7"
TOKENIZER_SHA = "d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c"
require, prep = run.require, run.prep


def verify(args):
    # Inventory and chain verification precede access to model response bodies.
    require(sha256_file(run.RUN / "RESPONSE_SEAL.json") == args.seal_sha256, "reviewed seal differs")
    seal = prep.base.verify_seal(run.RUN)
    plan = run.validate_package(prep.PACKAGE, PACKAGE_SHA)
    schedule = [dict(id="S01", seed=prep.SEED, stem="initial/S01")]
    require(seal["package_sha256"] == PACKAGE_SHA and seal["actor"] == plan["actor"], "seal binding differs")
    require(seal["memory_policy"] == plan["memory_policy"], "memory policy differs")
    require((run.RUN / "PACKAGE_MANIFEST.json").read_bytes() == (prep.PACKAGE / "PACKAGE_MANIFEST.json").read_bytes(), "run package differs")
    require((run.RUN / "SPEC.md").read_bytes() == prep.SPEC.read_bytes(), "run specification differs")
    public = {p.relative_to(run.RUN).as_posix() for p in run.RUN.rglob("*")
              if p.is_file() and "private-runtime" not in p.relative_to(run.RUN).parts}
    require(public == {r["path"] for r in seal["files"]} | {"RESPONSE_SEAL.json"}, "unsealed public evidence")
    for name, digest in seal["private_runtime_files_local_only"].items():
        require(sha256_file(run.RUN / "private-runtime" / name) == digest, "private runtime file differs")
    require(sha256_file(args.model) == plan["actor"]["model_sha256"], "offline model differs")
    require(sha256_file(args.tokenizer) == TOKENIZER_SHA, "offline tokenizer differs")
    records = verify_records(run.RUN / "records.jsonl", run.RUN)
    runtime_record = next(r["payload"] for r in records if r["record_type"] == "runtime_prepared")
    launch = load_json_strict((run.RUN / "private-runtime/launch.json").read_bytes())
    require(sha256_file(Path(launch[0])) == plan["actor"]["server_sha256"], "launched server identity differs")
    require(launch == prep.base.launch_args(Path(launch[0]), args.model), "actual runtime arguments differ")
    portable = list(launch)
    portable[0], portable[2] = "<pinned llama-server>", "<selected GGUF>"
    require(runtime_record["public_launch"] == portable, "portable launch differs")
    legacy_actor = runtime_record["actor"]
    runtime_metadata_differences = {k: {"runtime_prepared": legacy_actor.get(k), "active_plan": plan["actor"].get(k)}
        for k in sorted(legacy_actor.keys() | plan["actor"].keys()) if legacy_actor.get(k) != plan["actor"].get(k)}
    require(set(runtime_metadata_differences) <= {"generation_reserve", "minimum_free_gpu_mib"}, "runtime actor differs beyond legacy planning metadata")
    require(records[0]["record_type"] == "stage_prepared" and records[0]["payload"]["owner_approval"] == "Proceed", "owner direction differs")
    require(records[0]["payload"]["maximum_completion_calls"] == 20, "authorized scope differs")
    require(records[-1]["record_type"] == "stage_closed", "stage not closed")
    for row in records:
        if row["record_type"] in ("runtime_closed", "stage_closed"):
            require(row["payload"]["owned_server_shutdown_verified"] and row["payload"]["dedicated_port_free"], "runtime closure incomplete")

    def indexed(kind):
        rows = [r["payload"] for r in records if r["record_type"] == kind]
        require(len({r["id"] for r in rows}) == len(rows), "duplicate " + kind)
        return {r["id"]: r for r in rows}

    prepared, started = indexed("invocation_prepared"), indexed("invocation_started")
    received, completed = indexed("response_received"), indexed("invocation_completed")
    decisions, withheld = indexed("next_turn_decision"), indexed("invocation_withheld")
    require(set(completed) <= set(received) <= set(started) <= set(prepared), "invocation custody order differs")
    require(set(decisions) == set(completed) and not (set(withheld) & set(started)), "next-turn accounting differs")
    for key, rows in (("sent_requests", started), ("received_responses", received), ("completed_responses", completed)):
        require(seal[key] == len(rows) <= 20, "sealed count differs: " + key)
    require(set(prepared) == set(started) | set(withheld), "unclassified prepared input")
    run_starts = [r["payload"]["id"] for r in records if r["record_type"] == "run_started"]
    require(run_starts == [r["id"] for r in schedule][:len(run_starts)], "run order differs")
    finished = {r["payload"]["id"]: r["payload"] for r in records if r["record_type"] == "run_completed"}
    require(seal["runs"] == list(finished.values()), "run summary custody differs")
    expected_health = dict(full_offload=True, context_matches=True, q4_k_and_v=True,
                           mtp_disabled=True, truncation_observed=False, cuda_failure_observed=False)
    for row in records:
        if row["record_type"] in ("invocation_started", "post_response_runtime_check"):
            require(row["payload"]["effective_runtime"] == expected_health, "dispatch health differs")
            require(row["payload"]["memory"]["reference_is_advisory"] is True, "memory policy differs")

    profile = SimpleNamespace(model_path=args.model, tokenizer_path=args.tokenizer)
    counts = {}

    def count(raw):
        if not raw:
            return 0
        if raw not in counts:
            counts[raw] = tokenizer_count(profile, raw)
        return counts[raw]

    fixture = prep.load_fixture(prep.PACKAGE)
    reference = (prep.PACKAGE / "TOOL_REFERENCE.txt").read_text(encoding="utf-8")
    calls, inputs, runs, visited, payload_paths = [], [], [], [], set()
    for scheduled in schedule:
        rid = scheduled["id"]
        if rid not in run_starts:
            continue
        value = new_state(rid, fixture)
        rows = [r for r in prepared.values() if r["run_id"] == rid]
        require(0 < len(rows) <= 20, "run input count outside allowance")
        for index, row in enumerate(rows, 1):
            tag = f"{rid}-{index:03d}"
            require(row["id"] == tag and row["sequence"] == index and row["seed"] == scheduled["seed"], "per-run order differs")
            visited.append(tag)
            path = lambda suffix: run.RUN / "calls" / (tag + "-" + suffix)
            raw, native = path("endpoint-request.json").read_bytes(), path("rendered-prompt.txt").read_bytes()
            require(raw == canonical_json_bytes(prep.request_for(value, reference)), "actual reconstructed input differs: " + tag)
            request = load_json_strict(raw)
            user = load_json_strict(request["messages"][1]["content"].encode())
            require([resident_pair_v3(e) for e in user["active_phase_event_frame"]["events"]] == value.pairs, "resident action/result delivery differs")
            require(user["active_phase_event_frame"]["externalized_payload_through_sequence"] == 0, "unexpected externalization")
            require(user["active_user_authored_step"]["episode_annotation"] == prep.EPISODE_ANNOTATION, "episode annotation differs")
            require(user["resource_state"]["calls_remaining"] == 21-index, "visible remaining allowance differs")
            require(row["calls_remaining_before"] == 21-index and row["completion_sent"] is False, "allowance/preparation status differs")
            require(prep.pilot.reference.candidate_bytes(value.state.candidate) == path("candidate-before.json").read_bytes(), "before candidate differs")
            require(prep.pilot.reference.session_bytes(value.state) == path("state-before.json").read_bytes(), "before session differs")
            template = load_json_strict(path("template-response.json").read_bytes())
            tokens = load_json_strict(path("tokenization.json").read_bytes())["tokens"]
            n = count(native)
            require(template["prompt"].encode() == native and n == len(tokens) == row["prompt_tokens"], "native tokenization differs")
            require(sha256_bytes(native) == row["native_input_sha256"], "native identity differs")
            if index == 1:
                require(raw == (prep.PACKAGE / (scheduled["stem"] + "-request.json")).read_bytes(), "first API input differs")
                require(native == (prep.PACKAGE / (scheduled["stem"] + "-rendered-prompt.txt")).read_bytes(), "first native input differs")
                require(not value.pairs, "cross-run history")
            inputs.append(dict(id=tag, input_tokens=n, sent=tag in started, resident_pairs=len(value.pairs), native_sha256=sha256_bytes(native)))
            if tag in withheld:
                require(n > prep.INPUT_CEILING and index == len(rows), "incorrect capacity withholding")
                require(withheld[tag]["disposition"] == "native_input_capacity_denied" and not withheld[tag]["completion_sent"], "withholding disposition differs")
                continue
            require(n <= prep.INPUT_CEILING and started[tag]["completion_sent"] is True, "unadmitted dispatch")
            if tag not in completed:
                require(index == len(rows) and seal["disposition"] == "stopped_without_retry", "incomplete invocation did not stop attempt")
                continue
            response = load_json_strict(path("endpoint-response.json").read_bytes())
            require(len(response["choices"]) == 1, "response choice count differs")
            choice, usage, timings = response["choices"][0], response["usage"], response["timings"]
            require(choice["finish_reason"] == "stop", "incomplete accepted response")
            message = choice["message"]
            require(set(message) == {"role", "content", "reasoning_content"} and message["role"] == "assistant", "response channel differs")
            reasoning, final = path("assistant-reasoning.txt").read_bytes(), path("assistant-content.txt").read_bytes()
            require(reasoning == message["reasoning_content"].encode() and final == message["content"].encode(), "saved output fields differ")
            require(usage["prompt_tokens"] == timings["prompt_n"] == n, "endpoint prompt accounting differs")
            require(usage["prompt_tokens_details"]["cached_tokens"] == timings["cache_n"] == 0, "cache reuse")
            require(usage["completion_tokens"] == timings["predicted_n"] > 0, "generation accounting differs")
            require(usage["total_tokens"] == n + usage["completion_tokens"] <= prep.ACTOR["context"], "physical accounting differs")
            action = strict_action(final)
            require(canonical_json_bytes(action) == path("action.json").read_bytes(), "saved action differs")
            result = value.execute(action)
            host = dict(action=action, executed=True, execution_attempted=True, finish_reason="stop", result=result)
            require(canonical_json_bytes(host) == path("host-result.json").read_bytes(), "actual/replayed result differs: " + tag)
            require(prep.pilot.reference.candidate_bytes(value.state.candidate) == path("candidate-after.json").read_bytes(), "successor differs")
            require(prep.pilot.reference.session_bytes(value.state) == path("state-after.json").read_bytes(), "after session differs")
            done, decision = completed[tag], decisions[tag]
            require(done["host_result"] == host and done["usage"] == usage and done["timings"] == timings, "record/output disagreement")
            opportunity = check_opportunity(calls_used=index-1, call_limit=20, result=result) if action["action"] == "check" else None
            require(decision["check_opportunity"] == opportunity and decision["calls_remaining_after"] == 20-index, "correction opportunity differs")
            require(decision["submitted"] == value.state.submitted and decision["next_request_sent"] is False, "next-turn decision differs")
            require(decision["next_step"] == ("terminal" if value.state.submitted else "reconstruct_then_check_admission"), "terminal decision differs")
            for mapping in (value.result_payloads, value.event_payloads):
                for handle, body in mapping.items():
                    relative = f"payloads/{rid}/{handle}.json"
                    require((run.RUN / relative).read_bytes() == body, "canonical saved payload differs")
                    payload_paths.add(relative)
            next_tag = f"{rid}-{index+1:03d}"
            calls.append(dict(id=tag, run_id=rid, sequence=index, input_tokens=n, output_tokens=usage["completion_tokens"],
                retokenized_reasoning_text_tokens=count(reasoning), retokenized_final_text_tokens=count(final),
                request_seconds=done["elapsed_seconds"], response_processing_seconds=decision["response_processing_seconds"],
                physical_tokens_remaining=prep.ACTOR["context"]-usage["total_tokens"],
                action=action, accepted=result.get("accepted"), passed=result.get("passed"), check_opportunity=opportunity,
                result_json_bytes=len(canonical_json_bytes(result)),
                read_content_bytes=len(result["content"].encode()) if action["action"] == "read" and result.get("accepted") else None,
                result_in_next_saved_input=next_tag in prepared, result_in_next_sent_input=next_tag in started,
                submitted=value.state.submitted, replay_exact=True))
            print(f"Verified {tag}: native input, separate outputs, result, successor and next-turn decision", flush=True)
        selected = [c for c in calls if c["run_id"] == rid]
        summary = finished.get(rid)
        if summary:
            require(summary["actions"] == len(value.pairs), "run count differs")
            require(summary["submitted"] == value.state.submitted and summary["public_check_passed"] == value.state.public_check_passed, "run flags differ")
            require(summary["final_candidate_id"] == value.state.candidate.candidate_id, "final candidate differs")
            require((run.RUN / "runs" / (rid + "-pairs.json")).read_bytes() == canonical_json_bytes(value.pairs), "final history differs")
        differences = []
        for name in sorted(fixture.initial.file_map.keys() | value.state.candidate.file_map.keys()):
            before = fixture.initial.file_map.get(name, b"").decode().splitlines(keepends=True)
            after = value.state.candidate.file_map.get(name, b"").decode().splitlines(keepends=True)
            if before != after:
                differences.append(dict(path=name, diff="".join(difflib.unified_diff(before, after, fromfile="before/"+name, tofile="after/"+name))))
        runs.append(dict(id=rid, seed=scheduled["seed"], completed_summary=summary,
            totals={key: sum(c[key] for c in selected) for key in ("input_tokens", "output_tokens", "retokenized_reasoning_text_tokens", "retokenized_final_text_tokens", "request_seconds", "response_processing_seconds")},
            peak_sent_input=max((c["input_tokens"] for c in inputs if c["sent"] and c["id"].startswith(rid)), default=0),
            target_inspection_before_first_edit=inspection_status(value.pairs, (prep.TARGET,), initial_candidate=fixture.initial),
            action_counts=dict(Counter(c["action"]["action"] for c in selected)), final_differences=differences))
    require(visited == list(prepared), "unvisited or interleaved invocation")
    telemetry = [line.split(",") for line in (run.RUN / "memory.csv").read_text().splitlines()]
    stamps = [datetime.strptime(r[0].strip(), "%Y/%m/%d %H:%M:%S.%f") for r in telemetry]
    free = [int(r[-1]) for r in telemetry]
    require(seal["memory"] == dict(samples=len(free), min_free_mib=min(free), max_free_mib=max(free)), "memory summary differs")
    return dict(status="sealed_completed_prefix_verified_and_replayed", scope="Offline verification; zero completion requests; does not certify direct transcript review.",
        package_sha256=PACKAGE_SHA, response_seal_sha256=args.seal_sha256, verifier_sha256=sha256_file(Path(__file__)),
        episode_annotation=prep.EPISODE_ANNOTATION, disposition=seal["disposition"], owner_approval=records[0]["payload"]["owner_approval"], actor=plan["actor"],
        public_files_verified=len(seal["files"]), private_files_verified_local_only=len(seal["private_runtime_files_local_only"]),
        record_count=len(records), source_identities=len(plan["source_sha256"]), prepared_inputs=len(prepared),
        sent_requests=len(started), received_responses=len(received), replayed_actions=len(completed),
        unreplayed_started_ids=sorted(set(started)-set(completed)), canonical_payload_files_verified=len(payload_paths),
        tokenizer_sha256=TOKENIZER_SHA, distinct_cli_text_recounts=len(counts),
        tokenization_note="Separate saved-text counts are not original generated-token segmentation.",
        first_record_utc=records[0]["created_at_utc"], last_record_utc=records[-1]["created_at_utc"], memory=seal["memory"],
        maximum_telemetry_gap_seconds=max((b-a).total_seconds() for a,b in zip(stamps,stamps[1:])),
        effective_runtime=seal["effective_runtime"], runtime_prepared_metadata_differences=runtime_metadata_differences,
        runs=runs, inputs=inputs, calls=calls)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--seal-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "verification output already exists")
    result = verify(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(result))
    print({k: result[k] for k in ("status", "public_files_verified", "prepared_inputs", "sent_requests", "replayed_actions")})


if __name__ == "__main__":
    main()
