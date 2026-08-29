from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .candidate import Candidate
from .custody import ArtifactStore, RecordLog
from .fixture import Fixture
from .hierarchical_p0 import build_p0_root, p0_page
from .isolation import run_checker
from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from .request import TOOL_CONTRACT, observation_directory_v2, render_reasoning_prompt
from .runner import Actor, _execute_call, _save_candidate, _snapshot_prefix, verify_run
from .runtime import PHYSICAL_CONTEXT, REASONING_BUDGET, T25_TOTAL_CEILING, CapacityStopped, RuntimeProfile, endpoint_request, guard
from .tools import SessionState, ToolExecutor


EXPERIMENT_ID = "012_large_world_recurrent_continuity"
CASE_IDS = ("E12-SOURCE-ORBIT", "E12-OBS-COMPASS")
SEEDS = (173205, 223607)
CONDITIONS = ("C50", "T25")
PHASE_IDS = ("A", "B", "C", "D")
PHASE_CALL_LIMITS = {"A": 12, "B": 14, "C": 14, "D": 10}
READ_MODE = "maximal_bounded_page"
PORT = 18115
OUTPUT_ROOT = r"C:\e12-primary"
MAXIMUM_HTTP_COMPLETION_CALLS = 260
BANK_SCHEMA = "experiment-012-large-world-bank-v1"
PACKAGE_SCHEMA = "experiment-012-large-world-package-v1"


def _generated_module(domain: str, index: int, *, rows: int = 176) -> bytes:
    symbol = f"{domain.replace('_', '')}_{index:03d}_records"
    lines = [f'"""Exact task-independent {domain} custody module {index:03d}."""\n', "RECORDS = (\n"]
    for row in range(rows):
        digest = sha256_bytes(f"e12:{domain}:{index:03d}:{row:04d}".encode())[:28]
        lines.append(f'    ("{domain}-{index:03d}-{row:04d}", "{digest}", "retain-{(row * 41 + index * 17) % 1009:04d}"),\n')
    lines.extend([
        ")\n\n",
        f"def {symbol}() -> int:\n",
        "    return len(RECORDS)\n",
    ])
    return "".join(lines).encode()


def _large_background(namespace: str) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    domains = (
        "records_a", "records_b", "records_c", "adapters", "analytics", "backfill", "billing",
        "catalog", "connectors", "dispatch", "events", "exports", "imports", "telemetry",
    )
    for domain_index, domain in enumerate(domains):
        for index in range(11):
            files[f"{domain}/module_{index:03d}.py"] = _generated_module(f"{namespace}_{domain}", domain_index * 11 + index)
    return files


