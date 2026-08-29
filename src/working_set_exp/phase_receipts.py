from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .candidate import Candidate
from .custody import ArtifactStore, RecordLog
from .hierarchical_p0 import build_p0_root
from .isolation import run_checker
from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from .large_world import _inventory, _large_background
from .request import TOOL_CONTRACT, observation_directory_v2, render_reasoning_prompt
from .runner import Actor, _execute_call, _save_candidate, _snapshot_prefix, verify_run
from .runtime import PHYSICAL_CONTEXT, REASONING_BUDGET, T25_TOTAL_CEILING, CapacityStopped, RuntimeProfile, endpoint_request, guard
from .tools import SessionState, ToolExecutor


EXPERIMENT_ID = "013_active_phase_receipts"
CASE_IDS = ("E13-SOURCE-LUMEN", "E13-OBS-ANCHOR")
SEEDS = (173205, 223607)
CONDITIONS = ("T25-LATEST", "T25-RECEIPTS")
PHASE_CALL_LIMITS = {"A": 12, "B": 14}
READ_MODE = "maximal_bounded_page"
PORT = 18116
OUTPUT_ROOT = r"C:\e13-primary"
MAXIMUM_HTTP_COMPLETION_CALLS = 180
BANK_SCHEMA = "experiment-013-active-phase-receipt-bank-v1"
PACKAGE_SCHEMA = "experiment-013-active-phase-receipt-package-v1"
MAX_RECEIPT_LEDGER_BYTES = 12_000


