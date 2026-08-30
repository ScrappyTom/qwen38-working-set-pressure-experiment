from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .candidate import Candidate
from .custody import ArtifactStore, RecordLog
from .event_frame_capacity import (
    ACTIVE_PHASE_EVENT_LIMIT,
    accepted_patch_sequence,
    boundary_binding as stress_boundary_binding,
)
from .event_frame_placement import branch_inputs as v1_branch_inputs
from .event_frame_placement import build_event_request as build_v1_request
from .event_frame_v2 import (
    ACTION_PAYLOAD_FIELDS,
    action_payload_bytes,
    event_from_pair_v2,
    resident_pair_v2,
    verify_event_sequence_v2,
    verify_reopened_action_payload,
)
from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from .large_world import _inventory
from .phase_receipts import PhaseSpec, ReceiptFixture, _capture_observation
from .recurrent_pressure import build_closure, verify_closure
from .request import TOOL_CONTRACT, render_reasoning_prompt
from .runner import Actor, _execute_call, _save_candidate, _snapshot_prefix, verify_run
from .runtime import PHYSICAL_CONTEXT, T25_TOTAL_CEILING, RuntimeProfile, endpoint_request, guard
from .tools import SessionState, ToolExecutor
from .unified_receipts import hidden_grade, load_fixture


EXPERIMENT_ID = "017_signal_bearing_event_frame_v2"
DONOR_EXPERIMENT = "014_unified_active_phase_receipts"
DONOR_COMMIT = "2b0c9147380025e5f1b769c8a589670f96db1d64"
DONOR_CASES = ("E14-CLOSURE-MINT", "E14-STALE-SABLE")
SIGNAL_CASE = "E17-HISTORICAL-ACTION-SIGNAL"
CASE_IDS = (*DONOR_CASES, SIGNAL_CASE)
SEEDS = (173205, 223607)
CONDITION = "D17-SIGNAL-EVENT-FRAME-V2"
PORT = 18119
OUTPUT_ROOT = r"C:\e17-event-v2"
CALL_LIMIT = 6
MAXIMUM_HTTP_COMPLETION_CALLS = 36
PACKAGE_SCHEMA = "experiment-017-development-package-v1"


def schedule() -> dict[str, Any]:
    cells = []
    for ordinal, (fixture_id, seed) in enumerate(
        ((fixture_id, seed) for fixture_id in CASE_IDS for seed in SEEDS), 1
    ):
        cells.append({"ordinal": ordinal, "fixture_id": fixture_id, "seed": seed, "condition": CONDITION})
    return {
        "schema_version": "experiment-017-development-schedule-v1",
        "development_only": True,
        "cases": list(CASE_IDS),
        "seeds": list(SEEDS),
        "condition": CONDITION,
        "cells": cells,
        "attempts_per_branch": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
    }


def _payload_maps(pairs: list[dict[str, Any]]) -> tuple[dict[str, bytes], dict[str, bytes]]:
    event_reopenable: dict[str, bytes] = {}
    result_reopenable: dict[str, bytes] = {}
    for sequence, pair in enumerate(pairs, 1):
        payload = action_payload_bytes(pair["response"])
        if any(key in pair["response"] for key in ACTION_PAYLOAD_FIELDS):
            event_reopenable[f"EVT-{sequence:04d}"] = payload
        result_reopenable[f"RES-{sequence:04d}"] = canonical_json_bytes(pair["result"])
    return event_reopenable, result_reopenable