def _source_case() -> dict[str, Any]:
    files = _large_background("orbit")
    files.update({
        "workflow/progress.py": b'PHASES = ("A", "B", "C", "D")\n\n\ndef completed_phases() -> int:\n    return 0\n',
        "policies/current.py": b'POLICY_PREFIX = "orbit-"\n\n\ndef active_policy_prefix() -> str:\n    """Return the exact current policy prefix."""\n    return POLICY_PREFIX\n',
        "api/name.py": b'def normalize_name(value: str) -> str:\n    return value.strip().casefold()\n',
        "api/footer.py": b'def normalize_footer(value: str) -> str:\n    return value.strip().upper()\n',
        "api/render.py": b'from api.name import normalize_name\nfrom api.footer import normalize_footer\n\n\ndef render_identity(name: str, footer: str) -> str:\n    return f"{normalize_name(name)}|{normalize_footer(footer)}"\n',
        "runtime/state.py": b'def runtime_state() -> str:\n    return "stable"\n',
    })
    phase_a = (
        "Phase A: read `records_a/module_000.py` and `records_a/module_001.py` completely. Then repair "
        "`workflow/progress.py` so `completed_phases()` returns 1, run check `prefork`, and call `fork_ready`."
    )
    phase_b = (
        "Phase B: locate and read the exact current source definition of `active_policy_prefix()` using readable P0 orientation. "
        "Repair `api/name.py` so normalized names are prefixed by that exact current value while preserving trimming and case folding. "
        "Read `records_b/module_000.py` and `records_b/module_001.py` completely, run check `public`, and call `fork_ready`."
    )
    phase_c = (
        "Phase C: update the exact source governing `active_policy_prefix()` so the authorized current value becomes `zenith-`. "
        "Do not rewrite the already completed Phase-B name behavior. Read `records_c/module_000.py` and `records_c/module_001.py` "
        "completely, run check `public`, and call `fork_ready`."
    )
    phase_d = (
        "Phase D: reacquire the exact current source definition of `active_policy_prefix()` after the Phase-C mutation. "
        "Repair `api/footer.py` so normalized footers are prefixed by that current value while preserving trimming and uppercasing. "
        "Run check `public` and submit."
    )
    return {
        "fixture_id": CASE_IDS[0], "family": "large_world_evolving_source", "files": files,
        "task": "Perform the following four phases in order. " + " ".join((phase_a, phase_b, phase_c, phase_d)),
        "phases": {
            "A": {"text": phase_a, "required": ["records_a/module_000.py", "records_a/module_001.py"], "target": "workflow/progress.py", "probe_id": None, "probe_body": None,
                  "check": b"from workflow.progress import completed_phases\nassert completed_phases() == 1\nprint('phase A passed')\n"},
            "B": {"text": phase_b, "required": ["records_b/module_000.py", "records_b/module_001.py"], "target": "api/name.py", "probe_id": None, "probe_body": None,
                  "check": b"from api.name import normalize_name\nfrom policies.current import active_policy_prefix\nassert active_policy_prefix() == 'orbit-'\nassert normalize_name(' Blue ') == 'orbit-blue'\nprint('phase B passed')\n"},
            "C": {"text": phase_c, "required": ["records_c/module_000.py", "records_c/module_001.py"], "target": "policies/current.py", "probe_id": None, "probe_body": None,
                  "check": b"from api.name import normalize_name\nfrom policies.current import active_policy_prefix\nassert normalize_name(' Blue ') == 'orbit-blue'\nassert active_policy_prefix() == 'zenith-'\nprint('phase C passed')\n"},
            "D": {"text": phase_d, "required": [], "target": "api/footer.py", "probe_id": None, "probe_body": None,
                  "check": b"from api.name import normalize_name\nfrom api.footer import normalize_footer\nfrom api.render import render_identity\nfrom policies.current import active_policy_prefix\nassert active_policy_prefix() == 'zenith-'\nassert normalize_name(' Blue ') == 'orbit-blue'\nassert normalize_footer(' x7 ') == 'zenith-X7'\nassert render_identity(' MiXeD ', ' q2 ') == 'orbit-mixed|zenith-Q2'\nprint('public passed')\n"},
        },
        "patches": [
            {"path": "workflow/progress.py", "old": "    return 0", "new": "    return 1"},
            {"path": "api/name.py", "old": "    return value.strip().casefold()", "new": '    return "orbit-" + value.strip().casefold()'},
            {"path": "policies/current.py", "old": 'POLICY_PREFIX = "orbit-"', "new": 'POLICY_PREFIX = "zenith-"'},
            {"path": "api/footer.py", "old": "    return value.strip().upper()", "new": '    return "zenith-" + value.strip().upper()'},
        ],
        "hidden": b"from api.name import normalize_name\nfrom api.footer import normalize_footer\nfrom api.render import render_identity\nfrom policies.current import active_policy_prefix\nassert active_policy_prefix() == 'zenith-'\nassert normalize_name(' A ') == 'orbit-a'\nassert normalize_footer(' b9 ') == 'zenith-B9'\nassert render_identity(' MiXeD ', ' q2 ') == 'orbit-mixed|zenith-Q2'\nprint('hidden passed')\n",
    }


