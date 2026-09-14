"""Verify the preserved native probe without repeating native calls or inference."""
import copy
import json
from pathlib import Path

import pending_task as task
import run_uncoached_contribution as runner
from manage_pending import assembly
from working_set_exp.contribution_reply import completion_request_bytes, process_reply
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

module = task.Task()
folder = task.AREA / "review/c05-capacity-001"
prior = task.grouped.prior
seal = prior.verify_inventory(folder, "SEAL.json")
task.study.require(seal["status"] == "failed_preserved", "preserve the original probe failure")
original_task = prior.TASK
try:
    prior.TASK = module
    counts = prior.measurements(folder)
finally:
    prior.TASK = original_task
records = verify_records(folder / "records.jsonl", folder)
captured = []
original_snapshot = module.snapshot


def capture(session):
    if session.requests_used == 4 and session.calls_used == 4:
        captured.append(copy.deepcopy(session))
    return original_snapshot(session)


module.snapshot = capture
verification = assembly.verify(module, module.RUN)
module.snapshot = original_snapshot
task.study.require(len(captured) == 1, "actual C05 checkpoint is not unique")
starting = captured[0]
adapter = runner.Adapter(module)
task.study.require(completion_request_bytes(adapter.request_for(starting.view())) ==
                   (module.RUN / "calls/C05-wire-request.json").read_bytes(), "actual C05 input differs")
task.study.require(canonical_json_bytes(module.snapshot(starting)) ==
                   (folder / "starting-state.json").read_bytes(), "native probe start differs")


def measure(view):
    return counts[sha256_bytes(canonical_json_bytes(adapter.request_for(view)))]


session = copy.deepcopy(starting)
before = measure(session.view())
session.mark_delivered(session.view())
session.begin_request()
proposal = task.study.read(module.RUN / "calls/C02-reply.json")
task.study.require(canonical_json_bytes(proposal) == (folder / "proposed-reply.json").read_bytes(),
                   "probe changed the proposed action")
actual = process_reply(session, proposal, measure, adapter.preceding_feedback)
after = measure(session.view())
task.study.require(actual == task.study.read(folder / "actual-host-result.json") and
                   canonical_json_bytes(module.snapshot(session)) ==
                   (folder / "counterfactual-after-state.json").read_bytes(), "native probe replay differs")
task.study.require(before == 4765 and after == 7555 and
                   all(r["result"]["accepted"] for r in actual["operations"]), "capacity result differs")

# The original script used its mutated initial object as the replay start. Verify
# the exact missing key from that mistaken second application, without native calls.
failed_start, failed_adapter = copy.deepcopy(session), runner.Adapter(module)
failed_start.mark_delivered(failed_start.view())
failed_start.begin_request()


def failed_measure(view):
    return counts[sha256_bytes(canonical_json_bytes(failed_adapter.request_for(view)))]


try:
    process_reply(failed_start, proposal, failed_measure, failed_adapter.preceding_feedback)
except KeyError as error:
    task.study.require(str(error) == task.study.read(folder / "FAILED.json")["message"],
                       "original replay error is not explained by the mutated starting object")
else:
    raise AssertionError("expected original review-script replay failure")

closed = [r["payload"] for r in records if r["record_type"] == "runtime_closed"]
task.study.require(len(closed) == 1 and closed[0]["owned_server_shutdown_verified"] and
                   closed[0]["dedicated_port_free"], "native runtime did not close normally")
task.study.require(all(r["payload"].get("completion_sent") is not True for r in records),
                   "unexpected completion request")
report = dict(status="preserved_native_measurements_verified_offline", model_requests=0,
    native_requests_in_this_verification=0, original_probe_status="failed_preserved",
    original_probe_error="verification replay began from the already-mutated session; exact missing key reproduced",
    classification="reviewer applies exact C02 proposal at actual C05 selection; capacity feasibility only",
    input_tokens=before, next_input_tokens=after, hard_input_limit=23808,
    accepted=True, replayed_exactly=True, original_run_unmodified=True,
    native_inputs=len(counts), custody_records=len(records), source_identities=len(seal["source_sha256"]),
    candidate_id=session.candidate.candidate_id, actual_run_verification=verification,
    runtime_closed=closed[0],
    source_sha256={p.relative_to(task.study.ROOT).as_posix(): sha256_file(p)
                   for p in (Path(__file__), folder / "SEAL.json", module.RUN / "RESPONSE_SEAL.json")},
    limitation="This supplies a known proposal for sizing; it does not demonstrate autonomous recovery, sufficient supporting evidence, or completion.")
task.study.save(task.AREA / "review", "C05_CAPACITY_REPLAY.json", report)
print(json.dumps({k: report[k] for k in ("status", "input_tokens", "next_input_tokens", "native_inputs",
    "custody_records", "original_probe_error")}, indent=2))
