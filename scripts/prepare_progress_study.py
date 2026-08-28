from __future__ import annotations

from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes
from working_set_exp.progress import BRANCH_CALL_LIMIT, CASE_IDS, CONDITIONS, PREFIX_CALL_LIMIT, SEEDS, construct_bank
from working_set_exp.progress_measured import (
    build_executable_closure, construct_execution_package, expected_authorization,
)


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "003_progress_pointer_diagnostic"


def main() -> None:
    EXPERIMENT.mkdir(parents=True, exist_ok=True)
    atomic_write(
        EXPERIMENT / "STUDY_AUTHORIZATION.json",
        canonical_json_bytes(
            {
                "schema_version": "experiment-003-progress-study-authorization-v1",
                "owner_statement": "Run recommendation",
                "authorized": True,
                "scope": "two fresh shared prefixes and four 25k reconstructed branches",
                "conditions": list(CONDITIONS),
                "actor_inference": True,
                "attempts_per_call": 1,
                "retries": 0,
                "automatic_successor": False,
            }
        ),
    )
    source_profile = ROOT / "experiments" / "002_single_boundary_reconstruction" / "RUNTIME_PROFILE.json"
    atomic_write(EXPERIMENT / "RUNTIME_PROFILE.json", source_profile.read_bytes())
    schedule = {
        "schema_version": "experiment-003-progress-schedule-v1",
        "conditions": list(CONDITIONS),
        "prefix_call_limit": PREFIX_CALL_LIMIT,
        "branch_call_limit": BRANCH_CALL_LIMIT,
        "one_shot_probe": True,
        "prefix_order": [
            {"ordinal": 1, "fixture_id": CASE_IDS[0], "seed": SEEDS[CASE_IDS[0]], "branch_order": ["T25-M", "T25-P"]},
            {"ordinal": 2, "fixture_id": CASE_IDS[1], "seed": SEEDS[CASE_IDS[1]], "branch_order": ["T25-P", "T25-M"]},
        ],
        "attempts_per_call": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
        "reasoning": "off",
    }
    atomic_write(EXPERIMENT / "MEASURED_SCHEDULE.json", canonical_json_bytes(schedule))
    construct_bank(EXPERIMENT / "fresh_bank")
    construct_execution_package(
        EXPERIMENT / "measured_execution_package",
        bank_root=EXPERIMENT / "fresh_bank",
        schedule_path=EXPERIMENT / "MEASURED_SCHEDULE.json",
        runtime_profile_path=EXPERIMENT / "RUNTIME_PROFILE.json",
    )
    closure_path = EXPERIMENT / "MEASURED_EXECUTABLE_CLOSURE.json"
    atomic_write(closure_path, canonical_json_bytes(build_executable_closure(ROOT)))
    authorization = expected_authorization(
        experiment=EXPERIMENT, closure_path=closure_path,
        package_path=EXPERIMENT / "measured_execution_package",
    )
    atomic_write(EXPERIMENT / "MEASURED_EXECUTION_AUTHORIZATION.json", canonical_json_bytes(authorization))


if __name__ == "__main__":
    main()
