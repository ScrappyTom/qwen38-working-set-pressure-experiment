from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .candidate import Candidate
from .custody import ArtifactStore, RecordLog
from .event_frame_v2 import ACTION_PAYLOAD_FIELDS, action_payload_bytes
from .event_frame_v3 import capture_original_result_payload, event_from_pair_v3, verify_event_sequence_v3
from .hierarchical_p0 import build_p0_root
from .isolation import run_checker
from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from .large_world import _inventory
from .recurrent_pressure import build_closure, verify_closure
from .request import TOOL_CONTRACT, observation_directory_v2, render_reasoning_prompt
from .runner import Actor, _execute_call, _save_candidate, _snapshot_prefix, verify_run
from .runtime import PHYSICAL_CONTEXT, REASONING_BUDGET, T25_TOTAL_CEILING, RuntimeProfile, endpoint_request, guard
from .tools import SessionState, ToolExecutor


EXPERIMENT_ID = "019_owner_controlled_ecological_pilot"
CASE_IDS = ("E19-SOURCE-REOPEN", "E19-OBS-SUMMARY-GRAPH")
SEEDS = (173205, 223607)
CONDITIONS = ("R50", "X25")
CALL_LIMIT = 24
READ_MODE = "maximal_bounded_page"
PORT = 18121
OUTPUT_ROOT = r"C:\e19-ecological-v1"
MAXIMUM_HTTP_COMPLETION_CALLS = 220
PACKAGE_SCHEMA = "experiment-019-execution-package-v1"
SUBSET_INIT = b'"""Experiment 019 bounded subset of the owner-controlled package."""\n'


def admitted_donor_candidate(bank: Path) -> Candidate:
    donor = bank / "donor_snapshot"
    files = {
        path.relative_to(donor).as_posix(): path.read_bytes()
        for path in donor.rglob("*")
        if path.is_file()
    }
    files["src/addressable_information_layer/__init__.py"] = SUBSET_INIT
    return Candidate.create(files)


@dataclass(frozen=True)
class EcologicalFixture:
    fixture_id: str
    family: str
    task: str
    initial: Candidate
    public_checker: bytes
    hidden_checker: bytes
    observations: tuple[dict[str, Any], ...]
    observation_bodies: tuple[tuple[str, bytes], ...]
    provenance: dict[str, Any]


@dataclass
class PrefixOutcome:
    state: SessionState
    pairs: list[dict[str, Any]]
    result_reopenable: dict[str, bytes]
    event_reopenable: dict[str, bytes]
    calls: int
    prepared: int
    output_dir: Path
    disposition: str
    first_boundary: dict[str, Any] | None


def schedule() -> dict[str, Any]:
    cells = []
    ordinal = 0
    for case_index, fixture_id in enumerate(CASE_IDS):
        for seed_index, seed in enumerate(SEEDS):
            ordinal += 1
            order = list(CONDITIONS if (case_index + seed_index) % 2 == 0 else reversed(CONDITIONS))
            cells.append({"ordinal": ordinal, "fixture_id": fixture_id, "seed": seed, "branch_order": order})
    return {
        "schema_version": "experiment-019-schedule-v1",
        "cases": list(CASE_IDS),
        "seeds": list(SEEDS),
        "conditions": list(CONDITIONS),
        "cells": cells,
        "attempts_per_branch": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
        "reasoning_budget_tokens": REASONING_BUDGET,
    }


def verify_bank(target: Path) -> dict[str, Any]:
    manifest_path = target / "BANK_MANIFEST.json"
    observed = load_json_strict(manifest_path.read_bytes())
    files = _inventory(target, {"BANK_MANIFEST.json"})
    if observed["files"] != files:
        raise ValueError("Experiment 019 bank inventory differs")
    if observed["case_ids"] != list(CASE_IDS) or observed["evaluator_bytes_model_visible"]:
        raise ValueError("Experiment 019 bank contract differs")
    for row in observed["donor_files"]:
        path = target / row["bank_path"]
        if len(path.read_bytes()) != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise ValueError("Experiment 019 donor source custody differs")
    return {"verified": True, "bank_id": observed["bank_id"], "file_count": len(files)}


