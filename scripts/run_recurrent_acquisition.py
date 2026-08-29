from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from working_set_exp.isolation import run_checker
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.measured import FrozenInitialActor
from working_set_exp.reasoning_measured import seal_response_tree
from working_set_exp.recurrent_acquisition import (
    MAXIMUM_HTTP_COMPLETION_CALLS, OUTPUT_ROOT, PORT, READ_MODES, validate_authorization, verify_package,
)
from working_set_exp.recurrent_host_v2 import run_t25_final_operational
from working_set_exp.recurrent_pressure import (
    MIDDLE_CALL_LIMIT, PREFIX_CALL_LIMIT, load_recurrent_fixture, run_middle, verify_bank, verify_closure,
)
from working_set_exp.runner import run_prefix, verify_run
from working_set_exp.runtime import LiveActor, OwnedServer, REASONING_BUDGET, load_runtime, port_free


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "011_recurrent_acquisition_granularity"
OUTPUT = Path(OUTPUT_ROOT)


def _clean_checkout() -> None:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
    if result.stdout:
        raise RuntimeError("Experiment 011 requires a clean checkout")


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
        raise RuntimeError("Experiment 011 port is occupied")
    schedule = load_json_strict((EXPERIMENT / "SCHEDULE.json").read_bytes())
    OUTPUT.mkdir(parents=True)
    receipt: dict[str, Any] = {
        "schema_version": "experiment-011-run-receipt-v1", "status": "started", "started_at_utc": utc_now(),
        "bank": bank, "package": package, "closure": closure, "authorization": authorization,
        "cells": [], "prepared_invocations": 0, "http_completion_calls": 0,
        "retries": 0, "repairs": 0, "rescues": 0, "evaluator_reads_before_seal": False,
    }
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    grade_inputs = []
    try:
        verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
        server = OwnedServer(profile, OUTPUT, port=PORT, reasoning_mode="auto", reasoning_budget=REASONING_BUDGET)
        with server:
            for row in schedule["cells"]:
                fixture = load_recurrent_fixture(EXPERIMENT / "fresh_bank", row["fixture_id"])
                cell_root = OUTPUT / f"cell-{row['ordinal']:02d}"
                prefix_actor = FrozenInitialActor(
                    inner=LiveActor(profile, seed=row["seed"], port=PORT, reasoning_enabled=True),
                    expected_call_id=f"{fixture.fixture_id}-S{row['seed']}-P01",
                    package_cell=EXPERIMENT / "execution_package" / f"cell-{row['ordinal']:02d}",
                )
                cell: dict[str, Any] = {**row, "branches": {}}
                receipt["cells"].append(cell)
                try:
                    prefix = run_prefix(
                        fixture.prefix_fixture(), seed=row["seed"], actor=prefix_actor,
                        output_dir=cell_root / "shared-prefix", profile=profile,
                        prefix_call_limit=PREFIX_CALL_LIMIT, continuation_call_limit=MIDDLE_CALL_LIMIT,
                        one_shot_probe=True, reasoning_enabled=True,
                    )
                except RuntimeError:
                    verify_run(cell_root / "shared-prefix")
                    prefix_summary = load_json_strict((cell_root / "shared-prefix" / "SUMMARY.json").read_bytes())
                    cell["prefix"] = prefix_summary
                    cell["status"] = "shared_prefix_model_outcome"
                    receipt["prepared_invocations"] += prefix_summary["prepared_invocations"]
                    receipt["http_completion_calls"] += prefix_summary["http_completion_calls"]
                    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
                    continue
                verify_run(cell_root / "shared-prefix")
                prefix_summary = load_json_strict((cell_root / "shared-prefix" / "SUMMARY.json").read_bytes())
                cell["prefix"] = prefix_summary
                receipt["prepared_invocations"] += prefix_summary["prepared_invocations"]
                receipt["http_completion_calls"] += prefix_summary["http_completion_calls"]
                for condition in row["branch_order"]:
                    read_mode = READ_MODES[condition]
                    branch_root = cell_root / condition
                    middle = run_middle(
                        fixture, prefix, condition="T25", condition_label=condition, seed=row["seed"],
                        actor=LiveActor(profile, seed=row["seed"], port=PORT, reasoning_enabled=True, read_mode=read_mode),
                        output_dir=branch_root / "phase-b", read_mode=read_mode,
                        observation_directory_version=2, acquisition_contract=True,
                    )
                    verify_run(branch_root / "phase-b")
                    middle_summary = load_json_strict((branch_root / "phase-b" / "SUMMARY.json").read_bytes())
                    final_summary = None
                    if middle.binding is not None and middle.disposition in {"second_boundary_eligible", "second_boundary_not_reached"}:
                        final_summary = run_t25_final_operational(
                            fixture, middle, seed=row["seed"], condition_label=condition,
                            actor=LiveActor(profile, seed=row["seed"], port=PORT, reasoning_enabled=True, read_mode=read_mode),
                            output_dir=branch_root / "phase-c", read_mode=read_mode,
                            observation_directory_version=2, acquisition_contract=True,
                        )
                        verify_run(branch_root / "phase-c")
                    prepared = middle_summary["prepared_invocations"] + (final_summary or {}).get("prepared_invocations", 0)
                    http = middle_summary["http_completion_calls"] + (final_summary or {}).get("http_completion_calls", 0)
                    receipt["prepared_invocations"] += prepared
                    receipt["http_completion_calls"] += http
                    cell["branches"][condition] = {"middle": middle_summary, "final": final_summary}
                    grade_inputs.append((row, condition, fixture, middle, final_summary, branch_root))
                    if receipt["http_completion_calls"] > MAXIMUM_HTTP_COMPLETION_CALLS:
                        raise RuntimeError("Experiment 011 HTTP completion maximum exceeded")
                    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        seal = seal_response_tree(OUTPUT)
        receipt.update({
            "status": "completed_and_response_sealed", "completed_at_utc": utc_now(),
            "response_seal_sha256": sha256_file(OUTPUT / "RESPONSE_SEAL.json"),
            "response_aggregate_sha256": seal["aggregate_sha256"],
            "server_shutdown_verified": server.shutdown_verified,
        })
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        grades = []
        for row, condition, fixture, middle, final_summary, branch_root in grade_inputs:
            candidate = middle.state.candidate
            if final_summary is not None:
                candidate_id = final_summary["candidate_id"]
                snapshot = branch_root / "phase-c" / "snap" / candidate_id[:32]
                if snapshot.exists():
                    files = {
                        path.relative_to(snapshot).as_posix(): path.read_bytes()
                        for path in snapshot.rglob("*") if path.is_file()
                    }
                    candidate = Candidate.create(files)
                if candidate.candidate_id != candidate_id:
                    raise RuntimeError("terminal candidate custody differs")
            grade = run_checker(candidate, fixture.hidden_checker)
            grades.append({**row, "condition": condition, "candidate_id": candidate.candidate_id, "hidden_passed": grade["passed"]})
        atomic_write(OUTPUT / "POSTSEAL_HIDDEN_GRADING.json", canonical_json_bytes({
            "schema_version": "experiment-011-postseal-grading-v1", "branches": grades,
        }))
    except Exception as exc:
        receipt.update({
            "status": "infrastructure_or_integrity_stopped", "completed_at_utc": utc_now(),
            "error_type": type(exc).__name__, "error": str(exc),
            "server_shutdown_verified": server.shutdown_verified if "server" in locals() else False,
        })
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        raise
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
