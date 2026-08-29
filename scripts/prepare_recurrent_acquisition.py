from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes
from working_set_exp.recurrent_acquisition import case_definitions, construct_package, schedule, verify_package
from working_set_exp.recurrent_pressure import build_closure, construct_bank, verify_bank, verify_closure
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "011_recurrent_acquisition_granularity"


def main() -> None:
    replace = sys.argv[1:] == ["--replace-preseal"]
    bank = EXPERIMENT / "fresh_bank"
    package = EXPERIMENT / "execution_package"
    if (bank.exists() or package.exists()) and not replace:
        raise FileExistsError("Experiment 011 preseal artifacts already exist")
    if replace:
        for path in (bank, package):
            if path.exists():
                if path.resolve().parent != EXPERIMENT.resolve():
                    raise RuntimeError(f"unsafe preseal target: {path}")
                shutil.rmtree(path)
    construct_bank(bank, definitions=case_definitions())
    atomic_write(EXPERIMENT / "SCHEDULE.json", canonical_json_bytes(schedule()))
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    construct_package(package, bank=bank, profile=profile)
    closure = build_closure(ROOT, entrypoint="scripts/run_recurrent_acquisition.py")
    atomic_write(EXPERIMENT / "EXECUTABLE_CLOSURE.json", canonical_json_bytes(closure))
    result = {
        "schema_version": "experiment-011-offline-preparation-v1",
        "bank": verify_bank(bank), "package": verify_package(package, bank=bank, profile=profile),
        "closure": verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json"), "model_calls": 0,
    }
    atomic_write(EXPERIMENT / "OFFLINE_PREPARATION.json", canonical_json_bytes(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