def load_fixture(bank: Path, fixture_id: str, *, include_evaluator: bool) -> EcologicalFixture:
    if fixture_id not in CASE_IDS:
        raise ValueError("unknown Experiment 019 fixture")
    visible = bank / "model_visible" / fixture_id
    execution = bank / "execution_only" / fixture_id
    row = load_json_strict((execution / "FIXTURE.json").read_bytes())
    files = {
        item["path"]: (visible / "candidate" / Path(*item["path"].split("/"))).read_bytes()
        for item in row["candidate_files"]
    }
    bodies = tuple(
        (item["handle"], (execution / "observations" / f"{item['handle']}.json").read_bytes())
        for item in row["observations"]
    )
    return EcologicalFixture(
        fixture_id=fixture_id,
        family=row["family"],
        task=(visible / "TASK.txt").read_text(encoding="utf-8"),
        initial=Candidate.create(files),
        public_checker=(execution / "public.py").read_bytes(),
        hidden_checker=(bank / "evaluator_only" / fixture_id / "hidden.py").read_bytes()
        if include_evaluator
        else b"",
        observations=tuple(row["observations"]),
        observation_bodies=bodies,
        provenance=dict(row["provenance"]),
    )


def _payload_maps(pairs: list[dict[str, Any]]) -> tuple[dict[str, bytes], dict[str, bytes]]:
    events: dict[str, bytes] = {}
    results: dict[str, bytes] = {}
    for sequence, pair in enumerate(pairs, 1):
        action = pair["response"]
        if any(key in action for key in ACTION_PAYLOAD_FIELDS):
            events[f"EVT-{sequence:04d}"] = action_payload_bytes(action)
        capture_original_result_payload(
            action,
            pair["result"],
            sequence=sequence,
            result_reopenable=results,
        )
    return events, results


def build_request(
    fixture: EcologicalFixture,
    *,
    candidate: Candidate,
    pairs: list[dict[str, Any]],
    externalized_payload_count: int,
    calls_used: int,
    fork_binding: dict[str, Any] | None,
) -> bytes:
    if not 0 <= externalized_payload_count <= len(pairs):
        raise ValueError("externalized count differs")
    actions = [
        "p0_page",
        "tree",
        "search",
        "read",
        "patch",
        "check",
        "reopen_observation",
        "reopen_result",
        "reopen_event",
        "submit",
    ]
    contract = {name: TOOL_CONTRACT[name] for name in actions if name in TOOL_CONTRACT}
    contract["p0_page"] = "task-independent readable directory or file-outline page; exact source is not included"
    contract["read"] = "largest exact current whole-line page that fits the frozen result bound, with non-guessing continuation"
    contract["reopen_result"] = "exactly reopen the canonical event-result payload named by resident signal"
    contract["reopen_event"] = "exactly reopen the canonical patch payload named by resident signal"
    events = [
        event_from_pair_v3(
            pair["response"],
            pair["result"],
            sequence=index,
            payload_residency="external" if index <= externalized_payload_count else "resident",
        )
        for index, pair in enumerate(pairs, 1)
    ]
    verification = verify_event_sequence_v3(events)
    value = {
        "schema_version": "experiment-019-ecological-event-frame-request-v1",
        "fixture_id": fixture.fixture_id,
        "stage": "continuation",
        "task": fixture.task,
        "active_user_authored_step": {"id": "ECOLOGICAL-REPAIR", "text": fixture.task, "host_inference": False},
        "completed_step_ids": [],
        "candidate_id": candidate.candidate_id,
        "current_p0": build_p0_root(candidate),
        "p0_contract": {
            "task_independent": True,
            "semantic_ranking": False,
            "repository_complete": False,
            "root_complete": True,
            "scoped_access": "p0_page",
            "exact_source_required_before_mutation": True,
        },
        "observation_directory": observation_directory_v2(list(fixture.observations)),
        "active_phase_event_frame": {
            "schema_version": "exact-active-phase-event-frame-v3-canonical-payload-identity",
            "complete_through_sequence": len(events),
            "externalized_payload_through_sequence": externalized_payload_count,
            "one_action_result_identity_per_sequence": True,
            "reopen_is_access_not_new_payload": True,
            "semantic_ranking": False,
            "host_sufficiency_judgment": False,
            "resident_signal_contract": {
                "action": "type, readable target, and exact predecessor bindings remain resident",
                "result": "acceptance, ranges/status, and exact successor/check bindings remain resident",
                "canonical_source": "stable exact payload address and provenance; not semantic evidence",
            },
            "events": events,
        },
        "event_frame_verification": verification,
        "latest_transition_binding": fork_binding,
        "resource_state": {
            "calls_used": calls_used,
            "call_limit": CALL_LIMIT,
            "calls_remaining": CALL_LIMIT - calls_used,
            "reasoning_budget_tokens": REASONING_BUDGET,
            "correction_cycle_reserved_by_fixture_design": "check -> patch -> recheck -> submit fits within the prospective ideal path",
        },
        "available_check_ids": ["public"],
        "available_actions": actions,
        "tool_contract": contract,
        "read_paging_mode": READ_MODE,
        "reconstruction_notice": (
            "The ordered events are exact progress. Readable targets, status, ranges, and candidate/file/check bindings are the signal. "
            "A canonical payload address identifies exact custody but is not relevance or sufficiency advice. Reopening creates a new access "
            "event that retains the same canonical source. Sequence records occurrence, not semantic completion."
        ),
    }
    return canonical_json_bytes(value)


