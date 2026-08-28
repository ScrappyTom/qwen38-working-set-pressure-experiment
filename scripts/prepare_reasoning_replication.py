from __future__ import annotations

import json
from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes
from working_set_exp.reasoning_replication import (
    build_closure,
    construct_bank,
    construct_package,
    expected_authorization,
    verify_bank,
    verify_package,
)
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "005_bounded_reasoning_source_replication"


def main() -> None:
    bank = EXPERIMENT / "fresh_bank"
    package = EXPERIMENT / "execution_package"
    if bank.exists() or package.exists():
        raise FileExistsError("replication generated artifacts already exist")
    bank_manifest = construct_bank(bank)
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    package_manifest = construct_package(
        package, bank=bank, schedule_path=EXPERIMENT / "SCHEDULE.json", profile=profile
    )
    closure = build_closure(ROOT)
    atomic_write(EXPERIMENT / "EXECUTABLE_CLOSURE.json", canonical_json_bytes(closure))
    authorization = expected_authorization(experiment=EXPERIMENT)
    atomic_write(EXPERIMENT / "MEASURED_AUTHORIZATION.json", canonical_json_bytes(authorization))
    result = {
        "bank": verify_bank(bank),
        "package": verify_package(
            package, bank=bank, schedule_path=EXPERIMENT / "SCHEDULE.json", profile=profile
        ),
        "closure": {"aggregate_sha256": closure["aggregate_sha256"], "file_count": len(closure["files"])},
        "authorization": authorization,
        "bank_id": bank_manifest["bank_id"],
        "package_id": package_manifest["package_id"],
        "model_calls": 0,
    }
    atomic_write(EXPERIMENT / "OFFLINE_QUALIFICATION.json", canonical_json_bytes(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
