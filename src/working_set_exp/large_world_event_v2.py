from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .candidate import Candidate
from .custody import ArtifactStore, RecordLog
from .event_frame_v2 import ACTION_PAYLOAD_FIELDS, action_payload_bytes, event_from_pair_v2, verify_event_sequence_v2
from .hierarchical_p0 import build_p0_root
from .isolation import run_checker
from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from .large_world import _inventory
from .measured import _inventory as measured_inventory
from .recurrent_pressure import build_closure, verify_closure
from .request import TOOL_CONTRACT, observation_directory_v2, render_reasoning_prompt
from .runner import Actor, _execute_call, _save_candidate, _snapshot_prefix, verify_run
from .runtime import PHYSICAL_CONTEXT, REASONING_BUDGET, T25_TOTAL_CEILING, RuntimeProfile, endpoint_request, guard
from .tools import SessionState, ToolExecutor


EXPERIMENT_ID = "018_large_world_event_frame_v2"
CASE_IDS = ("E18-SOURCE-LANTERN", "E18-OBS-HARBOR")
SEEDS = (173205, 223607)
CONDITIONS = ("R50", "X25")
CALL_LIMIT = 18
READ_MODE = "maximal_bounded_page"
PORT = 18120
OUTPUT_ROOT = r"C:\e18-event-v2"
MAXIMUM_HTTP_COMPLETION_CALLS = 100
BANK_SCHEMA = "experiment-018-fresh-large-world-bank-v1"
PACKAGE_SCHEMA = "experiment-018-execution-package-v1"


@dataclass(frozen=True)
class EventWorldFixture:
    fixture_id: str
    family: str
    task: str
    initial: Candidate
    required_reads: tuple[str, ...]
    checker: bytes
    hidden_checker: bytes
    observations: tuple[dict[str, Any], ...]
    observation_bodies: tuple[tuple[str, bytes], ...]


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


def _generated_module(namespace: str, index: int, *, rows: int = 220) -> bytes:
    lines = [f'"""Fresh task-independent {namespace} custody ledger {index:03d}."""\n', "RECORDS = (\n"]
    for row in range(rows):
        digest = sha256_bytes(f"e18:{namespace}:{index:03d}:{row:04d}".encode())[:32]
        lines.append(f'    ("{namespace}-{index:03d}-{row:04d}", "{digest}", "retain-{(row * 53 + index * 29) % 2029:04d}"),\n')
    lines.extend([")\n\n", f"def {namespace.replace('_', '')}_{index:03d}_count() -> int:\n", "    return len(RECORDS)\n"])
    return "".join(lines).encode()


def _background(namespace: str) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for domain_index, domain in enumerate((
        "archives", "billing", "catalog", "connectors", "dispatch", "events",
        "exports", "imports", "metrics", "routing", "telemetry", "workers",
    )):
        for index in range(10):
            files[f"{domain}/module_{index:03d}.py"] = _generated_module(
                f"{namespace}_{domain}", domain_index * 10 + index, rows=96
            )
    for index in range(6):
        files[f"ledgers/required_{index:02d}.py"] = _generated_module(f"{namespace}_required", index)
    return files


