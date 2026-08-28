from __future__ import annotations

from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes
from working_set_exp.reasoning import (
    BRANCH_CALL_LIMIT,
    CASE_IDS,
    CONDITIONS,
    PREFIX_CALL_LIMIT,
    REASONING_BUDGET,
    SEEDS,
    construct_bank,
)
from working_set_exp.reasoning_measured import (
    build_executable_closure,
    construct_execution_package,
    expected_authorization,
)


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "004_reasoning_transition_diagnostic"


def main() -> None:
    source_profile = ROOT / "experiments" / "003_progress_pointer_diagnostic" / "RUNTIME_PROFILE.json"
    atomic_write(EXPERIMENT / "RUNTIME_PROFILE.json", source_profile.read_bytes())
    schedule = {
        "schema_version": "experiment-004-reasoning-schedule-v1",
        "conditions": list(CONDITIONS), "prefix_call_limit": PREFIX_CALL_LIMIT,
        "branch_call_limit": BRANCH_CALL_LIMIT, "one_shot_probe": True,
        "prefix_order": [
            {"ordinal": 1, "fixture_id": CASE_IDS[0], "seed": SEEDS[CASE_IDS[0]], "branch_order": ["R0", "R1"]},
            {"ordinal": 2, "fixture_id": CASE_IDS[1], "seed": SEEDS[CASE_IDS[1]], "branch_order": ["R1", "R0"]},
        ],
        "attempts_per_call": 1, "retries": 0, "repairs": 0, "rescues": 0,
        "reasoning": {"R0": "off", "R1": {"effort": "low", "budget_tokens": REASONING_BUDGET}},
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
