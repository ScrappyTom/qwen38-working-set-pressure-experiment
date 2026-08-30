from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .candidate import Candidate
from .custody import ArtifactStore, RecordLog
from .event_frame import event_from_pair, verify_event_sequence
from .hierarchical_p0 import build_p0_root
from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from .phase_receipts import _capture_observation, _receipt, _successor
from .request import observation_directory_v2, render_reasoning_prompt
from .runner import Actor, _execute_call, _save_candidate, _snapshot_prefix, verify_run
from .runtime import T25_TOTAL_CEILING, RuntimeProfile, endpoint_request, guard
from .tools import SessionState, ToolExecutor
from .unified_receipts import (
    READ_MODE,
    build_request as build_unified_request,
    case_definitions,
    hidden_grade,
    load_fixture,
)


EXPERIMENT_ID = "015_event_frame_placement_qualification"
DONOR_EXPERIMENT = "014_unified_active_phase_receipts"
DONOR_COMMIT = "2b0c9147380025e5f1b769c8a589670f96db1d64"
CASE_IDS = ("E14-CLOSURE-MINT", "E14-STALE-SABLE")
SEEDS = (173205, 223607)
CONDITIONS = ("D15-UNIFIED-DUP", "D15-EVENT-FRAME")
PORT = 18118
OUTPUT_ROOT = r"C:\e15-placement"
CALL_LIMIT = 5
MAXIMUM_HTTP_COMPLETION_CALLS = 40
PACKAGE_SCHEMA = "experiment-015-placement-package-v1"


def schedule() -> dict[str, Any]:
    cells = []
    ordinal = 0
    for case_index, fixture_id in enumerate(CASE_IDS):
        for seed_index, seed in enumerate(SEEDS):
            ordinal += 1
            order = list(CONDITIONS if (case_index + seed_index) % 2 == 0 else reversed(CONDITIONS))
            cells.append({"ordinal": ordinal, "fixture_id": fixture_id, "seed": seed, "branch_order": order})
    return {
        "schema_version": "experiment-015-placement-schedule-v1",
        "development_only": True,
        "cases": list(CASE_IDS),
        "seeds": list(SEEDS),
        "conditions": list(CONDITIONS),
        "cells": cells,
        "attempts_per_branch": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
    }


def _observation(
    observations: list[dict[str, Any]],
    reopenable: dict[str, bytes],
    *,
    action: dict[str, Any],
    result: dict[str, Any],
    target: str,
) -> None:
    body = canonical_json_bytes(result)
    handle = f"OBS-{len(observations) + 1:04d}"
    reopenable[handle] = body
    observations.append(
        {
            "handle": handle,
            "sequence": len(observations) + 1,
            "action": action["action"],
            "target": target,
            "candidate_id": result.get("checked_candidate_id", result.get("candidate_id")),
            "size_bytes": len(body),
            "sha256": sha256_bytes(body),
        }
    )


