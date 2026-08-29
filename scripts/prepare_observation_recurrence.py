from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes
from working_set_exp.observation_recurrence import case_definitions
from working_set_exp.recurrent_pressure import (
    build_closure,
    construct_bank,
    construct_package,
    verify_bank,
    verify_closure,
    verify_package,
)
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "009_recurrent_observation_validity"


def main() -> None:
    bank = EXPERIMENT / "fresh_bank"
    package = EXPERIMENT / "execution_package"
    replace_preseal = sys.argv[1:] == ["--replace-preseal"]
    if (bank.exists() or package.exists()) and not replace_preseal:
        raise FileExistsError("Experiment 009 preseal artifacts already exist")
    if replace_preseal:
        experiment_root = EXPERIMENT.resolve()
        for generated in (bank, package):
            if generated.exists():
                resolved = generated.resolve()
                if resolved.parent != experiment_root:
                    raise RuntimeError(f"unsafe preseal replacement target: {resolved}")
                shutil.rmtree(resolved)
    construct_bank(bank, definitions=case_definitions())
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    construct_package(
        package,
        bank=bank,
        schedule_path=EXPERIMENT / "SCHEDULE.json",
        profile=profile,
    )
    closure = build_closure(ROOT, entrypoint="scripts/run_observation_recurrence.py")
    atomic_write(EXPERIMENT / "EXECUTABLE_CLOSURE.json", canonical_json_bytes(closure))
    result = {
        "schema_version": "experiment-009-offline-preparation-v1",
        "bank": verify_bank(bank),
        "package": verify_package(
            package, bank=bank, schedule_path=EXPERIMENT / "SCHEDULE.json", profile=profile
        ),
        "closure": verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json"),
        "model_calls": 0,
    }
    atomic_write(EXPERIMENT / "OFFLINE_PREPARATION.json", canonical_json_bytes(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
