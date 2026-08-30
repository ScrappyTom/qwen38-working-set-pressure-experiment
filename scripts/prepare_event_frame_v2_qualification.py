from __future__ import annotations

import shutil
from pathlib import Path

from working_set_exp.event_frame_v2_qualification import (
    capacity_proof,
    closure,
    construct_package,
    expected_authorization,
    schedule,
)
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, sha256_file, utc_now
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "017_signal_bearing_event_frame_v2"
DONOR = ROOT / "experiments" / "014_unified_active_phase_receipts"
RUNTIME_DONOR = ROOT / "experiments" / "015_event_frame_placement_qualification" / "RUNTIME_PROFILE.json"


def main() -> None:
    EXPERIMENT.mkdir(parents=True, exist_ok=True)
    runtime = EXPERIMENT / "RUNTIME_PROFILE.json"
    if not runtime.exists():
        shutil.copyfile(RUNTIME_DONOR, runtime)
    profile = load_runtime(runtime)
    atomic_write(EXPERIMENT / "SCHEDULE.json", canonical_json_bytes(schedule()))
    atomic_write(EXPERIMENT / "CAPACITY_PROOF.json", canonical_json_bytes(capacity_proof(profile)))
    package = EXPERIMENT / "execution_package"
    if package.exists():
        raise FileExistsError(package)
    package_manifest = construct_package(package, donor_bank=DONOR / "fresh_bank", profile=profile)
    source_closure = closure(ROOT)
    atomic_write(EXPERIMENT / "EXECUTABLE_CLOSURE.json", canonical_json_bytes(source_closure))
    atomic_write(EXPERIMENT / "DEVELOPMENT_AUTHORIZATION.json", canonical_json_bytes(expected_authorization(EXPERIMENT)))
    atomic_write(
        EXPERIMENT / "OFFLINE_PREPARATION.json",
        canonical_json_bytes(
            {
                "schema_version": "experiment-017-offline-preparation-v1",
                "created_at_utc": utc_now(),
                "development_only": True,
                "package_id": package_manifest["package_id"],
                "package_manifest_sha256": sha256_file(package / "PACKAGE_MANIFEST.json"),
                "closure_aggregate_sha256": source_closure["aggregate_sha256"],
                "authorization_sha256": sha256_file(EXPERIMENT / "DEVELOPMENT_AUTHORIZATION.json"),
                "capacity_proof_sha256": sha256_file(EXPERIMENT / "CAPACITY_PROOF.json"),
                "model_execution": False,
                "large_world_experiment": False,
            }
        ),
    )


if __name__ == "__main__":
    main()
