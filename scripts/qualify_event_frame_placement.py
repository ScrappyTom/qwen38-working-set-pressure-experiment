from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from working_set_exp.event_frame_placement import (
    CONDITIONS,
    branch_inputs,
    run_branch,
    schedule,
    validate_authorization,
    verify_package,
)
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.recurrent_pressure import verify_closure
from working_set_exp.runner import ScriptedActor
from working_set_exp.runtime import load_runtime
from working_set_exp.unified_receipts import hidden_grade


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "015_event_frame_placement_qualification"
DONOR_BANK = ROOT / "experiments" / "014_unified_active_phase_receipts" / "fresh_bank"


def _current_check_visible(request: dict[str, Any]) -> bool:
    candidate_id = request["candidate_id"]
    ledger = request.get("active_phase_receipt_ledger")
    if ledger:
        return any(
            row.get("action") == "check"
            and row.get("passed") is True
            and row.get("checked_candidate_id") == candidate_id
            for row in ledger["entries"]
        )
    frame = request.get("active_phase_event_frame")
    return bool(
        frame
        and any(
            event["action"].get("action") == "check"
            and event["result"].get("passed") is True
            and event["result"].get("checked_candidate_id") == candidate_id
            for event in frame["events"]
        )
    )


def _policy(request: dict[str, Any]) -> dict[str, Any]:
    if _current_check_visible(request):
        return {"action": "submit", "expected_candidate_id": request["candidate_id"]}
    return {
        "action": "check",
        "check_id": "public",
        "expected_candidate_id": request["candidate_id"],
    }


def main() -> None:
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    package = verify_package(EXPERIMENT / "execution_package", donor_bank=DONOR_BANK, profile=profile)
    closure = verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
    authorization = validate_authorization(EXPERIMENT)
    rows = []
    with tempfile.TemporaryDirectory(prefix="e15-scripted-") as raw:
        target = Path(raw)
        for cell in schedule()["cells"]:
            for condition in cell["branch_order"]:
                actor = ScriptedActor(
                    profile,
                    seed=cell["seed"],
                    policy=_policy,
                    read_mode="maximal_bounded_page",
                )
                summary = run_branch(
                    DONOR_BANK,
                    fixture_id=cell["fixture_id"],
                    seed=cell["seed"],
                    condition=condition,
                    actor=actor,
                    output_dir=target / f"cell-{cell['ordinal']:02d}" / condition,
                )
                if not summary["submitted"] or not summary["public_check_passed"]:
                    raise RuntimeError("scripted placement branch did not check and submit")
                inputs = branch_inputs(DONOR_BANK, cell["fixture_id"])
                hidden = hidden_grade(inputs["fixture"], inputs["state"].candidate)
                if not hidden["passed"]:
                    raise RuntimeError("constructed placement candidate is not hidden-correct")
                package_request = (
                    EXPERIMENT
                    / "execution_package"
                    / f"cell-{cell['ordinal']:02d}"
                    / condition
                    / "initial-coding-request.json"
                ).read_bytes()
                expected_id = f"D15-{cell['fixture_id']}-S{cell['seed']}-{condition}-P01"
                if actor.requests[expected_id] != package_request:
                    raise RuntimeError("scripted initial request differs from frozen package")
                rows.append({**summary, "hidden": hidden})
    if len(rows) != 8 or any(not row["submitted"] for row in rows):
        raise RuntimeError("Experiment 015 scripted qualification row count differs")
    initial_event_requests = [
        load_json_strict(
            (
                EXPERIMENT
                / "execution_package"
                / f"cell-{cell['ordinal']:02d}"
                / CONDITIONS[1]
                / "initial-coding-request.json"
            ).read_bytes()
        )
        for cell in schedule()["cells"]
    ]
    if any("history" in request or "active_phase_receipt_ledger" in request for request in initial_event_requests):
        raise RuntimeError("single event frame retained a dual progress surface")
    atomic_write(
        EXPERIMENT / "OFFLINE_QUALIFICATION.json",
        canonical_json_bytes(
            {
                "schema_version": "experiment-015-offline-qualification-v1",
                "qualified_at_utc": utc_now(),
                "development_only": True,
                "package": package,
                "closure": closure,
                "authorization": authorization,
                "scripted_branches": rows,
                "scripted_pass_count": sum(row["hidden"]["passed"] for row in rows),
                "single_event_frame_has_no_history_or_parallel_receipt_ledger": True,
                "large_world_execution_authorized": False,
                "model_execution_occurred": False,
                "runtime_profile_sha256": sha256_file(EXPERIMENT / "RUNTIME_PROFILE.json"),
            }
        ),
    )


if __name__ == "__main__":
    main()