def _observation_case() -> dict[str, Any]:
    files = _large_background("compass")
    files.update({
        "workflow/progress.py": b'PHASES = ("A", "B", "C", "D")\n\n\ndef completed_phases() -> int:\n    return 0\n',
        "codec/label.py": b'def codec_label(value: str) -> str:\n    return value.strip().upper()\n',
        "codec/header.py": b'def codec_header(value: str) -> str:\n    return value.strip().casefold()\n',
        "codec/footer.py": b'def codec_footer(value: str) -> str:\n    return value.strip().upper()\n',
        "codec/wire.py": b'from codec.label import codec_label\nfrom codec.header import codec_header\nfrom codec.footer import codec_footer\n\n\ndef encode_wire(value: str) -> bytes:\n    return f"{codec_label(value)}|{codec_header(value)}|{codec_footer(value)}".encode("ascii")\n',
        "runtime/state.py": b'def runtime_state() -> str:\n    return "stable"\n',
    })
    phase_a = (
        "Phase A: read `records_a/module_000.py` and `records_a/module_001.py` completely. Repair `workflow/progress.py` "
        "so `completed_phases()` returns 1, run check `prefork`, call probe `compatibility`, and call `fork_ready`."
    )
    phase_b = (
        "Phase B: use candidate bindings to select and reopen the exact current `compatibility` observation. Repair `codec/label.py` "
        "so it prepends that exact marker while preserving trimming and uppercasing. Read `records_b/module_000.py` and "
        "`records_b/module_001.py` completely, run check `public`, call probe `compatibility` again, and call `fork_ready`."
    )
    phase_c = (
        "Phase C: select and reopen the exact `compatibility` observation valid for the current candidate; older exact observations remain "
        "available but stale. Repair `codec/header.py` so it prepends the current marker while preserving trimming and case folding. "
        "Read `records_c/module_000.py` and `records_c/module_001.py` completely, run check `public`, call probe `compatibility`, and call `fork_ready`."
    )
    phase_d = (
        "Phase D: select and reopen the exact `compatibility` observation valid for the current candidate among all listed observations. "
        "Repair `codec/footer.py` so it prepends that marker while preserving trimming and uppercasing. Run check `public` and submit."
    )
    return {
        "fixture_id": CASE_IDS[1], "family": "large_world_dense_observation_validity", "files": files,
        "task": "Perform the following four phases in order. " + " ".join((phase_a, phase_b, phase_c, phase_d)),
        "phases": {
            "A": {"text": phase_a, "required": ["records_a/module_000.py", "records_a/module_001.py"], "target": "workflow/progress.py", "probe_id": "compatibility", "probe_body": "compatibility observation\nmarker=A3::\nvalidity=current_candidate_only\n",
                  "check": b"from workflow.progress import completed_phases\nassert completed_phases() == 1\nprint('phase A passed')\n"},
            "B": {"text": phase_b, "required": ["records_b/module_000.py", "records_b/module_001.py"], "target": "codec/label.py", "probe_id": "compatibility", "probe_body": "compatibility observation\nmarker=B6::\nvalidity=current_candidate_only\n",
                  "check": b"from codec.label import codec_label\nassert codec_label(' blue ') == 'A3::BLUE'\nprint('phase B passed')\n"},
            "C": {"text": phase_c, "required": ["records_c/module_000.py", "records_c/module_001.py"], "target": "codec/header.py", "probe_id": "compatibility", "probe_body": "compatibility observation\nmarker=C9::\nvalidity=current_candidate_only\n",
                  "check": b"from codec.label import codec_label\nfrom codec.header import codec_header\nassert codec_label(' blue ') == 'A3::BLUE'\nassert codec_header(' X ') == 'B6::x'\nprint('phase C passed')\n"},
            "D": {"text": phase_d, "required": [], "target": "codec/footer.py", "probe_id": None, "probe_body": None,
                  "check": b"from codec.label import codec_label\nfrom codec.header import codec_header\nfrom codec.footer import codec_footer\nfrom codec.wire import encode_wire\nassert codec_label(' blue ') == 'A3::BLUE'\nassert codec_header(' X ') == 'B6::x'\nassert codec_footer(' q7 ') == 'C9::Q7'\nassert encode_wire(' Ab ') == b'A3::AB|B6::ab|C9::AB'\nprint('public passed')\n"},
        },
        "patches": [
            {"path": "workflow/progress.py", "old": "    return 0", "new": "    return 1"},
            {"path": "codec/label.py", "old": "    return value.strip().upper()", "new": '    return "A3::" + value.strip().upper()'},
            {"path": "codec/header.py", "old": "    return value.strip().casefold()", "new": '    return "B6::" + value.strip().casefold()'},
            {"path": "codec/footer.py", "old": "    return value.strip().upper()", "new": '    return "C9::" + value.strip().upper()'},
        ],
        "hidden": b"from codec.label import codec_label\nfrom codec.header import codec_header\nfrom codec.footer import codec_footer\nfrom codec.wire import encode_wire\nassert codec_label(' a ') == 'A3::A'\nassert codec_header(' B ') == 'B6::b'\nassert codec_footer(' c ') == 'C9::C'\nassert encode_wire(' Ab ') == b'A3::AB|B6::ab|C9::AB'\nprint('hidden passed')\n",
    }


def case_definitions() -> tuple[dict[str, Any], ...]:
    return (_source_case(), _observation_case())


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
class LargeWorldFixture:
    fixture_id: str
    family: str
    task: str
    initial: Candidate
    phases: dict[str, PhaseSpec]
    hidden_checker: bytes


