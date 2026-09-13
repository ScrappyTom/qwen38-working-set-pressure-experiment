"""Preserve an externally interrupted attempt without rewriting its run log.

This is an after-the-fact reviewer receipt, not a runner shutdown event. No
inference, tool execution, or reconstruction of an unreturned response occurs.
"""
from datetime import datetime, timezone
from pathlib import Path

import bounded_parser as task
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file, utc_now


def seal_stop():
    folder = task.RUN
    store = ArtifactStore(folder)
    task.require(not (folder / "REVIEWER_STOP.json").exists(), "stop receipt already exists")
    task.require(not (folder / "RESPONSE_SEAL.json").exists(), "attempt already sealed")
    manifest = task.read(folder / "EXECUTION_MANIFEST.json")
    task.verify_sources(manifest["source_sha256"])
    records = verify_records(folder / "records.jsonl", folder)
    before = task.base.file_inventory(folder)
    private_before = {p.name: sha256_file(p) for p in (folder / "private-runtime").glob("*") if p.is_file()}
    processes = {name: list(task.base.running_process_ids(name)) for name in ("llama-server.exe", "nvidia-smi.exe")}
    free = task.base.port_free(task.base.PORT)
    task.require(free and not any(processes.values()), "runtime or monitor still present")
    starts = [r for r in records if r["record_type"] == "invocation_started"]
    complete = [r for r in records if r["record_type"] == "invocation_completed"]
    task.require(len(starts) == 9 and len(complete) == 8, "reviewed interrupted attempt differs")
    task.require(records[-1] == starts[-1] and starts[-1]["payload"]["id"] == "C09", "unexpected run tail")
    task.require(not list((folder / "calls").glob("C09-*")), "C09 output exists; review it before sealing")
    task.require(not any(r["record_type"] in ("attempt_stopped", "runtime_closed", "task_loop_completed") for r in records),
                 "normal closure evidence exists; reconcile before sealing")
    stopped_files = {}
    for name in ("memory.csv", "private-runtime/server.stderr.log"):
        path = folder / name
        stopped_files[name] = dict(size_bytes=path.stat().st_size, sha256=sha256_file(path),
            last_write_time_utc=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat())
    receipt = dict(
        recorded_at_utc=utc_now(), closure_method="reviewer_external_process_group_interrupt",
        disposition="reviewer_stopped_known_host_restrictions", source_revision="2a58d31",
        reason="Repeated result access was rejected or reduced although full feedback fit the actual input ceiling. The reviewer stopped further exposure to the demonstrated reserve-policy defect.",
        stopping_rule_deviation="Adaptive reviewer/apparatus stop outside the frozen natural-stop list; not a natural Qwen completion failure or unchanged stopping policy.",
        interruption_evidence=dict(method="Ctrl-C sent through exec session 27236", observed_session_exit_code=1,
            exact_interrupt_timestamp_not_recorded=True, last_invocation=starts[-1],
            no_complete_C09_response=True, no_C09_action_or_tool_execution=True,
            last_logged_generation_counter=152, counter_is_not_final_endpoint_usage=True),
        preservation=dict(original_record_count=len(records), record_file_sha256=sha256_file(folder / "records.jsonl"),
            last_record_sha256=records[-1]["record_sha256"], runner_final_seal_was_absent=True,
            no_fabricated_runner_closure_event=True, no_existing_artifact_modified=True,
            original_public_inventory_sha256=sha256_bytes(canonical_json_bytes(before))),
        closure_observation=dict(process_ids=processes, port=task.base.PORT, port_free=free, stopped_file_evidence=stopped_files),
        limitations=["Receipt is recorded after the interruption, not contemporaneous runner telemetry.",
            "File modification times and the last server generation counter do not establish exact interrupted-request duration or total tokens.",
            "Eight complete responses can be reviewed; the ninth response cannot. No retry, rescue, or unused-allowance transfer is authorized by this receipt."],
    )
    # Recheck every original byte after observation, before adding the receipt.
    task.require(before == task.base.file_inventory(folder), "original public files changed during closure check")
    task.require(private_before == {p.name: sha256_file(p) for p in (folder / "private-runtime").glob("*") if p.is_file()},
                 "private runtime files are still changing")
    store.put("REVIEWER_STOP.json", canonical_json_bytes(receipt))
    files = task.base.file_inventory(folder)
    seal = dict(disposition=receipt["disposition"], closure_method=receipt["closure_method"],
        reviewer_stop_receipt="REVIEWER_STOP.json", actor=task.ACTOR, source_sha256=manifest["source_sha256"],
        manifest_sha256=sha256_file(folder / "EXECUTION_MANIFEST.json"), files=files,
        aggregate_sha256=sha256_bytes(canonical_json_bytes(files)), record_count=len(records),
        sent_requests=len(starts), completed_responses=len(complete),
        memory=task.base.memory_stats(folder / "memory.csv"),
        runtime=task.base.runtime_evidence(folder / "private-runtime/server.stderr.log"), port_free=free,
        private_runtime_files_local_only=private_before)
    store.put("RESPONSE_SEAL.json", canonical_json_bytes(seal))
    print(dict(seal_sha256=sha256_file(folder / "RESPONSE_SEAL.json"), record_count=len(records),
               files=len(files), sent_requests=len(starts), completed_responses=len(complete), memory=seal["memory"]))


if __name__ == "__main__":
    seal_stop()
