from __future__ import annotations

import shutil
from pathlib import Path

from working_set_exp.bank import construct_bank, verify_bank
from working_set_exp.fixture import load_fixture
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, sha256_bytes
from working_set_exp.runner import ScriptedActor, run_branch, run_prefix, scripted_policy, verify_run
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "002_single_boundary_reconstruction"
OFFLINE_TIMESTAMP = "2000-01-01T00:00:00.000000+00:00"


def main() -> None:
    development = EXPERIMENT / "development_bank"
    measured = EXPERIMENT / "fresh_bank"
    qualification = ROOT / "offline_qualification"
    for target in (development, measured, qualification):
        if target.exists():
            shutil.rmtree(target)
    dev_manifest = construct_bank(development, measured=False)
    measured_manifest = construct_bank(measured, measured=True)
    verify_bank(development)
    verify_bank(measured)
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    fixture = load_fixture(development, "DEV-RECONSTRUCTION")
    prefix_actor = ScriptedActor(profile, 42, scripted_policy(fixture, condition="C50"))
    prefix = run_prefix(
        fixture,
        seed=42,
        actor=prefix_actor,
        output_dir=qualification / "prefix",
        profile=profile,
        fixed_record_timestamp=OFFLINE_TIMESTAMP,
    )
    branches = {}
    for condition in ("C50", "T25"):
        actor = ScriptedActor(profile, 42, scripted_policy(fixture, condition=condition))
        summary = run_branch(
            fixture,
            prefix,
            condition=condition,
            seed=42,
            actor=actor,
            output_dir=qualification / condition,
            fixed_record_timestamp=OFFLINE_TIMESTAMP,
        )
        branches[condition] = summary
        verify_run(qualification / condition)
    verify_run(qualification / "prefix")
    schedule = {
        "schema_version": "experiment-002-measured-schedule-v1",
        "seeds": [42, 314159],
        "fork_order": [
            {"ordinal": 1, "fixture_id": "E2-SOURCE", "seed": 42},
            {"ordinal": 2, "fixture_id": "E2-OBSERVATION", "seed": 314159},
            {"ordinal": 3, "fixture_id": "E2-OBSERVATION", "seed": 42},
            {"ordinal": 4, "fixture_id": "E2-SOURCE", "seed": 314159},
        ],
        "branch_order_within_fork": ["C50", "T25"],
        "attempts": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
    }
    atomic_write(EXPERIMENT / "MEASURED_SCHEDULE.json", canonical_json_bytes(schedule))
    receipt = {
        "schema_version": "experiment-002-offline-preparation-receipt-v1",
        "development_bank_id": dev_manifest["bank_id"],
        "measured_bank_id": measured_manifest["bank_id"],
        "schedule_sha256": sha256_bytes(canonical_json_bytes(schedule)),
        "scripted_prefix_disposition": "fork_eligible",
        "scripted_branches": branches,
        "model_or_endpoint_calls": 0,
        "gpu_server_launch": False,
    }
    atomic_write(EXPERIMENT / "OFFLINE_PREPARATION_RECEIPT.json", canonical_json_bytes(receipt))
    print(receipt)


if __name__ == "__main__":
    main()
