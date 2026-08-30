from __future__ import annotations

import json
import shutil
from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes
from working_set_exp.recurrent_pressure import build_closure, verify_closure
from working_set_exp.runtime import load_runtime
from working_set_exp.unified_receipts import construct_bank, construct_package, expected_authorization, schedule, verify_bank, verify_package

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "014_unified_active_phase_receipts"


def main() -> None:
    for path in (EXPERIMENT / "fresh_bank", EXPERIMENT / "execution_package"):
        if path.exists():
            if path.resolve().parent != EXPERIMENT.resolve():
                raise RuntimeError(f"unsafe target: {path}")
            shutil.rmtree(path)
    construct_bank(EXPERIMENT / "fresh_bank")
    atomic_write(EXPERIMENT / "SCHEDULE.json", canonical_json_bytes(schedule()))
    source = ROOT / "experiments" / "013_active_phase_receipts" / "RUNTIME_PROFILE.json"
    atomic_write(EXPERIMENT / "RUNTIME_PROFILE.json", source.read_bytes())
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    construct_package(EXPERIMENT / "execution_package", bank=EXPERIMENT / "fresh_bank", profile=profile)
    closure = build_closure(ROOT, entrypoint="scripts/run_unified_receipts.py")
    atomic_write(EXPERIMENT / "EXECUTABLE_CLOSURE.json", canonical_json_bytes(closure))
    atomic_write(EXPERIMENT / "MEASURED_AUTHORIZATION.json", canonical_json_bytes(expected_authorization(EXPERIMENT)))
    result = {"schema_version": "experiment-014-offline-preparation-v1",
              "bank": verify_bank(EXPERIMENT / "fresh_bank"),
              "package": verify_package(EXPERIMENT / "execution_package", bank=EXPERIMENT / "fresh_bank", profile=profile),
              "closure": verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json"), "model_calls": 0}
    atomic_write(EXPERIMENT / "OFFLINE_PREPARATION.json", canonical_json_bytes(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