def build_v2_request(
    fixture: ReceiptFixture,
    *,
    candidate: Candidate,
    observations: list[dict[str, Any]],
    boundary_binding: dict[str, Any],
    calls_used: int,
    pairs: list[dict[str, Any]],
    externalized_payload_count: int,
) -> bytes:
    base = load_json_strict(
        build_v1_request(
            fixture,
            candidate=candidate,
            observations=observations,
            boundary_binding=boundary_binding,
            calls_used=calls_used,
            pairs=pairs,
            externalized_body_count=min(externalized_payload_count, len(pairs)),
        )
    )
    base.pop("active_phase_event_frame")
    base.pop("event_frame_verification")
    events = [
        event_from_pair_v2(
            pair["response"],
            pair["result"],
            sequence=sequence,
            event_handle=f"EVT-{sequence:04d}",
            result_handle=f"RES-{sequence:04d}",
            payload_residency="external" if sequence <= externalized_payload_count else "resident",
        )
        for sequence, pair in enumerate(pairs, 1)
    ]
    verification = verify_event_sequence_v2(events)
    actions = list(base["available_actions"])
    if "reopen_event" not in actions:
        actions.append("reopen_event")
    base["available_actions"] = actions
    contract = dict(base["tool_contract"])
    contract["reopen_event"] = TOOL_CONTRACT["reopen_event"]
    base["tool_contract"] = contract
    base["schema_version"] = "experiment-017-signal-bearing-event-frame-request-v2"
    base["active_phase_event_frame"] = {
        "schema_version": "exact-active-phase-event-frame-v2",
        "complete_through_sequence": len(events),
        "externalized_payload_through_sequence": externalized_payload_count,
        "one_action_result_identity_per_sequence": True,
        "semantic_ranking": False,
        "host_sufficiency_judgment": False,
        "resident_signal_contract": {
            "action": "type, readable target, and exact predecessor bindings remain resident",
            "result": "acceptance, ranges/status, and exact successor/check bindings remain resident",
            "handles": "addresses for exact payload access; handles are not semantic evidence",
        },
        "events": events,
    }
    base["event_frame_verification"] = verification
    base["reconstruction_notice"] = (
        "The single event sequence is exact active-phase progress. Readable action targets, acceptance/status, "
        "ranges, and candidate/file/check bindings remain resident and are the progress signal. Handles only "
        "address exact externally custodied payloads. Use reopen_event for listed old/new action fields and "
        "reopen_result for listed exact result bodies when those exact payloads are needed. Sequence records "
        "occurrence, not semantic sufficiency or current validity."
    )
    return canonical_json_bytes(base)


def _signal_fixture() -> tuple[ReceiptFixture, SessionState, list[dict[str, Any]], dict[str, Any]]:
    old_source = "legacy_marker=ARCHIVE-Z7\n"
    new_source = "legacy_marker=retired\n"
    initial = Candidate.create(
        {
            "archive/source.dat": old_source.encode("utf-8"),
            "report.py": b'def restored_marker() -> str:\n    return "missing"\n',
        }
    )
    state = SessionState(initial, stage="continuation")
    executor = ToolExecutor(
        state,
        required_full_reads=(),
        prefork_checker=b"",
        public_checker=b"",
        final_target="__none__",
        probe_id=None,
        probe_body=None,
        read_mode="maximal_bounded_page",
        hierarchical_p0=True,
    )
    action = {
        "action": "patch",
        "path": "archive/source.dat",
        "old": old_source,
        "new": new_source,
        "expected_candidate_id": initial.candidate_id,
        "expected_file_sha256": initial.file_sha256("archive/source.dat"),
    }
    result = executor.execute(action)
    if not result.get("accepted"):
        raise RuntimeError("historical signal patch was rejected")
    phase_a = PhaseSpec("A", "Phase A is mechanically complete.", (), "__none__", b"", None, None)
    phase_b_text = (
        "Phase B: the accepted historical patch event removed an exact marker from `archive/source.dat`. "
        "Use the resident event signal to locate and reopen its exact old/new action payload. Read exact current "
        "`report.py`, then repair `restored_marker()` so it returns the removed marker value exactly. Run check "
        "`public` on the current candidate and submit."
    )
    checker = b"from report import restored_marker\nassert restored_marker() == 'ARCHIVE-Z7'\nprint('public passed')\n"
    fixture = ReceiptFixture(
        SIGNAL_CASE,
        "historical_action_payload_reacquisition",
        "Perform Phase A and Phase B in order. " + phase_b_text,
        initial,
        {
            "A": phase_a,
            "B": PhaseSpec("B", phase_b_text, (), "report.py", checker, None, None),
        },
        checker,
    )
    pair = {"response": action, "result": result}
    binding = {
        "schema_version": "experiment-017-constructed-boundary-v1",
        "fixture_id": SIGNAL_CASE,
        "completed_phase_ids": ["A"],
        "pending_phase": "B",
        "candidate_id": state.candidate.candidate_id,
        "task_sha256": sha256_bytes(fixture.task.encode("utf-8")),
        "event_prefix_sha256": sha256_bytes(canonical_json_bytes([pair])),
        "host_semantic_selection": False,
    }
    return fixture, state, [pair], binding


