from __future__ import annotations

import json
import shutil
from pathlib import Path

from working_set_exp.authentic_pressure import _inventory
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, sha256_file
from working_set_exp.reasoning_measured import seal_response_tree


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\e9-final-dev")
TARGET = ROOT / "experiments" / "009_recurrent_observation_validity" / "final_path_rehearsal" / "attempt1_timeout"


def main() -> None:
    if TARGET.exists():
        raise FileExistsError(TARGET)
    seal = seal_response_tree(SOURCE)
    shutil.copytree(SOURCE, TARGET)
    finding = {
        "schema_version": "experiment-009-final-path-timeout-finding-v1",
        "disposition": "development_transport_timeout_before_actor_response",
        "prepared_invocations": 1,
        "http_completion_calls": 0,
        "call_id": "E9-DEV-OBS-DELTA-S271828-T25-C-P01",
        "error": "endpoint transport failure: timed out",
        "configured_timeout_seconds": 600,
        "server_was_still_decoding": True,
        "last_observed_generated_tokens": 251,
        "measured_bank_exposure": False,
        "response_seal_sha256": sha256_file(SOURCE / "RESPONSE_SEAL.json"),
        "response_aggregate_sha256": seal["aggregate_sha256"],
        "server_shutdown": "owned PID 3076 explicitly stopped after timeout; port 18110 released",
        "files": _inventory(TARGET, excluded={"TIMEOUT_FINDING.json"}),
    }
    atomic_write(TARGET / "TIMEOUT_FINDING.json", canonical_json_bytes(finding))
    print(json.dumps(finding, indent=2))


if __name__ == "__main__":
    main()
