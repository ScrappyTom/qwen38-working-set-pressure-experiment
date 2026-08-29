from __future__ import annotations

import json
from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, sha256_file
from working_set_exp.observation_recurrence import development_case_definition
from working_set_exp.recurrent_pressure import build_closure, construct_bank, verify_bank, verify_closure
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "009_recurrent_observation_validity"
DEVELOPMENT = EXPERIMENT / "development_rehearsal"


def main() -> None:
    bank = DEVELOPMENT / "bank"
    if bank.exists():
        raise FileExistsError("Experiment 009 development bank already exists")
    construct_bank(bank, definitions=(development_case_definition(),))
    load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    closure = build_closure(ROOT, entrypoint="scripts/run_observation_recurrence_development.py")
    atomic_write(DEVELOPMENT / "EXECUTABLE_CLOSURE.json", canonical_json_bytes(closure))
    authorization = {
        "schema_version": "experiment-009-development-rehearsal-authorization-v1",
        "status": "owner_authorized_fresh_development_only_live_rehearsal",
        "owner_statement": "Proceed with the next recurrent observation-validity experiment.",
        "fixture_id": "E9-DEV-OBS-GAMMA",
        "seed": 314159,
        "branch_order": ["T25", "C50"],
        "conditions": ["T25-R1-host-v2", "C50-R1"],
        "bank_manifest_sha256": sha256_file(bank / "BANK_MANIFEST.json"),
        "closure_manifest_sha256": sha256_file(DEVELOPMENT / "EXECUTABLE_CLOSURE.json"),
        "closure_aggregate_sha256": closure["aggregate_sha256"],
        "runtime_profile_sha256": sha256_file(EXPERIMENT / "RUNTIME_PROFILE.json"),
        "measured_bank_exposure": False,
        "attempts_per_call": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
        "response_seal_before_review": True,
        "output_root": r"C:\e9-dev",
        "automatic_successor": False,
    }
    atomic_write(DEVELOPMENT / "AUTHORIZATION.json", canonical_json_bytes(authorization))
    result = {
        "schema_version": "experiment-009-development-preparation-v1",
        "bank": verify_bank(bank),
        "closure": verify_closure(ROOT, DEVELOPMENT / "EXECUTABLE_CLOSURE.json"),
        "authorization": authorization,
        "model_calls": 0,
    }
    atomic_write(DEVELOPMENT / "OFFLINE_PREPARATION.json", canonical_json_bytes(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
