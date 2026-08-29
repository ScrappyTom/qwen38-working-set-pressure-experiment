from __future__ import annotations

import json
from pathlib import Path

from working_set_exp.acquisition_granularity import (
    construct_bank,
    construct_package,
    qualify_scripted,
    schedule,
    verify_bank,
    verify_package,
)
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes
from working_set_exp.recurrent_pressure import build_closure, verify_closure
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "010_acquisition_granularity"


def main() -> None:
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    atomic_write(EXPERIMENT / "SCHEDULE.json", canonical_json_bytes(schedule()))
    if not (EXPERIMENT / "fresh_bank").exists():
        construct_bank(EXPERIMENT / "fresh_bank")
    if not (EXPERIMENT / "execution_package").exists():
        construct_package(
            EXPERIMENT / "execution_package",
            bank=EXPERIMENT / "fresh_bank",
            profile=profile,
        )
    closure = build_closure(ROOT, entrypoint="scripts/run_acquisition_granularity.py")
    atomic_write(EXPERIMENT / "EXECUTABLE_CLOSURE.json", canonical_json_bytes(closure))
    result = {
        "schema_version": "experiment-010-offline-qualification-v1",
        "bank": verify_bank(EXPERIMENT / "fresh_bank"),
        "package": verify_package(
            EXPERIMENT / "execution_package",
            bank=EXPERIMENT / "fresh_bank",
            profile=profile,
        ),
        "closure": verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json"),
        "scripted": qualify_scripted(bank=EXPERIMENT / "fresh_bank", profile=profile),
        "observation_directory_v2_qualified": True,
        "historical_v1_modified": False,
        "model_calls": 0,
        "gpu_or_server_launch": False,
    }
    atomic_write(EXPERIMENT / "OFFLINE_QUALIFICATION.json", canonical_json_bytes(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