def _source_case() -> dict[str, Any]:
    files = _background("lantern")
    files.update({
        "policy/current.py": b'PREFIX = "ember-"\n\n\ndef active_prefix() -> str:\n    return PREFIX\n',
        "api/primary.py": b'def normalize_primary(value: str) -> str:\n    return value.strip().casefold()\n',
        "api/secondary.py": b'def normalize_secondary(value: str) -> str:\n    return value.strip().upper()\n',
        "api/render.py": b'from api.primary import normalize_primary\nfrom api.secondary import normalize_secondary\n\n\ndef render_pair(a: str, b: str) -> str:\n    return f"{normalize_primary(a)}|{normalize_secondary(b)}"\n',
    })
    required = tuple(f"ledgers/required_{index:02d}.py" for index in range(4))
    task = (
        "Complete this single long active step. Read every listed required ledger completely. Read exact current source before each mutation. "
        "First preserve the current policy value by repairing `api/primary.py` so it prefixes trimmed case-folded values with the exact current "
        "`active_prefix()` value. Then change the policy source so the authorized current prefix is `quartz-`. Reacquire the exact current policy "
        "source after that mutation and repair `api/secondary.py` so it prefixes trimmed uppercased values with the now-current policy value. "
        "Required ledgers: " + ", ".join(f"`{path}`" for path in required) + ". Run check `public` on the current candidate and submit."
    )
    checker = (
        b"from policy.current import active_prefix\nfrom api.primary import normalize_primary\n"
        b"from api.secondary import normalize_secondary\nfrom api.render import render_pair\n"
        b"assert active_prefix() == 'quartz-'\nassert normalize_primary(' A ') == 'ember-a'\n"
        b"assert normalize_secondary(' b7 ') == 'quartz-B7'\n"
        b"assert render_pair(' Mix ', ' q2 ') == 'ember-mix|quartz-Q2'\nprint('public passed')\n"
    )
    return {"fixture_id": CASE_IDS[0], "family": "fresh_large_world_evolving_source", "files": files,
            "task": task, "required": required, "checker": checker, "hidden": checker,
            "observations": [], "observation_bodies": {}}


def _observation_case() -> dict[str, Any]:
    files = _background("harbor")
    files.update({
        "runtime/version.py": b'WORLD_VERSION = 1\n',
        "codec/label.py": b'def codec_label(value: str) -> str:\n    return value.strip().upper()\n',
        "codec/footer.py": b'def codec_footer(value: str) -> str:\n    return value.strip().casefold()\n',
        "codec/wire.py": b'from codec.label import codec_label\nfrom codec.footer import codec_footer\n\n\ndef encode_wire(value: str) -> str:\n    return f"{codec_label(value)}|{codec_footer(value)}"\n',
    })
    predecessor = Candidate.create({**files, "runtime/version.py": b'WORLD_VERSION = 0\n'})
    current = Candidate.create(files)
    stale_body = canonical_json_bytes({"accepted": True, "probe_id": "marker", "candidate_id": predecessor.candidate_id,
                                       "observation": "marker=DOCK-OLD"})
    current_body = canonical_json_bytes({"accepted": True, "probe_id": "marker", "candidate_id": current.candidate_id,
                                         "observation": "marker=HARBOR-K9"})
    observations = [
        {"handle": "OBS-0001", "sequence": 1, "action": "probe", "target": "marker",
         "candidate_id": predecessor.candidate_id, "size_bytes": len(stale_body), "sha256": sha256_bytes(stale_body)},
        {"handle": "OBS-0002", "sequence": 2, "action": "probe", "target": "marker",
         "candidate_id": current.candidate_id, "size_bytes": len(current_body), "sha256": sha256_bytes(current_body)},
    ]
    required = tuple(f"ledgers/required_{index:02d}.py" for index in range(4))
    task = (
        "Complete this single long active step. The observation directory contains an older and a current exact `marker` result. Select by exact "
        "candidate binding, reopen the current body, and use its marker value. Read every listed required ledger completely. Read exact current "
        "source before mutation. Repair `codec/label.py` so it prefixes trimmed uppercased values with the current marker plus `::`. Later repair "
        "`codec/footer.py` so it prefixes trimmed case-folded values with that same exact current marker plus `::`; reacquire the exact observation "
        "or exact externalized action/result payload if the marker body is no longer resident. Required ledgers: "
        + ", ".join(f"`{path}`" for path in required) + ". Run check `public` on the current candidate and submit."
    )
    checker = (
        b"from codec.label import codec_label\nfrom codec.footer import codec_footer\nfrom codec.wire import encode_wire\n"
        b"assert codec_label(' a ') == 'HARBOR-K9::A'\nassert codec_footer(' B ') == 'HARBOR-K9::b'\n"
        b"assert encode_wire(' Ab ') == 'HARBOR-K9::AB|HARBOR-K9::ab'\nprint('public passed')\n"
    )
    return {"fixture_id": CASE_IDS[1], "family": "fresh_large_world_observation_reuse", "files": files,
            "task": task, "required": required, "checker": checker, "hidden": checker,
            "observations": observations, "observation_bodies": {"OBS-0001": stale_body, "OBS-0002": current_body}}


