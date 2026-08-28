from __future__ import annotations

import json
import subprocess
from pathlib import Path

from working_set_exp.fixture import load_fixture
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.measured import FrozenInitialActor
from working_set_exp.progress import BRANCH_CALL_LIMIT, PREFIX_CALL_LIMIT, progress_pointer, verify_bank
from working_set_exp.progress_measured import (
    OUTPUT_ROOT, seal_response_tree, validate_authorization, verify_executable_closure, verify_execution_package,
)
from working_set_exp.runner import run_branch, run_prefix, verify_run
from working_set_exp.runtime import LiveActor, OwnedServer, PORT, load_runtime, port_free


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "003_progress_pointer_diagnostic"
PACKAGE = EXPERIMENT / "measured_execution_package"
CLOSURE = EXPERIMENT / "MEASURED_EXECUTABLE_CLOSURE.json"
AUTHORIZATION = EXPERIMENT / "MEASURED_EXECUTION_AUTHORIZATION.json"
OUTPUT = Path(OUTPUT_ROOT)


def _clean_checkout() -> None:
    completed = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, check=True, text=True)
    if completed.stdout:
        raise RuntimeError("progress measured execution requires a clean checkout")


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError("progress measured output root already exists")
    _clean_checkout()
    package = verify_execution_package(
        PACKAGE, bank_root=EXPERIMENT / "fresh_bank", schedule_path=EXPERIMENT / "MEASURED_SCHEDULE.json",
        runtime_profile_path=EXPERIMENT / "RUNTIME_PROFILE.json",
    )
    closure = verify_executable_closure(ROOT, CLOSURE)
    authorization = validate_authorization(
        experiment=EXPERIMENT, closure_path=CLOSURE, package_path=PACKAGE, authorization_path=AUTHORIZATION,
    )
    bank = verify_bank(EXPERIMENT / "fresh_bank")
    schedule = load_json_strict((EXPERIMENT / "MEASURED_SCHEDULE.json").read_bytes())
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    if not port_free(PORT):
        raise RuntimeError("dedicated progress-study port is occupied")
    OUTPUT.mkdir(parents=True)
    receipt: dict[str, object] = {
        "schema_version": "experiment-003-progress-measured-receipt-v1", "started_at_utc": utc_now(),
        "status": "started", "authorization": authorization, "package": package, "closure": closure, "bank": bank,
        "schedule_sha256": sha256_file(EXPERIMENT / "MEASURED_SCHEDULE.json"), "actor_sha256": profile.model_sha256,
        "attempts_per_call": 1, "retries": 0, "repairs": 0, "rescues": 0,
        "evaluator_reads_before_seal": False, "prefixes": [],
    }
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    try:
        verify_executable_closure(ROOT, CLOSURE)
        with OwnedServer(profile, OUTPUT, port=PORT):
            for row in schedule["prefix_order"]:
                ordinal = row["ordinal"]
                root = OUTPUT / f"prefix-{ordinal:02d}"
                fixture = load_fixture(EXPERIMENT / "fresh_bank", row["fixture_id"])
                actor = FrozenInitialActor(
                    inner=LiveActor(profile, seed=row["seed"]),
                    expected_call_id=f"{fixture.fixture_id}-S{row['seed']}-P01",
                    package_cell=PACKAGE / f"prefix-{ordinal:02d}",
                )
                cell: dict[str, object] = {
                    "ordinal": ordinal, "fixture_id": fixture.fixture_id, "seed": row["seed"],
                    "status": "prefix_started", "branches": {},
                }
                receipt["prefixes"].append(cell)  # type: ignore[union-attr]
                atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
                try:
                    prefix = run_prefix(
                        fixture, seed=row["seed"], actor=actor, output_dir=root / "shared_prefix", profile=profile,
                        prefix_call_limit=PREFIX_CALL_LIMIT, continuation_call_limit=BRANCH_CALL_LIMIT, one_shot_probe=True,
                    )
                except RuntimeError:
                    summary_path = root / "shared_prefix" / "SUMMARY.json"
                    if not summary_path.is_file():
                        raise
                    summary = load_json_strict(summary_path.read_bytes())
                    if summary["disposition"] not in {"prefix_incomplete", "pressure_boundary_not_eligible"}:
                        raise
                    verify_run(root / "shared_prefix")
                    cell.update({"status": "prefix_model_outcome", "prefix": summary})
                    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
                    continue
                verify_run(root / "shared_prefix")
                cell["prefix"] = load_json_strict((root / "shared_prefix" / "SUMMARY.json").read_bytes())
                cell["status"] = "branches_started"
                for condition in row["branch_order"]:
                    pointer = progress_pointer(EXPERIMENT / "fresh_bank", fixture.fixture_id) if condition == "T25-P" else None
                    summary = run_branch(
                        fixture, prefix, condition=condition, seed=row["seed"],
                        actor=LiveActor(profile, seed=row["seed"]), output_dir=root / condition,
                        progress_pointer=pointer, prefix_call_limit=PREFIX_CALL_LIMIT, branch_call_limit=BRANCH_CALL_LIMIT,
                    )
                    verify_run(root / condition)
                    cell["branches"][condition] = summary  # type: ignore[index]
                    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
                cell["status"] = "completed"
                atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        seal = seal_response_tree(OUTPUT)
        receipt.update(
            {
                "status": "completed_and_response_sealed", "completed_at_utc": utc_now(),
                "response_seal_sha256": sha256_file(OUTPUT / "RESPONSE_SEAL.json"),
                "response_aggregate_sha256": seal["aggregate_sha256"], "server_shutdown_verified": port_free(PORT),
                "evaluator_reads_before_seal": False,
            }
        )
    except Exception as exc:
        receipt.update(
            {"status": "infrastructure_or_integrity_stopped", "completed_at_utc": utc_now(),
             "error_type": type(exc).__name__, "error": str(exc), "server_shutdown_verified": port_free(PORT)}
        )
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        raise
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
