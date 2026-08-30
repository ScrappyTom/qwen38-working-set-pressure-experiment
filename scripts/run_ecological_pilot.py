from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from working_set_exp.candidate import Candidate
from working_set_exp.ecological_pilot import (
    MAXIMUM_HTTP_COMPLETION_CALLS,
    OUTPUT_ROOT,
    PORT,
    hidden_grade,
    load_fixture,
    run_branch,
    run_shared_prefix,
    validate_authorization,
    verify_bank,
    verify_package,
    verify_source_closure,
)
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.measured import seal_response_tree
from working_set_exp.runner import verify_run
from working_set_exp.runtime import LiveActor, OwnedServer, REASONING_BUDGET, load_runtime, port_free


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "019_owner_controlled_ecological_pilot"
OUTPUT = Path(OUTPUT_ROOT)
EVIDENCE = EXPERIMENT / "measured_run"


class FrozenSharedActor:
    def __init__(self, inner: LiveActor, *, expected_call_id: str, package_cell: Path):
        self.inner = inner
        self.profile = inner.profile
        self.expected_call_id = expected_call_id
        self.package_cell = package_cell
        self.checked = False

    def prepare(self, request: bytes, *, stage: str, probe_id: str | None, call_id: str, active_total_ceiling: int):
        prepared = self.inner.prepare(
            request,
            stage=stage,
            probe_id=probe_id,
            call_id=call_id,
            active_total_ceiling=active_total_ceiling,
        )
        if not self.checked:
            if call_id != self.expected_call_id or stage != "continuation":
                raise RuntimeError("first Experiment 019 call identity differs")
            for observed, name in (
                (request, "initial-coding-request.json"),
                (prepared.endpoint_request, "initial-endpoint-request.json"),
                (prepared.rendered_prompt, "initial-rendered-prompt.txt"),
            ):
                if observed != (self.package_cell / name).read_bytes():
                    raise RuntimeError(f"frozen first {name} differs")
            self.checked = True
        return prepared

    def invoke(self, prepared):
        return self.inner.invoke(prepared)


def _clean_checkout() -> None:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
    if result.stdout:
        raise RuntimeError("Experiment 019 requires a clean checkout")


def _candidate_from_custody(branch: Path, candidate_id: str) -> Candidate:
    matches = [path for path in branch.rglob(candidate_id[:32]) if path.is_dir() and path.parent.name == "snap"]
    for snapshot in reversed(matches):
        candidate = Candidate.create(
            {
                path.relative_to(snapshot).as_posix(): path.read_bytes()
                for path in snapshot.rglob("*")
                if path.is_file()
            }
        )
        if candidate.candidate_id == candidate_id:
            return candidate
    raise RuntimeError("terminal Experiment 019 candidate snapshot absent")