def case_definitions() -> tuple[dict[str, Any], ...]:
    return (_source_case(), _observation_case())


def schedule() -> dict[str, Any]:
    cells = []
    ordinal = 0
    for case_index, fixture_id in enumerate(CASE_IDS):
        for seed_index, seed in enumerate(SEEDS):
            ordinal += 1
            order = list(CONDITIONS if (case_index + seed_index) % 2 == 0 else reversed(CONDITIONS))
            cells.append({"ordinal": ordinal, "fixture_id": fixture_id, "seed": seed, "branch_order": order})
    return {"schema_version": "experiment-018-schedule-v1", "cases": list(CASE_IDS), "seeds": list(SEEDS),
            "conditions": list(CONDITIONS), "cells": cells, "attempts_per_branch": 1,
            "retries": 0, "repairs": 0, "rescues": 0, "reasoning_budget_tokens": REASONING_BUDGET}


def construct_bank(target: Path) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    files: dict[str, bytes] = {}
    rows = []
    for case in case_definitions():
        visible = f"model_visible/{case['fixture_id']}"
        execution = f"execution_only/{case['fixture_id']}"
        evaluator = f"evaluator_only/{case['fixture_id']}"
        files[f"{visible}/TASK.txt"] = case["task"].encode()
        candidate = Candidate.create(case["files"])
        candidate_rows = []
        for path, body in candidate.files:
            files[f"{visible}/candidate/{path}"] = body
            candidate_rows.append({"path": path, "size_bytes": len(body), "sha256": sha256_bytes(body)})
        files[f"{execution}/public.py"] = case["checker"]
        for handle, body in case["observation_bodies"].items():
            files[f"{execution}/observations/{handle}.json"] = body
        fixture_row = {"fixture_id": case["fixture_id"], "family": case["family"], "candidate_id": candidate.candidate_id,
                       "candidate_files": candidate_rows, "required_reads": list(case["required"]),
                       "observations": case["observations"]}
        files[f"{execution}/FIXTURE.json"] = canonical_json_bytes(fixture_row)
        files[f"{evaluator}/hidden.py"] = case["hidden"]
        rows.append({"fixture_id": case["fixture_id"], "family": case["family"],
                     "task_sha256": sha256_bytes(case["task"].encode()), "candidate_id": candidate.candidate_id})
    for relative, body in files.items():
        atomic_write(target / relative, body)
    inventory = measured_inventory(target, excluded={"BANK_MANIFEST.json"})
    manifest = {"schema_version": BANK_SCHEMA, "case_ids": list(CASE_IDS), "rows": rows,
                "evaluator_separated": True, "fresh_after_experiment_017": True, "files": inventory,
                "bank_id": "E18BANK-" + sha256_bytes(canonical_json_bytes(inventory))}
    atomic_write(target / "BANK_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_bank(target: Path) -> dict[str, Any]:
    observed = load_json_strict((target / "BANK_MANIFEST.json").read_bytes())
    if observed["files"] != measured_inventory(target, excluded={"BANK_MANIFEST.json"}):
        raise ValueError("Experiment 018 bank inventory differs")
    with tempfile.TemporaryDirectory(prefix="e18-bank-") as raw:
        rebuilt = construct_bank(Path(raw) / "bank")
        if canonical_json_bytes(rebuilt) != canonical_json_bytes(observed):
            raise ValueError("Experiment 018 bank reconstruction differs")
    return {"verified": True, "bank_id": observed["bank_id"], "file_count": len(observed["files"])}


def load_fixture(bank: Path, fixture_id: str, *, include_evaluator: bool = True) -> EventWorldFixture:
    if fixture_id not in CASE_IDS:
        raise ValueError("unknown Experiment 018 fixture")
    visible = bank / "model_visible" / fixture_id
    execution = bank / "execution_only" / fixture_id
    row = load_json_strict((execution / "FIXTURE.json").read_bytes())
    files = {item["path"]: (visible / "candidate" / Path(*item["path"].split("/"))).read_bytes()
             for item in row["candidate_files"]}
    bodies = tuple((item["handle"], (execution / "observations" / f"{item['handle']}.json").read_bytes())
                   for item in row["observations"])
    return EventWorldFixture(fixture_id, row["family"], (visible / "TASK.txt").read_text(), Candidate.create(files),
                             tuple(row["required_reads"]), (execution / "public.py").read_bytes(),
                             (bank / "evaluator_only" / fixture_id / "hidden.py").read_bytes() if include_evaluator else b"",
                             tuple(row["observations"]), bodies)


def _payload_maps(pairs: list[dict[str, Any]]) -> tuple[dict[str, bytes], dict[str, bytes]]:
    events: dict[str, bytes] = {}
    results: dict[str, bytes] = {}
    for sequence, pair in enumerate(pairs, 1):
        if any(key in pair["response"] for key in ACTION_PAYLOAD_FIELDS):
            events[f"EVT-{sequence:04d}"] = action_payload_bytes(pair["response"])
        results[f"RES-{sequence:04d}"] = canonical_json_bytes(pair["result"])
    return events, results


def build_request(
    fixture: EventWorldFixture, *, candidate: Candidate, state: SessionState, pairs: list[dict[str, Any]],
    externalized_payload_count: int, calls_used: int, fork_binding: dict[str, Any] | None,
) -> bytes:
    if not 0 <= externalized_payload_count <= len(pairs):
        raise ValueError("externalized count differs")
    actions = ["p0_page", "tree", "search", "read", "patch", "check", "reopen_observation",
               "reopen_result", "reopen_event", "submit"]
    contract = {name: TOOL_CONTRACT[name] for name in actions if name in TOOL_CONTRACT}
    contract["p0_page"] = "task-independent readable directory or file-outline page; exact source is not included"
    contract["read"] = "largest exact current whole-line page that fits the frozen result bound, with non-guessing continuation"
    events = [event_from_pair_v2(pair["response"], pair["result"], sequence=index,
                                event_handle=f"EVT-{index:04d}", result_handle=f"RES-{index:04d}",
                                payload_residency="external" if index <= externalized_payload_count else "resident")
              for index, pair in enumerate(pairs, 1)]
    verification = verify_event_sequence_v2(events)
    value = {
        "schema_version": "experiment-018-large-world-event-frame-request-v1",
        "fixture_id": fixture.fixture_id,
        "stage": "continuation",
        "task": fixture.task,
        "active_user_authored_step": {"id": "LONG-STEP", "text": fixture.task, "host_inference": False},
        "completed_step_ids": [],
        "candidate_id": candidate.candidate_id,
        "current_p0": build_p0_root(candidate),
        "p0_contract": {"task_independent": True, "semantic_ranking": False, "repository_complete": False,
                        "root_complete": True, "scoped_access": "p0_page", "exact_source_required_before_mutation": True},
        "observation_directory": observation_directory_v2(list(fixture.observations)),
        "active_phase_event_frame": {
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
        },
        "event_frame_verification": verification,
        "latest_transition_binding": fork_binding,
        "resource_state": {"calls_used": calls_used, "call_limit": CALL_LIMIT,
                           "reasoning_budget_tokens": REASONING_BUDGET},
        "available_check_ids": ["public"],
        "available_actions": actions,
        "tool_contract": contract,
        "read_paging_mode": READ_MODE,
        "reconstruction_notice": (
            "The single event sequence is exact progress. Readable action targets, acceptance/status, ranges, and candidate/file/check "
            "bindings are the resident signal. Handles only address exact externally custodied payloads. Use reopen_event for listed old/new "
            "action fields and reopen_result for listed exact result bodies when needed. Sequence records occurrence, not semantic sufficiency."
        ),
    }
    return canonical_json_bytes(value)


def _fork_binding(fixture: EventWorldFixture, *, seed: int, state: SessionState,
                  pairs: list[dict[str, Any]], calls: int) -> dict[str, Any]:
    return {"schema_version": "experiment-018-authentic-fork-binding-v1", "fixture_id": fixture.fixture_id,
            "seed": seed, "candidate_id": state.candidate.candidate_id, "calls_completed": calls,
            "event_prefix_sha256": sha256_bytes(canonical_json_bytes(pairs)),
            "required_reads_completed": sorted(state.complete_reads), "host_semantic_selection": False}


def _executor(fixture: EventWorldFixture, state: SessionState, *, result_reopenable: dict[str, bytes],
              event_reopenable: dict[str, bytes]) -> ToolExecutor:
    return ToolExecutor(state, required_full_reads=fixture.required_reads, prefork_checker=fixture.checker,
                        public_checker=fixture.checker, final_target="__none__", probe_id=None, probe_body=None,
                        reopenable=dict(fixture.observation_bodies), result_reopenable=result_reopenable,
                        event_reopenable=event_reopenable, read_mode=READ_MODE, hierarchical_p0=True)


def _record_pair(pairs: list[dict[str, Any]], action: dict[str, Any], result: dict[str, Any],
                 event_reopenable: dict[str, bytes], result_reopenable: dict[str, bytes]) -> None:
    pairs.append({"response": action, "result": result})
    sequence = len(pairs)
    if any(key in action for key in ACTION_PAYLOAD_FIELDS):
        event_reopenable[f"EVT-{sequence:04d}"] = action_payload_bytes(action)
    result_reopenable[f"RES-{sequence:04d}"] = canonical_json_bytes(result)


def _admit_externalization(profile: RuntimeProfile, fixture: EventWorldFixture, *, state: SessionState,
                           pairs: list[dict[str, Any]], calls: int, fork_binding: dict[str, Any],
                           starting_count: int) -> tuple[int, bytes, dict[str, Any]]:
    count = starting_count
    while count <= len(pairs):
        request = build_request(fixture, candidate=state.candidate, state=state, pairs=pairs,
                                externalized_payload_count=count, calls_used=calls, fork_binding=fork_binding)
        admission = guard(profile, request, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
        if admission["authorized"]:
            return count, request, admission
        count += 1
    raise RuntimeError("all exact payloads externalized but X25 request is not admitted")


def run_shared_prefix(fixture: EventWorldFixture, *, seed: int, actor: Actor, output_dir: Path) -> PrefixOutcome:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    store = ArtifactStore(output_dir)
    log = RecordLog(output_dir / "records.jsonl", f"{fixture.fixture_id}-S{seed}-SHARED")
    state = SessionState(fixture.initial, stage="continuation")
    pairs: list[dict[str, Any]] = []
    event_reopenable, result_reopenable = _payload_maps(pairs)
    executor = _executor(fixture, state, result_reopenable=result_reopenable, event_reopenable=event_reopenable)
    log.append("event_world_shared_started", {"fixture_id": fixture.fixture_id, "seed": seed,
               "candidate_id": state.candidate.candidate_id}, _save_candidate(store, state.candidate, _snapshot_prefix(state.candidate)))
    calls = prepared = 0
    boundary = None
    disposition = "shared_call_budget_exhausted"
    while calls < CALL_LIMIT and not state.submitted:
        request = build_request(fixture, candidate=state.candidate, state=state, pairs=pairs,
                                externalized_payload_count=0, calls_used=calls, fork_binding=None)
        own = guard(actor.profile, request, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
        physical = guard(actor.profile, request, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True)
        if not own["authorized"]:
            if not physical["authorized"] or not pairs:
                disposition = "invalid_or_physical_prepressure_stop"
                break
            boundary = {"schema_version": "experiment-018-first-authentic-boundary-v1", "t25": own, "r50": physical,
                        "calls_completed": calls, "event_count": len(pairs),
                        "request_sha256": sha256_bytes(request),
                        "prepressure_request_bytes_shared": True}
            atomic_write(output_dir / "FIRST_BOUNDARY.json", canonical_json_bytes(boundary))
            disposition = "authentic_25k_boundary_reached"
            break
        prepared += 1
        action, result, _ = _execute_call(actor=actor, request=request, stage="continuation", probe_id=None,
            call_id=f"{fixture.fixture_id}-S{seed}-SHARED-P{prepared:02d}", active_total_ceiling=PHYSICAL_CONTEXT,
            executor=executor, store=store, log=log, artifact_prefix=f"transcript/{prepared:03d}")
        calls += 1
        _record_pair(pairs, action, result, event_reopenable, result_reopenable)
    stopped = log.append("event_world_shared_stopped", {"fixture_id": fixture.fixture_id, "seed": seed,
        "disposition": disposition, "calls": calls, "prepared_invocations": prepared,
        "candidate_id": state.candidate.candidate_id, "event_count": len(pairs)}, [])
    atomic_write(output_dir / "SUMMARY.json", canonical_json_bytes({"schema_version": "experiment-018-shared-summary-v1",
        "fixture_id": fixture.fixture_id, "seed": seed, "disposition": disposition, "calls": calls,
        "prepared_invocations": prepared, "candidate_id": state.candidate.candidate_id,
        "event_count": len(pairs), "last_record_sha256": stopped["record_sha256"]}))
    verify_run(output_dir)
    return PrefixOutcome(state, pairs, result_reopenable, event_reopenable, calls, prepared, output_dir, disposition, boundary)


def run_branch(fixture: EventWorldFixture, prefix: PrefixOutcome, *, seed: int, condition: str,
               actor: Actor, output_dir: Path) -> dict[str, Any]:
    if condition not in CONDITIONS or output_dir.exists() or prefix.disposition != "authentic_25k_boundary_reached":
        raise ValueError("invalid Experiment 018 branch")
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
    log.append("event_world_branch_started", {"fixture_id": fixture.fixture_id, "seed": seed, "condition": condition,
        "candidate_id": state.candidate.candidate_id, "shared_calls": prefix.calls, "fork_binding": binding},
        _save_candidate(store, state.candidate, _snapshot_prefix(state.candidate)))
    calls = prefix.calls
    branch_http = prepared = 0
    max_prompt = 0
    capacity_stops = 0
    disposition = "call_budget_exhausted"
    externalization_events = []
    while calls < CALL_LIMIT and not state.submitted:
        prepared += 1
        if condition == "X25":
            previous = externalized
            externalized, request, admission = _admit_externalization(
                actor.profile, fixture, state=state, pairs=pairs, calls=calls, fork_binding=binding,
                starting_count=externalized,
            )
            if externalized != previous:
                row = {"before": previous, "after": externalized, "calls_used": calls,
                       "event_count": len(pairs), "admission": admission}
                externalization_events.append(row)
                log.append("event_payloads_externalized", row, [])
            ceiling = T25_TOTAL_CEILING
        else:
            request = build_request(fixture, candidate=state.candidate, state=state, pairs=pairs,
                                    externalized_payload_count=0, calls_used=calls, fork_binding=binding)
            admission = guard(actor.profile, request, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True)
            ceiling = PHYSICAL_CONTEXT
            if not admission["authorized"]:
                capacity_stops += 1
                disposition = "physical_capacity_stopped_before_http"
                atomic_write(output_dir / "CAPACITY_STOP.json", canonical_json_bytes(admission))
                break
        max_prompt = max(max_prompt, admission["offline_prompt_tokens"])
        action, result, outcome = _execute_call(actor=actor, request=request, stage="continuation", probe_id=None,
            call_id=f"{fixture.fixture_id}-S{seed}-{condition}-P{prepared:02d}", active_total_ceiling=ceiling,
            executor=executor, store=store, log=log, artifact_prefix=f"transcript/{prepared:03d}")
        branch_http += 1
        calls += 1
        max_prompt = max(max_prompt, outcome.offline_prompt_tokens)
        _record_pair(pairs, action, result, event_reopenable, result_reopenable)
    if state.submitted:
        disposition = "submitted"
    stopped = log.append("event_world_branch_stopped", {"fixture_id": fixture.fixture_id, "seed": seed,
        "condition": condition, "disposition": disposition, "total_calls": calls, "branch_http_calls": branch_http,
        "prepared_invocations": prepared, "candidate_id": state.candidate.candidate_id,
        "public_check_passed": state.public_check_passed, "submitted": state.submitted,
        "event_count": len(pairs), "externalized_payload_count": externalized}, [])
    summary = {"schema_version": "experiment-018-branch-summary-v1", "fixture_id": fixture.fixture_id,
        "seed": seed, "condition": condition, "disposition": disposition, "shared_calls": prefix.calls,
        "branch_http_calls": branch_http, "prepared_invocations": prepared, "total_calls": calls,
        "candidate_id": state.candidate.candidate_id, "public_check_passed": state.public_check_passed,
        "submitted": state.submitted, "event_count": len(pairs), "externalized_payload_count": externalized,
        "externalization_events": externalization_events, "capacity_stops": capacity_stops,
        "maximum_offline_prompt_tokens": max_prompt, "last_record_sha256": stopped["record_sha256"]}
    atomic_write(output_dir / "SUMMARY.json", canonical_json_bytes(summary))
    verify_run(output_dir)
    return summary


def hidden_grade(fixture: EventWorldFixture, candidate: Candidate) -> dict[str, Any]:
    return run_checker(candidate, fixture.hidden_checker)


def construct_package(target: Path, *, bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True)
    rows = []
    for cell in schedule()["cells"]:
        fixture = load_fixture(bank, cell["fixture_id"], include_evaluator=False)
        state = SessionState(fixture.initial, stage="continuation")
        request = build_request(fixture, candidate=fixture.initial, state=state, pairs=[],
                                externalized_payload_count=0, calls_used=0, fork_binding=None)
        endpoint = endpoint_request(profile, request, stage="continuation", probe_id=None, seed=cell["seed"],
                                    reasoning_enabled=True, read_mode=READ_MODE, hierarchical_p0=True,
                                    result_reopen=True, event_reopen=True)
        admission = guard(profile, request, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
        if not admission["authorized"]:
            raise RuntimeError("Experiment 018 initial shared request is not admitted")
        rendered = render_reasoning_prompt(request, enabled=True)
        path = target / f"cell-{cell['ordinal']:02d}"
        atomic_write(path / "initial-coding-request.json", request)
        atomic_write(path / "initial-endpoint-request.json", endpoint)
        atomic_write(path / "initial-rendered-prompt.txt", rendered)
        rows.append({**cell, "expected_call_id": f"{cell['fixture_id']}-S{cell['seed']}-SHARED-P01",
                     "coding_request_sha256": sha256_bytes(request), "endpoint_request_sha256": sha256_bytes(endpoint),
                     "rendered_prompt_sha256": sha256_bytes(rendered), "initial_admission": admission})
    files = _inventory(target, {"PACKAGE_MANIFEST.json"})
    manifest = {"schema_version": PACKAGE_SCHEMA, "bank_id": verify_bank(bank)["bank_id"],
                "schedule_sha256": sha256_bytes(canonical_json_bytes(schedule())), "rows": rows,
                "event_frame_version": 2, "read_mode": READ_MODE, "reasoning_budget_tokens": REASONING_BUDGET,
                "evaluator_bytes_present": False, "files": files,
                "package_id": "E18PKG-" + sha256_bytes(canonical_json_bytes(files))}
    atomic_write(target / "PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_package(target: Path, *, bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    observed = load_json_strict((target / "PACKAGE_MANIFEST.json").read_bytes())
    if observed["files"] != _inventory(target, {"PACKAGE_MANIFEST.json"}):
        raise ValueError("Experiment 018 package inventory differs")
    with tempfile.TemporaryDirectory(prefix="e18-package-") as raw:
        rebuilt = construct_package(Path(raw) / "package", bank=bank, profile=profile)
        if canonical_json_bytes(rebuilt) != canonical_json_bytes(observed):
            raise ValueError("Experiment 018 package reconstruction differs")
    return {"verified": True, "package_id": observed["package_id"], "file_count": len(observed["files"])}


def expected_authorization(experiment: Path) -> dict[str, Any]:
    package = load_json_strict((experiment / "execution_package" / "PACKAGE_MANIFEST.json").read_bytes())
    bank = load_json_strict((experiment / "fresh_bank" / "BANK_MANIFEST.json").read_bytes())
    closure = load_json_strict((experiment / "EXECUTABLE_CLOSURE.json").read_bytes())
    profile = load_json_strict((experiment / "RUNTIME_PROFILE.json").read_bytes())
    return {"schema_version": "experiment-018-owner-authorization-v1",
            "status": "owner_authorized_exact_fresh_large_world_event_frame_v2_run",
            "owner_statement": "Proceed with the next fresh large-world experiment using signal-bearing handles and no duplicated chronology.",
            "bank_id": bank["bank_id"], "bank_manifest_sha256": sha256_file(experiment / "fresh_bank" / "BANK_MANIFEST.json"),
            "package_id": package["package_id"], "package_manifest_sha256": sha256_file(experiment / "execution_package" / "PACKAGE_MANIFEST.json"),
            "closure_aggregate_sha256": closure["aggregate_sha256"],
            "closure_manifest_sha256": sha256_file(experiment / "EXECUTABLE_CLOSURE.json"),
            "runtime_profile_sha256": sha256_file(experiment / "RUNTIME_PROFILE.json"),
            "actor_sha256": profile["model_sha256"], "cases": list(CASE_IDS), "seeds": list(SEEDS),
            "conditions": list(CONDITIONS), "branches": 8, "attempts_per_branch": 1,
            "retries": 0, "repairs": 0, "rescues": 0,
            "maximum_http_completion_calls": MAXIMUM_HTTP_COMPLETION_CALLS, "output_root": OUTPUT_ROOT,
            "port": PORT, "seal_before_evaluator": True, "automatic_successor": False}


def validate_authorization(experiment: Path) -> dict[str, Any]:
    observed = load_json_strict((experiment / "MEASURED_AUTHORIZATION.json").read_bytes())
    if canonical_json_bytes(observed) != canonical_json_bytes(expected_authorization(experiment)):
        raise ValueError("Experiment 018 authorization differs")
    return {"verified": True, "authorization_sha256": sha256_file(experiment / "MEASURED_AUTHORIZATION.json")}


def closure(root: Path) -> dict[str, Any]:
    return build_closure(root, entrypoint="scripts/run_large_world_event_v2.py")


def verify_source_closure(root: Path, path: Path) -> dict[str, Any]:
    return verify_closure(root, path)
