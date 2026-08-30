from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, utc_now
from working_set_exp.large_world_event_v2 import (
    CASE_IDS, CALL_LIMIT, CONDITIONS, EventWorldFixture, hidden_grade, load_fixture, run_branch,
    run_shared_prefix, schedule, validate_authorization, verify_bank, verify_package, verify_source_closure,
)
from working_set_exp.runner import ScriptedActor
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "018_large_world_event_frame_v2"


def _events(request: dict[str, Any]) -> list[dict[str, Any]]:
    return request["active_phase_event_frame"]["events"]


def _accepted(request: dict[str, Any], action_name: str, path: str | None = None) -> list[dict[str, Any]]:
    return [event for event in _events(request)
            if event["action"].get("action") == action_name
            and (path is None or event["action"].get("path") == path)
            and event["result"].get("accepted") is True]


def _read_next(request: dict[str, Any], path: str) -> dict[str, Any] | None:
    rows = _accepted(request, "read", path)
    if not rows:
        return {"action": "read", "path": path, "start_line": 1}
    latest = rows[-1]
    if latest["result"].get("complete"):
        return None
    return {"action": "read", "path": path, "start_line": latest["result"]["next_start_line"]}


def _file_sha(request: dict[str, Any], path: str) -> str:
    rows = _accepted(request, "read", path)
    if not rows:
        raise RuntimeError(f"scripted exact read missing for {path}")
    return rows[-1]["result"]["file_sha256"]


def _policy(request: dict[str, Any]) -> dict[str, Any]:
    fixture_id = request["fixture_id"]
    candidate_id = request["candidate_id"]
    events = _events(request)
    for event in events:
        if (event["action"].get("action") == "check" and event["result"].get("passed") is True
                and event["result"].get("checked_candidate_id") == candidate_id):
            return {"action": "submit", "expected_candidate_id": candidate_id}
    required = [f"ledgers/required_{index:02d}.py" for index in range(4)]
    for path in required:
        action = _read_next(request, path)
        if action:
            return action
    if fixture_id == CASE_IDS[0]:
        for path in ("policy/current.py", "api/primary.py", "api/secondary.py"):
            action = _read_next(request, path)
            if action:
                return action
        if not _accepted(request, "patch", "api/primary.py"):
            return {"action": "patch", "path": "api/primary.py", "old": "    return value.strip().casefold()",
                    "new": '    return "ember-" + value.strip().casefold()', "expected_candidate_id": candidate_id,
                    "expected_file_sha256": _file_sha(request, "api/primary.py")}
        if not _accepted(request, "patch", "policy/current.py"):
            return {"action": "patch", "path": "policy/current.py", "old": 'PREFIX = "ember-"',
                    "new": 'PREFIX = "quartz-"', "expected_candidate_id": candidate_id,
                    "expected_file_sha256": _file_sha(request, "policy/current.py")}
        policy_patch_sequence = _accepted(request, "patch", "policy/current.py")[-1]["sequence"]
        policy_reads_after = [event for event in _accepted(request, "read", "policy/current.py")
                              if event["sequence"] > policy_patch_sequence]
        if not policy_reads_after:
            return {"action": "read", "path": "policy/current.py", "start_line": 1}
        if not _accepted(request, "patch", "api/secondary.py"):
            return {"action": "patch", "path": "api/secondary.py", "old": "    return value.strip().upper()",
                    "new": '    return "quartz-" + value.strip().upper()', "expected_candidate_id": candidate_id,
                    "expected_file_sha256": _file_sha(request, "api/secondary.py")}
    else:
        if not _accepted(request, "reopen_observation"):
            return {"action": "reopen_observation", "handle": "OBS-0002"}
        for path in ("codec/label.py", "codec/footer.py"):
            action = _read_next(request, path)
            if action:
                return action
        if not _accepted(request, "patch", "codec/label.py"):
            return {"action": "patch", "path": "codec/label.py", "old": "    return value.strip().upper()",
                    "new": '    return "HARBOR-K9::" + value.strip().upper()', "expected_candidate_id": candidate_id,
                    "expected_file_sha256": _file_sha(request, "codec/label.py")}
        if not _accepted(request, "patch", "codec/footer.py"):
            return {"action": "patch", "path": "codec/footer.py", "old": "    return value.strip().casefold()",
                    "new": '    return "HARBOR-K9::" + value.strip().casefold()', "expected_candidate_id": candidate_id,
                    "expected_file_sha256": _file_sha(request, "codec/footer.py")}
    return {"action": "check", "check_id": "public", "expected_candidate_id": candidate_id}


