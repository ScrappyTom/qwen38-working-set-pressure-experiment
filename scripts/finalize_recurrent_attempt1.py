from __future__ import annotations

import json
from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.reasoning_measured import seal_response_tree
from working_set_exp.runtime import PORT, port_free


OUTPUT = Path(r"C:\e7-primary")


def main() -> None:
    if not OUTPUT.is_dir() or (OUTPUT / "RESPONSE_SEAL.json").exists():
        raise RuntimeError("attempt-1 output is absent or already sealed")
    prepared = 0
    completed = 0
    for path in OUTPUT.rglob("records.jsonl"):
        for line in path.read_bytes().splitlines():
            row = load_json_strict(line)
            prepared += row["record_type"] == "external_call_prepared"
            completed += row["record_type"] == "action_result"
    seal = seal_response_tree(OUTPUT)
    receipt = load_json_strict((OUTPUT / "RECEIPT.json").read_bytes())
    receipt.update({
        "status": "operator_stopped_on_integrity_finding",
        "completed_at_utc": utc_now(),
        "integrity_finding": "append_only_control_was_not_continued_when_phase_c_remained_physically_admitted",
        "research_disposition": "immutable_apparatus_evidence_not_recurrent_result",
        "prepared_invocations": prepared,
        "http_completion_calls": completed,
        "response_seal_sha256": sha256_file(OUTPUT / "RESPONSE_SEAL.json"),
        "response_aggregate_sha256": seal["aggregate_sha256"],
        "server_shutdown_verified": port_free(PORT),
        "evaluator_reads_before_seal": False,
    })
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