def case_definitions() -> tuple[dict[str, Any], ...]:
    source_files = _large_background("lumen")
    source_files.update({
        "workflow/progress.py": b'def completed_phases() -> int:\n    return 0\n',
        "policies/current.py": b'POLICY_PREFIX = "lumen-"\n\n\ndef active_policy_prefix() -> str:\n    return POLICY_PREFIX\n',
        "api/name.py": b'def normalize_name(value: str) -> str:\n    return value.strip().casefold()\n',
        "api/footer.py": b'def normalize_footer(value: str) -> str:\n    return value.strip().upper()\n',
        "api/render.py": b'from api.name import normalize_name\n\n\ndef render_name(value: str) -> str:\n    return normalize_name(value)\n',
        "runtime/state.py": b'def runtime_state() -> str:\n    return "steady"\n',
    })
    source_a = (
        "Phase A: read `records_a/module_000.py` and `records_a/module_001.py` completely. "
        "Repair `workflow/progress.py` so `completed_phases()` returns 1, run check `prefork`, and call `fork_ready`."
    )
    source_b = (
        "Phase B: locate and read the exact current source definition of `active_policy_prefix()` using readable P0 orientation. "
        "Repair `api/name.py` so normalized names are prefixed by that exact current value while preserving trimming and case folding. "
        "Read `records_b/module_000.py` and `records_b/module_001.py` completely, run check `public`, and submit."
    )
    source = {
        "fixture_id": CASE_IDS[0], "family": "receipt_large_world_source", "files": source_files,
        "task": "Perform these two phases in order. " + source_a + " " + source_b,
        "phases": {
            "A": {"text": source_a, "required": ["records_a/module_000.py", "records_a/module_001.py"],
                  "target": "workflow/progress.py", "probe_id": None, "probe_body": None,
                  "check": b"from workflow.progress import completed_phases\nassert completed_phases() == 1\nprint('phase A passed')\n"},
            "B": {"text": source_b, "required": ["records_b/module_000.py", "records_b/module_001.py"],
                  "target": "api/name.py", "probe_id": None, "probe_body": None,
                  "check": b"from api.name import normalize_name\nfrom policies.current import active_policy_prefix\nassert active_policy_prefix() == 'lumen-'\nassert normalize_name(' Blue ') == 'lumen-blue'\nprint('public passed')\n"},
        },
        "patches": [
            {"path": "workflow/progress.py", "old": "    return 0", "new": "    return 1"},
            {"path": "api/name.py", "old": "    return value.strip().casefold()", "new": '    return "lumen-" + value.strip().casefold()'},
        ],
        "hidden": b"from api.name import normalize_name\nfrom policies.current import active_policy_prefix\nassert active_policy_prefix() == 'lumen-'\nassert normalize_name(' A ') == 'lumen-a'\nprint('hidden passed')\n",
    }

    obs_files = _large_background("anchor")
    obs_files.update({
        "workflow/progress.py": b'def completed_phases() -> int:\n    return 0\n',
        "codec/label.py": b'def codec_label(value: str) -> str:\n    return value.strip().upper()\n',
        "codec/header.py": b'def codec_header(value: str) -> str:\n    return value.strip().casefold()\n',
        "codec/footer.py": b'def codec_footer(value: str) -> str:\n    return value.strip().upper()\n',
        "codec/wire.py": b'from codec.label import codec_label\n\n\ndef encode_wire(value: str) -> bytes:\n    return codec_label(value).encode("ascii")\n',
        "runtime/state.py": b'def runtime_state() -> str:\n    return "steady"\n',
    })
    obs_a = (
        "Phase A: read `records_a/module_000.py` and `records_a/module_001.py` completely. Repair `workflow/progress.py` "
        "so `completed_phases()` returns 1, run check `prefork`, call probe `integrity`, and call `fork_ready`."
    )
    obs_b = (
        "Phase B: use candidate bindings to select and reopen the exact current `integrity` observation. Repair `codec/label.py` "
        "so it prepends that exact marker while preserving trimming and uppercasing. Read `records_b/module_000.py` and "
        "`records_b/module_001.py` completely, run check `public`, and submit."
    )
    observation = {
        "fixture_id": CASE_IDS[1], "family": "receipt_large_world_observation", "files": obs_files,
        "task": "Perform these two phases in order. " + obs_a + " " + obs_b,
        "phases": {
            "A": {"text": obs_a, "required": ["records_a/module_000.py", "records_a/module_001.py"],
                  "target": "workflow/progress.py", "probe_id": "integrity",
                  "probe_body": "integrity observation\nmarker=D4::\nvalidity=current_candidate_only\n",
                  "check": b"from workflow.progress import completed_phases\nassert completed_phases() == 1\nprint('phase A passed')\n"},
            "B": {"text": obs_b, "required": ["records_b/module_000.py", "records_b/module_001.py"],
                  "target": "codec/label.py", "probe_id": None, "probe_body": None,
                  "check": b"from codec.label import codec_label\nassert codec_label(' blue ') == 'D4::BLUE'\nprint('public passed')\n"},
        },
        "patches": [
            {"path": "workflow/progress.py", "old": "    return 0", "new": "    return 1"},
            {"path": "codec/label.py", "old": "    return value.strip().upper()", "new": '    return "D4::" + value.strip().upper()'},
        ],
        "hidden": b"from codec.label import codec_label\nfrom codec.wire import encode_wire\nassert codec_label(' a ') == 'D4::A'\nassert encode_wire(' Ab ') == b'D4::AB'\nprint('hidden passed')\n",
    }
    return source, observation


@dataclass(frozen=True)
class PhaseSpec:
    phase_id: str
    text: str
    required: tuple[str, ...]
    target: str
    checker: bytes
    probe_id: str | None
    probe_body: str | None


@dataclass(frozen=True)
class ReceiptFixture:
    fixture_id: str
    family: str
    task: str
    initial: Candidate
    phases: dict[str, PhaseSpec]
    hidden_checker: bytes


def _successor(case: dict[str, Any], count: int) -> Candidate:
    candidate = Candidate.create(case["files"])
    for row in case["patches"][:count]:
        candidate, _ = candidate.patch(
            path=row["path"], old=row["old"], new=row["new"],
            expected_candidate_id=candidate.candidate_id,
            expected_file_sha256=candidate.file_sha256(row["path"]),
        )
    return candidate