def constructed_world(
    donor_bank: Path, fixture_id: str
) -> tuple[
    Any,
    SessionState,
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, bytes],
    dict[str, bytes],
    dict[str, Any],
]:
    """Construct an exposed, development-only post-reset state with real tool effects."""
    fixture = load_fixture(donor_bank, fixture_id)
    case = next(row for row in case_definitions() if row["fixture_id"] == fixture_id)
    candidate = _successor(case, 1)
    state = SessionState(candidate, stage="continuation", prefork_check_passed=True, fork_ready=True)
    observations: list[dict[str, Any]] = []
    reopenable: dict[str, bytes] = {}
    result_reopenable: dict[str, bytes] = {}
    prefork = {
        "accepted": True,
        "check_id": "prefork",
        "checked_candidate_id": candidate.candidate_id,
        "passed": True,
        "returncode": 0,
        "stdout": "phase A passed\r\n",
        "stdout_size_bytes": 16,
        "stdout_sha256": sha256_bytes(b"phase A passed\r\n"),
        "stderr": "",
        "stderr_size_bytes": 0,
        "stderr_sha256": sha256_bytes(b""),
        "streams_truncated": False,
    }
    _observation(observations, reopenable, action={"action": "check", "check_id": "prefork"}, result=prefork, target="prefork")
    if fixture.phases["A"].probe_id:
        probe = {
            "accepted": True,
            "probe_id": fixture.phases["A"].probe_id,
            "candidate_id": candidate.candidate_id,
            "observation": fixture.phases["A"].probe_body,
        }
        _observation(
            observations,
            reopenable,
            action={"action": "probe", "probe_id": fixture.phases["A"].probe_id},
            result=probe,
            target=fixture.phases["A"].probe_id,
        )
    boundary = {
        "accepted": True,
        "fork_ready": True,
        "candidate_id": candidate.candidate_id,
        "pending_stage": "continuation",
    }
    _observation(observations, reopenable, action={"action": "fork_ready"}, result=boundary, target="phase_boundary")

    executor = ToolExecutor(
        state,
        required_full_reads=fixture.phases["B"].required,
        prefork_checker=fixture.phases["B"].checker,
        public_checker=fixture.phases["B"].checker,
        final_target="__none__",
        probe_id=fixture.phases["B"].probe_id,
        probe_body=fixture.phases["B"].probe_body,
        reopenable=reopenable,
        result_reopenable=result_reopenable,
        read_mode=READ_MODE,
        hierarchical_p0=True,
    )
    patch = case["patches"][1]
    actions: list[dict[str, Any]]
    if fixture_id == CASE_IDS[0]:
        actions = [
            {"action": "reopen_observation", "handle": "OBS-0002"},
            {"action": "read", "path": patch["path"], "start_line": 1},
        ]
    else:
        actions = [
            {"action": "check", "check_id": "public", "expected_candidate_id": state.candidate.candidate_id},
            {"action": "read", "path": patch["path"], "start_line": 1},
        ]
    pairs: list[dict[str, Any]] = []
    for action in actions:
        result = executor.execute(action)
        if not result.get("accepted"):
            raise RuntimeError("constructed development action rejected")
        pairs.append({"response": action, "result": result})
        _capture_observation(action, result, observations=observations, reopenable=reopenable, state=state)
    file_sha = state.candidate.file_sha256(patch["path"])
    patch_action = {
        "action": "patch",
        "path": patch["path"],
        "old": patch["old"],
        "new": patch["new"],
        "expected_candidate_id": state.candidate.candidate_id,
        "expected_file_sha256": file_sha,
    }
    patch_result = executor.execute(patch_action)
    if not patch_result.get("accepted"):
        raise RuntimeError("constructed development patch rejected")
    pairs.append({"response": patch_action, "result": patch_result})
    for path in fixture.phases["B"].required:
        action = {"action": "read", "path": path, "start_line": 1}
        result = executor.execute(action)
        if not result.get("accepted") or not result.get("complete"):
            raise RuntimeError("constructed development read incomplete")
        pairs.append({"response": action, "result": result})
    if len(pairs) != 5:
        raise RuntimeError("constructed development prefix action count differs")
    receipts = []
    for sequence, pair in enumerate(pairs, 1):
        handle = f"RES-{sequence:04d}"
        body = canonical_json_bytes(pair["result"])
        result_reopenable[handle] = body
        receipts.append(_receipt(pair["response"], pair["result"], sequence=sequence, handle=handle))
    binding = {
        "schema_version": "experiment-015-constructed-boundary-v1",
        "development_only": True,
        "fixture_id": fixture_id,
        "completed_phase_ids": ["A"],
        "pending_phase": "B",
        "candidate_id": state.candidate.candidate_id,
        "task_sha256": sha256_bytes(fixture.task.encode()),
        "event_prefix_sha256": sha256_bytes(canonical_json_bytes(pairs)),
        "observation_directory_sha256": sha256_bytes(canonical_json_bytes(observation_directory_v2(observations))),
        "host_semantic_selection": False,
    }
    return fixture, state, pairs, receipts, observations, reopenable, result_reopenable, binding


