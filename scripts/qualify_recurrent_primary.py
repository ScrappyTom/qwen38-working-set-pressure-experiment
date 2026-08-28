from __future__ import annotations

import json
from pathlib import Path

import qualify_recurrent_pressure as qualification
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes
from working_set_exp.recurrent_pressure import verify_bank, verify_closure, verify_package
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "008_recurrent_bounded_pressure_primary"


def main() -> None:
    qualification.EXPERIMENT = EXPERIMENT
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    result = {
        "schema_version": "experiment-008-recurrent-mechanical-qualification-v1",
        "bank": verify_bank(EXPERIMENT / "fresh_bank"),
        "package": verify_package(
            EXPERIMENT / "execution_package", bank=EXPERIMENT / "fresh_bank",
            schedule_path=EXPERIMENT / "SCHEDULE.json", profile=profile,
        ),
        "closure": verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json"),
        "cases": [qualification._run_case(fixture_id, 173205) for fixture_id in ("E8-SOURCE", "E8-OBSERVATION")],
        "model_calls": 0,
    }
    atomic_write(EXPERIMENT / "MECHANICAL_QUALIFICATION.json", canonical_json_bytes(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
