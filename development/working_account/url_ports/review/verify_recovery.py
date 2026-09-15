"""Recheck exact native custody and every offline recovery transition."""
import copy
import json
from pathlib import Path

import task
from working_set_exp.accounted_contribution import process_reply
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

folder = Path(__file__).resolve().parent / "recovery-001"
seal = task.read(folder / "SEAL.json")
assert sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"]
for row in seal["files"]:
    path = folder / row["path"]
    assert path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"]
task.verify_sources(task.read(folder / "RESULTS.json")["source_sha256"])
records = verify_records(folder / "records.jsonl", folder)
session, adapter = task.initial_session(), task.runner.Adapter(task.Task())
state = task.read(task.AREA / "run-001/after/C03-O01-state.json")
for key in ("pairs", "ranges", "saved", "last", "requests_used", "delivered_sources"):
    setattr(session, key, copy.deepcopy(state[key]))
counts = {}
for record in records:
    if record["record_type"] != "native_input_prepared":
        continue
    row = record["payload"]
    stem = row["stem"]
    request = task.read(folder / (stem + "-endpoint-request.json"))
    native = (folder / (stem + "-native.txt")).read_bytes()
    assert native == adapter.expected_native(request) == task.read(folder / (stem + "-template.json"))["prompt"].encode()
    assert row["prompt_tokens"] == len(task.read(folder / (stem + "-tokens.json"))["tokens"])
    assert (folder / (stem + "-wire-request.json")).read_bytes() == completion_request_bytes(request)
    counts[sha256_bytes(canonical_json_bytes(request))] = row["prompt_tokens"]
def measure(view):
    return counts[sha256_bytes(canonical_json_bytes(adapter.request_for(view))) ]
assert measure(session.view()) == 23802
for number in range(1, 7):
    session.mark_delivered(session.view())
    session.begin_request()
    actual = process_reply(session, task.read(folder / f"step-{number:02d}-reply.json"), measure, adapter.preceding_feedback)
    assert actual == task.read(folder / f"step-{number:02d}-result.json")
    assert canonical_json_bytes(task.snapshot(session)) == (folder / f"step-{number:02d}-state.json").read_bytes()
    assert task.candidate_bytes(session.candidate) == (folder / f"step-{number:02d}-candidate.json").read_bytes()
    assert measure(session.view()) <= 23808
assert session.submitted
closed, = [r["payload"] for r in records if r["record_type"] == "runtime_closed"]
assert closed["owned_server_shutdown_verified"] and closed["dedicated_port_free"]
assert not any(r["record_type"] == "invocation_started" for r in records)
result = dict(status="replayed_exactly", native_inputs=len(counts), custody_records=len(records),
              steps=6, new_operations=session.calls_used - 3, submitted=True, model_completion_requests=0,
              source_files=len(task.read(folder / "RESULTS.json")["source_sha256"]), owned_runtime_closed=True)
task.save(folder.parent, "RECOVERY_VERIFICATION.json", result)
print(json.dumps(result, indent=2))