def branch_inputs(donor_bank: Path, fixture_id: str) -> dict[str, Any]:
    if fixture_id == SIGNAL_CASE:
        fixture, state, pairs, binding = _signal_fixture()
        observations: list[dict[str, Any]] = []
        reopenable: dict[str, bytes] = {}
    else:
        values = v1_branch_inputs(donor_bank, fixture_id)
        fixture, state, pairs, binding = values["fixture"], values["state"], values["pairs"], values["binding"]
        observations, reopenable = values["observations"], values["reopenable"]
    event_reopenable, result_reopenable = _payload_maps(pairs)
    return {
        "fixture": fixture,
        "state": state,
        "pairs": list(pairs),
        "binding": binding,
        "observations": list(observations),
        "reopenable": dict(reopenable),
        "event_reopenable": event_reopenable,
        "result_reopenable": result_reopenable,
    }


def initial_request(donor_bank: Path, fixture_id: str) -> bytes:
    values = branch_inputs(donor_bank, fixture_id)
    return build_v2_request(
        values["fixture"],
        candidate=values["state"].candidate,
        observations=values["observations"],
        boundary_binding=values["binding"],
        calls_used=0,
        pairs=values["pairs"],
        externalized_payload_count=len(values["pairs"]),
    )


def run_branch(
    donor_bank: Path,
    *,
    fixture_id: str,
    seed: int,
    actor: Actor,
    output_dir: Path,
) -> dict[str, Any]:
    if fixture_id not in CASE_IDS or output_dir.exists():
        raise ValueError("invalid or existing Experiment 017 branch")
    values = branch_inputs(donor_bank, fixture_id)
    fixture = values["fixture"]
    state = values["state"]
    pairs = values["pairs"]
    observations = values["observations"]
    reopenable = values["reopenable"]
    event_reopenable = values["event_reopenable"]
    result_reopenable = values["result_reopenable"]
    binding = values["binding"]
    externalized = len(pairs)
    output_dir.mkdir(parents=True)
    store = ArtifactStore(output_dir)
    log = RecordLog(output_dir / "records.jsonl", f"{EXPERIMENT_ID}-{fixture_id}-S{seed}")
    executor = ToolExecutor(
        state,
        required_full_reads=(),
        prefork_checker=fixture.phases["B"].checker,
        public_checker=fixture.phases["B"].checker,
        final_target="__none__",
        probe_id=None,
        probe_body=None,
        reopenable=reopenable,
        result_reopenable=result_reopenable,
        event_reopenable=event_reopenable,
        read_mode="maximal_bounded_page",
        hierarchical_p0=True,
    )
    log.append(
        "event_v2_branch_started",
        {
            "development_only": True,
            "fixture_id": fixture_id,
            "seed": seed,
            "constructed_event_count": externalized,
            "candidate_id": state.candidate.candidate_id,
            "resident_signal_present": True,
        },
        _save_candidate(store, state.candidate, _snapshot_prefix(state.candidate)),
    )
    http = 0
    while http < CALL_LIMIT and not state.submitted:
        request = build_v2_request(
            fixture,
            candidate=state.candidate,
            observations=observations,
            boundary_binding=binding,
            calls_used=http,
            pairs=pairs,
            externalized_payload_count=externalized,
        )
        action, result, _ = _execute_call(
            actor=actor,
            request=request,
            stage="continuation",
            probe_id=None,
            call_id=f"D17-{fixture_id}-S{seed}-P{http + 1:02d}",
            active_total_ceiling=T25_TOTAL_CEILING,
            executor=executor,
            store=store,
            log=log,
            artifact_prefix=f"transcript/{http + 1:03d}",
        )
        http += 1
        pair = {"response": action, "result": result}
        pairs.append(pair)
        sequence = len(pairs)
        if any(key in action for key in ACTION_PAYLOAD_FIELDS):
            event_reopenable[f"EVT-{sequence:04d}"] = action_payload_bytes(action)
        result_reopenable[f"RES-{sequence:04d}"] = canonical_json_bytes(result)
        _capture_observation(action, result, observations=observations, reopenable=reopenable, state=state)
    disposition = "submitted" if state.submitted else "development_call_budget_exhausted"
    stopped = log.append(
        "event_v2_branch_stopped",
        {
            "development_only": True,
            "fixture_id": fixture_id,
            "seed": seed,
            "disposition": disposition,
            "http_completion_calls": http,
            "candidate_id": state.candidate.candidate_id,
            "public_check_passed": state.public_check_passed,
            "submitted": state.submitted,
            "event_count": len(pairs),
            "externalized_payload_count": externalized,
        },
        [],
    )
    summary = {
        "schema_version": "experiment-017-branch-summary-v1",
        "development_only": True,
        "fixture_id": fixture_id,
        "seed": seed,
        "condition": CONDITION,
        "disposition": disposition,
        "http_completion_calls": http,
        "candidate_id": state.candidate.candidate_id,
        "public_check_passed": state.public_check_passed,
        "submitted": state.submitted,
        "event_count": len(pairs),
        "externalized_payload_count": externalized,
        "last_record_sha256": stopped["record_sha256"],
    }
    atomic_write(output_dir / "SUMMARY.json", canonical_json_bytes(summary))
    verify_run(output_dir)
    return summary