def build_event_request(
    fixture: Any,
    *,
    candidate: Candidate,
    observations: list[dict[str, Any]],
    boundary_binding: dict[str, Any],
    calls_used: int,
    pairs: list[dict[str, Any]],
    externalized_body_count: int,
) -> bytes:
    receipts = [
        _receipt(pair["response"], pair["result"], sequence=index, handle=f"RES-{index:04d}")
        for index, pair in enumerate(pairs, 1)
    ]
    base = load_json_strict(
        build_unified_request(
            fixture,
            candidate=candidate,
            phase_id="B",
            history=[],
            observations=observations,
            completed=["A"],
            reconstructed=True,
            boundary_binding=boundary_binding,
            calls_used=calls_used,
            stage="continuation",
            condition="T25-UNIFIED",
            receipt_entries=receipts,
            externalized_receipt_count=externalized_body_count,
        )
    )
    for key in ("history", "history_contract", "active_phase_receipt_ledger", "reconstruction_notice"):
        base.pop(key)
    events = [
        event_from_pair(
            pair["response"],
            pair["result"],
            sequence=index,
            handle=f"RES-{index:04d}",
            body_residency="external" if index <= externalized_body_count else "resident",
        )
        for index, pair in enumerate(pairs, 1)
    ]
    verification = verify_event_sequence(events)
    base["schema_version"] = "experiment-015-single-event-frame-request-v1"
    base["active_phase_event_frame"] = {
        "schema_version": "exact-active-phase-event-frame-v1",
        "complete_through_sequence": len(events),
        "externalized_body_through_sequence": externalized_body_count,
        "one_action_result_identity_per_sequence": True,
        "semantic_ranking": False,
        "host_sufficiency_judgment": False,
        "events": events,
    }
    base["event_frame_verification"] = verification
    base["reconstruction_notice"] = (
        "The event sequence is the exact active-phase progress order. Each action/result appears once. "
        "Resident result bodies are inline; external bodies remain exact behind their sequence-bound reopen handle. "
        "Sequence identity records occurrence, not semantic sufficiency or current validity."
    )
    return canonical_json_bytes(base)


def build_legacy_request(
    fixture: Any,
    *,
    candidate: Candidate,
    observations: list[dict[str, Any]],
    boundary_binding: dict[str, Any],
    calls_used: int,
    recent_history: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
    externalized_body_count: int,
) -> bytes:
    return build_unified_request(
        fixture,
        candidate=candidate,
        phase_id="B",
        history=recent_history,
        observations=observations,
        completed=["A"],
        reconstructed=True,
        boundary_binding=boundary_binding,
        calls_used=calls_used,
        stage="continuation",
        condition="T25-UNIFIED",
        receipt_entries=receipts,
        externalized_receipt_count=externalized_body_count,
    )


def initial_request(donor_bank: Path, fixture_id: str, condition: str) -> bytes:
    inputs = branch_inputs(donor_bank, fixture_id)
    if condition == CONDITIONS[0]:
        return build_legacy_request(
            inputs["fixture"], candidate=inputs["state"].candidate, observations=inputs["observations"],
            boundary_binding=inputs["binding"], calls_used=0, recent_history=[], receipts=inputs["receipts"],
            externalized_body_count=5,
        )
    return build_event_request(
        inputs["fixture"], candidate=inputs["state"].candidate, observations=inputs["observations"],
        boundary_binding=inputs["binding"], calls_used=0, pairs=inputs["pairs"], externalized_body_count=5,
    )


def branch_inputs(donor_bank: Path, fixture_id: str) -> dict[str, Any]:
    fixture, state, pairs, receipts, observations, reopenable, result_reopenable, binding = constructed_world(
        donor_bank, fixture_id
    )
    exact_observations = observation_directory_v2(observations)
    if sha256_bytes(canonical_json_bytes(exact_observations)) != binding["observation_directory_sha256"]:
        raise RuntimeError("constructed observation directory binding differs")
    if fixture_id == CASE_IDS[0] and not any(
        row["handle"] == "OBS-0002" for row in exact_observations["entries"]
    ):
        raise RuntimeError("constructed integrity observation absent")
    return {"fixture": fixture, "state": state, "pairs": pairs, "receipts": receipts,
            "observations": observations, "reopenable": reopenable,
            "result_reopenable": result_reopenable, "binding": binding}


