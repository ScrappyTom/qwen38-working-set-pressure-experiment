"""Verify a closed configparser attempt; never send a model request or resume it."""
from pathlib import Path
import argparse

import run_configparser_backport as run
import qualify_compiler_delivery as native_helper
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.custody import verify_records
from working_set_exp.measurement import check_opportunities


def verify(folder):
    seal = run.base.verify_seal(folder)
    plan = run.task.read(folder / "EXECUTION_MANIFEST.json")
    assert sha256_file(folder / "EXECUTION_MANIFEST.json") == seal["execution_manifest_sha256"]
    assert plan["actor"] == seal["actor"] == run.work.ACTOR
    run.check_sources(plan)
    run.verified_package()
    records = verify_records(folder / "records.jsonl", folder)
    value = new_state("verification", run.task.fixture())
    assert run.pilot.reference.candidate_bytes(value.state.candidate) == (folder / "starting-candidate.json").read_bytes()
    initial_request = run.task.read(run.PACKAGE / "initial-request.json")
    initial_native = (run.PACKAGE / "initial-native.txt").read_bytes().decode()
    prepared, started, extracted, actions = {}, [], [], []
    previous_prefix = 0
    attempts_for_next = []
    for record in records:
        kind, row = record["record_type"], record["payload"]
        if kind == "native_input_prepared":
            call, prefix = row["id"], row["externalized_through"]
            assert call == f"C{len(value.pairs)+1:02d}"
            stem = folder / f"admission/{call}-x{prefix:03d}"
            request_raw = Path(str(stem) + "-endpoint-request.json").read_bytes()
            request = load_json_strict(request_raw)
            rebuilt = run.work.request_for(value, prefix)
            assert canonical_json_bytes(rebuilt) == request_raw
            native = Path(str(stem) + "-native.txt").read_bytes()
            assert native_helper.native_for(request, initial_request, initial_native) == native
            template = run.task.read(Path(str(stem) + "-template.json"))
            tokenized = run.task.read(Path(str(stem) + "-tokens.json"))
            assert template["prompt"].encode() == native
            assert len(tokenized["tokens"]) == row["prompt_tokens"]
            assert sha256_bytes(native) == row["native_input_sha256"]
            assert sha256_bytes(request_raw) == row["endpoint_request_sha256"]
            assert row["calls_remaining_before"] == run.work.CALL_LIMIT-len(value.pairs)
            assert row["physical_generation_space"] == run.work.ACTOR["context"]-row["prompt_tokens"]
            prepared[(call, prefix)] = (request, row)
            attempts_for_next.append(row)
        elif kind == "invocation_started":
            request, prepared_row = prepared[(row["id"], row["externalized_through"])]
            prefixes = [r["externalized_through"] for r in attempts_for_next]
            assert prefixes == list(range(previous_prefix, row["externalized_through"]+1))
            assert all(r["prompt_tokens"] > run.work.INPUT_CEILING for r in attempts_for_next[:-1])
            assert prepared_row["prompt_tokens"] == row["prompt_tokens"] <= run.work.INPUT_CEILING
            assert run.work.latest_result_delivered(request, value)
            previous_prefix = row["externalized_through"]
            attempts_for_next = []
            started.append(row)
        elif kind == "response_extracted":
            stem = folder / ("calls/" + row["id"])
            raw = run.task.read(Path(str(stem) + "-endpoint-response.json"))
            message = raw["choices"][0]["message"]
            assert Path(str(stem) + "-assistant-reasoning.txt").read_bytes() == (message.get("reasoning_content") or "").encode()
            assert Path(str(stem) + "-assistant-content.txt").read_bytes() == (message.get("content") or "").encode()
            assert row["usage"] == raw["usage"]
            extracted.append(dict(id=row["id"], usage=raw["usage"], finish_reason=row["finish_reason"]))
        elif kind == "invocation_completed":
            stem = folder / ("calls/" + row["id"])
            host_result = run.task.read(Path(str(stem) + "-host-result.json"))
            action = run.host.shared.strict_action(Path(str(stem) + "-assistant-content.txt").read_bytes())
            request = prepared[(row["id"], row["externalized_through"])][0]
            run.host.validate_action(action, request)
            assert action == host_result["action"] == run.task.read(Path(str(stem) + "-action.json"))
            result = value.execute(action)
            assert result == host_result["result"], "actual tool replay differs: " + row["id"]
            assert run.pilot.reference.candidate_bytes(value.state.candidate) == Path(str(stem) + "-candidate-after.json").read_bytes()
            assert run.pilot.reference.session_bytes(value.state) == Path(str(stem) + "-state-after.json").read_bytes()
            assert run.host.snapshot(value) == run.task.read(folder / ("after/" + row["id"] + "-snapshot.json"))
            assert row["selected_generation_reserve"] == run.work.ACTOR["generation_reserve"]
            assert row["within_proposed_generation_reserve"] == (row["usage"]["completion_tokens"] <= 32768)
            actions.append(dict(id=row["id"], action=action, accepted=result.get("accepted"),
                passed=result.get("passed"), candidate=value.state.candidate.candidate_id))
    assert len(started) == seal["sent_requests"] <= run.work.CALL_LIMIT
    assert len(actions) == seal["completed_responses"]
    terminal_delivery_denial_verified = False
    if attempts_for_next:
        prefixes = [r["externalized_through"] for r in attempts_for_next]
        assert prefixes == list(range(previous_prefix, len(value.pairs)+1))
        assert all(r["prompt_tokens"] > run.work.INPUT_CEILING for r in attempts_for_next[:-1])
        last = attempts_for_next[-1]
        assert last["prompt_tokens"] <= run.work.INPUT_CEILING
        assert not run.work.latest_result_delivered(prepared[(last["id"], last["externalized_through"])][0], value)
        assert not any(r["id"] == last["id"] for r in started)
        denial = [r["payload"] for r in records if r["record_type"] == "immediate_feedback_withheld"]
        assert denial == [{"sent": len(value.pairs), "next_request_sent": False}]
        terminal_delivery_denial_verified = True
    if (folder / "final-snapshot.json").exists():
        assert run.host.snapshot(value) == run.task.read(folder / "final-snapshot.json")
    private = folder / "private-runtime"
    for name, digest in seal["private_runtime_files_local_only"].items():
        if (private / name).exists():
            assert sha256_file(private / name) == digest
    return dict(response_seal_sha256=sha256_file(folder / "RESPONSE_SEAL.json"),
        source_identities_verified=len(plan["source_sha256"]), native_inputs_reconstructed=len(prepared),
        completed_actions_replayed=len(actions), extracted_responses_verified=len(extracted),
        terminal_delivery_denial_verified=terminal_delivery_denial_verified,
        all_sent_inputs_deliver_immediate_result=True, no_model_requests_in_verification=True,
        final_candidate=value.state.candidate.candidate_id, submitted=value.state.submitted,
        current_public_check_passed=value.state.public_check_passed,
        peak_sent_input=max((r["prompt_tokens"] for r in started), default=0),
        input_tokens=sum(r["usage"]["prompt_tokens"] for r in extracted),
        output_tokens=sum(r["usage"]["completion_tokens"] for r in extracted),
        check_opportunities=check_opportunities(value.pairs, call_limit=run.work.CALL_LIMIT),
        actions=actions, responses=extracted,
        direct_transcript_and_artifact_review="separate human-readable audit required; not inferred by this verifier")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=run.RUN)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.run)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(canonical_json_bytes(result))
    print({k: v for k, v in result.items() if k not in ("actions", "responses", "check_opportunities")})
