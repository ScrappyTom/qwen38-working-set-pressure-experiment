from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from working_set_exp.event_frame_v2_qualification import (
    DONOR_CASES,
    SIGNAL_CASE,
    branch_inputs,
    capacity_proof,
    run_branch,
    schedule,
    validate_authorization,
    verify_package,
    verify_source_closure,
)
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.runner import ScriptedActor
from working_set_exp.runtime import load_runtime
from working_set_exp.unified_receipts import hidden_grade


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "017_signal_bearing_event_frame_v2"
DONOR_BANK = ROOT / "experiments" / "014_unified_active_phase_receipts" / "fresh_bank"


def _events(request: dict[str, Any]) -> list[dict[str, Any]]:
    return request["active_phase_event_frame"]["events"]


def _policy(request: dict[str, Any]) -> dict[str, Any]:
    events = _events(request)
    candidate_id = request["candidate_id"]
    if any(
        event["action"].get("action") == "check"
        and event["result"].get("passed") is True
        and event["result"].get("checked_candidate_id") == candidate_id
        for event in events
    ):
        return {"action": "submit", "expected_candidate_id": candidate_id}
    if request["fixture_id"] != SIGNAL_CASE:
        return {"action": "check", "check_id": "public", "expected_candidate_id": candidate_id}
    report_read = next(
        (event for event in events if event["action"].get("action") == "read" and event["action"].get("path") == "report.py"),
        None,
    )
    reopened = next((event for event in events if event["action"].get("action") == "reopen_event"), None)
    repaired = next(
        (event for event in events if event["action"].get("action") == "patch" and event["action"].get("path") == "report.py"),
        None,
    )
    if report_read is None:
        return {"action": "read", "path": "report.py", "start_line": 1}
    if reopened is None:
        return {"action": "reopen_event", "handle": "EVT-0001"}
    if repaired is None:
        read_fields = report_read["result_body"]["fields"]
        reopened_fields = reopened["result_body"]["fields"]
        old_payload = reopened_fields["action_payload"]["old"]
        marker = old_payload.split("=", 1)[1].strip()
        return {
            "action": "patch",
            "path": "report.py",
            "old": read_fields["content"],
            "new": f'def restored_marker() -> str:\n    return "{marker}"\n',
            "expected_candidate_id": candidate_id,
            "expected_file_sha256": report_read["result"]["file_sha256"],
        }
    return {"action": "check", "check_id": "public", "expected_candidate_id": candidate_id}


def main() -> None:
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    package = verify_package(EXPERIMENT / "execution_package", donor_bank=DONOR_BANK, profile=profile)
    source_closure = verify_source_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
    authorization = validate_authorization(EXPERIMENT)
    observed_capacity = load_json_strict((EXPERIMENT / "CAPACITY_PROOF.json").read_bytes())
    if canonical_json_bytes(observed_capacity) != canonical_json_bytes(capacity_proof(profile)):
        raise RuntimeError("Experiment 017 capacity proof differs")
    rows = []
    with tempfile.TemporaryDirectory(prefix="e17-scripted-") as raw:
        target = Path(raw)
        for cell in schedule()["cells"]:
            actor = ScriptedActor(profile, seed=cell["seed"], policy=_policy, read_mode="maximal_bounded_page")
            summary = run_branch(
                DONOR_BANK,
                fixture_id=cell["fixture_id"],
                seed=cell["seed"],
                actor=actor,
                output_dir=target / f"cell-{cell['ordinal']:02d}",
            )
            values = branch_inputs(DONOR_BANK, cell["fixture_id"])
            candidate = values["state"].candidate
            if summary["candidate_id"] != candidate.candidate_id:
                snapshots = [path for path in (target / f"cell-{cell['ordinal']:02d}").rglob(summary["candidate_id"][:32]) if path.is_dir()]
                if not snapshots:
                    raise RuntimeError("scripted successor snapshot absent")
                candidate = candidate.create(
                    {path.relative_to(snapshots[-1]).as_posix(): path.read_bytes() for path in snapshots[-1].rglob("*") if path.is_file()}
                )
            hidden = hidden_grade(values["fixture"], candidate)
            if not summary["submitted"] or not summary["public_check_passed"] or not hidden["passed"]:
                raise RuntimeError("scripted V2 branch did not check, submit, and pass")
            expected = f"D17-{cell['fixture_id']}-S{cell['seed']}-P01"
            frozen = (EXPERIMENT / "execution_package" / f"cell-{cell['ordinal']:02d}" / "initial-coding-request.json").read_bytes()
            if actor.requests[expected] != frozen:
                raise RuntimeError("scripted V2 initial request differs")
            rows.append({**summary, "hidden": hidden})
    if len(rows) != 6 or any(not row["submitted"] for row in rows):
        raise RuntimeError("Experiment 017 scripted branch count differs")
    atomic_write(
        EXPERIMENT / "OFFLINE_QUALIFICATION.json",
        canonical_json_bytes(
            {
                "schema_version": "experiment-017-offline-qualification-v1",
                "qualified_at_utc": utc_now(),
                "development_only": True,
                "package": package,
                "closure": source_closure,
                "authorization": authorization,
                "capacity_proof_sha256": sha256_file(EXPERIMENT / "CAPACITY_PROOF.json"),
                "scripted_branches": rows,
                "scripted_pass_count": len(rows),
                "signal_case_reopen_event_path_exercised": True,
                "handles_are_addresses_not_progress_signal": True,
                "large_world_execution_authorized": False,
                "model_execution_occurred": False,
            }
        ),
    )


if __name__ == "__main__":
    main()
