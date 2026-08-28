from __future__ import annotations

from pathlib import Path

from working_set_exp.bank import verify_bank
from working_set_exp.measured import validate_authorization, verify_executable_closure, verify_execution_package


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "002_single_boundary_reconstruction"


def main() -> None:
    package = verify_execution_package(
        EXPERIMENT / "measured_execution_package",
        bank_root=EXPERIMENT / "fresh_bank",
        schedule_path=EXPERIMENT / "MEASURED_SCHEDULE.json",
        runtime_profile_path=EXPERIMENT / "RUNTIME_PROFILE.json",
    )
    closure = verify_executable_closure(ROOT, EXPERIMENT / "MEASURED_EXECUTABLE_CLOSURE.json")
    authorization = validate_authorization(
        repo_root=ROOT,
        experiment=EXPERIMENT,
        closure_path=EXPERIMENT / "MEASURED_EXECUTABLE_CLOSURE.json",
        package_path=EXPERIMENT / "measured_execution_package",
        authorization_path=EXPERIMENT / "MEASURED_EXECUTION_AUTHORIZATION.json",
    )
    bank = verify_bank(EXPERIMENT / "fresh_bank")
    print({"qualified": True, "package": package, "closure": closure, "authorization": authorization, "bank": bank, "model_calls": 0})


if __name__ == "__main__":
    main()