def run_branch(
    donor_bank: Path,
    *,
    fixture_id: str,
    seed: int,
    condition: str,
    actor: Actor,
    output_dir: Path,
) -> dict[str, Any]:
    if condition not in CONDITIONS or output_dir.exists():
        raise ValueError("invalid or existing Experiment 015 branch")
    inputs = branch_inputs(donor_bank, fixture_id)
    fixture = inputs["fixture"]
    state = inputs["state"]
    pairs = list(inputs["pairs"])
    receipts = list(inputs["receipts"])
    observations = list(inputs["observations"])
    reopenable = dict(inputs["reopenable"])
    result_reopenable = dict(inputs["result_reopenable"])
    binding = inputs["binding"]
    externalized = len(pairs)
    recent_history: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True)
    store = ArtifactStore(output_dir)
    log = RecordLog(output_dir / "records.jsonl", f"{EXPERIMENT_ID}-{fixture_id}-S{seed}-{condition}")
    executor = ToolExecutor(
        state,
        required_full_reads=fixture.phases["B"].required,
        prefork_checker=fixture.phases["B"].checker,
        public_checker=fixture.phases["B"].checker,
        final_target="__none__",
        probe_id=fixture.phases["B"].probe_id,
        probe_body=fixture.phases["B"].probe_body,
        reopenable=reopenable,
        result_reopenable=result_reopenable,
        read_mode=READ_MODE,
        hierarchical_p0=True,
    )
    log.append(
        "placement_branch_started",
        {"development_only": True, "fixture_id": fixture_id, "seed": seed, "condition": condition,
         "constructed_event_count": externalized, "candidate_id": state.candidate.candidate_id},
        _save_candidate(store, state.candidate, _snapshot_prefix(state.candidate)),
    )
    http = 0
    while http < CALL_LIMIT and not state.submitted:
        if condition == CONDITIONS[0]:
            request = build_legacy_request(
                fixture, candidate=state.candidate, observations=observations, boundary_binding=binding,
                calls_used=http, recent_history=recent_history, receipts=receipts,
                externalized_body_count=externalized,
            )
        else:
            request = build_event_request(
                fixture, candidate=state.candidate, observations=observations, boundary_binding=binding,
                calls_used=http, pairs=pairs, externalized_body_count=externalized,
            )
        action, result, _ = _execute_call(
            actor=actor,
            request=request,
            stage="continuation",
            probe_id=None,
            call_id=f"D15-{fixture_id}-S{seed}-{condition}-P{http + 1:02d}",
            active_total_ceiling=T25_TOTAL_CEILING,
            executor=executor,
            store=store,
            log=log,
            artifact_prefix=f"transcript/{http + 1:03d}",
        )
        http += 1
        pair = {"response": action, "result": result}
        recent_history.append(pair)
        pairs.append(pair)
        handle = f"RES-{len(pairs):04d}"
        body = canonical_json_bytes(result)
        result_reopenable[handle] = body
        receipts.append(_receipt(action, result, sequence=len(pairs), handle=handle))
        _capture_observation(action, result, observations=observations, reopenable=reopenable, state=state)
    disposition = "submitted" if state.submitted else "development_call_budget_exhausted"
    stopped = log.append(
        "placement_branch_stopped",
        {"development_only": True, "fixture_id": fixture_id, "seed": seed, "condition": condition,
         "disposition": disposition, "http_completion_calls": http, "candidate_id": state.candidate.candidate_id,
         "public_check_passed": state.public_check_passed, "submitted": state.submitted,
         "event_count": len(pairs), "externalized_body_count": externalized},
        [],
    )
    summary = {
        "schema_version": "experiment-015-placement-branch-summary-v1",
        "development_only": True,
        "fixture_id": fixture_id,
        "seed": seed,
        "condition": condition,
        "disposition": disposition,
        "http_completion_calls": http,
        "candidate_id": state.candidate.candidate_id,
        "public_check_passed": state.public_check_passed,
        "submitted": state.submitted,
        "event_count": len(pairs),
        "externalized_body_count": externalized,
        "last_record_sha256": stopped["record_sha256"],
    }
    atomic_write(output_dir / "SUMMARY.json", canonical_json_bytes(summary))
    verify_run(output_dir)
    return summary


