from __future__ import annotations

import json
from pathlib import Path

import qualify_recurrent_pressure as recurrent_qualifier
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes
from working_set_exp.recurrent_acquisition import CASE_IDS, READ_MODES, SEEDS, verify_package
from working_set_exp.recurrent_pressure import verify_bank, verify_closure
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "011_recurrent_acquisition_granularity"


def main() -> None:
    recurrent_qualifier.EXPERIMENT = EXPERIMENT
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    paths = []
    for fixture_id in CASE_IDS:
        for condition, read_mode in READ_MODES.items():
            paths.append(recurrent_qualifier._run_case(
                fixture_id, SEEDS[0], read_mode=read_mode, acquisition_contract=True,
                observation_directory_version=2,
            ))
    result = {
        "schema_version": "experiment-011-mechanical-qualification-v1",
        "bank": verify_bank(EXPERIMENT / "fresh_bank"),
        "package": verify_package(EXPERIMENT / "execution_package", bank=EXPERIMENT / "fresh_bank", profile=profile),
        "closure": verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json"),
        "paths": paths, "path_count": len(paths), "hidden_passes": sum(row["final_hidden_pass"] for row in paths),
        "model_calls": 0,
    }
    atomic_write(EXPERIMENT / "MECHANICAL_QUALIFICATION.json", canonical_json_bytes(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
