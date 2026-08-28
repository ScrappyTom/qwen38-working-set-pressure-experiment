from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from working_set_exp.fixture import load_fixture, load_truth
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, sha256_file
from working_set_exp.reasoning import BRANCH_CALL_LIMIT, CASE_IDS, PREFIX_CALL_LIMIT, progress_pointer, verify_bank
from working_set_exp.reasoning_measured import (
    validate_authorization,
    verify_executable_closure,
    verify_execution_package,
)
from working_set_exp.runner import ScriptedActor, replay_prefix, run_branch, run_prefix, verify_run
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "004_reasoning_transition_diagnostic"


def _policy(fixture_id: str):
    fixture = load_fixture(EXPERIMENT / "fresh_bank", fixture_id)
    truth = load_truth(EXPERIMENT / "fresh_bank", fixture_id)
    required_index = 0
    readiness_read = False
    prefork_patched = False
    prefork_checked = False
    branch_fact = False
    target_read = False
    final_patched = False
    final_checked = False

    def policy(request: dict[str, Any]) -> dict[str, Any]:
        nonlocal required_index, readiness_read, prefork_patched, prefork_checked
        nonlocal branch_fact, target_read, final_patched, final_checked
        if request["stage"] == "setup":
            return {"action": "begin"}
        candidate_id = request["candidate_id"]
        if request["stage"] == "prefix":
            if request["available_probe_ids"]:
                return {"action": "probe", "probe_id": request["available_probe_ids"][0]}
            if required_index < len(fixture.required_full_reads):
                path = fixture.required_full_reads[required_index]
                required_index += 1
                return {"action": "read", "path": path, "start_line": 1, "line_count": 500}
            if not readiness_read:
                readiness_read = True
                return {"action": "read", "path": truth["prefork_patch"]["path"], "start_line": 1, "line_count": 100}
            if not prefork_patched:
                prefork_patched = True
                latest = request["history"][-1]["result"]
                patch = truth["prefork_patch"]
                return {
                    "action": "patch", "path": patch["path"], "old": patch["old"], "new": patch["new"],
                    "expected_candidate_id": candidate_id, "expected_file_sha256": latest["file_sha256"],
                }
            if not prefork_checked:
                prefork_checked = True
                return {"action": "check", "check_id": "prefork", "expected_candidate_id": candidate_id}
            return {"action": "fork_ready", "expected_candidate_id": candidate_id}
        if not branch_fact:
            branch_fact = True
            governing = truth["governing_requirement"]
            if governing["kind"] == "current_source":
                return {"action": "read", "path": governing["path"], "start_line": 1, "line_count": 500}
            handle = next(row["handle"] for row in request["observation_directory"]["entries"] if row["action"] == "probe")
            return {"action": "reopen_observation", "handle": handle}
        if not target_read:
            target_read = True
            return {"action": "read", "path": fixture.final_target, "start_line": 1, "line_count": 100}
        if not final_patched:
            final_patched = True
            latest = request["history"][-1]["result"]
            patch = truth["final_patch"]
            return {
                "action": "patch", "path": patch["path"], "old": patch["old"], "new": patch["new"],
                "expected_candidate_id": candidate_id, "expected_file_sha256": latest["file_sha256"],
            }
        if not final_checked:
            final_checked = True
            return {"action": "check", "check_id": "public", "expected_candidate_id": candidate_id}
        return {"action": "submit", "expected_candidate_id": candidate_id}

    return policy


def main() -> None:
    python = ROOT.parent / "_venvs" / "qwen38_metadata_working_set" / "Scripts" / "python.exe"
    completed = subprocess.run(
        [str(python), "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": "src"}, check=True,
    )
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    checks: dict[str, Any] = {
        "schema_version": "experiment-004-offline-qualification-v1",
        "tests": {"passed": True, "summary": completed.stderr.strip().splitlines()[-1]},
        "bank": verify_bank(EXPERIMENT / "fresh_bank"),
        "package": verify_execution_package(
            EXPERIMENT / "measured_execution_package",
            bank_root=EXPERIMENT / "fresh_bank",
            schedule_path=EXPERIMENT / "MEASURED_SCHEDULE.json",
            runtime_profile_path=EXPERIMENT / "RUNTIME_PROFILE.json",
        ),
        "closure": verify_executable_closure(ROOT, EXPERIMENT / "MEASURED_EXECUTABLE_CLOSURE.json"),
        "authorization": validate_authorization(
            experiment=EXPERIMENT,
            closure_path=EXPERIMENT / "MEASURED_EXECUTABLE_CLOSURE.json",
            package_path=EXPERIMENT / "measured_execution_package",
            authorization_path=EXPERIMENT / "MEASURED_EXECUTION_AUTHORIZATION.json",
        ),
        "scripted": [],
        "model_calls": 0,
    }
    with tempfile.TemporaryDirectory(prefix="e4-scripted-") as raw:
        root = Path(raw)
        for fixture_id in CASE_IDS:
            fixture = load_fixture(EXPERIMENT / "fresh_bank", fixture_id)
            for condition in ("R0", "R1"):
                policy = _policy(fixture_id)
                actor = ScriptedActor(profile, 1, policy)
                prefix = run_prefix(
                    fixture, seed=1, actor=actor,
                    output_dir=root / fixture_id / f"{condition}-prefix",
                    profile=profile, fixed_record_timestamp="2026-08-28T00:00:00Z",
                    prefix_call_limit=PREFIX_CALL_LIMIT,
                    continuation_call_limit=BRANCH_CALL_LIMIT,
                    one_shot_probe=True,
                )
                verify_run(prefix.output_dir)
                replay_prefix(fixture, prefix.output_dir)
                summary = run_branch(
                    fixture, prefix, condition=condition, seed=1, actor=actor,
                    output_dir=root / fixture_id / condition,
                    fixed_record_timestamp="2026-08-28T00:00:00Z",
                    progress_pointer=progress_pointer(EXPERIMENT / "fresh_bank", fixture_id),
                    prefix_call_limit=PREFIX_CALL_LIMIT,
                    branch_call_limit=BRANCH_CALL_LIMIT,
                )
                verify_run(root / fixture_id / condition)
                if summary["disposition"] != "submitted" or not summary["public_check_passed"]:
                    raise RuntimeError("scripted reasoning condition did not complete")
                checks["scripted"].append({"fixture_id": fixture_id, "condition": condition, "summary": summary})
    checks["qualified"] = True
    checks["runtime_profile_sha256"] = sha256_file(EXPERIMENT / "RUNTIME_PROFILE.json")
    atomic_write(EXPERIMENT / "OFFLINE_QUALIFICATION.json", canonical_json_bytes(checks))
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
