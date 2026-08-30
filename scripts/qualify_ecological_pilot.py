from __future__ import annotations

from pathlib import Path

from working_set_exp.ecological_pilot import (
    CASE_IDS,
    admitted_donor_candidate,
    closure,
    construct_package,
    hidden_grade,
    load_fixture,
    verify_bank,
    verify_package,
)
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, sha256_file, utc_now
from working_set_exp.recurrent_pressure import verify_closure
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "019_owner_controlled_ecological_pilot"


def main() -> None:
    bank = verify_bank(EXPERIMENT / "fresh_bank")
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    package_dir = EXPERIMENT / "execution_package"
    if not package_dir.exists():
        construct_package(package_dir, bank=EXPERIMENT / "fresh_bank", profile=profile)
    package = verify_package(package_dir, bank=EXPERIMENT / "fresh_bank", profile=profile)
    closure_path = EXPERIMENT / "EXECUTABLE_CLOSURE.json"
    observed_closure = closure(ROOT)
    atomic_write(closure_path, canonical_json_bytes(observed_closure))
    verified_closure = verify_closure(ROOT, closure_path)
    donor = admitted_donor_candidate(EXPERIMENT / "fresh_bank")
    checks = []
    for fixture_id in CASE_IDS:
        fixture = load_fixture(EXPERIMENT / "fresh_bank", fixture_id, include_evaluator=True)
        initial_public = run_checker(fixture.initial, fixture.public_checker)
        initial_hidden = hidden_grade(fixture, fixture.initial)
        good_public = run_checker(donor, fixture.public_checker)
        good_hidden = hidden_grade(fixture, donor)
        if initial_public["passed"] or initial_hidden["passed"] or not good_public["passed"] or not good_hidden["passed"]:
            raise RuntimeError("Experiment 019 fixture qualification differs")
        checks.append({
            "fixture_id": fixture_id,
            "initial_public_passed": False,
            "initial_hidden_passed": False,
            "known_good_public_passed": True,
            "known_good_hidden_passed": True,
        })
    receipt = {
        "schema_version": "experiment-019-offline-qualification-v1",
        "status": "offline_qualified_not_model_exposed",
        "qualified_at_utc": utc_now(),
        "bank": bank,
        "package": package,
        "closure": verified_closure,
        "fixture_checks": checks,
        "runtime_profile_sha256": sha256_file(EXPERIMENT / "RUNTIME_PROFILE.json"),
        "canonical_payload_identity": {
            "reopen_is_access_not_new_payload": True,
            "model_request_required_for_every_reopen": True,
            "automatic_reuse": False,
        },
        "model_calls": 0,
        "endpoint_requests": 0,
        "gpu_launches": 0,
    }
    atomic_write(EXPERIMENT / "OFFLINE_QUALIFICATION_RECEIPT.json", canonical_json_bytes(receipt))
    print(canonical_json_bytes(receipt).decode())


if __name__ == "__main__":
    main()
