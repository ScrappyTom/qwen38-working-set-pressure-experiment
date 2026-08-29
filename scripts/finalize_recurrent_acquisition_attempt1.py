from __future__ import annotations

import json
from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.reasoning_measured import seal_response_tree
from working_set_exp.runtime import port_free


OUTPUT = Path(r"C:\e11-primary")
PORT = 18113
EXPECTED_TERMINAL_CALL = "E11-OBS-KAPPA-S223607-P04"


def main() -> None:
    if not OUTPUT.is_dir() or (OUTPUT / "RESPONSE_SEAL.json").exists():
        raise RuntimeError("partial Experiment 011 output is absent or already sealed")
    if not port_free(PORT):
        raise RuntimeError("owned port remains occupied")

    prepared = 0
    completed = 0
    last_prepared: dict[str, object] | None = None
    completed_ids: set[str] = set()
    for path in sorted(OUTPUT.rglob("records.jsonl")):
        for line in path.read_bytes().splitlines():
            row = load_json_strict(line)
            if row["record_type"] == "external_call_prepared":
                prepared += 1
                last_prepared = row["payload"]
            elif row["record_type"] == "action_result":
                completed += 1
                completed_ids.add(row["payload"]["call_id"])

    if prepared != 110 or completed != 108:
        raise RuntimeError(f"unexpected partial counts: prepared={prepared}, completed={completed}")
    if last_prepared is None or last_prepared.get("call_id") != EXPECTED_TERMINAL_CALL:
        raise RuntimeError(f"unexpected terminal prepared call: {last_prepared!r}")
    if EXPECTED_TERMINAL_CALL in completed_ids:
        raise RuntimeError("terminal prepared call unexpectedly completed")

    seal = seal_response_tree(OUTPUT)
    receipt = load_json_strict((OUTPUT / "RECEIPT.json").read_bytes())
    receipt.update(
        {
            "status": "external_execution_host_terminated_mid_http_call",
            "completed_at_utc": utc_now(),
            "integrity_finding": (
                "the runner and owned llama-server disappeared without entering the runner's exception/finally path; "
                "the final durable record is prepared call E11-OBS-KAPPA-S223607-P04, with no endpoint response"
            ),
            "research_disposition": "immutable_partial_measured_evidence_not_complete_primary",
            "prepared_invocations": prepared,
            "http_completion_calls": completed,
            "terminal_prepared_call_id": EXPECTED_TERMINAL_CALL,
            "terminal_call_endpoint_response_present": False,
            "other_prepared_without_http_call_ids": ["E11-OBS-IOTA-S173205-T25-L0-B10"],
            "other_prepared_without_http_disposition": "prospective_capacity_denial_as_designed",
            "response_seal_sha256": sha256_file(OUTPUT / "RESPONSE_SEAL.json"),
            "response_aggregate_sha256": seal["aggregate_sha256"],
            "server_shutdown_verified": True,
            "orderly_runner_shutdown_record_present": False,
            "evaluator_reads_by_execution_process_before_seal": False,
            "no_resume_no_rerun_under_consumed_authorization": True,
        }
    )
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
