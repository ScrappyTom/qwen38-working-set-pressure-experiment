"""Verify a closed bounded-host attempt using recorded native sizing; no inference."""
import argparse
from pathlib import Path

import bounded_parser as task
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.measurement import check_opportunities
from working_set_exp.working_session import INPUT_LIMIT


def verify_source_bytes(source, candidate):
    raw = candidate.file_map[source["path"]]
    assert source["candidate_id"] == candidate.candidate_id
    assert source["file_sha256"] == sha256_bytes(raw)
    lines = raw.decode().splitlines(keepends=True)
    first, last = source["returned_start_line"], source["returned_end_line"]
    assert source["content"] == "".join(lines[first-1:last])
    assert source["next_start_line"] == (last+1 if last < len(lines) else None)


def verify(folder):
    seal = task.read(folder / "RESPONSE_SEAL.json")
    manifest = task.read(folder / "EXECUTION_MANIFEST.json")
    assert sha256_file(folder / "EXECUTION_MANIFEST.json") == seal["manifest_sha256"]
    assert manifest["source_sha256"] == seal["source_sha256"]
    task.verify_sources(manifest["source_sha256"])
    assert manifest["actor"] == seal["actor"] == task.ACTOR
    assert sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"]
    for row in seal["files"]:
        data = (folder / row["path"]).read_bytes()
        assert len(data) == row["size_bytes"] and sha256_bytes(data) == row["sha256"]
    records = verify_records(folder / "records.jsonl", folder)
    assert len(records) == seal["record_count"]
    prepared, by_digest = {}, {}
    for record in records:
        if record["record_type"] != "native_input_prepared":
            continue
        row = record["payload"]
        stem = row["stem"]
        raw = (folder / (stem + "-endpoint-request.json")).read_bytes()
        req = task.read(folder / (stem + "-endpoint-request.json"))
        native = (folder / (stem + "-native.txt")).read_bytes()
        count = task.read(folder / (stem + "-count.json"))
        assert raw == canonical_json_bytes(req)
        assert sha256_bytes(raw) == row["request_sha256"]
        assert native == task.expected_native(req)
        assert native == task.read(folder / (stem + "-template.json"))["prompt"].encode()
        assert len(task.read(folder / (stem + "-tokens.json"))["tokens"]) == row["prompt_tokens"]
        assert sha256_bytes(native) == row["native_sha256"]
        assert row["physical_generation_space"] == task.ACTOR["context"] - row["prompt_tokens"]
        assert {k: row[k] for k in count} == count
        prepared[stem] = (req, row)
        by_digest[row["request_sha256"]] = row

    used_inputs = set()

    def measure(view):
        digest = sha256_bytes(canonical_json_bytes(task.request_for(view)))
        assert digest in by_digest, "replayed admission was not measured in the actual run"
        used_inputs.add(digest)
        return by_digest[digest]["prompt_tokens"]

    session = task.initial_session()
    assert task.candidate_bytes(session.candidate) == (folder / "starting-candidate.json").read_bytes()
    assert canonical_json_bytes(task.snapshot(session)) == (folder / "starting-state.json").read_bytes()
    starts, responses, actions, received_times = [], [], [], {}
    latest_start = None
    for record in records:
        kind, row = record["record_type"], record["payload"]
        if kind == "invocation_started":
            assert row["id"] == f"C{len(starts)+1:02d}"
            req, native_row = prepared[row["input_stem"]]
            view = session.view()
            assert task.request_for(view) == req, "actual decision input differs from reconstructed state"
            assert measure(view) == row["prompt_tokens"] <= INPUT_LIMIT
            for source in view["working_set"]["sources"] + session.feedback_sources(view["latest_feedback"]):
                verify_source_bytes(source, session.candidate)
            if not starts:
                for key in ("prompt_tokens", "request_sha256", "native_sha256"):
                    assert native_row[key] == manifest["initial"][key]
            session.mark_delivered(view)
            starts.append(row)
            latest_start = row
        elif kind == "response_received":
            received_times[row["id"]] = row["elapsed_seconds"]
        elif kind == "response_extracted":
            tag = row["id"]
            raw = task.read(folder / f"calls/{tag}-endpoint-response.json")
            assert len(raw["choices"]) == 1
            choice = raw["choices"][0]
            message, usage = choice["message"], raw["usage"]
            assert (folder / f"calls/{tag}-assistant-reasoning.txt").read_bytes() == (message.get("reasoning_content") or "").encode()
            assert (folder / f"calls/{tag}-assistant-content.txt").read_bytes() == (message.get("content") or "").encode()
            assert row["usage"] == usage and row["finish_reason"] == choice["finish_reason"]
            assert latest_start["id"] == tag and usage["prompt_tokens"] == latest_start["prompt_tokens"]
            assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"] <= task.ACTOR["context"]
            assert usage.get("prompt_tokens_details", {}).get("cached_tokens") == 0
            assert raw.get("timings", {}).get("cache_n") == 0
            responses.append(dict(id=tag, usage=usage, finish_reason=choice["finish_reason"],
                elapsed_seconds=received_times[tag], reasoning_characters=len(message.get("reasoning_content") or ""),
                final_characters=len(message.get("content") or "")))
        elif kind == "action_executed":
            tag = row["id"]
            action = task.read(folder / f"calls/{tag}-assistant-content.txt")
            saved = task.read(folder / f"calls/{tag}-host-result.json")
            assert saved["executed"] and action == saved["action"] == task.read(folder / f"calls/{tag}-action.json")
            assert responses[-1]["id"] == tag and responses[-1]["finish_reason"] == "stop"
            before = session.candidate
            prior_pairs = list(session.pairs)
            result = session.execute(action, measure)
            assert result == saved["result"], "actual action replay differs: " + tag
            if action["action"] == "patch" and result["accepted"]:
                path = action["path"]
                text = before.file_map[path].decode()
                assert text.count(action["old"]) == 1
                assert session.candidate.file_map[path] == text.replace(action["old"], action["new"], 1).encode()
                assert {p:b for p,b in before.files if p != path} == {p:b for p,b in session.candidate.files if p != path}
                assert action["expected_candidate_id"] == before.candidate_id
                assert action["expected_file_sha256"] == before.file_sha256(path)
            else:
                assert session.candidate == before, "read-only or rejected action changed saved work"
            for source in session.sources():
                verify_source_bytes(source, session.candidate)
            if result.get("kind") == "saved_bytes":
                prefix, number = action["handle"].split("-")
                original = canonical_json_bytes(prior_pairs[int(number)-1]["result" if prefix == "RES" else "response"])
                first = result["offset"]
                data = result["exact_utf8"].encode()
                assert data == original[first:first+len(data)]
                assert result["total_bytes"] == len(original) and result["sha256"] == sha256_bytes(original)
                assert result["next_offset"] == (first+len(data) if first+len(data) < len(original) else None)
            assert task.candidate_bytes(session.candidate) == (folder / f"after/{tag}-candidate.json").read_bytes()
            assert canonical_json_bytes(task.snapshot(session)) == (folder / f"after/{tag}-state.json").read_bytes(), tag
            for sequence, diff in session.diffs.items():
                assert (folder / f"diffs/EVT-{sequence:04d}.patch").read_bytes() == diff.encode()
            actions.append(dict(id=tag, action=action["action"], path=action.get("path"), accepted=result["accepted"],
                passed=result.get("passed"), error=result.get("error"), candidate_id=session.candidate.candidate_id,
                processing_and_admission_seconds=row["processing_and_admission_seconds"],
                source_intervals=session.ranges, feedback_scope=(session.last or {}).get("output_scope", "complete")))
    assert len(starts) == seal["sent_requests"] <= manifest["maximum_requests"]
    assert len(actions) == seal["completed_responses"]
    assert used_inputs == set(by_digest), "a native preparation is not explained by deterministic replay"
    if (folder / "final-state.json").exists():
        assert canonical_json_bytes(task.snapshot(session)) == (folder / "final-state.json").read_bytes()
        assert task.candidate_bytes(session.candidate) == (folder / "final-candidate.json").read_bytes()
    for sequence, pair in enumerate(session.pairs, 1):
        assert session.payload(f"RES-{sequence:04d}") == canonical_json_bytes(pair["result"])
        assert session.payload(f"EVT-{sequence:04d}") == canonical_json_bytes(pair["response"])
    local_private_verified = []
    for name, digest in seal["private_runtime_files_local_only"].items():
        path = folder / "private-runtime" / name
        if path.exists():
            assert sha256_file(path) == digest
            local_private_verified.append(name)
    assert seal["port_free"]
    censored = [r["id"] for r in starts if r["id"] not in {x["id"] for x in responses}]
    if seal.get("closure_method") == "reviewer_external_process_group_interrupt":
        stop = task.read(folder / seal["reviewer_stop_receipt"])
        assert stop["preservation"]["record_file_sha256"] == sha256_file(folder / "records.jsonl")
        assert stop["preservation"]["last_record_sha256"] == records[-1]["record_sha256"]
        assert stop["preservation"]["original_record_count"] == len(records)
        assert stop["disposition"] == seal["disposition"] and censored == ["C09"]
        assert not list((folder / "calls").glob("C09-*"))
        assert not any(r["record_type"] == "task_loop_completed" for r in records)
    finished = [r["payload"] for r in records if r["record_type"] == "task_loop_completed"]
    return dict(response_seal_sha256=sha256_file(folder / "RESPONSE_SEAL.json"), disposition=seal["disposition"],
        source_identities_verified=len(manifest["source_sha256"]), sealed_artifacts_verified=len(seal["files"]),
        native_inputs_verified=len(prepared), actual_actions_replayed=len(actions), raw_responses_verified=len(responses),
        all_actual_inputs_and_admission_trials_reconstructed=True, private_runtime_files_verified=local_private_verified,
        no_model_requests_in_verification=True, final_candidate=session.candidate.candidate_id,
        submitted=session.submitted, current_check=session.check_state(), memory=seal["memory"],
        sent_requests=len(starts), completed_responses=len(responses), censored_requests=censored,
        closure_method=seal.get("closure_method", "runner"),
        peak_sent_input=max((r["prompt_tokens"] for r in starts), default=0),
        input_tokens=sum(r["usage"]["prompt_tokens"] for r in responses),
        output_tokens=sum(r["usage"]["completion_tokens"] for r in responses),
        model_request_seconds=sum(r["elapsed_seconds"] for r in responses),
        completed_loop=finished[0] if finished else None,
        check_opportunities=check_opportunities(session.pairs[session.starting_archive_length:], call_limit=session.call_limit),
        actions=actions, responses=responses,
        direct_review="Separate direct review of complete thinking, final actions, inputs and artifacts is required.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=task.RUN)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = verify(args.run)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(canonical_json_bytes(value))
    print({k: v for k, v in value.items() if k not in {"actions", "responses", "check_opportunities"}})
