from __future__ import annotations

import json
from pathlib import Path

import qualify_recurrent_pressure as recurrent_qualifier
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes
from working_set_exp.observation_recurrence import CASE_IDS, SEEDS
from working_set_exp.recurrent_pressure import verify_bank, verify_closure, verify_package
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "009_recurrent_observation_validity"


def main() -> None:
    recurrent_qualifier.EXPERIMENT = EXPERIMENT
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    result = {
        "schema_version": "experiment-009-recurrent-observation-mechanical-qualification-v1",
        "bank": verify_bank(EXPERIMENT / "fresh_bank"),
        "package": verify_package(
            EXPERIMENT / "execution_package",
            bank=EXPERIMENT / "fresh_bank",
            schedule_path=EXPERIMENT / "SCHEDULE.json",
            profile=profile,
        ),
        "closure": verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json"),
        "cases": [
            recurrent_qualifier._run_case(fixture_id, seed)
            for fixture_id in CASE_IDS
            for seed in SEEDS[:1]
        ],
        "model_calls": 0,
    }
    atomic_write(EXPERIMENT / "MECHANICAL_QUALIFICATION.json", canonical_json_bytes(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
