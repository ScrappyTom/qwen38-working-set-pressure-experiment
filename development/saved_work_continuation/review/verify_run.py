"""Verify the sealed saved-work attempt offline; never send a model request.

Run only after the live runtime closes. Exact replay and tokenization support,
but cannot replace, direct reading of the complete prompts and responses.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import run_saved_work_continuation as runner
import saved_work_continuation as work
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count
from working_set_exp.tools import strict_action

TOKENIZER_SHA = "d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c"
RUN = work.AREA / "run-001"
require, read = work.require, work.read


def verify(args):
    require(not args.output.exists(), "preserve the existing verification")
    require(sha256_file(RUN / "RESPONSE_SEAL.json") == args.seal_sha256, "seal differs")
    seal = runner.base.verify_seal(RUN)
    plan = read(runner.MANIFEST)
    runner.check_sources(plan)
    require((RUN / "EXECUTION_MANIFEST.json").read_bytes() == runner.MANIFEST.read_bytes(), "manifest differs")
    require((RUN / "SPEC.md").read_bytes() == (work.AREA / "SPEC.md").read_bytes(), "specification differs")
    require(seal["actor"] == plan["actor"] == work.ACTOR, "selected actor differs")
    require(seal["memory_policy"] == plan["memory_policy"], "memory policy differs")
    require(seal["execution_manifest_sha256"] == sha256_file(runner.MANIFEST), "execution binding differs")
    public = {p.relative_to(RUN).as_posix() for p in RUN.rglob("*")
              if p.is_file() and "private-runtime" not in p.relative_to(RUN).parts}
    require(public == {r["path"] for r in seal["files"]} | {"RESPONSE_SEAL.json"}, "unsealed public evidence")
    for name, digest in seal["private_runtime_files_local_only"].items():
        require(sha256_file(RUN / "private-runtime" / name) == digest, "private runtime evidence differs")
    records = verify_records(RUN / "records.jsonl", RUN)
    require(len(records) == seal["record_count"], "record count differs")
    require(records[0]["record_type"] == "attempt_reserved" and records[-1]["record_type"] == "stage_closed", "attempt is not closed")
    require(records[0]["payload"]["manifest_sha256"] == sha256_file(runner.MANIFEST), "approval binding differs")
    require("Current owner goal instruction:" in records[0]["payload"]["owner_approval"], "authorization basis differs")
    closures = [r["payload"] for r in records if r["record_type"] == "runtime_closed"]
    require(len(closures) == 1 and closures[0]["owned_server_shutdown_verified"]
            and closures[0]["dedicated_port_free"], "owned runtime is not closed")
    launch = read(RUN / "private-runtime/launch.json")
    model, server = Path(launch[2]), Path(launch[0])
    require(sha256_file(model) == plan["actor"]["model_sha256"], "model binary differs")
    require(sha256_file(server) == plan["actor"]["server_sha256"], "server binary differs")
    require(launch == runner.base.launch_args(server, model), "runtime launch differs")
    require(sha256_file(args.tokenizer) == TOKENIZER_SHA, "tokenizer differs")
    profile = SimpleNamespace(model_path=model, tokenizer_path=args.tokenizer)
    counts = {}

    def count(raw):
        if not raw:
            return 0
        if raw not in counts:
            counts[raw] = tokenizer_count(profile, raw)
        return counts[raw]

    def indexed(kind):
        rows = [r["payload"] for r in records if r["record_type"] == kind]
        require(len({r["id"] for r in rows}) == len(rows), "duplicate " + kind)
        return {r["id"]: r for r in rows}

    started, received, completed = [indexed(k) for k in
        ("invocation_started", "response_received", "invocation_completed")]
    feedback = indexed("action_feedback_recorded")
    require(set(completed) == set(feedback) and set(completed) <= set(received) <= set(started), "response custody differs")
    for name, rows in (("sent_requests", started), ("received_responses", received), ("completed_responses", completed)):
        require(seal[name] == len(rows) <= work.MAX_CALLS, "sealed completion count differs")
    require(len(set(started) - set(completed)) <= 1, "more than one unfinished invocation")
    health = dict(context_matches=True, full_offload=True, mtp_disabled=True,
                  q4_k_and_v=True, truncation_observed=False, cuda_failure_observed=False)
    for item in started.values():
        require(item["effective_runtime"] == health and item["memory"]["reference_is_advisory"], "dispatch health differs")
    runtime = next(r["payload"] for r in records if r["record_type"] == "runtime_prepared")
    require(runtime["actor"] == work.ACTOR and runtime["memory_policy"] == plan["memory_policy"], "runtime metadata differs")

    # Use the qualified complete native envelope, replacing only its exact user
    # message. All live calls have the same system text, template and thinking.
    initial_request = read(work.PACKAGE / "initial-request.json")
    initial_native = (work.PACKAGE / "initial-native.txt").read_bytes()
    initial_user = initial_request["messages"][1]["content"].strip().encode()
    require(initial_native.count(initial_user) == 1, "initial user span is not unique")
    native_before, native_after = initial_native.split(initial_user)

    value = work.starting_state()
    ranges, groups, setup_start = [[1, 3]], {}, {}
    phase_used, sent, prefix = Counter(), 0, 0
    prepared, calls, input_rows, restarts = {}, [], [], []
    previous_preparation = None
    payload_paths = set()
    final_summary = None
    for record in records:
        kind, p = record["record_type"], record["payload"]
        if kind == "assisted_acquisition":
            phase = p["phase"]
            if phase not in groups:
                groups[phase] = []
                setup_start[phase] = len(value.pairs) + 1
            pair = read(RUN / f"setup/P{phase}-{p['sequence']:03d}-pair.json")
            require(p["model_action"] is False and p["completion_sent"] is False, "setup charged as actor action")
            result = value.execute(pair["response"])
            require(result == pair["result"] and p["sequence"] == len(value.pairs), "assisted action replay differs")
            groups[phase].append(len(value.pairs))
        elif kind == "working_state_saved":
            stem = p["stem"]
            require((RUN / (stem + "-snapshot.json")).read_bytes() == canonical_json_bytes(work.compiler.snapshot(value)), "saved snapshot differs: " + stem)
            require((RUN / (stem + "-candidate.json")).read_bytes() == work.pilot.reference.candidate_bytes(value.state.candidate), "saved candidate differs: " + stem)
            for mapping in (value.result_payloads, value.event_payloads):
                for handle, raw in mapping.items():
                    path = f"payloads/{stem}/{handle}.json"
                    require((RUN / path).read_bytes() == raw, "saved canonical payload differs")
                    payload_paths.add(path)
            if stem.startswith("setup/P"):
                phase = int(stem[-1])
                require(len(groups[phase]) == (4 if phase == 1 else 5), "setup action count differs")
                ranges.append([setup_start[phase], len(value.pairs)])
        elif kind == "deliberate_working_context_restart":
            require(value.pairs[-1]["response"]["action"] == "check" and value.pairs[-1]["result"]["accepted"], "restart not after accepted check")
            require(any(work.report_changed(x["response"], x["result"]) for x in value.pairs[7:]), "restart before report edit")
            require(p["prefix"] == len(value.pairs) and p["candidate_id"] == value.state.candidate.candidate_id,
                    "restart state differs")
            require(p["semantic_assessment_used"] is False and p["prior_thinking_reintroduced"] is False, "restart used semantic intervention")
            prefix = p["prefix"]
            restarts.append(p)
        elif kind == "native_input_prepared":
            tag, phase, selected_prefix = p["id"], p["phase"], p["externalized_through"]
            require(p["phase_calls_used"] == phase_used[phase] and p["calls_remaining_before"] == work.PHASE_LIMIT - phase_used[phase], "phase allowance differs")
            if previous_preparation is None or previous_preparation["id"] != tag:
                require(selected_prefix == prefix, "admission skipped the current prefix")
            else:
                require(previous_preparation["prompt_tokens"] > work.INPUT_CEILING
                        and selected_prefix == previous_preparation["externalized_through"] + 1,
                        "admission did not try consecutive oldest prefixes")
            previous_preparation = p
            stem = f"admission/{tag}-x{selected_prefix:03d}"
            raw = (RUN / (stem + "-endpoint-request.json")).read_bytes()
            request = read(RUN / (stem + "-endpoint-request.json"))
            expected = work.request_for(value, phase=phase, phase_used=phase_used[phase],
                total_used=sent, externalized=selected_prefix, setup_ranges=ranges)
            require(raw == canonical_json_bytes(expected), "actual input differs from reconstructed state: " + tag)
            require(request["messages"][0] == initial_request["messages"][0], "system/reference changed")
            native = (RUN / (stem + "-native.txt")).read_bytes()
            require(native == native_before + request["messages"][1]["content"].strip().encode() + native_after,
                    "complete native envelope differs")
            require(native == read(RUN / (stem + "-template.json"))["prompt"].encode(), "template body differs")
            n = count(native)
            require(n == len(read(RUN / (stem + "-tokens.json"))["tokens"]) == p["prompt_tokens"], "native count differs")
            require(sha256_bytes(raw) == p["endpoint_request_sha256"] and sha256_bytes(native) == p["native_input_sha256"], "native hashes differ")
            require(p["physical_generation_space"] == work.ACTOR["context"] - n, "physical allowance differs")
            delivered = [i for i in range(1, len(value.pairs) + 1) if work.result_delivered(request, value, i)]
            row = dict(id=tag, phase=phase, externalized_through=selected_prefix, input_tokens=n,
                latest_sequence=len(value.pairs), delivered_result_sequences=delivered,
                assembled_group_delivered=work.delivered(request, value, groups[phase]),
                sent=tag in started and started[tag]["externalized_through"] == selected_prefix)
            prepared[tag, selected_prefix] = (p, request, row)
            input_rows.append(row)
        elif kind == "invocation_started":
            _, request, row = prepared[p["id"], p["externalized_through"]]
            require(row["sent"] and row["input_tokens"] <= work.INPUT_CEILING, "unadmitted dispatch")
            require(work.result_delivered(request, value, len(value.pairs)), "immediate feedback omitted at dispatch")
            prefix = p["externalized_through"]
            sent += 1
        elif kind == "invocation_completed":
            tag, phase = p["id"], p["phase"]
            _, request, row = prepared[tag, p["externalized_through"]]
            path = lambda suffix: RUN / "calls" / (tag + "-" + suffix)
            response = read(path("endpoint-response.json"))
            require(len(response["choices"]) == 1, "multiple output choices")
            choice, usage, timing = response["choices"][0], response["usage"], response["timings"]
            message = choice["message"]
            require(choice["finish_reason"] == "stop" and set(message) == {"role", "reasoning_content", "content"}, "unexpected output channel")
            reasoning, final = path("assistant-reasoning.txt").read_bytes(), path("assistant-content.txt").read_bytes()
            require(reasoning == message["reasoning_content"].encode() and final == message["content"].encode(), "raw/extracted output differs")
            require(usage == p["usage"] and usage["prompt_tokens"] == timing["prompt_n"] == row["input_tokens"], "input usage differs")
            require(usage["completion_tokens"] == timing["predicted_n"] > 0 and usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"] <= work.ACTOR["context"], "generation usage differs")
            require(usage["prompt_tokens_details"]["cached_tokens"] == timing["cache_n"] == 0, "cache reused")
            require(p["selected_generation_reserve"] == 32768 and p["within_selected_generation_reserve"] == (usage["completion_tokens"] <= 32768), "selected reserve measurement differs")
            action = strict_action(final)
            work.compiler.validate_action(action, request)
            require(path("action.json").read_bytes() == canonical_json_bytes(action), "final action transformed")
            result = value.execute(action)
            host = dict(action=action, execution_attempted=True, executed=True, finish_reason="stop", result=result)
            require(host == p["host_result"] and path("host-result.json").read_bytes() == canonical_json_bytes(host), "tool replay differs: " + tag)
            require(path("candidate-after.json").read_bytes() == work.pilot.reference.candidate_bytes(value.state.candidate), "actual successor differs")
            require(path("state-after.json").read_bytes() == work.pilot.reference.session_bytes(value.state), "session state differs")
            require(feedback[tag]["sequence"] == len(value.pairs), "feedback sequence differs")
            phase_used[phase] += 1
            calls.append(dict(id=tag, phase=phase, sequence=len(value.pairs), input_tokens=row["input_tokens"],
                output_tokens=usage["completion_tokens"], request_seconds=p["elapsed_seconds"],
                response_processing_seconds=feedback[tag]["response_processing_seconds"],
                reasoning_characters=len(message["reasoning_content"]), final_characters=len(message["content"]),
                physical_tokens_remaining=work.ACTOR["context"] - usage["total_tokens"],
                action=action, accepted=result.get("accepted"), passed=result.get("passed"),
                phase_actions_remaining=work.PHASE_LIMIT-phase_used[phase], replay_exact=True))
            print("Replayed " + tag, flush=True)
        elif kind == "continuation_completed":
            require(p["sent_requests"] == sent and p["final_candidate"] == value.state.candidate.candidate_id,
                    "terminal candidate/count differs")
            require(p["submitted"] == value.state.submitted and p["current_public_check_passed"] == value.state.public_check_passed,
                    "terminal state differs")
            final_summary = p
    require(sent == len(started) and len(calls) == len(completed), "unreplayed action")
    require(all(n <= work.PHASE_LIMIT for n in phase_used.values()) and len(restarts) <= 1, "phase scope exceeded")
    # Incomplete response paths are preserved but this verifier must not claim
    # complete verification until their exact failure has been inspected too.
    require(set(started) == set(completed), "unfinished invocation needs a separate exact failure audit")
    require(final_summary is not None, "stopped loop needs a separate terminal audit")
    require(seal["memory"] == runner.base.memory_stats(RUN / "memory.csv"), "memory summary differs")
    stamps = [datetime.strptime(line.split(",")[0], "%Y/%m/%d %H:%M:%S.%f")
              for line in (RUN / "memory.csv").read_text().splitlines()]
    runner.check_sources(plan)
    result = dict(status="sealed_run_verified_offline", new_completion_requests=0,
        verification_source_sha256=sha256_file(Path(__file__)), response_seal_sha256=args.seal_sha256,
        execution_manifest_sha256=sha256_file(runner.MANIFEST), public_files=len(seal["files"]),
        private_runtime_files_verified=len(seal["private_runtime_files_local_only"]), source_files_verified=len(plan["source_sha256"]),
        records=len(records), initial_saved_actions_replayed=3, total_operations_replayed=len(value.pairs),
        canonical_payload_copies_verified=len(payload_paths), native_inputs=input_rows, calls=calls,
        deliberate_restarts=restarts, terminal=final_summary, memory=seal["memory"],
        maximum_sampling_gap_seconds=max((b-a).total_seconds() for a,b in zip(stamps,stamps[1:])),
        exact_raw_output_action_result_and_successor_verified=True,
        complete_native_messages_and_cli_token_counts_verified=True,
        direct_transcript_reading_not_certified_by_this_script=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(canonical_json_bytes(result))
    print({k: result[k] for k in ("status", "public_files", "records", "total_operations_replayed", "terminal")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal-sha256", required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args())
