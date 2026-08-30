from __future__ import annotations

import shutil
from pathlib import Path

from working_set_exp.event_frame_placement import construct_package, expected_authorization, schedule
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, sha256_file, utc_now
from working_set_exp.recurrent_pressure import build_closure
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "015_event_frame_placement_qualification"
DONOR = ROOT / "experiments" / "014_unified_active_phase_receipts"


def main() -> None:
    EXPERIMENT.mkdir(parents=True, exist_ok=True)
    runtime = EXPERIMENT / "RUNTIME_PROFILE.json"
    if not runtime.exists():
        shutil.copyfile(DONOR / "RUNTIME_PROFILE.json", runtime)
    atomic_write(EXPERIMENT / "SCHEDULE.json", canonical_json_bytes(schedule()))
    package = EXPERIMENT / "execution_package"
    if package.exists():
        raise FileExistsError(package)
    profile = load_runtime(runtime)
    package_manifest = construct_package(package, donor_bank=DONOR / "fresh_bank", profile=profile)
    closure = build_closure(ROOT, entrypoint="scripts/run_event_frame_placement.py")
    atomic_write(EXPERIMENT / "EXECUTABLE_CLOSURE.json", canonical_json_bytes(closure))
    atomic_write(EXPERIMENT / "DEVELOPMENT_AUTHORIZATION.json", canonical_json_bytes(expected_authorization(EXPERIMENT)))
    atomic_write(
        EXPERIMENT / "OFFLINE_PREPARATION.json",
        canonical_json_bytes(
            {
                "schema_version": "experiment-015-offline-preparation-v1",
                "created_at_utc": utc_now(),
                "development_only": True,
                "package_id": package_manifest["package_id"],
                "package_manifest_sha256": sha256_file(package / "PACKAGE_MANIFEST.json"),
                "closure_aggregate_sha256": closure["aggregate_sha256"],
                "authorization_sha256": sha256_file(EXPERIMENT / "DEVELOPMENT_AUTHORIZATION.json"),
                "model_execution": False,
                "large_world_experiment": False,
            }
        ),
    )


if __name__ == "__main__":
    main()
