from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.measured import FrozenInitialActor
from working_set_exp.reasoning_measured import seal_response_tree
from working_set_exp.recurrent_pressure import (
    MAXIMUM_HTTP_COMPLETION_CALLS,
    MIDDLE_CALL_LIMIT,
    OUTPUT_ROOT,
    PREFIX_CALL_LIMIT,
    load_recurrent_fixture,
    run_final,
    run_middle,
    validate_authorization,
    verify_bank,
    verify_closure,
    verify_package,
)
from working_set_exp.runner import run_prefix, verify_run
from working_set_exp.runtime import LiveActor, OwnedServer, PORT, REASONING_BUDGET, load_runtime, port_free


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "007_recurrent_bounded_pressure"
OUTPUT = Path(OUTPUT_ROOT)


def _clean_checkout() -> None:
    completed = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, check=True, text=True)
    if completed.stdout:
        raise RuntimeError("recurrent execution requires a clean checkout")


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError("recurrent output root already exists")
    _clean_checkout()
    bank = verify_bank(EXPERIMENT / "fresh_bank")
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    package = verify_package(
        EXPERIMENT / "execution_package", bank=EXPERIMENT / "fresh_bank",
        schedule_path=EXPERIMENT / "SCHEDULE.json", profile=profile,
    )
    closure = verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
    authorization = validate_authorization(EXPERIMENT)
    schedule = load_json_strict((EXPERIMENT / "SCHEDULE.json").read_bytes())
    if not port_free(PORT):
        raise RuntimeError("recurrent execution port is occupied")
    OUTPUT.mkdir(parents=True)
    receipt: dict[str, Any] = {
        "schema_version": "experiment-007-recurrent-pressure-receipt-v1", "started_at_utc": utc_now(),
        "status": "started", "bank": bank, "package": package, "closure": closure,
        "authorization": authorization, "actor_sha256": profile.model_sha256,
        "server_reasoning_budget_tokens": REASONING_BUDGET,
        "maximum_http_completion_calls": MAXIMUM_HTTP_COMPLETION_CALLS,
        "prepared_invocations": 0, "http_completion_calls": 0, "attempts_per_call": 1,
        "retries": 0, "repairs": 0, "rescues": 0, "evaluator_reads_before_seal": False, "cells": [],
    }
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    prepared_total = 0
    http_total = 0
    try:
        verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
        with OwnedServer(profile, OUTPUT, port=PORT, reasoning_mode="auto", reasoning_budget=REASONING_BUDGET):
            for row in schedule["cells"]:
                fixture = load_recurrent_fixture(EXPERIMENT / "fresh_bank", row["fixture_id"])
                cell_root = OUTPUT / f"cell-{row['ordinal']:02d}"
                actor = FrozenInitialActor(
                    inner=LiveActor(profile, seed=row["seed"], reasoning_enabled=True),
                    expected_call_id=f"{fixture.fixture_id}-S{row['seed']}-P01",
                    package_cell=EXPERIMENT / "execution_package" / f"cell-{row['ordinal']:02d}",
                )
                cell: dict[str, Any] = {
                    "ordinal": row["ordinal"], "fixture_id": row["fixture_id"], "seed": row["seed"],
                    "branch_order": row["branch_order"], "middle": {}, "final": None,
                }
                receipt["cells"].append(cell)
                atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
                try:
                    prefix = run_prefix(
                        fixture.prefix_fixture(), seed=row["seed"], actor=actor, output_dir=cell_root / "prefix",
                        profile=profile, prefix_call_limit=PREFIX_CALL_LIMIT,
                        continuation_call_limit=MIDDLE_CALL_LIMIT, one_shot_probe=True, reasoning_enabled=True,
                    )
                except RuntimeError:
                    summary_path = cell_root / "prefix" / "SUMMARY.json"
                    if not summary_path.is_file():
                        raise
                    summary = load_json_strict(summary_path.read_bytes())
                    verify_run(cell_root / "prefix")
                    prepared_total += summary["prepared_invocations"]
                    http_total += summary["http_completion_calls"]
                    cell.update({"status": "prefix_model_outcome", "prefix": summary})
                    receipt["prepared_invocations"] = prepared_total
                    receipt["http_completion_calls"] = http_total
                    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
                    continue
                verify_run(cell_root / "prefix")
                prefix_summary = load_json_strict((cell_root / "prefix" / "SUMMARY.json").read_bytes())
                prepared_total += prefix_summary["prepared_invocations"]
                http_total += prefix_summary["http_completion_calls"]
                cell["prefix"] = prefix_summary
                for condition in row["branch_order"]:
                    middle = run_middle(
                        fixture, prefix, condition=condition, seed=row["seed"],
                        actor=LiveActor(profile, seed=row["seed"], reasoning_enabled=True),
                        output_dir=cell_root / condition / "phase-b",
                    )
                    verify_run(cell_root / condition / "phase-b")
                    summary = load_json_strict((cell_root / condition / "phase-b" / "SUMMARY.json").read_bytes())
                    prepared_total += summary["prepared_invocations"]
                    http_total += summary["http_completion_calls"]
                    cell["middle"][condition] = summary
                    if condition == "T25" and middle.disposition == "second_boundary_eligible":
                        final = run_final(
                            fixture, middle, condition="T25", seed=row["seed"],
                            actor=LiveActor(profile, seed=row["seed"], reasoning_enabled=True),
                            output_dir=cell_root / condition / "phase-c",
                        )
                        verify_run(cell_root / condition / "phase-c")
                        prepared_total += final["prepared_invocations"]
                        http_total += final["http_completion_calls"]
                        cell["final"] = final
                    if http_total > MAXIMUM_HTTP_COMPLETION_CALLS:
                        raise RuntimeError("recurrent HTTP-completion maximum exceeded")
                    receipt["prepared_invocations"] = prepared_total
                    receipt["http_completion_calls"] = http_total
                    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
                cell["status"] = "completed"
        seal = seal_response_tree(OUTPUT)
        receipt.update({
            "status": "completed_and_response_sealed", "completed_at_utc": utc_now(),
            "response_seal_sha256": sha256_file(OUTPUT / "RESPONSE_SEAL.json"),
            "response_aggregate_sha256": seal["aggregate_sha256"],
            "server_shutdown_verified": port_free(PORT), "evaluator_reads_before_seal": False,
        })
    except Exception as exc:
        receipt.update({
            "status": "infrastructure_or_integrity_stopped", "completed_at_utc": utc_now(),
            "error_type": type(exc).__name__, "error": str(exc), "server_shutdown_verified": port_free(PORT),
        })
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        raise
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
