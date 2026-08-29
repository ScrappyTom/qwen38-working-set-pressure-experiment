from __future__ import annotations

import json
import shutil
from pathlib import Path

from working_set_exp.authentic_pressure import _inventory
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, sha256_file
from working_set_exp.reasoning_measured import seal_response_tree


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\e9-dev")
TARGET = ROOT / "experiments" / "009_recurrent_observation_validity" / "development_rehearsal" / "attempt1_cache_economics"


def main() -> None:
    if TARGET.exists():
        raise FileExistsError(TARGET)
    if not SOURCE.is_dir():
        raise FileNotFoundError(SOURCE)
    seal = seal_response_tree(SOURCE)
    shutil.copytree(SOURCE, TARGET)
    finding = {
        "schema_version": "experiment-009-development-partial-finding-v1",
        "disposition": "operator_stopped_development_only_runtime_economics_diagnostic",
        "prepared_invocations": 3,
        "http_completion_calls": 2,
        "completed_action_call_ids": [
            "E9-DEV-OBS-GAMMA-S314159-P01",
            "E9-DEV-OBS-GAMMA-S314159-P02",
        ],
        "interrupted_prepared_call_id": "E9-DEV-OBS-GAMMA-S314159-P03",
        "measured_bank_exposure": False,
        "response_seal_sha256": sha256_file(SOURCE / "RESPONSE_SEAL.json"),
        "response_aggregate_sha256": seal["aggregate_sha256"],
        "cache_diagnosis": (
            "llama.cpp cached the available exact prefix; call 3 introduced genuinely new custody tokens. "
            "No prompt-layout defect was established and no cache-layout change was made."
        ),
        "server_shutdown": "owned PID 11640 explicitly stopped after runner interrupt; port 18110 released",
        "files": _inventory(TARGET, excluded={"PARTIAL_FINDING.json"}),
    }
    atomic_write(TARGET / "PARTIAL_FINDING.json", canonical_json_bytes(finding))
    print(json.dumps(finding, indent=2))


if __name__ == "__main__":
    main()