def _candidate_after(case: dict[str, Any], count: int) -> Candidate:
    candidate = Candidate.create(case["files"])
    for row in case["patches"][:count]:
        candidate, _ = candidate.patch(
            path=row["path"], old=row["old"], new=row["new"], expected_candidate_id=candidate.candidate_id,
            expected_file_sha256=candidate.file_sha256(row["path"]),
        )
    return candidate


def _inventory(root: Path, excluded: set[str]) -> list[dict[str, Any]]:
    paths = [p for p in root.rglob("*") if p.is_file() and p.relative_to(root).as_posix() not in excluded]
    paths.sort(key=lambda p: p.relative_to(root).as_posix())
    return [
        {"path": p.relative_to(root).as_posix(), "size_bytes": p.stat().st_size, "sha256": sha256_file(p)}
        for p in paths
    ]


def construct_bank(target: Path) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    files: dict[str, bytes] = {}
    definitions = case_definitions()
    for case in definitions:
        initial = Candidate.create(case["files"])
        successors = [_candidate_after(case, count) for count in range(1, 5)]
        visible = f"model_visible/{case['fixture_id']}"
        candidate_rows = []
        for path, data in initial.files:
            files[f"{visible}/candidate/{path}"] = data
            candidate_rows.append({"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)})
        files[f"{visible}/TASK.txt"] = case["task"].encode()
        for phase_id in PHASE_IDS:
            files[f"{visible}/PHASE_{phase_id}.txt"] = case["phases"][phase_id]["text"].encode()
            files[f"execution_only/{case['fixture_id']}/checks/{phase_id}.py"] = case["phases"][phase_id]["check"]
            body = case["phases"][phase_id]["probe_body"]
            if body is not None:
                files[f"execution_only/{case['fixture_id']}/probes/{phase_id}.txt"] = body.encode()
        files[f"execution_only/{case['fixture_id']}/FIXTURE.json"] = canonical_json_bytes({
            "schema_version": "experiment-012-fixture-v1", "fixture_id": case["fixture_id"], "family": case["family"],
            "initial_candidate_id": initial.candidate_id, "candidate_files": candidate_rows,
            "phase_candidate_ids": {phase: successors[index].candidate_id for index, phase in enumerate(PHASE_IDS)},
            "phases": {phase: {
                "required": case["phases"][phase]["required"], "target": case["phases"][phase]["target"],
                "probe_id": case["phases"][phase]["probe_id"], "probe_body_present": case["phases"][phase]["probe_body"] is not None,
            } for phase in PHASE_IDS},
        })
        evaluator = f"evaluator_only/{case['fixture_id']}"
        files[f"{evaluator}/hidden.py"] = case["hidden"]
        for path, data in successors[-1].files:
            files[f"{evaluator}/known_good/{path}"] = data
        files[f"{evaluator}/TRUTH.json"] = canonical_json_bytes({
            "schema_version": "experiment-012-truth-v1", "fixture_id": case["fixture_id"],
            "known_good_candidate_id": successors[-1].candidate_id, "patches": case["patches"],
        })
    for relative, data in files.items():
        atomic_write(target / Path(*relative.split("/")), data)
    inventory = [{"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)} for path, data in sorted(files.items())]
    manifest = {
        "schema_version": BANK_SCHEMA, "bank_id": "E12BANK-" + sha256_bytes(canonical_json_bytes(inventory)),
        "case_ids": list(CASE_IDS), "seeds": list(SEEDS), "conditions": list(CONDITIONS),
        "fresh_before_actor_exposure": True, "evaluator_separate": True, "files": inventory,
    }
    atomic_write(target / "BANK_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_bank(target: Path) -> dict[str, Any]:
    manifest = load_json_strict((target / "BANK_MANIFEST.json").read_bytes())
    files = _inventory(target, {"BANK_MANIFEST.json"})
    if manifest["schema_version"] != BANK_SCHEMA or manifest["files"] != files:
        raise ValueError("Experiment 012 bank differs")
    if manifest["bank_id"] != "E12BANK-" + sha256_bytes(canonical_json_bytes(files)):
        raise ValueError("Experiment 012 bank identity differs")
    return {"verified": True, "bank_id": manifest["bank_id"], "file_count": len(files)}


def load_fixture(bank: Path, fixture_id: str) -> LargeWorldFixture:
    visible = bank / "model_visible" / fixture_id
    execution = bank / "execution_only" / fixture_id
    row = load_json_strict((execution / "FIXTURE.json").read_bytes())
    files = {item["path"]: (visible / "candidate" / Path(*item["path"].split("/"))).read_bytes() for item in row["candidate_files"]}
    initial = Candidate.create(files)
    phases: dict[str, PhaseSpec] = {}
    for phase_id in PHASE_IDS:
        phase_row = row["phases"][phase_id]
        probe_path = execution / "probes" / f"{phase_id}.txt"
        phases[phase_id] = PhaseSpec(
            phase_id, (visible / f"PHASE_{phase_id}.txt").read_text(), tuple(phase_row["required"]),
            phase_row["target"], (execution / "checks" / f"{phase_id}.py").read_bytes(), phase_row["probe_id"],
            probe_path.read_text() if probe_path.exists() else None,
        )
    return LargeWorldFixture(
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
        "schema_version": "experiment-012-schedule-v1", "cases": list(CASE_IDS), "seeds": list(SEEDS),
        "conditions": list(CONDITIONS), "cells": cells, "attempts_per_branch": 1,
        "retries": 0, "repairs": 0, "rescues": 0, "reasoning_budget_tokens": REASONING_BUDGET,
    }


def build_request(
    fixture: LargeWorldFixture, *, candidate: Candidate, phase_id: str, history: list[dict[str, Any]],
    observations: list[dict[str, Any]], completed: list[str], reconstructed: bool,
    boundary_binding: dict[str, Any] | None, calls_used: int, stage: str,
) -> bytes:
    phase = fixture.phases[phase_id]
    actions = ["p0_page", "tree", "search", "read", "patch", "check", "reopen_observation"]
    if stage == "setup":
        actions = ["begin"]
    elif phase_id == "D":
        actions.append("submit")
    else:
        actions.append("fork_ready")
        if phase.probe_id:
            actions.append("probe")
    contract = {name: TOOL_CONTRACT[name] for name in actions if name in TOOL_CONTRACT}
    contract["p0_page"] = "task-independent readable directory or file-outline page; exact source is not included"
    if "read" in actions:
        contract["read"] = "largest exact current whole-line page that fits the frozen result bound, with non-guessing continuation"
    value = {
        "schema_version": "experiment-012-large-world-coding-request-v1", "fixture_id": fixture.fixture_id,
        "stage": stage, "phase": phase_id, "task": fixture.task,
        "active_user_authored_step": {"phase": phase_id, "text": phase.text, "host_inference": False},
        "completed_phase_ids": completed, "candidate_id": candidate.candidate_id,
        "current_p0": build_p0_root(candidate),
        "p0_contract": {"task_independent": True, "semantic_ranking": False, "repository_complete": False,
                        "root_complete": True, "scoped_access": "p0_page", "exact_source_required_before_mutation": True},
        "history": history,
        "history_contract": "fresh_context_exact_task_current_world_latest_boundary_result_only" if reconstructed else "exact_append_only_chronology",
        "older_chronology_present": not reconstructed,
        "observation_directory": observation_directory_v2(observations),
        "boundary_binding": boundary_binding,
        "resource_state": {"phase_calls_used": calls_used, "phase_call_limit": PHASE_CALL_LIMITS[phase_id],
                           "active_total_ceiling_tokens": T25_TOTAL_CEILING if reconstructed else PHYSICAL_CONTEXT},
        "available_check_ids": (["prefork"] if phase_id == "A" else ["public"]) if stage != "setup" else [],
        "available_probe_ids": [phase.probe_id] if phase.probe_id and phase_id != "D" and stage != "setup" else [],
        "available_actions": actions, "tool_contract": contract, "read_paging_mode": READ_MODE,
    }
    if reconstructed:
        value["reconstruction_notice"] = (
            "Older exact chronology is externally custodied but absent. Use the current hierarchical P0, exact source tools, "
            "and identity-only observation directory to reacquire governing evidence."
        )
    return canonical_json_bytes(value)


def boundary_binding(
    fixture: LargeWorldFixture, *, seed: int, condition: str, candidate: Candidate, completed: list[str],
    history: list[dict[str, Any]], observations: list[dict[str, Any]], last_record_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "experiment-012-boundary-binding-v1", "fixture_id": fixture.fixture_id,
        "seed": seed, "condition": condition, "completed_phase_ids": completed,
        "task_sha256": sha256_bytes(fixture.task.encode()), "candidate_id": candidate.candidate_id,
        "candidate_manifest_sha256": sha256_bytes(canonical_json_bytes([
            {"path": path, "sha256": sha256_bytes(data)} for path, data in candidate.files
        ])),
        "p0_root_sha256": sha256_bytes(canonical_json_bytes(build_p0_root(candidate))),
        "active_history_sha256": sha256_bytes(canonical_json_bytes(history)),
        "observation_directory_sha256": sha256_bytes(canonical_json_bytes(observation_directory_v2(observations))),
        "last_record_sha256": last_record_sha256,
        "pending_phase": PHASE_IDS[len(completed)] if len(completed) < len(PHASE_IDS) else None,
    }


def _capture(
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
    fixture: LargeWorldFixture, *, phase_id: str, seed: int, condition: str, actor: Actor,
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
    terminal = phase_id == "D"
    state = SessionState(candidate, stage="continuation" if terminal else ("prefix" if phase_id == "A" else "recurrent"))
    executor = ToolExecutor(
        state, required_full_reads=phase.required, prefork_checker=phase.checker, public_checker=phase.checker,
        final_target="__future_phase_target__", probe_id=phase.probe_id, probe_body=phase.probe_body,
        reopenable=reopenable, read_mode=READ_MODE, hierarchical_p0=True,
    )
    active_history = list(history)
    reconstructed = force_reconstructed
    resets = 1 if force_reconstructed else 0
    log.append("large_world_phase_started", {
        "phase": phase_id, "condition": condition, "candidate_id": candidate.candidate_id,
        "completed_phase_ids": completed, "reconstructed": reconstructed, "prior_binding": prior_binding,
    }, _save_candidate(store, candidate, _snapshot_prefix(candidate)))
    prepared = 0
    http = 0
    disposition = "phase_call_budget_exhausted"
    binding = None
    while http < PHASE_CALL_LIMITS[phase_id] and not state.submitted and not state.fork_ready:
        prepared += 1
        stage = "setup" if phase_id == "A" and http == 0 else state.stage
        request = build_request(
            fixture, candidate=state.candidate, phase_id=phase_id, history=active_history,
            observations=observations, completed=completed, reconstructed=reconstructed,
            boundary_binding=prior_binding, calls_used=http, stage=stage,
        )
        try:
            action, result, _ = _execute_call(
                actor=actor, request=request, stage=stage, probe_id=phase.probe_id,
                call_id=f"{fixture.fixture_id}-S{seed}-{condition}-{phase_id}-P{prepared:02d}",
                active_total_ceiling=T25_TOTAL_CEILING if condition == "T25" else PHYSICAL_CONTEXT,
                executor=executor, store=store, log=log, artifact_prefix=f"transcript/{prepared:03d}",
            )
        except CapacityStopped as exc:
            if condition != "T25" or not active_history or resets >= 4:
                disposition = "capacity_stopped_before_http"
                atomic_write(output_dir / "CAPACITY_STOP.json", canonical_json_bytes(exc.admission))
                break
            reconstructed = True
            resets += 1
            prior_binding = boundary_binding(
                fixture, seed=seed, condition=condition, candidate=state.candidate, completed=completed,
                history=active_history, observations=observations, last_record_sha256=log.previous or "",
            )
            active_history = [active_history[-1]]
            log.append("runtime_reconstruction_applied", {
                "phase": phase_id, "denied_prepared_invocation": prepared, "candidate_id": state.candidate.candidate_id,
                "boundary_binding": prior_binding,
            }, [])
            continue
        http += 1
        pair = {"response": action, "result": result}
        active_history.append(pair)
        _capture(action, result, observations=observations, reopenable=reopenable, state=state)
    else:
        if state.submitted:
            disposition = "submitted"
        elif state.fork_ready:
            disposition = "phase_complete"
    if state.fork_ready:
        completed_now = [*completed, phase_id]
        binding = boundary_binding(
            fixture, seed=seed, condition=condition, candidate=state.candidate, completed=completed_now,
            history=active_history, observations=observations, last_record_sha256=log.previous or "",
        )
    stopped = log.append("large_world_phase_stopped", {
        "phase": phase_id, "condition": condition, "disposition": disposition,
        "prepared_invocations": prepared, "http_completion_calls": http, "runtime_resets": resets,
        "candidate_id": state.candidate.candidate_id, "submitted": state.submitted,
        "public_check_passed": state.public_check_passed, "boundary_binding": binding,
    }, [])
    summary = {
        "schema_version": "experiment-012-phase-summary-v1", "fixture_id": fixture.fixture_id,
        "phase": phase_id, "condition": condition, "seed": seed, "disposition": disposition,
        "prepared_invocations": prepared, "http_completion_calls": http, "runtime_resets": resets,
        "candidate_id": state.candidate.candidate_id, "submitted": state.submitted,
        "public_check_passed": state.public_check_passed, "boundary_binding": binding,
        "active_history_sha256": sha256_bytes(canonical_json_bytes(active_history)),
        "last_record_sha256": stopped["record_sha256"],
    }
    atomic_write(output_dir / "SUMMARY.json", canonical_json_bytes(summary))
    return PhaseOutcome(state, active_history, observations, reopenable, binding, disposition, prepared, http, output_dir)


def run_shared_prefix(
    fixture: LargeWorldFixture, *, seed: int, actor: Actor, output_dir: Path,
) -> PhaseOutcome:
    return run_phase(
        fixture, phase_id="A", seed=seed, condition="SHARED", actor=actor, candidate=fixture.initial,
        history=[], observations=[], reopenable={}, completed=[], prior_binding=None, output_dir=output_dir,
    )


def run_branch(
    fixture: LargeWorldFixture, prefix: PhaseOutcome, *, seed: int, condition: str, actor_factory: Any, output_dir: Path,
) -> dict[str, Any]:
    if condition not in CONDITIONS:
        raise ValueError("invalid Experiment 012 condition")
    candidate = prefix.state.candidate
    observations = [dict(row) for row in prefix.observations]
    reopenable = dict(prefix.reopenable)
    full_history = list(prefix.history)
    history = full_history if condition == "C50" else [full_history[-1]]
    next_reconstructed = condition == "T25"
    completed = ["A"]
    binding = prefix.binding
    if condition == "T25":
        prospective = build_request(
            fixture, candidate=candidate, phase_id="B", history=full_history, observations=observations,
            completed=["A"], reconstructed=False, boundary_binding=binding, calls_used=0, stage="recurrent",
        )
        profile = actor_factory("B").profile
        own = guard(profile, prospective, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
        physical = guard(profile, prospective, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True)
        if own["authorized"] or not physical["authorized"]:
            raise RuntimeError("Experiment 012 first boundary is not authentically T25-only")
        atomic_write(output_dir / "FIRST_BOUNDARY_CAPACITY.json", canonical_json_bytes({
            "schema_version": "experiment-012-first-boundary-capacity-v1", "t25": own, "physical": physical,
        }))
    phases = []
    prepared = http = resets = 0
    for phase_id in ("B", "C", "D"):
        phase_root = output_dir / f"phase-{phase_id.lower()}"
        outcome = run_phase(
            fixture, phase_id=phase_id, seed=seed, condition=condition, actor=actor_factory(phase_id),
            candidate=candidate, history=history, observations=observations, reopenable=reopenable,
            completed=completed, prior_binding=binding, output_dir=phase_root,
            force_reconstructed=next_reconstructed,
        )
        verify_run(phase_root)
        phases.append(load_json_strict((phase_root / "SUMMARY.json").read_bytes()))
        prepared += outcome.prepared
        http += outcome.http
        resets += phases[-1]["runtime_resets"]
        candidate, observations, reopenable, history, binding = (
            outcome.state.candidate, outcome.observations, outcome.reopenable, outcome.history, outcome.binding,
        )
        if outcome.disposition not in {"phase_complete", "submitted"}:
            break
        completed.append(phase_id)
        next_reconstructed = False
        if phase_id != "D" and condition == "T25":
            prospective = build_request(
                fixture, candidate=candidate, phase_id=PHASE_IDS[len(completed)], history=history,
                observations=observations, completed=completed, reconstructed=False,
                boundary_binding=binding, calls_used=0, stage="recurrent" if len(completed) < 3 else "continuation",
            )
            admission = guard(actor_factory(phase_id).profile, prospective, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
            if not admission["authorized"]:
                history = [history[-1]]
                resets += 1
                next_reconstructed = True
                atomic_write(phase_root / "NEXT_PHASE_RECONSTRUCTION.json", canonical_json_bytes(admission))
    result = {
        "schema_version": "experiment-012-branch-summary-v1", "fixture_id": fixture.fixture_id,
        "condition": condition, "seed": seed, "phases": phases, "completed_phase_ids": completed,
        "prepared_invocations": prepared, "http_completion_calls": http, "reconstruction_count": resets,
        "candidate_id": candidate.candidate_id, "submitted": bool(phases and phases[-1]["submitted"]),
    }
    atomic_write(output_dir / "SUMMARY.json", canonical_json_bytes(result))
    return result


def hidden_grade(fixture: LargeWorldFixture, candidate: Candidate) -> dict[str, Any]:
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
            reconstructed=False, boundary_binding=None, calls_used=0, stage="setup",
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
        cells.append({**row, "expected_call_id": f"{row['fixture_id']}-S{row['seed']}-SHARED-A-P01",
                      "coding_request_sha256": sha256_bytes(request), "endpoint_request_sha256": sha256_bytes(endpoint),
                      "rendered_prompt_sha256": sha256_bytes(rendered), "initial_admission": admission})
    files = _inventory(target, {"PACKAGE_MANIFEST.json"})
    manifest = {
        "schema_version": PACKAGE_SCHEMA, "bank_id": verify_bank(bank)["bank_id"],
        "schedule_sha256": sha256_bytes(canonical_json_bytes(schedule())), "cells": cells,
        "hierarchical_p0": True, "read_mode": READ_MODE, "reasoning_budget_tokens": REASONING_BUDGET,
        "evaluator_bytes_present": False, "files": files,
        "package_id": "E12PKG-" + sha256_bytes(canonical_json_bytes(files)),
    }
    atomic_write(target / "PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_package(target: Path, *, bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    observed = load_json_strict((target / "PACKAGE_MANIFEST.json").read_bytes())
    if observed["files"] != _inventory(target, {"PACKAGE_MANIFEST.json"}):
        raise ValueError("Experiment 012 package differs")
    with tempfile.TemporaryDirectory(prefix="e12-package-") as raw:
        rebuilt = construct_package(Path(raw) / "package", bank=bank, profile=profile)
        if canonical_json_bytes(rebuilt) != canonical_json_bytes(observed):
            raise ValueError("Experiment 012 package reconstruction differs")
    return {"verified": True, "package_id": observed["package_id"], "file_count": len(observed["files"])}


def expected_authorization(experiment: Path) -> dict[str, Any]:
    bank = load_json_strict((experiment / "fresh_bank" / "BANK_MANIFEST.json").read_bytes())
    package = load_json_strict((experiment / "execution_package" / "PACKAGE_MANIFEST.json").read_bytes())
    closure = load_json_strict((experiment / "EXECUTABLE_CLOSURE.json").read_bytes())
    profile = load_json_strict((experiment / "RUNTIME_PROFILE.json").read_bytes())
    return {
        "schema_version": "experiment-012-owner-authorization-v1",
        "status": "owner_authorized_exact_large_world_recurrent_execution",
        "owner_statement": "Proceed with the larger-world longer-horizon study using the earned minimal controller.",
        "bank_id": bank["bank_id"], "bank_manifest_sha256": sha256_file(experiment / "fresh_bank" / "BANK_MANIFEST.json"),
        "package_id": package["package_id"], "package_manifest_sha256": sha256_file(experiment / "execution_package" / "PACKAGE_MANIFEST.json"),
        "closure_manifest_sha256": sha256_file(experiment / "EXECUTABLE_CLOSURE.json"),
        "closure_aggregate_sha256": closure["aggregate_sha256"],
        "schedule_sha256": sha256_file(experiment / "SCHEDULE.json"),
        "runtime_profile_sha256": sha256_file(experiment / "RUNTIME_PROFILE.json"),
        "actor_sha256": profile["model_sha256"], "conditions": list(CONDITIONS), "cases": list(CASE_IDS),
        "seeds": list(SEEDS), "shared_prefixes": 4, "measured_branches": 8,
        "phase_ids": list(PHASE_IDS), "attempts_per_branch": 1, "retries": 0, "repairs": 0, "rescues": 0,
        "maximum_http_completion_calls": MAXIMUM_HTTP_COMPLETION_CALLS, "output_root": OUTPUT_ROOT, "port": PORT,
        "read_mode": READ_MODE, "hierarchical_p0": True, "reasoning_budget_tokens": REASONING_BUDGET,
        "response_seal_before_evaluator_access": True, "automatic_successor": False,
        "no_summaries_relationships_embeddings_ranking_or_host_semantic_selection": True,
    }


def validate_authorization(experiment: Path) -> dict[str, Any]:
    observed = load_json_strict((experiment / "MEASURED_AUTHORIZATION.json").read_bytes())
    expected = expected_authorization(experiment)
    if canonical_json_bytes(observed) != canonical_json_bytes(expected):
        raise ValueError("Experiment 012 authorization differs")
    return {"verified": True, "authorization_sha256": sha256_file(experiment / "MEASURED_AUTHORIZATION.json")}
