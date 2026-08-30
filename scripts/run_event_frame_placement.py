from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from working_set_exp.candidate import Candidate
from working_set_exp.event_frame_placement import (
    MAXIMUM_HTTP_COMPLETION_CALLS,
    OUTPUT_ROOT,
    PORT,
    READ_MODE,
    hidden_grade,
    load_fixture,
    run_branch,
    validate_authorization,
    verify_package,
)
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.measured import seal_response_tree
from working_set_exp.recurrent_pressure import verify_closure
from working_set_exp.runner import verify_run
from working_set_exp.runtime import LiveActor, OwnedServer, REASONING_BUDGET, load_runtime, port_free


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "015_event_frame_placement_qualification"
DONOR_BANK = ROOT / "experiments" / "014_unified_active_phase_receipts" / "fresh_bank"
OUTPUT = Path(OUTPUT_ROOT)


class FrozenPlacementActor:
    def __init__(self, inner: LiveActor, *, expected_call_id: str, package_cell: Path):
        self.inner = inner
        self.expected_call_id = expected_call_id
        self.package_cell = package_cell
        self.checked = False

    def prepare(
        self,
        request: bytes,
        *,
        stage: str,
        probe_id: str | None,
        call_id: str,
        active_total_ceiling: int,
    ):
        prepared = self.inner.prepare(
            request,
            stage=stage,
            probe_id=probe_id,
            call_id=call_id,
            active_total_ceiling=active_total_ceiling,
        )
        if not self.checked:
            if call_id != self.expected_call_id or stage != "continuation":
                raise RuntimeError("first placement call identity differs")
            for observed, name in (
                (request, "initial-coding-request.json"),
                (prepared.endpoint_request, "initial-endpoint-request.json"),
                (prepared.rendered_prompt, "initial-rendered-prompt.txt"),
            ):
                if observed != (self.package_cell / name).read_bytes():
                    raise RuntimeError(f"first placement {name} differs from freeze")
            self.checked = True
        return prepared

    def invoke(self, prepared):
        return self.inner.invoke(prepared)


def _clean_checkout() -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    if result.stdout:
        raise RuntimeError("Experiment 015 requires a clean checkout")


def _candidate_from_custody(branch_root: Path, candidate_id: str) -> Candidate:
    matches = [path for path in branch_root.rglob(candidate_id[:32]) if path.is_dir() and path.parent.name == "snap"]
    if not matches:
        raise RuntimeError("terminal placement candidate snapshot is absent")
    snapshot = matches[-1]
    candidate = Candidate.create(
        {path.relative_to(snapshot).as_posix(): path.read_bytes() for path in snapshot.rglob("*") if path.is_file()}
    )
    if candidate.candidate_id != candidate_id:
        raise RuntimeError("terminal placement candidate binding differs")
    return candidate


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    _clean_checkout()
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    package = verify_package(EXPERIMENT / "execution_package", donor_bank=DONOR_BANK, profile=profile)
    closure = verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
    authorization = validate_authorization(EXPERIMENT)
    if not port_free(PORT):
        raise RuntimeError("Experiment 015 dedicated port is occupied")
    planned = load_json_strict((EXPERIMENT / "SCHEDULE.json").read_bytes())
    OUTPUT.mkdir(parents=True)
    receipt: dict[str, Any] = {
        "schema_version": "experiment-015-development-run-receipt-v1",
        "status": "started",
        "started_at_utc": utc_now(),
        "development_only": True,
        "package": package,
        "closure": closure,
        "authorization": authorization,
        "cells": [],
        "prepared_invocations": 0,
        "http_completion_calls": 0,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
        "large_world_fixture_exposure": False,
    }
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    grade_rows: list[tuple[dict[str, Any], str, Path, str]] = []
    try:
        verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
        server = OwnedServer(profile, OUTPUT, port=PORT, reasoning_mode="auto", reasoning_budget=REASONING_BUDGET)
        with server:
            for row in planned["cells"]:
                cell: dict[str, Any] = {**row, "branches": {}}
                receipt["cells"].append(cell)
                for condition in row["branch_order"]:
                    package_cell = EXPERIMENT / "execution_package" / f"cell-{row['ordinal']:02d}" / condition
                    expected_call_id = f"D15-{row['fixture_id']}-S{row['seed']}-{condition}-P01"
                    live = LiveActor(
                        profile,
                        seed=row["seed"],
                        port=PORT,
                        reasoning_enabled=True,
                        read_mode=READ_MODE,
                        hierarchical_p0=True,
                        result_reopen=True,
                    )
                    actor = FrozenPlacementActor(
                        live, expected_call_id=expected_call_id, package_cell=package_cell
                    )
                    branch_root = OUTPUT / f"cell-{row['ordinal']:02d}" / condition
                    summary = run_branch(
                        DONOR_BANK,
                        fixture_id=row["fixture_id"],
                        seed=row["seed"],
                        condition=condition,
                        actor=actor,
                        output_dir=branch_root,
                    )
                    verify_run(branch_root)
                    if not actor.checked:
                        raise RuntimeError("frozen initial placement request was not checked")
                    cell["branches"][condition] = summary
                    receipt["prepared_invocations"] += summary["http_completion_calls"]
                    receipt["http_completion_calls"] += summary["http_completion_calls"]
                    if receipt["http_completion_calls"] > MAXIMUM_HTTP_COMPLETION_CALLS:
                        raise RuntimeError("authorized placement HTTP ceiling exceeded")
                    grade_rows.append((row, condition, branch_root, summary["candidate_id"]))
                    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        if not server.shutdown_verified:
            raise RuntimeError("Experiment 015 owned server shutdown differs")
        receipt["server_shutdown_verified"] = True
        seal = seal_response_tree(OUTPUT)
        atomic_write(OUTPUT / "RESPONSE_SEAL.json", canonical_json_bytes(seal))
        receipt["status"] = "completed_and_response_sealed"
        receipt["completed_at_utc"] = utc_now()
        receipt["response_seal_sha256"] = sha256_file(OUTPUT / "RESPONSE_SEAL.json")
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        grades = []
        for row, condition, branch_root, candidate_id in grade_rows:
            fixture = load_fixture(DONOR_BANK, row["fixture_id"])
            candidate = _candidate_from_custody(branch_root, candidate_id)
            grades.append(
                {
                    "ordinal": row["ordinal"],
                    "fixture_id": row["fixture_id"],
                    "seed": row["seed"],
                    "condition": condition,
                    "candidate_id": candidate_id,
                    "hidden": hidden_grade(fixture, candidate),
                }
            )
        atomic_write(
            OUTPUT / "POSTSEAL_HIDDEN_GRADING.json",
            canonical_json_bytes(
                {
                    "schema_version": "experiment-015-postseal-hidden-grading-v1",
                    "response_seal_sha256": receipt["response_seal_sha256"],
                    "evaluator_opened_after_seal": True,
                    "rows": grades,
                }
            ),
        )
    except Exception as exc:
        receipt["status"] = "infrastructure_or_integrity_stopped"
        receipt["stopped_at_utc"] = utc_now()
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        raise


if __name__ == "__main__":
    main()
