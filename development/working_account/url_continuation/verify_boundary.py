"""Check preserved native inputs, wire bytes and custody without inference."""
import argparse
import json
from pathlib import Path

import task
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


def verify(folder):
    seal = task.read(folder / "SEAL.json")
    assert sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"]
    for row in seal["files"]:
        path = folder / row["path"]
        assert path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"]
    bound = task.read(folder / "RESULTS.json")["source_sha256"]
    task.verify_sources(bound)
    records = verify_records(folder / "records.jsonl", folder)
    native = 0
    for record in records:
        if record["record_type"] != "native_input_prepared":
            continue
        row, stem = record["payload"], record["payload"]["stem"]
        request = task.read(folder / (stem + "-endpoint-request.json"))
        assert (folder / (stem + "-native.txt")).read_bytes() == task.expected_native(request)
        assert task.read(folder / (stem + "-template.json"))["prompt"].encode() == task.expected_native(request)
        assert row["prompt_tokens"] == len(task.read(folder / (stem + "-tokens.json"))["tokens"])
        assert (folder / (stem + "-wire-request.json")).read_bytes() == completion_request_bytes(request)
        native += 1
    assert not any(r["record_type"] == "invocation_started" for r in records)
    closed, = [r["payload"] for r in records if r["record_type"] == "runtime_closed"]
    assert closed["owned_server_shutdown_verified"] and closed["dedicated_port_free"]
    return dict(status="native_and_custody_verified", native_inputs=native, custody_records=len(records),
                source_files=len(bound), model_completion_requests=0, owned_runtime_closed=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    folder = parser.parse_args().folder
    value = verify(folder)
    task.save(folder.parent, folder.name + "-VERIFICATION.json", value)
    print(json.dumps(value, indent=2))