def capacity_proof(profile: RuntimeProfile) -> dict[str, Any]:
    cases = []
    for kind in ("maximum_schema_ascii_patch", "reasoning_budget_compatible_control_escape_patch"):
        fixture, candidate, pairs = accepted_patch_sequence(kind)
        binding = stress_boundary_binding(fixture, candidate, pairs)
        external = build_v2_request(
            fixture,
            candidate=candidate,
            observations=[],
            boundary_binding=binding,
            calls_used=16,
            pairs=pairs,
            externalized_payload_count=16,
        )
        one_resident = build_v2_request(
            fixture,
            candidate=candidate,
            observations=[],
            boundary_binding=binding,
            calls_used=16,
            pairs=pairs,
            externalized_payload_count=15,
        )
        resident = build_v2_request(
            fixture,
            candidate=candidate,
            observations=[],
            boundary_binding=binding,
            calls_used=16,
            pairs=pairs,
            externalized_payload_count=0,
        )
        event_reopenable, _ = _payload_maps(pairs)
        executor = ToolExecutor(
            SessionState(candidate, stage="continuation"),
            required_full_reads=(),
            prefork_checker=b"",
            public_checker=b"",
            final_target="__none__",
            probe_id=None,
            probe_body=None,
            event_reopenable=event_reopenable,
        )
        reopened = executor.execute({"action": "reopen_event", "handle": "EVT-0001"})
        first_event = load_json_strict(external)["active_phase_event_frame"]["events"][0]
        reopen_verification = verify_reopened_action_payload(first_event, reopened)
        cases.append(
            {
                "kind": kind,
                "event_count": len(pairs),
                "fully_externalized": {
                    "request_bytes": len(external),
                    "x25": guard(profile, external, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True),
                },
                "one_newly_resident_maximum_event": {
                    "request_bytes": len(one_resident),
                    "x25": guard(profile, one_resident, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True),
                },
                "fully_resident": {
                    "request_bytes": len(resident),
                    "r50": guard(profile, resident, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True),
                },
                "prepressure_r50_x25_byte_identity": resident == build_v2_request(
                    fixture,
                    candidate=candidate,
                    observations=[],
                    boundary_binding=binding,
                    calls_used=16,
                    pairs=pairs,
                    externalized_payload_count=0,
                ),
                "reopen_event": reopen_verification,
                "first_external_event": first_event,
            }
        )
    if any(not row["fully_externalized"]["x25"]["authorized"] for row in cases):
        raise RuntimeError("event-frame V2 fully externalized X25 proof failed")
    if any(not row["one_newly_resident_maximum_event"]["x25"]["authorized"] for row in cases):
        raise RuntimeError("event-frame V2 one-resident-event X25 proof failed")
    return {
        "schema_version": "experiment-017-event-frame-v2-capacity-proof-v1",
        "event_limit": ACTIVE_PHASE_EVENT_LIMIT,
        "cases": cases,
        "conclusion": {
            "v2_fully_externalized_x25": True,
            "v2_one_newly_resident_maximum_event_x25": True,
            "prepressure_common_renderer": True,
            "opaque_handle_is_not_the_progress_signal": True,
            "large_world_execution_authorized": False,
        },
    }


