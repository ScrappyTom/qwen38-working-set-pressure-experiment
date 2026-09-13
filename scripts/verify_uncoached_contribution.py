"""Reconstruct inputs and replay recorded operations without model inference."""
import argparse
from pathlib import Path

import parser_roundtrip as task
from run_uncoached_contribution import Adapter
from working_set_exp.contribution_reply import completion_request_bytes, process_reply
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


def verify(folder):
    records = verify_records(folder / "records.jsonl", folder)
    indexed, by_stem = {}, {}
    for record in records:
        if record["record_type"] != "native_input_prepared":
            continue
        row, stem = record["payload"], record["payload"]["stem"]
        request = task.read(folder / (stem + "-endpoint-request.json"))
        native = (folder / (stem + "-native.txt")).read_bytes()
        assert native == task.expected_native(request) == task.read(folder / (stem + "-template.json"))["prompt"].encode()
        assert row["prompt_tokens"] == len(task.read(folder / (stem + "-tokens.json"))["tokens"])
        assert row["request_sha256"] == sha256_bytes(canonical_json_bytes(request))
        assert row["native_sha256"] == sha256_bytes(native)
        wire = (folder / (stem + "-wire-request.json")).read_bytes()
        assert wire == completion_request_bytes(request)
        wire_row = next(r["payload"] for r in records if r["record_type"] == "wire_input_prepared" and r["payload"]["stem"] == stem)
        assert wire_row["wire_request_sha256"] == sha256_bytes(wire)
        indexed[row["request_sha256"]] = row
        by_stem[stem] = request
    session, adapter = task.initial_session(), Adapter(task)
    assert canonical_json_bytes(task.snapshot(session)) == (folder / "starting-state.json").read_bytes()
    assert task.candidate_bytes(session.candidate) == (folder / "starting-candidate.json").read_bytes()
    def measure(view):
        digest = sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
        assert digest in indexed, "replayed admission state was not measured"
        return indexed[digest]["prompt_tokens"]
    starts = [r["payload"] for r in records if r["record_type"] == "invocation_started"]
    completed = []
    for start in starts:
        tag = start["id"]
        request = adapter.request_for(session.view())
        assert request == by_stem[start["input_stem"]]
        assert measure(session.view()) == start["prompt_tokens"]
        wire = (folder / f"calls/{tag}-wire-request.json").read_bytes()
        assert wire == completion_request_bytes(request) and sha256_bytes(wire) == start["wire_request_sha256"]
        assert set(task.read(folder / f"calls/{tag}-wire-request.json")) == set(request)
        session.mark_delivered(session.view())
        response_path = folder / f"calls/{tag}-endpoint-response.json"
        if not response_path.exists():
            assert start is starts[-1]
            break
        response = task.read(response_path)
        choice, usage = response["choices"][0], response["usage"]
        for field, suffix in (("reasoning_content", "reasoning"), ("content", "content")):
            assert (choice["message"].get(field) or "").encode() == (folder / f"calls/{tag}-assistant-{suffix}.txt").read_bytes()
        assert usage["prompt_tokens"] == start["prompt_tokens"]
        if choice["finish_reason"] != "stop":
            assert start is starts[-1]
            break
        reply = task.read(folder / f"calls/{tag}-reply.json")
        assert reply == task.read(folder / f"calls/{tag}-assistant-content.txt")
        def intermediate(number, operation):
            assert operation == task.read(folder / f"calls/{tag}-operation-{number:02d}.json")
            assert canonical_json_bytes(task.snapshot(session)) == (folder / f"after/{tag}-O{number:02d}-state.json").read_bytes()
            assert task.candidate_bytes(session.candidate) == (folder / f"after/{tag}-O{number:02d}-candidate.json").read_bytes()
        host = process_reply(session, reply, measure, adapter.preceding_feedback, intermediate)
        assert host == task.read(folder / f"calls/{tag}-host-result.json")
        finished = next(r["payload"] for r in records if r["record_type"] == "reply_processed" and r["payload"]["id"] == tag)
        assert measure(session.view()) == finished["feedback_input_tokens"]
        completed.append(tag)
    stem = "final" if (folder / "final-state.json").exists() else "stopped"
    assert canonical_json_bytes(task.snapshot(session)) == (folder / (stem + "-state.json")).read_bytes()
    assert task.candidate_bytes(session.candidate) == (folder / (stem + "-candidate.json")).read_bytes()
    assert adapter.preceding_feedback == task.read(folder / (stem + "-preceding-feedback.json"))
    return dict(status="native_inputs_reconstructed_operations_replayed", model_requests=0,
                records=len(records), native_inputs=len(indexed), returned_scripted_or_model_replies=len(completed),
                actual_operations=session.calls_used, submitted=session.submitted, candidate_id=session.candidate.candidate_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    print(canonical_json_bytes(verify(parser.parse_args().folder)).decode())