def _executor(
    fixture: EcologicalFixture,
    state: SessionState,
    *,
    result_reopenable: dict[str, bytes],
    event_reopenable: dict[str, bytes],
) -> ToolExecutor:
    return ToolExecutor(
        state,
        required_full_reads=(),
        prefork_checker=fixture.public_checker,
        public_checker=fixture.public_checker,
        final_target="__none__",
        probe_id=None,
        probe_body=None,
        reopenable=dict(fixture.observation_bodies),
        result_reopenable=result_reopenable,
        event_reopenable=event_reopenable,
        read_mode=READ_MODE,
        hierarchical_p0=True,
    )


def _record_pair(
    pairs: list[dict[str, Any]],
    action: dict[str, Any],
    result: dict[str, Any],
    event_reopenable: dict[str, bytes],
    result_reopenable: dict[str, bytes],
) -> str:
    pairs.append({"response": action, "result": result})
    sequence = len(pairs)
    if any(key in action for key in ACTION_PAYLOAD_FIELDS):
        event_reopenable[f"EVT-{sequence:04d}"] = action_payload_bytes(action)
    return capture_original_result_payload(
        action,
        result,
        sequence=sequence,
        result_reopenable=result_reopenable,
    )


def _fork_binding(
    fixture: EcologicalFixture,
    *,
    seed: int,
    state: SessionState,
    pairs: list[dict[str, Any]],
    calls: int,
) -> dict[str, Any]:
    return {
        "schema_version": "experiment-019-authentic-fork-binding-v1",
        "fixture_id": fixture.fixture_id,
        "seed": seed,
        "candidate_id": state.candidate.candidate_id,
        "calls_completed": calls,
        "event_prefix_sha256": sha256_bytes(canonical_json_bytes(pairs)),
        "host_semantic_selection": False,
    }


