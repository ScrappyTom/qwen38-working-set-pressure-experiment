from __future__ import annotations

from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes
from working_set_exp.measured import build_executable_closure, construct_execution_package, expected_authorization


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "002_single_boundary_reconstruction"
PACKAGE = EXPERIMENT / "measured_execution_package"
CLOSURE = EXPERIMENT / "MEASURED_EXECUTABLE_CLOSURE.json"
AUTHORIZATION = EXPERIMENT / "MEASURED_EXECUTION_AUTHORIZATION.json"


def main() -> None:
    if PACKAGE.exists() or CLOSURE.exists() or AUTHORIZATION.exists():
        raise FileExistsError("measured freeze artifacts already exist")
    manifest = construct_execution_package(
        PACKAGE,
        bank_root=EXPERIMENT / "fresh_bank",
        schedule_path=EXPERIMENT / "MEASURED_SCHEDULE.json",
        runtime_profile_path=EXPERIMENT / "RUNTIME_PROFILE.json",
    )
    closure = build_executable_closure(ROOT)
    atomic_write(CLOSURE, canonical_json_bytes(closure))
    authorization = expected_authorization(
        repo_root=ROOT,
        experiment=EXPERIMENT,
        closure_path=CLOSURE,
        package_path=PACKAGE,
    )
    atomic_write(AUTHORIZATION, canonical_json_bytes(authorization))
    print({"package_id": manifest["package_id"], "closure": closure["aggregate_sha256"]})


if __name__ == "__main__":
    main()
