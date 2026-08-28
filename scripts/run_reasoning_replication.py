from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from working_set_exp.fixture import load_fixture
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.reasoning import BRANCH_CALL_LIMIT, PREFIX_CALL_LIMIT
from working_set_exp.reasoning_measured import seal_response_tree
from working_set_exp.reasoning_replication import (
    MAXIMUM_COMPLETION_CALLS,
    OUTPUT_ROOT,
    FrozenBranchActor,
    construct_prefix,
    progress_pointer,
    validate_authorization,
    verify_bank,
    verify_closure,
    verify_package,
)
from working_set_exp.runner import run_branch, verify_run
from working_set_exp.runtime import LiveActor, OwnedServer, PORT, REASONING_BUDGET, load_runtime, port_free


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "005_bounded_reasoning_source_replication"
OUTPUT = Path(OUTPUT_ROOT)


def _clean_checkout() -> None:
    completed = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, check=True, text=True)
    if completed.stdout:
        raise RuntimeError("reasoning replication requires a clean checkout")


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError("reasoning replication output root already exists")
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
        raise RuntimeError("replication port is occupied")
    OUTPUT.mkdir(parents=True)
    receipt: dict[str, Any] = {
        "schema_version": "experiment-005-reasoning-replication-receipt-v1",
        "started_at_utc": utc_now(), "status": "started", "bank": bank,
        "package": package, "closure": closure, "authorization": authorization,
        "actor_sha256": profile.model_sha256, "server_reasoning_budget_tokens": REASONING_BUDGET,
        "maximum_completion_calls": MAXIMUM_COMPLETION_CALLS, "model_calls": 0,
        "attempts_per_call": 1, "retries": 0, "repairs": 0, "rescues": 0,
        "evaluator_reads_before_seal": False, "cases": [],
    }
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    prefixes = {}
    for row in schedule["cases"]:
        prefixes[row["fixture_id"]] = construct_prefix(
            bank=EXPERIMENT / "fresh_bank", fixture_id=row["fixture_id"], seed=row["seed"],
            profile=profile, output=OUTPUT / f"case-{row['ordinal']:02d}" / "constructed_prefix",
        )
        verify_run(prefixes[row["fixture_id"]].output_dir)
    total_calls = 0
    try:
        verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
        with OwnedServer(
            profile, OUTPUT, port=PORT, reasoning_mode="auto", reasoning_budget=REASONING_BUDGET
        ):
            for row in schedule["cases"]:
                fixture = load_fixture(EXPERIMENT / "fresh_bank", row["fixture_id"])
                prefix = prefixes[row["fixture_id"]]
                case_receipt = {
                    "ordinal": row["ordinal"], "fixture_id": row["fixture_id"],
                    "seed": row["seed"], "branch_order": row["branch_order"], "branches": {},
                }
                receipt["cases"].append(case_receipt)
                for condition in row["branch_order"]:
                    cell = EXPERIMENT / "execution_package" / f"case-{row['ordinal']:02d}-{condition}"
                    actor = FrozenBranchActor(
                        inner=LiveActor(profile, seed=row["seed"], reasoning_enabled=condition == "R1"),
                        expected_call_id=f"{row['fixture_id']}-S{row['seed']}-{condition}-01",
                        package_cell=cell,
                    )
                    summary = run_branch(
                        fixture, prefix, condition=condition, seed=row["seed"], actor=actor,
                        output_dir=OUTPUT / f"case-{row['ordinal']:02d}" / condition,
                        progress_pointer=progress_pointer(EXPERIMENT / "fresh_bank", fixture.fixture_id),
                        prefix_call_limit=PREFIX_CALL_LIMIT, branch_call_limit=BRANCH_CALL_LIMIT,
                    )
                    verify_run(OUTPUT / f"case-{row['ordinal']:02d}" / condition)
                    total_calls += summary["calls"]
                    if total_calls > MAXIMUM_COMPLETION_CALLS:
                        raise RuntimeError("replication completion-call maximum exceeded")
                    case_receipt["branches"][condition] = summary
                    receipt["model_calls"] = total_calls
                    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        seal = seal_response_tree(OUTPUT)
        receipt.update(
            {
                "status": "completed_and_response_sealed", "completed_at_utc": utc_now(),
                "response_seal_sha256": sha256_file(OUTPUT / "RESPONSE_SEAL.json"),
                "response_aggregate_sha256": seal["aggregate_sha256"],
                "server_shutdown_verified": port_free(PORT), "evaluator_reads_before_seal": False,
            }
        )
    except Exception as exc:
        receipt.update(
            {
                "status": "infrastructure_or_integrity_stopped", "completed_at_utc": utc_now(),
                "error_type": type(exc).__name__, "error": str(exc),
                "server_shutdown_verified": port_free(PORT),
            }
        )
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        raise
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