def _candidate_from_branch(fixture: EventWorldFixture, branch: Path, candidate_id: str):
    matches = [path for path in branch.rglob(candidate_id[:32]) if path.is_dir() and path.parent.name == "snap"]
    if not matches:
        if fixture.initial.candidate_id == candidate_id:
            return fixture.initial
        raise RuntimeError("scripted terminal candidate absent")
    from working_set_exp.candidate import Candidate
    return Candidate.create({path.relative_to(matches[-1]).as_posix(): path.read_bytes()
                             for path in matches[-1].rglob("*") if path.is_file()})


def main() -> None:
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    bank = verify_bank(EXPERIMENT / "fresh_bank")
    package = verify_package(EXPERIMENT / "execution_package", bank=EXPERIMENT / "fresh_bank", profile=profile)
    closure = verify_source_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
    authorization = validate_authorization(EXPERIMENT)
    rows = []
    with tempfile.TemporaryDirectory(prefix="e18-scripted-") as raw:
        target = Path(raw)
        for cell in schedule()["cells"]:
            fixture = load_fixture(EXPERIMENT / "fresh_bank", cell["fixture_id"])
            shared_actor = ScriptedActor(profile, seed=cell["seed"], policy=_policy, read_mode="maximal_bounded_page")
            prefix = run_shared_prefix(fixture, seed=cell["seed"], actor=shared_actor,
                                       output_dir=target / f"cell-{cell['ordinal']:02d}" / "shared")
            if prefix.disposition != "authentic_25k_boundary_reached":
                raise RuntimeError("scripted branch did not reach authentic boundary")
            for condition in cell["branch_order"]:
                actor = ScriptedActor(profile, seed=cell["seed"], policy=_policy, read_mode="maximal_bounded_page")
                branch = target / f"cell-{cell['ordinal']:02d}" / condition
                summary = run_branch(fixture, prefix, seed=cell["seed"], condition=condition,
                                     actor=actor, output_dir=branch)
                candidate = _candidate_from_branch(fixture, branch, summary["candidate_id"])
                grade = hidden_grade(fixture, candidate)
                if condition == "X25" and (not summary["submitted"] or not grade["passed"]):
                    raise RuntimeError("scripted X25 branch did not complete hidden-correct")
                rows.append({**summary, "hidden_passed": grade["passed"]})
    if len(rows) != 8 or not all(row["hidden_passed"] for row in rows if row["condition"] == "X25"):
        raise RuntimeError("scripted qualification rows differ")
    qualification_path = EXPERIMENT / "OFFLINE_QUALIFICATION.json"
    qualified_at = (
        load_json_strict(qualification_path.read_bytes())["qualified_at_utc"]
        if qualification_path.exists() else utc_now()
    )
    atomic_write(qualification_path, canonical_json_bytes({
        "schema_version": "experiment-018-offline-qualification-v1", "qualified_at_utc": qualified_at,
        "bank": bank, "package": package, "closure": closure, "authorization": authorization,
        "scripted_rows": rows, "authentic_prepressure_fork": True,
        "prepressure_condition_bytes_identical": True, "single_event_plane_no_history_duplication": True,
        "x25_externalization_mechanical_oldest_first": True, "model_execution": False,
    }))


if __name__ == "__main__":
    main()
