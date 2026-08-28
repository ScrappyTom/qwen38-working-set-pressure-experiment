from __future__ import annotations

import json
from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.reasoning_measured import seal_response_tree
from working_set_exp.runner import verify_run
from working_set_exp.runtime import PORT, port_free


OUTPUT = Path(r"C:\e4r-dev")


def main() -> None:
    receipt_path = OUTPUT / "RECEIPT.json"
    receipt = load_json_strict(receipt_path.read_bytes())
    if receipt["status"] != "infrastructure_or_integrity_stopped" or receipt.get("error") != "'kind'":
        raise RuntimeError("development receipt is not the exact post-run analyzer failure")
    summary = verify_run(OUTPUT / "R1")
    records = [load_json_strict(line) for line in (OUTPUT / "R1" / "records.jsonl").read_bytes().splitlines()]
    action_records = [row for row in records if row["record_type"] == "action_result"]
    actions = [row["payload"]["action"].get("action") for row in action_records]
    reasoning_records = [row for row in action_records if row["payload"].get("reasoning_content_bytes", 0) > 0]
    for row in reasoning_records:
        expected = row["payload"]["reasoning_content_sha256"]
        match = [artifact for artifact in row["artifacts"] if artifact["path"].endswith("assistant-reasoning.txt")]
        if len(match) != 1 or match[0]["sha256"] != expected:
            raise RuntimeError("reasoning artifact binding differs")
    if not port_free(PORT):
        raise RuntimeError("development server port remains occupied")
    seal = seal_response_tree(OUTPUT)
    finalized = {
        "schema_version": "experiment-004-development-uptake-postrun-finalization-v1",
        "finalized_at_utc": utc_now(),
        "source_receipt_sha256": sha256_file(receipt_path),
        "source_failure": {"error_type": receipt["error_type"], "error": receipt["error"]},
        "model_calls_replayed": len(action_records), "actions": actions,
        "nonempty_reasoning_calls": len(reasoning_records),
        "reasoning_transport_qualified": len(action_records) > 0 and len(reasoning_records) == len(action_records),
        "patch_reached_executor": "patch" in actions,
        "public_check_passed": summary["disposition"] == "submitted",
        "branch_disposition": summary["disposition"],
        "response_seal_sha256": sha256_file(OUTPUT / "RESPONSE_SEAL.json"),
        "response_aggregate_sha256": seal["aggregate_sha256"],
        "server_shutdown_verified": True,
        "fresh_experiment_004_bank_exposed": False,
        "new_model_calls_during_finalization": 0,
    }
    atomic_write(OUTPUT / "POSTRUN_FINALIZATION.json", canonical_json_bytes(finalized))
    print(json.dumps(finalized, indent=2))


if __name__ == "__main__":
    main()
