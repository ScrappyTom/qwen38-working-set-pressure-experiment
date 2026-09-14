"""Offline custody, exact-input and operation replay for this identified task."""
import argparse
import json
from pathlib import Path

import interpolation_contribution as task
import run_uncoached_contribution as runner
from working_set_exp.contribution_reply import completion_request_bytes, process_reply
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


def verify(folder):
    seal_path = folder / ("RESPONSE_SEAL.json" if (folder / "RESPONSE_SEAL.json").exists() else "SEAL.json")
    seal = task.read(seal_path)
    task.require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "seal inventory differs")
    for row in seal["files"]:
        path = folder / row["path"]
        task.require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"], "sealed artifact changed: " + row["path"])
    task.verify_sources(seal["source_sha256"])
    records = verify_records(folder / "records.jsonl", folder)
    adapter, session = runner.Adapter(task), task.initial_session()
    counts = {}
    for record in records:
        if record["record_type"] != "native_input_prepared":
            continue
        row, stem = record["payload"], record["payload"]["stem"]
        request = task.read(folder / (stem + "-endpoint-request.json"))
        native = (folder / (stem + "-native.txt")).read_bytes()
        task.require(native == adapter.expected_native(request) == task.read(folder / (stem + "-template.json"))["prompt"].encode(), "native input differs")
        task.require(row["prompt_tokens"] == len(task.read(folder / (stem + "-tokens.json"))["tokens"]), "token count differs")
        task.require((folder / (stem + "-wire-request.json")).read_bytes() == completion_request_bytes(request), "wire serialization differs")
        counts[sha256_bytes(canonical_json_bytes(request))] = row["prompt_tokens"]
    def measure(view):
        return counts[sha256_bytes(canonical_json_bytes(adapter.request_for(view)))]
    task.require(canonical_json_bytes(task.snapshot(session)) == (folder / "starting-state.json").read_bytes(), "starting state differs")
    completed = 0
    for record in records:
        if record["record_type"] != "invocation_started":
            continue
        tag = record["payload"]["id"]
        task.require((folder / f"calls/{tag}-wire-request.json").read_bytes() == completion_request_bytes(adapter.request_for(session.view())), "sent request differs")
        task.require(measure(session.view()) == record["payload"]["prompt_tokens"], "sent count differs")
        session.mark_delivered(session.view())
        session.begin_request()
        response_path = folder / f"calls/{tag}-endpoint-response.json"
        if not response_path.exists():
            break
        response = task.read(response_path)
        choice = response["choices"][0]
        for field, suffix in (("content", "content"), ("reasoning_content", "reasoning")):
            task.require((choice["message"].get(field) or "").encode() == (folder / f"calls/{tag}-assistant-{suffix}.txt").read_bytes(), "response extraction differs")
        if choice["finish_reason"] != "stop":
            break
        reply = task.read(folder / f"calls/{tag}-reply.json")
        task.require(reply == json.loads(choice["message"]["content"]), "selected reply differs")
        def intermediate(number, operation):
            task.require(operation == task.read(folder / f"calls/{tag}-operation-{number:02d}.json"), "operation differs")
            stem = f"after/{tag}-O{number:02d}"
            task.require(canonical_json_bytes(task.snapshot(session)) == (folder / (stem + "-state.json")).read_bytes(), "intermediate state differs")
            task.require(task.candidate_bytes(session.candidate) == (folder / (stem + "-candidate.json")).read_bytes(), "saved work differs")
        actual = process_reply(session, reply, measure, adapter.preceding_feedback, intermediate)
        task.require(actual == task.read(folder / f"calls/{tag}-host-result.json"), "actual feedback differs")
        completed += 1
    final = "final" if (folder / "final-state.json").exists() else "stopped"
    task.require(canonical_json_bytes(task.snapshot(session)) == (folder / (final + "-state.json")).read_bytes(), "final state differs")
    task.require(task.candidate_bytes(session.candidate) == (folder / (final + "-candidate.json")).read_bytes(), "final artifact differs")
    for name, expected in seal.get("private_runtime_files_local_only", {}).items():
        task.require(sha256_file(folder / "private-runtime" / name) == expected, "private runtime file differs")
    return dict(status="replayed_exactly", replies=completed, requests_used=session.requests_used,
        actual_operations=session.calls_used, native_inputs=len(counts), custody_records=len(records),
        submitted=session.submitted, source_files=len(seal["source_sha256"]), no_additional_model_inference=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.folder), indent=2))
