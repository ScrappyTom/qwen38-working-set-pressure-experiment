from __future__ import annotations

import shutil
from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, sha256_file, utc_now
from working_set_exp.large_world_event_v2 import (
    closure, construct_bank, construct_package, expected_authorization, schedule,
)
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "018_large_world_event_frame_v2"
RUNTIME_DONOR = ROOT / "experiments" / "017_signal_bearing_event_frame_v2" / "RUNTIME_PROFILE.json"


def main() -> None:
    EXPERIMENT.mkdir(parents=True, exist_ok=True)
    runtime = EXPERIMENT / "RUNTIME_PROFILE.json"
    if not runtime.exists():
        shutil.copyfile(RUNTIME_DONOR, runtime)
    profile = load_runtime(runtime)
    atomic_write(EXPERIMENT / "SCHEDULE.json", canonical_json_bytes(schedule()))
    bank = construct_bank(EXPERIMENT / "fresh_bank")
    package = construct_package(EXPERIMENT / "execution_package", bank=EXPERIMENT / "fresh_bank", profile=profile)
    source_closure = closure(ROOT)
    atomic_write(EXPERIMENT / "EXECUTABLE_CLOSURE.json", canonical_json_bytes(source_closure))
    atomic_write(EXPERIMENT / "MEASURED_AUTHORIZATION.json", canonical_json_bytes(expected_authorization(EXPERIMENT)))
    atomic_write(EXPERIMENT / "OFFLINE_PREPARATION.json", canonical_json_bytes({
        "schema_version": "experiment-018-offline-preparation-v1", "created_at_utc": utc_now(),
        "bank_id": bank["bank_id"], "bank_manifest_sha256": sha256_file(EXPERIMENT / "fresh_bank" / "BANK_MANIFEST.json"),
        "package_id": package["package_id"], "package_manifest_sha256": sha256_file(EXPERIMENT / "execution_package" / "PACKAGE_MANIFEST.json"),
        "closure_aggregate_sha256": source_closure["aggregate_sha256"],
        "authorization_sha256": sha256_file(EXPERIMENT / "MEASURED_AUTHORIZATION.json"),
        "model_execution": False, "fresh_bank_actor_exposure": False,
    }))


if __name__ == "__main__":
    main()