def construct_package(target: Path, *, donor_bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True)
    rows = []
    for cell in schedule()["cells"]:
        for condition in cell["branch_order"]:
            request = initial_request(donor_bank, cell["fixture_id"], condition)
            endpoint = endpoint_request(
                profile,
                request,
                stage="continuation",
                probe_id=None,
                seed=cell["seed"],
                reasoning_enabled=True,
                read_mode=READ_MODE,
                hierarchical_p0=True,
                result_reopen=True,
            )
            admission = guard(profile, request, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
            if not admission["authorized"]:
                raise RuntimeError("placement qualification initial request is not admitted")
            rendered = render_reasoning_prompt(request, enabled=True)
            path = target / f"cell-{cell['ordinal']:02d}" / condition
            atomic_write(path / "initial-coding-request.json", request)
            atomic_write(path / "initial-endpoint-request.json", endpoint)
            atomic_write(path / "initial-rendered-prompt.txt", rendered)
            rows.append({"ordinal": cell["ordinal"], "fixture_id": cell["fixture_id"], "seed": cell["seed"],
                         "condition": condition, "coding_request_sha256": sha256_bytes(request),
                         "endpoint_request_sha256": sha256_bytes(endpoint),
                         "rendered_prompt_sha256": sha256_bytes(rendered),
                         "expected_call_id": f"D15-{cell['fixture_id']}-S{cell['seed']}-{condition}-P01",
                         "admission": admission})
    files = []
    for path in sorted(target.rglob("*")):
        if path.is_file() and path.name != "PACKAGE_MANIFEST.json":
            data = path.read_bytes()
            files.append({"path": path.relative_to(target).as_posix(), "size_bytes": len(data), "sha256": sha256_bytes(data)})
    manifest = {"schema_version": PACKAGE_SCHEMA, "development_only": True, "donor_experiment": DONOR_EXPERIMENT,
                "donor_commit": DONOR_COMMIT, "schedule_sha256": sha256_bytes(canonical_json_bytes(schedule())),
                "rows": rows, "files": files, "package_id": "E15PKG-" + sha256_bytes(canonical_json_bytes(files))}
    atomic_write(target / "PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_package(target: Path, *, donor_bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    observed = load_json_strict((target / "PACKAGE_MANIFEST.json").read_bytes())
    with tempfile.TemporaryDirectory(prefix="e15-package-") as raw:
        rebuilt = construct_package(Path(raw) / "package", donor_bank=donor_bank, profile=profile)
        if canonical_json_bytes(rebuilt) != canonical_json_bytes(observed):
            raise ValueError("Experiment 015 package differs")
    return {"verified": True, "package_id": observed["package_id"], "file_count": len(observed["files"])}


def expected_authorization(experiment: Path) -> dict[str, Any]:
    package = load_json_strict((experiment / "execution_package" / "PACKAGE_MANIFEST.json").read_bytes())
    closure = load_json_strict((experiment / "EXECUTABLE_CLOSURE.json").read_bytes())
    profile = load_json_strict((experiment / "RUNTIME_PROFILE.json").read_bytes())
    donor_manifest = experiment.parent / DONOR_EXPERIMENT / "fresh_bank" / "BANK_MANIFEST.json"
    return {
        "schema_version": "experiment-015-development-authorization-v1",
        "status": "owner_authorized_sacrificial_live_placement_qualification",
        "owner_statement": "Proceed",
        "development_only": True,
        "donor_commit": DONOR_COMMIT,
        "donor_bank_manifest_sha256": sha256_file(donor_manifest),
        "package_manifest_sha256": sha256_file(experiment / "execution_package" / "PACKAGE_MANIFEST.json"),
        "package_id": package["package_id"],
        "closure_manifest_sha256": sha256_file(experiment / "EXECUTABLE_CLOSURE.json"),
        "closure_aggregate_sha256": closure["aggregate_sha256"],
        "runtime_profile_sha256": sha256_file(experiment / "RUNTIME_PROFILE.json"),
        "actor_sha256": profile["model_sha256"],
        "conditions": list(CONDITIONS),
        "cases": list(CASE_IDS),
        "seeds": list(SEEDS),
        "branches": 8,
        "attempts_per_branch": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
        "maximum_http_completion_calls": MAXIMUM_HTTP_COMPLETION_CALLS,
        "output_root": OUTPUT_ROOT,
        "port": PORT,
        "measured_claim": False,
        "fresh_bank_construction": False,
        "automatic_successor": False,
    }


def validate_authorization(experiment: Path) -> dict[str, Any]:
    observed = load_json_strict((experiment / "DEVELOPMENT_AUTHORIZATION.json").read_bytes())
    if canonical_json_bytes(observed) != canonical_json_bytes(expected_authorization(experiment)):
        raise ValueError("Experiment 015 development authorization differs")
    return {"verified": True, "authorization_sha256": sha256_file(experiment / "DEVELOPMENT_AUTHORIZATION.json")}