def main() -> None:
    if OUTPUT.exists() or EVIDENCE.exists():
        raise FileExistsError("Experiment 019 output root already exists")
    _clean_checkout()
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    bank = verify_bank(EXPERIMENT / "fresh_bank")
    package = verify_package(EXPERIMENT / "execution_package", bank=EXPERIMENT / "fresh_bank", profile=profile)
    closure = verify_source_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
    authorization = validate_authorization(EXPERIMENT)
    if not port_free(PORT):
        raise RuntimeError("Experiment 019 dedicated port is occupied")
    planned = load_json_strict((EXPERIMENT / "SCHEDULE.json").read_bytes())
    OUTPUT.mkdir(parents=True)
    receipt: dict[str, Any] = {
        "schema_version": "experiment-019-run-receipt-v1",
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
    grade_rows: list[tuple[dict[str, Any], str, Path, str]] = []
    try:
        verify_source_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
        server = OwnedServer(profile, OUTPUT, port=PORT, reasoning_mode="auto", reasoning_budget=REASONING_BUDGET)
        with server:
            for row in planned["cells"]:
                fixture = load_fixture(EXPERIMENT / "fresh_bank", row["fixture_id"], include_evaluator=False)
                cell_root = OUTPUT / f"cell-{row['ordinal']:02d}"
                live = LiveActor(
                    profile,
                    seed=row["seed"],
                    port=PORT,
                    reasoning_enabled=True,
                    read_mode="maximal_bounded_page",
                    hierarchical_p0=True,
                    result_reopen=True,
                    event_reopen=True,
                )
                frozen = FrozenSharedActor(
                    inner=live,
                    expected_call_id=f"{fixture.fixture_id}-S{row['seed']}-SHARED-P01",
                    package_cell=EXPERIMENT / "execution_package" / f"cell-{row['ordinal']:02d}",
                )
                prefix = run_shared_prefix(fixture, seed=row["seed"], actor=frozen, output_dir=cell_root / "shared")
                verify_run(cell_root / "shared")
                cell: dict[str, Any] = {
                    **row,
                    "shared": load_json_strict((cell_root / "shared" / "SUMMARY.json").read_bytes()),
                    "branches": {},
                }
                receipt["cells"].append(cell)
                receipt["prepared_invocations"] += prefix.prepared
                receipt["http_completion_calls"] += prefix.calls
                if prefix.disposition != "authentic_25k_boundary_reached":
                    cell["status"] = "shared_prefix_model_or_capacity_outcome"
                    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
                    continue
                for condition in row["branch_order"]:
                    actor = LiveActor(
                        profile,
                        seed=row["seed"],
                        port=PORT,
                        reasoning_enabled=True,
                        read_mode="maximal_bounded_page",
                        hierarchical_p0=True,
                        result_reopen=True,
                        event_reopen=True,
                    )
                    branch_root = cell_root / condition
                    summary = run_branch(
                        fixture,
                        prefix,
                        seed=row["seed"],
                        condition=condition,
                        actor=actor,
                        output_dir=branch_root,
                    )
                    cell["branches"][condition] = summary
                    receipt["prepared_invocations"] += summary["prepared_invocations"]
                    receipt["http_completion_calls"] += summary["branch_http_calls"]
                    if receipt["http_completion_calls"] > MAXIMUM_HTTP_COMPLETION_CALLS:
                        raise RuntimeError("Experiment 019 HTTP completion ceiling exceeded")
                    grade_rows.append((row, condition, branch_root, summary["candidate_id"]))
                    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        if not server.shutdown_verified:
            raise RuntimeError("Experiment 019 owned server shutdown differs")
        seal = seal_response_tree(OUTPUT)
        atomic_write(OUTPUT / "RESPONSE_SEAL.json", canonical_json_bytes(seal))
        receipt.update(
            {
                "status": "completed_and_response_sealed",
                "completed_at_utc": utc_now(),
                "response_seal_sha256": sha256_file(OUTPUT / "RESPONSE_SEAL.json"),
                "response_aggregate_sha256": seal["aggregate_sha256"],
                "server_shutdown_verified": True,
            }
        )
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        grades = []
        for row, condition, branch_root, candidate_id in grade_rows:
            fixture = load_fixture(EXPERIMENT / "fresh_bank", row["fixture_id"], include_evaluator=True)
            candidate = _candidate_from_custody(branch_root, candidate_id)
            grades.append(
                {
                    **row,
                    "condition": condition,
                    "candidate_id": candidate_id,
                    "hidden": hidden_grade(fixture, candidate),
                }
            )
        atomic_write(
            OUTPUT / "POSTSEAL_HIDDEN_GRADING.json",
            canonical_json_bytes(
                {
                    "schema_version": "experiment-019-postseal-hidden-grading-v1",
                    "response_seal_sha256": receipt["response_seal_sha256"],
                    "evaluator_opened_after_seal": True,
                    "rows": grades,
                }
            ),
        )
        shutil.copytree(OUTPUT, EVIDENCE)
    except Exception as exc:
        # A failure can occur after the exact endpoint response was custodied
        # but before the enclosing cell summary updates aggregate counters.
        # Count immutable call artifacts so the stop receipt reflects reality.
        observed_prepared = len(list(OUTPUT.rglob("*-endpoint-request.json")))
        observed_completed = len(list(OUTPUT.rglob("*-endpoint-response.json")))
        receipt.update(
            {
                "status": "infrastructure_or_integrity_stopped",
                "stopped_at_utc": utc_now(),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "prepared_invocations": observed_prepared,
                "http_completion_calls": observed_completed,
                "server_shutdown_verified": server.shutdown_verified if "server" in locals() else False,
            }
        )
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        raise
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