def construct_bank(target: Path) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    files: dict[str, bytes] = {}
    for case in case_definitions():
        initial = Candidate.create(case["files"])
        successors = [_successor(case, 1), _successor(case, 2)]
        visible = f"model_visible/{case['fixture_id']}"
        candidate_rows = []
        for path, data in initial.files:
            files[f"{visible}/candidate/{path}"] = data
            candidate_rows.append({"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)})
        files[f"{visible}/TASK.txt"] = case["task"].encode()
        for phase_id in ("A", "B"):
            phase = case["phases"][phase_id]
            files[f"{visible}/PHASE_{phase_id}.txt"] = phase["text"].encode()
            files[f"execution_only/{case['fixture_id']}/checks/{phase_id}.py"] = phase["check"]
            if phase["probe_body"] is not None:
                files[f"execution_only/{case['fixture_id']}/probes/{phase_id}.txt"] = phase["probe_body"].encode()
        files[f"execution_only/{case['fixture_id']}/FIXTURE.json"] = canonical_json_bytes({
            "schema_version": "experiment-013-fixture-v1", "fixture_id": case["fixture_id"], "family": case["family"],
            "initial_candidate_id": initial.candidate_id, "candidate_files": candidate_rows,
            "phase_candidate_ids": {"A": successors[0].candidate_id, "B": successors[1].candidate_id},
            "phases": {phase_id: {
                "required": case["phases"][phase_id]["required"], "target": case["phases"][phase_id]["target"],
                "probe_id": case["phases"][phase_id]["probe_id"],
                "probe_body_present": case["phases"][phase_id]["probe_body"] is not None,
            } for phase_id in ("A", "B")},
        })
        evaluator = f"evaluator_only/{case['fixture_id']}"
        files[f"{evaluator}/hidden.py"] = case["hidden"]
        for path, data in successors[1].files:
            files[f"{evaluator}/known_good/{path}"] = data
        files[f"{evaluator}/TRUTH.json"] = canonical_json_bytes({
            "schema_version": "experiment-013-truth-v1", "fixture_id": case["fixture_id"],
            "known_good_candidate_id": successors[1].candidate_id, "patches": case["patches"],
        })
    for relative, data in files.items():
        atomic_write(target / Path(*relative.split("/")), data)
    inventory = [{"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)} for path, data in sorted(files.items())]
    manifest = {
        "schema_version": BANK_SCHEMA, "bank_id": "E13BANK-" + sha256_bytes(canonical_json_bytes(inventory)),
        "case_ids": list(CASE_IDS), "seeds": list(SEEDS), "conditions": list(CONDITIONS),
        "fresh_before_actor_exposure": True, "selected_before_actor_behavior": True,
        "evaluator_separate": True, "files": inventory,
    }
    atomic_write(target / "BANK_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_bank(target: Path) -> dict[str, Any]:
    manifest = load_json_strict((target / "BANK_MANIFEST.json").read_bytes())
    files = _inventory(target, {"BANK_MANIFEST.json"})
    expected = "E13BANK-" + sha256_bytes(canonical_json_bytes(files))
    if manifest["schema_version"] != BANK_SCHEMA or manifest["files"] != files or manifest["bank_id"] != expected:
        raise ValueError("Experiment 013 bank differs")
    return {"verified": True, "bank_id": expected, "file_count": len(files)}


def load_fixture(bank: Path, fixture_id: str) -> ReceiptFixture:
    visible = bank / "model_visible" / fixture_id
    execution = bank / "execution_only" / fixture_id
    row = load_json_strict((execution / "FIXTURE.json").read_bytes())
    files = {item["path"]: (visible / "candidate" / Path(*item["path"].split("/"))).read_bytes() for item in row["candidate_files"]}
    initial = Candidate.create(files)
    if initial.candidate_id != row["initial_candidate_id"]:
        raise ValueError("Experiment 013 initial candidate differs")
    phases = {}
    for phase_id in ("A", "B"):
        phase_row = row["phases"][phase_id]
        probe = execution / "probes" / f"{phase_id}.txt"
        phases[phase_id] = PhaseSpec(
            phase_id, (visible / f"PHASE_{phase_id}.txt").read_text(), tuple(phase_row["required"]),
            phase_row["target"], (execution / "checks" / f"{phase_id}.py").read_bytes(),
            phase_row["probe_id"], probe.read_text() if probe.exists() else None,
        )
    return ReceiptFixture(
        fixture_id, row["family"], (visible / "TASK.txt").read_text(), initial, phases,
        (bank / "evaluator_only" / fixture_id / "hidden.py").read_bytes(),
    )


def schedule() -> dict[str, Any]:
    cells = []
    ordinal = 0
    for case_index, fixture_id in enumerate(CASE_IDS):
        for seed_index, seed in enumerate(SEEDS):
            ordinal += 1
            order = list(CONDITIONS if (case_index + seed_index) % 2 == 0 else reversed(CONDITIONS))
            cells.append({"ordinal": ordinal, "fixture_id": fixture_id, "seed": seed, "branch_order": order})
    return {
        "schema_version": "experiment-013-schedule-v1", "cases": list(CASE_IDS), "seeds": list(SEEDS),
        "conditions": list(CONDITIONS), "cells": cells, "attempts_per_branch": 1,
        "retries": 0, "repairs": 0, "rescues": 0, "reasoning_budget_tokens": REASONING_BUDGET,
    }


def _receipt(action: dict[str, Any], result: dict[str, Any], *, sequence: int, handle: str) -> dict[str, Any]:
    body = canonical_json_bytes(result)
    row: dict[str, Any] = {
        "sequence": sequence, "action": action.get("action"), "accepted": bool(result.get("accepted")),
        "result_handle": handle, "result_size_bytes": len(body), "result_sha256": sha256_bytes(body),
    }
    for key in ("path", "handle", "check_id", "probe_id"):
        if key in action:
            row[key] = action[key]
    for key in (
        "candidate_id", "previous_candidate_id", "checked_candidate_id", "file_sha256",
        "requested_start_line", "returned_start_line", "returned_end_line", "next_start_line",
        "complete", "passed", "fork_ready", "submitted_candidate_id",
    ):
        if key in result:
            row[key] = result[key]
    return row


def build_request(
    fixture: ReceiptFixture, *, candidate: Candidate, phase_id: str, history: list[dict[str, Any]],
    observations: list[dict[str, Any]], completed: list[str], reconstructed: bool,
    boundary_binding: dict[str, Any] | None, calls_used: int, stage: str, condition: str,
    receipt_entries: list[dict[str, Any]], externalized_receipt_count: int,
) -> bytes:
    phase = fixture.phases[phase_id]
    actions = ["p0_page", "tree", "search", "read", "patch", "check", "reopen_observation"]
    if stage == "setup":
        actions = ["begin"]
    elif phase_id == "A":
        actions.append("fork_ready")
        if phase.probe_id:
            actions.append("probe")
    else:
        actions.append("submit")
        if condition == "T25-RECEIPTS":
            actions.append("reopen_result")
    contract = {name: TOOL_CONTRACT[name] for name in actions if name in TOOL_CONTRACT}
    contract["p0_page"] = "task-independent readable directory or file-outline page; exact source is not included"
    if "read" in actions:
        contract["read"] = "largest exact current whole-line page that fits the frozen result bound, with non-guessing continuation"
    visible_receipts = receipt_entries[:externalized_receipt_count] if condition == "T25-RECEIPTS" else []
    if len(canonical_json_bytes(visible_receipts)) > MAX_RECEIPT_LEDGER_BYTES:
        raise RuntimeError("active-phase receipt ledger exceeds bound")
    value = {
        "schema_version": "experiment-013-active-phase-receipt-request-v1", "fixture_id": fixture.fixture_id,
        "stage": stage, "phase": phase_id, "task": fixture.task,
        "active_user_authored_step": {"phase": phase_id, "text": phase.text, "host_inference": False},
        "completed_phase_ids": completed, "candidate_id": candidate.candidate_id,
        "current_p0": build_p0_root(candidate),
        "p0_contract": {"task_independent": True, "semantic_ranking": False, "repository_complete": False,
                        "root_complete": True, "scoped_access": "p0_page", "exact_source_required_before_mutation": True},
        "history": history,
        "history_contract": (
            "fresh_context_exact_task_current_world_active_phase_receipts_and_postreset_history"
            if reconstructed and condition == "T25-RECEIPTS"
            else "fresh_context_exact_task_current_world_latest_result_only"
            if reconstructed else "exact_append_only_chronology"
        ),
        "older_chronology_present": not reconstructed,
        "active_phase_receipt_ledger": {
            "schema_version": "exact-active-phase-receipts-v1", "complete_through_sequence": externalized_receipt_count,
            "semantic_ranking": False, "host_sufficiency_judgment": False, "entries": visible_receipts,
        } if condition == "T25-RECEIPTS" else None,
        "observation_directory": observation_directory_v2(observations), "boundary_binding": boundary_binding,
        "resource_state": {"phase_calls_used": calls_used, "phase_call_limit": PHASE_CALL_LIMITS[phase_id],
                           "active_total_ceiling_tokens": T25_TOTAL_CEILING},
        "available_check_ids": (["prefork"] if phase_id == "A" else ["public"]) if stage != "setup" else [],
        "available_probe_ids": [phase.probe_id] if phase.probe_id and phase_id == "A" and stage != "setup" else [],
        "available_actions": actions, "tool_contract": contract, "read_paging_mode": READ_MODE,
    }
    if reconstructed:
        value["reconstruction_notice"] = (
            "Older exact chronology is externally custodied but absent. Mechanical active-phase receipts identify completed actions; "
            "use reopen_result only when the exact result body is needed. Receipts do not assert semantic sufficiency."
            if condition == "T25-RECEIPTS" else
            "Older exact chronology is externally custodied but absent. Use P0 and exact tools to reacquire evidence."
        )
    return canonical_json_bytes(value)


def _binding(
    fixture: ReceiptFixture, *, seed: int, condition: str, candidate: Candidate, completed: list[str],
    history: list[dict[str, Any]], observations: list[dict[str, Any]], last_record_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "experiment-013-boundary-binding-v1", "fixture_id": fixture.fixture_id,
        "seed": seed, "condition": condition, "completed_phase_ids": completed,
        "task_sha256": sha256_bytes(fixture.task.encode()), "candidate_id": candidate.candidate_id,
        "candidate_manifest_sha256": sha256_bytes(canonical_json_bytes([
            {"path": path, "sha256": sha256_bytes(data)} for path, data in candidate.files
        ])),
        "p0_root_sha256": sha256_bytes(canonical_json_bytes(build_p0_root(candidate))),
        "active_history_sha256": sha256_bytes(canonical_json_bytes(history)),
        "observation_directory_sha256": sha256_bytes(canonical_json_bytes(observation_directory_v2(observations))),
        "last_record_sha256": last_record_sha256, "pending_phase": "B" if completed == ["A"] else None,
    }


def _capture_observation(
    action: dict[str, Any], result: dict[str, Any], *, observations: list[dict[str, Any]],
    reopenable: dict[str, bytes], state: SessionState,
) -> None:
    if action.get("action") not in {"probe", "check", "fork_ready"} or not result.get("accepted"):
        return
    body = canonical_json_bytes(result)
    handle = f"OBS-{len(observations) + 1:04d}"
    reopenable[handle] = body
    observations.append({
        "handle": handle, "sequence": len(observations) + 1, "action": action["action"],
        "target": action.get("probe_id", action.get("check_id", "phase_boundary")),
        "candidate_id": result.get("checked_candidate_id", result.get("candidate_id", state.candidate.candidate_id)),
        "size_bytes": len(body), "sha256": sha256_bytes(body),
    })


@dataclass
class PhaseOutcome:
    state: SessionState
    history: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    reopenable: dict[str, bytes]
    binding: dict[str, Any] | None
    disposition: str
    prepared: int
    http: int
    output_dir: Path


def run_phase(
    fixture: ReceiptFixture, *, phase_id: str, seed: int, condition: str, actor: Actor,
    candidate: Candidate, history: list[dict[str, Any]], observations: list[dict[str, Any]],
    reopenable: dict[str, bytes], completed: list[str], prior_binding: dict[str, Any] | None,
    output_dir: Path, force_reconstructed: bool = False,
) -> PhaseOutcome:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    store = ArtifactStore(output_dir)
    log = RecordLog(output_dir / "records.jsonl", f"{fixture.fixture_id}-S{seed}-{condition}-{phase_id}")
    phase = fixture.phases[phase_id]
    state = SessionState(candidate, stage="prefix" if phase_id == "A" else "continuation")
    result_reopenable: dict[str, bytes] = {}
    executor = ToolExecutor(
        state, required_full_reads=phase.required, prefork_checker=phase.checker, public_checker=phase.checker,
        final_target="__none__", probe_id=phase.probe_id, probe_body=phase.probe_body,
        reopenable=reopenable, result_reopenable=result_reopenable,
        read_mode=READ_MODE, hierarchical_p0=True,
    )
    active_history = list(history)
    reconstructed = force_reconstructed
    resets = 1 if force_reconstructed else 0
    receipts: list[dict[str, Any]] = []
    externalized_receipt_count = 0
    log.append("receipt_phase_started", {
        "phase": phase_id, "condition": condition, "candidate_id": candidate.candidate_id,
        "completed_phase_ids": completed, "reconstructed": reconstructed, "prior_binding": prior_binding,
    }, _save_candidate(store, candidate, _snapshot_prefix(candidate)))
    prepared = http = 0
    disposition = "phase_call_budget_exhausted"
    binding = None
    while http < PHASE_CALL_LIMITS[phase_id] and not state.submitted and not state.fork_ready:
        prepared += 1
        stage = "setup" if phase_id == "A" and http == 0 else state.stage
        request = build_request(
            fixture, candidate=state.candidate, phase_id=phase_id, history=active_history,
            observations=observations, completed=completed, reconstructed=reconstructed,
            boundary_binding=prior_binding, calls_used=http, stage=stage, condition=condition,
            receipt_entries=receipts, externalized_receipt_count=externalized_receipt_count,
        )
        try:
            action, result, _ = _execute_call(
                actor=actor, request=request, stage=stage, probe_id=phase.probe_id,
                call_id=f"{fixture.fixture_id}-S{seed}-{condition}-{phase_id}-P{prepared:02d}",
                active_total_ceiling=T25_TOTAL_CEILING if condition in CONDITIONS else PHYSICAL_CONTEXT,
                executor=executor, store=store, log=log,
                artifact_prefix=f"transcript/{prepared:03d}",
            )
        except CapacityStopped as exc:
            if phase_id == "A" or not active_history or resets >= 4:
                disposition = "capacity_stopped_before_http"
                atomic_write(output_dir / "CAPACITY_STOP.json", canonical_json_bytes(exc.admission))
                break
            reconstructed = True
            resets += 1
            prior_binding = _binding(
                fixture, seed=seed, condition=condition, candidate=state.candidate, completed=completed,
                history=active_history, observations=observations, last_record_sha256=log.previous or "",
            )
            if condition == "T25-RECEIPTS":
                externalized_receipt_count = len(receipts)
                active_history = []
            else:
                active_history = [active_history[-1]]
            log.append("runtime_reconstruction_applied", {
                "phase": phase_id, "denied_prepared_invocation": prepared, "candidate_id": state.candidate.candidate_id,
                "boundary_binding": prior_binding, "externalized_receipt_count": externalized_receipt_count,
            }, [])
            continue
        http += 1
        pair = {"response": action, "result": result}
        active_history.append(pair)
        if phase_id == "B":
            body = canonical_json_bytes(result)
            handle = f"RES-{len(receipts) + 1:04d}"
            result_reopenable[handle] = body
            receipts.append(_receipt(action, result, sequence=len(receipts) + 1, handle=handle))
        _capture_observation(action, result, observations=observations, reopenable=reopenable, state=state)
    else:
        if state.submitted:
            disposition = "submitted"
        elif state.fork_ready:
            disposition = "phase_complete"
    if state.fork_ready:
        binding = _binding(
            fixture, seed=seed, condition=condition, candidate=state.candidate, completed=[*completed, phase_id],
            history=active_history, observations=observations, last_record_sha256=log.previous or "",
        )
    stopped = log.append("receipt_phase_stopped", {
        "phase": phase_id, "condition": condition, "disposition": disposition,
        "prepared_invocations": prepared, "http_completion_calls": http, "runtime_resets": resets,
        "candidate_id": state.candidate.candidate_id, "submitted": state.submitted,
        "public_check_passed": state.public_check_passed, "boundary_binding": binding,
        "receipt_count": len(receipts), "externalized_receipt_count": externalized_receipt_count,
    }, [])
    summary = {
        "schema_version": "experiment-013-phase-summary-v1", "fixture_id": fixture.fixture_id,
        "phase": phase_id, "condition": condition, "seed": seed, "disposition": disposition,
        "prepared_invocations": prepared, "http_completion_calls": http, "runtime_resets": resets,
        "candidate_id": state.candidate.candidate_id, "submitted": state.submitted,
        "public_check_passed": state.public_check_passed, "boundary_binding": binding,
        "receipt_count": len(receipts), "externalized_receipt_count": externalized_receipt_count,
        "active_history_sha256": sha256_bytes(canonical_json_bytes(active_history)),
        "last_record_sha256": stopped["record_sha256"],
    }
    atomic_write(output_dir / "SUMMARY.json", canonical_json_bytes(summary))
    return PhaseOutcome(state, active_history, observations, reopenable, binding, disposition, prepared, http, output_dir)


def run_shared_prefix(fixture: ReceiptFixture, *, seed: int, actor: Actor, output_dir: Path) -> PhaseOutcome:
    return run_phase(
        fixture, phase_id="A", seed=seed, condition="SHARED", actor=actor, candidate=fixture.initial,
        history=[], observations=[], reopenable={}, completed=[], prior_binding=None, output_dir=output_dir,
    )


def run_branch(
    fixture: ReceiptFixture, prefix: PhaseOutcome, *, seed: int, condition: str, actor: Actor, output_dir: Path,
) -> dict[str, Any]:
    if condition not in CONDITIONS:
        raise ValueError("invalid Experiment 013 condition")
    full_history = list(prefix.history)
    prospective = build_request(
        fixture, candidate=prefix.state.candidate, phase_id="B", history=full_history,
        observations=prefix.observations, completed=["A"], reconstructed=False,
        boundary_binding=prefix.binding, calls_used=0, stage="continuation", condition=condition,
        receipt_entries=[], externalized_receipt_count=0,
    )
    own = guard(actor.profile, prospective, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
    physical = guard(actor.profile, prospective, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True)
    if own["authorized"] or not physical["authorized"]:
        raise RuntimeError("Experiment 013 first boundary is not authentically T25-only")
    atomic_write(output_dir / "FIRST_BOUNDARY_CAPACITY.json", canonical_json_bytes({
        "schema_version": "experiment-013-first-boundary-capacity-v1", "t25": own, "physical": physical,
    }))
    outcome = run_phase(
        fixture, phase_id="B", seed=seed, condition=condition, actor=actor,
        candidate=prefix.state.candidate, history=[full_history[-1]], observations=[dict(row) for row in prefix.observations],
        reopenable=dict(prefix.reopenable), completed=["A"], prior_binding=prefix.binding,
        output_dir=output_dir / "phase-b", force_reconstructed=True,
    )
    verify_run(outcome.output_dir)
    result = {
        "schema_version": "experiment-013-branch-summary-v1", "fixture_id": fixture.fixture_id,
        "condition": condition, "seed": seed, "phase": load_json_strict((outcome.output_dir / "SUMMARY.json").read_bytes()),
        "prepared_invocations": outcome.prepared, "http_completion_calls": outcome.http,
        "candidate_id": outcome.state.candidate.candidate_id, "submitted": outcome.state.submitted,
    }
    atomic_write(output_dir / "SUMMARY.json", canonical_json_bytes(result))
    return result


def hidden_grade(fixture: ReceiptFixture, candidate: Candidate) -> dict[str, Any]:
    return run_checker(candidate, fixture.hidden_checker)


def construct_package(target: Path, *, bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True)
    cells = []
    for row in schedule()["cells"]:
        fixture = load_fixture(bank, row["fixture_id"])
        request = build_request(
            fixture, candidate=fixture.initial, phase_id="A", history=[], observations=[], completed=[],
            reconstructed=False, boundary_binding=None, calls_used=0, stage="setup", condition="SHARED",
            receipt_entries=[], externalized_receipt_count=0,
        )
        endpoint = endpoint_request(
            profile, request, stage="setup", probe_id=fixture.phases["A"].probe_id, seed=row["seed"],
            reasoning_enabled=True, read_mode=READ_MODE, hierarchical_p0=True,
        )
        admission = guard(profile, request, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True)
        rendered = render_reasoning_prompt(request, enabled=True)
        cell = target / f"cell-{row['ordinal']:02d}"
        atomic_write(cell / "initial-coding-request.json", request)
        atomic_write(cell / "initial-endpoint-request.json", endpoint)
        atomic_write(cell / "initial-rendered-prompt.txt", rendered)
        cells.append({
            **row, "expected_call_id": f"{row['fixture_id']}-S{row['seed']}-SHARED-A-P01",
            "coding_request_sha256": sha256_bytes(request), "endpoint_request_sha256": sha256_bytes(endpoint),
            "rendered_prompt_sha256": sha256_bytes(rendered), "initial_admission": admission,
        })
    files = _inventory(target, {"PACKAGE_MANIFEST.json"})
    manifest = {
        "schema_version": PACKAGE_SCHEMA, "bank_id": verify_bank(bank)["bank_id"],
        "schedule_sha256": sha256_bytes(canonical_json_bytes(schedule())), "cells": cells,
        "hierarchical_p0": True, "read_mode": READ_MODE, "reasoning_budget_tokens": REASONING_BUDGET,
        "result_reopen_condition": "T25-RECEIPTS", "evaluator_bytes_present": False, "files": files,
        "package_id": "E13PKG-" + sha256_bytes(canonical_json_bytes(files)),
    }
    atomic_write(target / "PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_package(target: Path, *, bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    observed = load_json_strict((target / "PACKAGE_MANIFEST.json").read_bytes())
    if observed["files"] != _inventory(target, {"PACKAGE_MANIFEST.json"}):
        raise ValueError("Experiment 013 package differs")
    with tempfile.TemporaryDirectory(prefix="e13-package-") as raw:
        rebuilt = construct_package(Path(raw) / "package", bank=bank, profile=profile)
        if canonical_json_bytes(rebuilt) != canonical_json_bytes(observed):
            raise ValueError("Experiment 013 package reconstruction differs")
    return {"verified": True, "package_id": observed["package_id"], "file_count": len(observed["files"])}


def expected_authorization(experiment: Path) -> dict[str, Any]:
    bank = load_json_strict((experiment / "fresh_bank" / "BANK_MANIFEST.json").read_bytes())
    package = load_json_strict((experiment / "execution_package" / "PACKAGE_MANIFEST.json").read_bytes())
    closure = load_json_strict((experiment / "EXECUTABLE_CLOSURE.json").read_bytes())
    profile = load_json_strict((experiment / "RUNTIME_PROFILE.json").read_bytes())
    return {
        "schema_version": "experiment-013-owner-authorization-v1",
        "status": "owner_authorized_exact_active_phase_receipt_execution",
        "owner_statement": "Proceed",
        "bank_id": bank["bank_id"], "bank_manifest_sha256": sha256_file(experiment / "fresh_bank" / "BANK_MANIFEST.json"),
        "package_id": package["package_id"], "package_manifest_sha256": sha256_file(experiment / "execution_package" / "PACKAGE_MANIFEST.json"),
        "closure_manifest_sha256": sha256_file(experiment / "EXECUTABLE_CLOSURE.json"),
        "closure_aggregate_sha256": closure["aggregate_sha256"], "schedule_sha256": sha256_file(experiment / "SCHEDULE.json"),
        "runtime_profile_sha256": sha256_file(experiment / "RUNTIME_PROFILE.json"), "actor_sha256": profile["model_sha256"],
        "conditions": list(CONDITIONS), "cases": list(CASE_IDS), "seeds": list(SEEDS),
        "shared_prefixes": 4, "measured_branches": 8, "attempts_per_branch": 1,
        "retries": 0, "repairs": 0, "rescues": 0, "maximum_http_completion_calls": MAXIMUM_HTTP_COMPLETION_CALLS,
        "output_root": OUTPUT_ROOT, "port": PORT, "read_mode": READ_MODE, "hierarchical_p0": True,
        "reasoning_budget_tokens": REASONING_BUDGET, "response_seal_before_evaluator_access": True,
        "automatic_successor": False, "only_causal_difference": "active_phase_receipt_ledger_and_result_reopen",
        "no_summaries_relationships_embeddings_ranking_suppression_or_host_semantic_selection": True,
    }


def validate_authorization(experiment: Path) -> dict[str, Any]:
    observed = load_json_strict((experiment / "MEASURED_AUTHORIZATION.json").read_bytes())
    expected = expected_authorization(experiment)
    if canonical_json_bytes(observed) != canonical_json_bytes(expected):
        raise ValueError("Experiment 013 authorization differs")
    return {"verified": True, "authorization_sha256": sha256_file(experiment / "MEASURED_AUTHORIZATION.json")}
