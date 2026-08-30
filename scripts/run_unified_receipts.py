from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.measured import FrozenInitialActor, seal_response_tree
from working_set_exp.recurrent_pressure import verify_closure
from working_set_exp.runner import verify_run
from working_set_exp.runtime import LiveActor, OwnedServer, REASONING_BUDGET, load_runtime, port_free
from working_set_exp.unified_receipts import MAXIMUM_HTTP_COMPLETION_CALLS, OUTPUT_ROOT, PORT, READ_MODE, hidden_grade, load_fixture, run_branch, run_shared_prefix, validate_authorization, verify_bank, verify_package

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "014_unified_active_phase_receipts"
OUTPUT = Path(OUTPUT_ROOT)


def _clean_checkout() -> None:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
    if result.stdout:
        raise RuntimeError("Experiment 014 requires a clean checkout")


def _candidate_from_custody(branch_root: Path, candidate_id: str) -> Candidate:
    matches = [p for p in branch_root.rglob(candidate_id[:32]) if p.is_dir() and p.parent.name == "snap"]
    if not matches:
        raise RuntimeError("terminal candidate snapshot is absent")
    snapshot = matches[-1]
    candidate = Candidate.create({p.relative_to(snapshot).as_posix(): p.read_bytes() for p in snapshot.rglob("*") if p.is_file()})
    if candidate.candidate_id != candidate_id:
        raise RuntimeError("terminal candidate snapshot binding differs")
    return candidate


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    _clean_checkout()
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    bank = verify_bank(EXPERIMENT / "fresh_bank")
    package = verify_package(EXPERIMENT / "execution_package", bank=EXPERIMENT / "fresh_bank", profile=profile)
    closure = verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
    authorization = validate_authorization(EXPERIMENT)
    if not port_free(PORT):
        raise RuntimeError("Experiment 014 port is occupied")
    schedule = load_json_strict((EXPERIMENT / "SCHEDULE.json").read_bytes())
    OUTPUT.mkdir(parents=True)
    receipt: dict[str, Any] = {"schema_version": "experiment-014-run-receipt-v1", "status": "started",
        "started_at_utc": utc_now(), "bank": bank, "package": package, "closure": closure,
        "authorization": authorization, "cells": [], "prepared_invocations": 0, "http_completion_calls": 0,
        "retries": 0, "repairs": 0, "rescues": 0, "evaluator_reads_before_seal": False}
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    grade_rows: list[tuple[dict[str, Any], str, Path, str]] = []
    try:
        verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
        server = OwnedServer(profile, OUTPUT, port=PORT, reasoning_mode="auto", reasoning_budget=REASONING_BUDGET)
        with server:
            for row in schedule["cells"]:
                fixture = load_fixture(EXPERIMENT / "fresh_bank", row["fixture_id"])
                cell_root = OUTPUT / f"cell-{row['ordinal']:02d}"
                live = LiveActor(profile, seed=row["seed"], port=PORT, reasoning_enabled=True,
                                 read_mode=READ_MODE, hierarchical_p0=True, result_reopen=True)
                prefix_actor = FrozenInitialActor(inner=live,
                    expected_call_id=f"{fixture.fixture_id}-S{row['seed']}-SHARED-A-P01",
                    package_cell=EXPERIMENT / "execution_package" / f"cell-{row['ordinal']:02d}")
                prefix = run_shared_prefix(fixture, seed=row["seed"], actor=prefix_actor,
                                           output_dir=cell_root / "shared-prefix")
                verify_run(cell_root / "shared-prefix")
                cell: dict[str, Any] = {**row, "prefix": load_json_strict((cell_root / "shared-prefix" / "SUMMARY.json").read_bytes()), "branches": {}}
                receipt["cells"].append(cell); receipt["prepared_invocations"] += prefix.prepared; receipt["http_completion_calls"] += prefix.http
                if prefix.disposition != "phase_complete":
                    cell["status"] = "shared_prefix_model_outcome"; atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt)); continue
                for condition in row["branch_order"]:
                    actor = LiveActor(profile, seed=row["seed"], port=PORT, reasoning_enabled=True,
                                      read_mode=READ_MODE, hierarchical_p0=True, result_reopen=True)
                    branch_root = cell_root / condition
                    summary = run_branch(fixture, prefix, seed=row["seed"], condition=condition,
                                         actor=actor, output_dir=branch_root)
                    cell["branches"][condition] = summary
                    receipt["prepared_invocations"] += summary["prepared_invocations"]
                    receipt["http_completion_calls"] += summary["http_completion_calls"]
                    if receipt["http_completion_calls"] > MAXIMUM_HTTP_COMPLETION_CALLS:
                        raise RuntimeError("authorized HTTP completion-call ceiling exceeded")
                    grade_rows.append((row, condition, branch_root, summary["candidate_id"]))
                    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        receipt["server_shutdown_verified"] = True
        seal = seal_response_tree(OUTPUT); atomic_write(OUTPUT / "RESPONSE_SEAL.json", canonical_json_bytes(seal))
        receipt["status"] = "completed_and_response_sealed"; receipt["completed_at_utc"] = utc_now()
        receipt["response_seal_sha256"] = sha256_file(OUTPUT / "RESPONSE_SEAL.json")
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        grades = []
        for row, condition, branch_root, candidate_id in grade_rows:
            fixture = load_fixture(EXPERIMENT / "fresh_bank", row["fixture_id"])
            candidate = _candidate_from_custody(branch_root, candidate_id)
            grades.append({"ordinal": row["ordinal"], "fixture_id": row["fixture_id"], "seed": row["seed"],
                           "condition": condition, "candidate_id": candidate_id, "hidden": hidden_grade(fixture, candidate)})
        atomic_write(OUTPUT / "POSTSEAL_HIDDEN_GRADING.json", canonical_json_bytes({
            "schema_version": "experiment-014-postseal-hidden-grading-v1",
            "response_seal_sha256": receipt["response_seal_sha256"], "evaluator_opened_after_seal": True, "rows": grades}))
    except Exception as exc:
        receipt["status"] = "infrastructure_or_integrity_stopped"; receipt["stopped_at_utc"] = utc_now()
        receipt["error_type"] = type(exc).__name__; receipt["error"] = str(exc)
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt)); raise


if __name__ == "__main__":
    main()
