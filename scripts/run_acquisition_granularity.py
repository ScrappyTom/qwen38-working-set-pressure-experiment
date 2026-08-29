from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from working_set_exp.acquisition_granularity import (
    CALL_LIMIT,
    READ_MODES,
    verify_bank,
    verify_package,
)
from working_set_exp.fixture import load_fixture
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.measured import FrozenInitialActor
from working_set_exp.reasoning_measured import seal_response_tree
from working_set_exp.recurrent_pressure import verify_closure
from working_set_exp.runner import run_prefix, verify_run
from working_set_exp.runtime import LiveActor, OwnedServer, load_runtime, port_free


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "010_acquisition_granularity"
OUTPUT = Path(r"C:\e10-primary")
PORT = 18112


def _clean_checkout() -> None:
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    if status.stdout:
        raise RuntimeError("Experiment 010 requires a clean checkout")


def _validate_authorization(profile_sha256: str) -> dict[str, Any]:
    authorization = load_json_strict((EXPERIMENT / "MEASURED_AUTHORIZATION.json").read_bytes())
    package = load_json_strict((EXPERIMENT / "execution_package" / "PACKAGE_MANIFEST.json").read_bytes())
    bank = load_json_strict((EXPERIMENT / "fresh_bank" / "BANK_MANIFEST.json").read_bytes())
    closure = load_json_strict((EXPERIMENT / "EXECUTABLE_CLOSURE.json").read_bytes())
    expected = {
        "schema_version": "experiment-010-measured-authorization-v1",
        "status": "owner_authorized_exact_acquisition_granularity_execution",
        "owner_statement": "Plan and test the recommended deterministic acquisition-granularity study.",
        "bank_id": bank["bank_id"],
        "bank_manifest_sha256": sha256_file(EXPERIMENT / "fresh_bank" / "BANK_MANIFEST.json"),
        "package_id": package["package_id"],
        "package_manifest_sha256": sha256_file(EXPERIMENT / "execution_package" / "PACKAGE_MANIFEST.json"),
        "closure_manifest_sha256": sha256_file(EXPERIMENT / "EXECUTABLE_CLOSURE.json"),
        "closure_aggregate_sha256": closure["aggregate_sha256"],
        "schedule_sha256": sha256_file(EXPERIMENT / "SCHEDULE.json"),
        "actor_sha256": profile_sha256,
        "cells": 8,
        "attempts_per_cell": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
        "maximum_actions_per_cell": CALL_LIMIT,
        "conditions": ["L0", "L1"],
        "port": PORT,
        "response_seal_before_evaluator_access": True,
        "output_root": str(OUTPUT),
        "automatic_successor": False,
    }
    if canonical_json_bytes(authorization) != canonical_json_bytes(expected):
        raise RuntimeError("Experiment 010 authorization differs")
    return {"verified": True, "sha256": sha256_file(EXPERIMENT / "MEASURED_AUTHORIZATION.json")}


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    _clean_checkout()
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    bank = verify_bank(EXPERIMENT / "fresh_bank")
    package = verify_package(
        EXPERIMENT / "execution_package", bank=EXPERIMENT / "fresh_bank", profile=profile
    )
    closure = verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
    authorization = _validate_authorization(profile.model_sha256)
    if not port_free(PORT):
        raise RuntimeError("Experiment 010 port is occupied")
    schedule = load_json_strict((EXPERIMENT / "SCHEDULE.json").read_bytes())
    OUTPUT.mkdir(parents=True)
    receipt: dict[str, Any] = {
        "schema_version": "experiment-010-run-receipt-v1",
        "status": "started",
        "started_at_utc": utc_now(),
        "bank": bank,
        "package": package,
        "closure": closure,
        "authorization": authorization,
        "cells": [],
        "prepared_invocations": 0,
        "http_completion_calls": 0,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
        "evaluator_reads_before_seal": False,
    }
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    outcomes = []
    try:
        verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
        server = OwnedServer(profile, OUTPUT, port=PORT, reasoning_mode="auto", reasoning_budget=512)
        with server:
            for row in schedule["cells"]:
                fixture = load_fixture(EXPERIMENT / "fresh_bank", row["fixture_id"])
                read_mode = READ_MODES[row["condition"]]
                inner = LiveActor(
                    profile,
                    seed=row["seed"],
                    port=PORT,
                    reasoning_enabled=True,
                    read_mode=read_mode,
                )
                actor = FrozenInitialActor(
                    inner=inner,
                    expected_call_id=f"{fixture.fixture_id}-S{row['seed']}-P01",
                    package_cell=EXPERIMENT / "execution_package" / f"cell-{row['ordinal']:02d}",
                )
                run_root = OUTPUT / f"cell-{row['ordinal']:02d}"
                outcome = run_prefix(
                    fixture,
                    seed=row["seed"],
                    actor=actor,
                    output_dir=run_root,
                    profile=profile,
                    prefix_call_limit=CALL_LIMIT,
                    continuation_call_limit=1,
                    one_shot_probe=True,
                    reasoning_enabled=True,
                    read_mode=read_mode,
                    acquisition_contract=True,
                    require_pressure_eligible=False,
                )
                replay = verify_run(run_root)
                summary = load_json_strict((run_root / "SUMMARY.json").read_bytes())
                cell = {
                    **row,
                    "summary": summary,
                    "replay": replay,
                    "complete_reads": sorted(outcome.state.complete_reads),
                }
                receipt["cells"].append(cell)
                receipt["prepared_invocations"] += summary["prepared_invocations"]
                receipt["http_completion_calls"] += summary["http_completion_calls"]
                outcomes.append((row, fixture, outcome))
                atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        seal = seal_response_tree(OUTPUT)
        receipt.update(
            {
                "status": "completed_and_response_sealed",
                "completed_at_utc": utc_now(),
                "response_seal_sha256": sha256_file(OUTPUT / "RESPONSE_SEAL.json"),
                "response_aggregate_sha256": seal["aggregate_sha256"],
                "server_shutdown_verified": server.shutdown_verified,
            }
        )
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        grades = []
        for row, fixture, outcome in outcomes:
            hidden = (EXPERIMENT / "fresh_bank" / "evaluator_only" / fixture.fixture_id / "hidden.py").read_bytes()
            grade = run_checker(outcome.state.candidate, hidden)
            grades.append({**row, "candidate_id": outcome.state.candidate.candidate_id, "hidden_passed": grade["passed"]})
        atomic_write(
            OUTPUT / "POSTSEAL_HIDDEN_GRADING.json",
            canonical_json_bytes({"schema_version": "experiment-010-postseal-grading-v1", "cells": grades}),
        )
    except Exception as exc:
        receipt.update(
            {
                "status": "infrastructure_or_integrity_stopped",
                "completed_at_utc": utc_now(),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "server_shutdown_verified": server.shutdown_verified if "server" in locals() else False,
            }
        )
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        raise
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