def _admit_externalization(
    profile: RuntimeProfile,
    fixture: EcologicalFixture,
    *,
    state: SessionState,
    pairs: list[dict[str, Any]],
    calls: int,
    fork_binding: dict[str, Any],
    starting_count: int,
) -> tuple[int, bytes, dict[str, Any]]:
    count = starting_count
    while count <= len(pairs):
        request = build_request(
            fixture,
            candidate=state.candidate,
            pairs=pairs,
            externalized_payload_count=count,
            calls_used=calls,
            fork_binding=fork_binding,
        )
        admission = guard(profile, request, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
        if admission["authorized"]:
            return count, request, admission
        count += 1
    raise RuntimeError("all exact payloads externalized but X25 request is not admitted")


def run_shared_prefix(
    fixture: EcologicalFixture,
    *,
    seed: int,
    actor: Actor,
    output_dir: Path,
) -> PrefixOutcome:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    store = ArtifactStore(output_dir)
    log = RecordLog(output_dir / "records.jsonl", f"{fixture.fixture_id}-S{seed}-SHARED")
    state = SessionState(fixture.initial, stage="continuation")
    pairs: list[dict[str, Any]] = []
    event_reopenable, result_reopenable = _payload_maps(pairs)
    executor = _executor(fixture, state, result_reopenable=result_reopenable, event_reopenable=event_reopenable)
    log.append(
        "ecological_shared_started",
        {"fixture_id": fixture.fixture_id, "seed": seed, "candidate_id": state.candidate.candidate_id},
        _save_candidate(store, state.candidate, _snapshot_prefix(state.candidate)),
    )
    calls = prepared = 0
    boundary = None
    disposition = "shared_call_budget_exhausted"
    while calls < CALL_LIMIT and not state.submitted:
        request = build_request(
            fixture,
            candidate=state.candidate,
            pairs=pairs,
            externalized_payload_count=0,
            calls_used=calls,
            fork_binding=None,
        )
        own = guard(actor.profile, request, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
        physical = guard(actor.profile, request, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True)
        if not own["authorized"]:
            if not physical["authorized"] or not pairs:
                disposition = "invalid_or_physical_prepressure_stop"
                break
            boundary = {
                "schema_version": "experiment-019-first-authentic-boundary-v1",
                "t25": own,
                "r50": physical,
                "calls_completed": calls,
                "event_count": len(pairs),
                "request_sha256": sha256_bytes(request),
                "prepressure_request_bytes_shared": True,
            }
            atomic_write(output_dir / "FIRST_BOUNDARY.json", canonical_json_bytes(boundary))
            disposition = "authentic_25k_boundary_reached"
            break
        prepared += 1
        action, result, _ = _execute_call(
            actor=actor,
            request=request,
            stage="continuation",
            probe_id=None,
            call_id=f"{fixture.fixture_id}-S{seed}-SHARED-P{prepared:02d}",
            active_total_ceiling=PHYSICAL_CONTEXT,
            executor=executor,
            store=store,
            log=log,
            artifact_prefix=f"transcript/{prepared:03d}",
        )
        calls += 1
        canonical = _record_pair(pairs, action, result, event_reopenable, result_reopenable)
        log.append("canonical_payload_identity_recorded", {"sequence": len(pairs), "handle": canonical}, [])
    stopped = log.append(
        "ecological_shared_stopped",
        {
            "fixture_id": fixture.fixture_id,
            "seed": seed,
            "disposition": disposition,
            "calls": calls,
            "prepared_invocations": prepared,
            "candidate_id": state.candidate.candidate_id,
            "event_count": len(pairs),
        },
        [],
    )
    atomic_write(
        output_dir / "SUMMARY.json",
        canonical_json_bytes(
            {
                "schema_version": "experiment-019-shared-summary-v1",
                "fixture_id": fixture.fixture_id,
                "seed": seed,
                "disposition": disposition,
                "calls": calls,
                "prepared_invocations": prepared,
                "candidate_id": state.candidate.candidate_id,
                "event_count": len(pairs),
                "last_record_sha256": stopped["record_sha256"],
            }
        ),
    )
    verify_run(output_dir)
    return PrefixOutcome(
        state,
        pairs,
        result_reopenable,
        event_reopenable,
        calls,
        prepared,
        output_dir,
        disposition,
        boundary,
    )


def run_branch(
    fixture: EcologicalFixture,
    prefix: PrefixOutcome,
    *,
    seed: int,
    condition: str,
    actor: Actor,
    output_dir: Path,
) -> dict[str, Any]:
    if condition not in CONDITIONS or output_dir.exists() or prefix.disposition != "authentic_25k_boundary_reached":
        raise ValueError("invalid Experiment 019 branch")
    output_dir.mkdir(parents=True)
    store = ArtifactStore(output_dir)
    log = RecordLog(output_dir / "records.jsonl", f"{fixture.fixture_id}-S{seed}-{condition}")
    state = prefix.state.clone_for_branch()
    pairs = [{"response": dict(pair["response"]), "result": dict(pair["result"])} for pair in prefix.pairs]
    event_reopenable = dict(prefix.event_reopenable)
    result_reopenable = dict(prefix.result_reopenable)
    executor = _executor(fixture, state, result_reopenable=result_reopenable, event_reopenable=event_reopenable)
    binding = _fork_binding(fixture, seed=seed, state=state, pairs=pairs, calls=prefix.calls)
    externalized = 0
    log.append(
        "ecological_branch_started",
        {
            "fixture_id": fixture.fixture_id,
            "seed": seed,
            "condition": condition,
            "candidate_id": state.candidate.candidate_id,
            "shared_calls": prefix.calls,
            "fork_binding": binding,
        },
        _save_candidate(store, state.candidate, _snapshot_prefix(state.candidate)),
    )
    calls = prefix.calls
    branch_http = prepared = 0
    max_prompt = 0
    capacity_stops = 0
    disposition = "call_budget_exhausted"
    externalization_events = []
    minimum_adjusted_headroom = PHYSICAL_CONTEXT
    while calls < CALL_LIMIT and not state.submitted:
        prepared += 1
        if condition == "X25":
            previous = externalized
            externalized, request, admission = _admit_externalization(
                actor.profile,
                fixture,
                state=state,
                pairs=pairs,
                calls=calls,
                fork_binding=binding,
                starting_count=externalized,
            )
            if externalized != previous:
                row = {
                    "before": previous,
                    "after": externalized,
                    "calls_used": calls,
                    "event_count": len(pairs),
                    "admission": admission,
                }
                externalization_events.append(row)
                log.append("event_payloads_externalized", row, [])
            ceiling = T25_TOTAL_CEILING
        else:
            request = build_request(
                fixture,
                candidate=state.candidate,
                pairs=pairs,
                externalized_payload_count=0,
                calls_used=calls,
                fork_binding=binding,
            )
            admission = guard(actor.profile, request, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True)
            ceiling = PHYSICAL_CONTEXT
            if not admission["authorized"]:
                capacity_stops += 1
                disposition = "physical_capacity_stopped_before_http"
                atomic_write(output_dir / "CAPACITY_STOP.json", canonical_json_bytes(admission))
                break
        adjusted = admission["offline_prompt_tokens"] + REASONING_BUDGET + 2500
        minimum_adjusted_headroom = min(minimum_adjusted_headroom, ceiling - adjusted)
        max_prompt = max(max_prompt, admission["offline_prompt_tokens"])
        action, result, outcome = _execute_call(
            actor=actor,
            request=request,
            stage="continuation",
            probe_id=None,
            call_id=f"{fixture.fixture_id}-S{seed}-{condition}-P{prepared:02d}",
            active_total_ceiling=ceiling,
            executor=executor,
            store=store,
            log=log,
            artifact_prefix=f"transcript/{prepared:03d}",
        )
        branch_http += 1
        calls += 1
        max_prompt = max(max_prompt, outcome.offline_prompt_tokens)
        canonical = _record_pair(pairs, action, result, event_reopenable, result_reopenable)
        log.append("canonical_payload_identity_recorded", {"sequence": len(pairs), "handle": canonical}, [])
    if state.submitted:
        disposition = "submitted"
    stopped = log.append(
        "ecological_branch_stopped",
        {
            "fixture_id": fixture.fixture_id,
            "seed": seed,
            "condition": condition,
            "disposition": disposition,
            "total_calls": calls,
            "branch_http_calls": branch_http,
            "prepared_invocations": prepared,
            "candidate_id": state.candidate.candidate_id,
            "public_check_passed": state.public_check_passed,
            "submitted": state.submitted,
            "event_count": len(pairs),
            "externalized_payload_count": externalized,
        },
        [],
    )
    summary = {
        "schema_version": "experiment-019-branch-summary-v1",
        "fixture_id": fixture.fixture_id,
        "seed": seed,
        "condition": condition,
        "disposition": disposition,
        "shared_calls": prefix.calls,
        "branch_http_calls": branch_http,
        "prepared_invocations": prepared,
        "total_calls": calls,
        "candidate_id": state.candidate.candidate_id,
        "public_check_passed": state.public_check_passed,
        "submitted": state.submitted,
        "event_count": len(pairs),
        "externalized_payload_count": externalized,
        "externalization_events": externalization_events,
        "capacity_stops": capacity_stops,
        "maximum_offline_prompt_tokens": max_prompt,
        "minimum_adjusted_headroom_tokens": minimum_adjusted_headroom,
        "last_record_sha256": stopped["record_sha256"],
    }
    atomic_write(output_dir / "SUMMARY.json", canonical_json_bytes(summary))
    verify_run(output_dir)
    return summary


def hidden_grade(fixture: EcologicalFixture, candidate: Candidate) -> dict[str, Any]:
    return run_checker(candidate, fixture.hidden_checker)


def construct_package(target: Path, *, bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True)
    rows = []
    for cell in schedule()["cells"]:
        fixture = load_fixture(bank, cell["fixture_id"], include_evaluator=False)
        request = build_request(
            fixture,
            candidate=fixture.initial,
            pairs=[],
            externalized_payload_count=0,
            calls_used=0,
            fork_binding=None,
        )
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
            event_reopen=True,
        )
        admission = guard(profile, request, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
        if not admission["authorized"]:
            raise RuntimeError("Experiment 019 initial request is not admitted")
        rendered = render_reasoning_prompt(request, enabled=True)
        path = target / f"cell-{cell['ordinal']:02d}"
        atomic_write(path / "initial-coding-request.json", request)
        atomic_write(path / "initial-endpoint-request.json", endpoint)
        atomic_write(path / "initial-rendered-prompt.txt", rendered)
        rows.append(
            {
                **cell,
                "expected_call_id": f"{cell['fixture_id']}-S{cell['seed']}-SHARED-P01",
                "coding_request_sha256": sha256_bytes(request),
                "endpoint_request_sha256": sha256_bytes(endpoint),
                "rendered_prompt_sha256": sha256_bytes(rendered),
                "initial_admission": admission,
            }
        )
    files = _inventory(target, {"PACKAGE_MANIFEST.json"})
    manifest = {
        "schema_version": PACKAGE_SCHEMA,
        "bank_id": verify_bank(bank)["bank_id"],
        "schedule_sha256": sha256_bytes(canonical_json_bytes(schedule())),
        "rows": rows,
        "event_frame_version": 3,
        "canonical_payload_identity": True,
        "read_mode": READ_MODE,
        "reasoning_budget_tokens": REASONING_BUDGET,
        "evaluator_bytes_present": False,
        "files": files,
        "package_id": "E19PKG-" + sha256_bytes(canonical_json_bytes(files)),
    }
    atomic_write(target / "PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_package(target: Path, *, bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    observed = load_json_strict((target / "PACKAGE_MANIFEST.json").read_bytes())
    if observed["files"] != _inventory(target, {"PACKAGE_MANIFEST.json"}):
        raise ValueError("Experiment 019 package inventory differs")
    with tempfile.TemporaryDirectory(prefix="e19-package-") as raw:
        rebuilt = construct_package(Path(raw) / "package", bank=bank, profile=profile)
        if canonical_json_bytes(rebuilt) != canonical_json_bytes(observed):
            raise ValueError("Experiment 019 package reconstruction differs")
    return {"verified": True, "package_id": observed["package_id"], "file_count": len(observed["files"])}


def expected_authorization(experiment: Path) -> dict[str, Any]:
    package = load_json_strict((experiment / "execution_package" / "PACKAGE_MANIFEST.json").read_bytes())
    bank = load_json_strict((experiment / "fresh_bank" / "BANK_MANIFEST.json").read_bytes())
    closure = load_json_strict((experiment / "EXECUTABLE_CLOSURE.json").read_bytes())
    profile = load_json_strict((experiment / "RUNTIME_PROFILE.json").read_bytes())
    return {
        "schema_version": "experiment-019-owner-authorization-v1",
        "status": "owner_authorized_exact_owner_controlled_ecological_pilot",
        "owner_statement": "Proceed with the next experiment using the earned signal-bearing controller and no unearned feature.",
        "bank_id": bank["bank_id"],
        "bank_manifest_sha256": sha256_file(experiment / "fresh_bank" / "BANK_MANIFEST.json"),
        "package_id": package["package_id"],
        "package_manifest_sha256": sha256_file(experiment / "execution_package" / "PACKAGE_MANIFEST.json"),
        "closure_aggregate_sha256": closure["aggregate_sha256"],
        "closure_manifest_sha256": sha256_file(experiment / "EXECUTABLE_CLOSURE.json"),
        "runtime_profile_sha256": sha256_file(experiment / "RUNTIME_PROFILE.json"),
        "actor_sha256": profile["model_sha256"],
        "cases": list(CASE_IDS),
        "seeds": list(SEEDS),
        "conditions": list(CONDITIONS),
        "branches": 8,
        "attempts_per_branch": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
        "maximum_http_completion_calls": MAXIMUM_HTTP_COMPLETION_CALLS,
        "output_root": OUTPUT_ROOT,
        "port": PORT,
        "seal_before_evaluator": True,
        "automatic_successor": False,
    }


def validate_authorization(experiment: Path) -> dict[str, Any]:
    observed = load_json_strict((experiment / "MEASURED_AUTHORIZATION.json").read_bytes())
    if canonical_json_bytes(observed) != canonical_json_bytes(expected_authorization(experiment)):
        raise ValueError("Experiment 019 authorization differs")
    return {"verified": True, "authorization_sha256": sha256_file(experiment / "MEASURED_AUTHORIZATION.json")}


def closure(root: Path) -> dict[str, Any]:
    return build_closure(root, entrypoint="scripts/run_ecological_pilot.py")


def verify_source_closure(root: Path, path: Path) -> dict[str, Any]:
    return verify_closure(root, path)