def construct_package(target: Path, *, donor_bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True)
    rows = []
    for cell in schedule()["cells"]:
        request = initial_request(donor_bank, cell["fixture_id"])
        endpoint = endpoint_request(
            profile,
            request,
            stage="continuation",
            probe_id=None,
            seed=cell["seed"],
            reasoning_enabled=True,
            read_mode="maximal_bounded_page",
            hierarchical_p0=True,
            result_reopen=True,
            event_reopen=True,
        )
        admission = guard(profile, request, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
        if not admission["authorized"]:
            raise RuntimeError("Experiment 017 initial request is not admitted")
        rendered = render_reasoning_prompt(request, enabled=True)
        path = target / f"cell-{cell['ordinal']:02d}"
        atomic_write(path / "initial-coding-request.json", request)
        atomic_write(path / "initial-endpoint-request.json", endpoint)
        atomic_write(path / "initial-rendered-prompt.txt", rendered)
        rows.append(
            {
                **cell,
                "coding_request_sha256": sha256_bytes(request),
                "endpoint_request_sha256": sha256_bytes(endpoint),
                "rendered_prompt_sha256": sha256_bytes(rendered),
                "expected_call_id": f"D17-{cell['fixture_id']}-S{cell['seed']}-P01",
                "admission": admission,
            }
        )
    files = _inventory(target, {"PACKAGE_MANIFEST.json"})
    manifest = {
        "schema_version": PACKAGE_SCHEMA,
        "development_only": True,
        "donor_experiment": DONOR_EXPERIMENT,
        "donor_commit": DONOR_COMMIT,
        "schedule_sha256": sha256_bytes(canonical_json_bytes(schedule())),
        "rows": rows,
        "files": files,
        "package_id": "E17PKG-" + sha256_bytes(canonical_json_bytes(files)),
    }
    atomic_write(target / "PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_package(target: Path, *, donor_bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    observed = load_json_strict((target / "PACKAGE_MANIFEST.json").read_bytes())
    if observed["files"] != _inventory(target, {"PACKAGE_MANIFEST.json"}):
        raise ValueError("Experiment 017 package inventory differs")
    with tempfile.TemporaryDirectory(prefix="e17-package-") as raw:
        rebuilt = construct_package(Path(raw) / "package", donor_bank=donor_bank, profile=profile)
        if canonical_json_bytes(rebuilt) != canonical_json_bytes(observed):
            raise ValueError("Experiment 017 package reconstruction differs")
    return {"verified": True, "package_id": observed["package_id"], "file_count": len(observed["files"])}


def expected_authorization(experiment: Path) -> dict[str, Any]:
    package = load_json_strict((experiment / "execution_package" / "PACKAGE_MANIFEST.json").read_bytes())
    closure = load_json_strict((experiment / "EXECUTABLE_CLOSURE.json").read_bytes())
    profile = load_json_strict((experiment / "RUNTIME_PROFILE.json").read_bytes())
    return {
        "schema_version": "experiment-017-development-authorization-v1",
        "status": "owner_authorized_signal_bearing_event_v2_qualification",
        "owner_statement": "Proceed; handles are addresses and resident event fields must carry mechanical signal.",
        "development_only": True,
        "package_manifest_sha256": sha256_file(experiment / "execution_package" / "PACKAGE_MANIFEST.json"),
        "package_id": package["package_id"],
        "closure_manifest_sha256": sha256_file(experiment / "EXECUTABLE_CLOSURE.json"),
        "closure_aggregate_sha256": closure["aggregate_sha256"],
        "runtime_profile_sha256": sha256_file(experiment / "RUNTIME_PROFILE.json"),
        "actor_sha256": profile["model_sha256"],
        "cases": list(CASE_IDS),
        "seeds": list(SEEDS),
        "branches": len(schedule()["cells"]),
        "attempts_per_branch": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
        "maximum_http_completion_calls": MAXIMUM_HTTP_COMPLETION_CALLS,
        "output_root": OUTPUT_ROOT,
        "port": PORT,
        "measured_claim": False,
        "fresh_bank_construction": False,
        "large_world_execution": False,
        "automatic_successor": False,
    }


def validate_authorization(experiment: Path) -> dict[str, Any]:
    observed = load_json_strict((experiment / "DEVELOPMENT_AUTHORIZATION.json").read_bytes())
    if canonical_json_bytes(observed) != canonical_json_bytes(expected_authorization(experiment)):
        raise ValueError("Experiment 017 development authorization differs")
    return {"verified": True, "authorization_sha256": sha256_file(experiment / "DEVELOPMENT_AUTHORIZATION.json")}


def closure(root: Path) -> dict[str, Any]:
    return build_closure(root, entrypoint="scripts/run_event_frame_v2_qualification.py")


def verify_source_closure(root: Path, path: Path) -> dict[str, Any]:
    return verify_closure(root, path)
