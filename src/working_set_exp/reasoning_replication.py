from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .candidate import Candidate
from .fixture import load_fixture
from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from .reasoning import BRANCH_CALL_LIMIT, PREFIX_CALL_LIMIT
from .request import build_request
from .runner import ScriptedActor, run_prefix
from .runtime import (
    LiveActor,
    PreparedCall,
    REASONING_BUDGET,
    RuntimeProfile,
    endpoint_request,
    guard,
    render_prompt,
    render_reasoning_prompt,
)


BANK_SCHEMA = "experiment-005-reasoning-replication-bank-v1"
PACKAGE_SCHEMA = "experiment-005-reasoning-replication-package-v1"
CLOSURE_SCHEMA = "experiment-005-reasoning-replication-closure-v1"
AUTHORIZATION_SCHEMA = "experiment-005-reasoning-replication-authorization-v1"
CASE_IDS = ("E5-CHANNEL", "E5-FRAME")
SEEDS = {"E5-CHANNEL": 73771, "E5-FRAME": 88001}
OUTPUT_ROOT = r"C:\e5r-primary"
MAXIMUM_COMPLETION_CALLS = 32


def _ledger(module: str, marker: str, *, fact: str | None = None) -> bytes:
    lines = [f'"""Exact {module} audit ledger; preserve every row."""\n']
    if fact:
        lines.append(fact.rstrip("\n") + "\n")
    lines.append("AUDIT_ROWS = (\n")
    for index in range(210):
        digest = sha256_bytes(f"e5:{module}:{marker}:{index:04d}".encode("utf-8"))[:24]
        lines.append(f'    ("{marker}-{index:04d}", "{digest}", "hold-{(index * 29 + 13) % 997:03d}"),\n')
    lines.extend([")\n", "\n", f"def {module}_audit_size() -> int:\n", "    return len(AUDIT_ROWS)\n"])
    return "".join(lines).encode("utf-8")


def _case_channel() -> dict[str, Any]:
    files = {
        "history/cedar.py": _ledger("cedar", "EC"),
        "history/maple.py": _ledger("maple", "EM"),
        "history/oak.py": _ledger("oak", "EO"),
        "policy/channel.py": _ledger("channel", "EP", fact='ACTIVE_CHANNEL = "quartz/"')
        + b'\n\ndef active_channel() -> str:\n    return ACTIVE_CHANNEL\n',
        "stage/gate.py": b'AUDIT_GROUPS = ("cedar", "maple", "oak", "channel")\n\n\ndef audited_count() -> int:\n    return 0\n',
        "publish/slug.py": b"def publish_slug(name: str) -> str:\n    return name.strip().casefold()\n",
        "publish/render.py": b'from publish.slug import publish_slug\n\ndef render_slug(name: str) -> str:\n    return f"publish={publish_slug(name)}"\n',
    }
    required = ("history/cedar.py", "history/maple.py", "history/oak.py", "policy/channel.py")
    phase_b = (
        "Phase B: repair `publish/slug.py` so the normalized name is prefixed by the exact active channel audited in Phase A. "
        "Preserve trimming, case folding, and `publish/render.py` behavior. Run check `public` and submit."
    )
    return {
        "fixture_id": "E5-CHANNEL", "family": "fresh_constructed_source_channel",
        "files": files, "required": required,
        "task": (
            "Perform the two phases in order. Phase A: read each exact audit file completely: "
            + ", ".join(f"`{path}`" for path in required)
            + ". Preserve their contents. Then repair `stage/gate.py` so `audited_count()` returns the number of `AUDIT_GROUPS`, "
            "run check `prefork`, and call `fork_ready`. Do not change the Phase B target before `fork_ready`. "
            + phase_b
        ),
        "phase_b": phase_b,
        "prefork": b"from stage.gate import audited_count\nassert audited_count() == 4\nprint('prefork check passed')\n",
        "public": (
            b"from publish.slug import publish_slug\nfrom publish.render import render_slug\n"
            b"assert publish_slug(' Blue ') == 'quartz/blue'\n"
            b"assert render_slug('X') == 'publish=quartz/x'\nprint('public check passed')\n"
        ),
        "hidden": (
            b"from publish.slug import publish_slug\nfrom publish.render import render_slug\n"
            b"assert publish_slug(' Blue ') == 'quartz/blue'\n"
            b"assert render_slug('X') == 'publish=quartz/x'\n"
            b"assert publish_slug(' MiXeD ') == 'quartz/mixed'\nprint('hidden check passed')\n"
        ),
        "target": "publish/slug.py",
        "prefork_patch": {"path": "stage/gate.py", "old": "    return 0", "new": "    return len(AUDIT_GROUPS)"},
        "final_patch": {"path": "publish/slug.py", "old": "    return name.strip().casefold()", "new": '    return "quartz/" + name.strip().casefold()'},
        "governing": {"path": "policy/channel.py", "fact": 'ACTIVE_CHANNEL = "quartz/"'},
    }


def _case_frame() -> dict[str, Any]:
    files = {
        "journal/alpha.py": _ledger("alpha", "FA"),
        "journal/beta.py": _ledger("beta", "FB"),
        "journal/gamma.py": _ledger("gamma", "FG"),
        "config/frame.py": _ledger("frame", "FC", fact='FRAME_PREFIX = "m7:"')
        + b'\n\ndef frame_prefix() -> str:\n    return FRAME_PREFIX\n',
        "stage/gate.py": b'FRAME_GROUPS = ("alpha", "beta", "gamma", "frame")\n\n\ndef audited_count() -> int:\n    return 0\n',
        "wire/header.py": b"def wire_header(name: str) -> str:\n    return name.strip().upper()\n",
        "wire/encode.py": b"from wire.header import wire_header\n\ndef encoded_header(name: str) -> bytes:\n    return wire_header(name).encode('ascii')\n",
    }
    required = ("journal/alpha.py", "journal/beta.py", "journal/gamma.py", "config/frame.py")
    phase_b = (
        "Phase B: repair `wire/header.py` so the normalized name is prefixed by the exact frame prefix audited in Phase A. "
        "Preserve trimming, uppercasing, and `wire/encode.py` ASCII behavior. Run check `public` and submit."
    )
    return {
        "fixture_id": "E5-FRAME", "family": "fresh_constructed_source_frame",
        "files": files, "required": required,
        "task": (
            "Perform the two phases in order. Phase A: read each exact audit file completely: "
            + ", ".join(f"`{path}`" for path in required)
            + ". Preserve their contents. Then repair `stage/gate.py` so `audited_count()` returns the number of `FRAME_GROUPS`, "
            "run check `prefork`, and call `fork_ready`. Do not change the Phase B target before `fork_ready`. "
            + phase_b
        ),
        "phase_b": phase_b,
        "prefork": b"from stage.gate import audited_count\nassert audited_count() == 4\nprint('prefork check passed')\n",
        "public": (
            b"from wire.header import wire_header\nfrom wire.encode import encoded_header\n"
            b"assert wire_header(' blue ') == 'm7:BLUE'\n"
            b"assert encoded_header('x') == b'm7:X'\nprint('public check passed')\n"
        ),
        "hidden": (
            b"from wire.header import wire_header\nfrom wire.encode import encoded_header\n"
            b"assert wire_header(' blue ') == 'm7:BLUE'\n"
            b"assert encoded_header('x') == b'm7:X'\n"
            b"assert wire_header(' MiXeD ') == 'm7:MIXED'\nprint('hidden check passed')\n"
        ),
        "target": "wire/header.py",
        "prefork_patch": {"path": "stage/gate.py", "old": "    return 0", "new": "    return len(FRAME_GROUPS)"},
        "final_patch": {"path": "wire/header.py", "old": "    return name.strip().upper()", "new": '    return "m7:" + name.strip().upper()'},
        "governing": {"path": "config/frame.py", "fact": 'FRAME_PREFIX = "m7:"'},
    }


def case_definitions() -> tuple[dict[str, Any], ...]:
    return (_case_channel(), _case_frame())


def _candidate_after(case: dict[str, Any], *, final: bool) -> Candidate:
    candidate = Candidate.create(case["files"])
    for patch in [case["prefork_patch"], *([case["final_patch"]] if final else [])]:
        candidate, _ = candidate.patch(
            path=patch["path"], old=patch["old"], new=patch["new"],
            expected_candidate_id=candidate.candidate_id,
            expected_file_sha256=candidate.file_sha256(patch["path"]),
        )
    return candidate


def _inventory(root: Path, *, excluded: set[str] | None = None) -> list[dict[str, Any]]:
    excluded = excluded or set()
    rows = []
    for path in sorted(root.rglob("*"), key=lambda value: value.relative_to(root).as_posix()):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        if path.is_symlink():
            raise ValueError("linked files are prohibited")
        rows.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return rows


def construct_bank(target: Path) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    files: dict[str, bytes] = {}
    for case in case_definitions():
        initial = Candidate.create(case["files"])
        prefork = _candidate_after(case, final=False)
        known = _candidate_after(case, final=True)
        visible = f"model_visible/{case['fixture_id']}"
        candidate_rows = []
        for path, data in initial.files:
            files[f"{visible}/candidate/{path}"] = data
            candidate_rows.append({"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)})
        files[f"{visible}/TASK.txt"] = case["task"].encode("utf-8")
        files[f"{visible}/PHASE_B.txt"] = case["phase_b"].encode("utf-8")
        execution = f"execution_only/{case['fixture_id']}"
        files[f"{execution}/checks/prefork.py"] = case["prefork"]
        files[f"{execution}/checks/public.py"] = case["public"]
        files[f"{execution}/FIXTURE.json"] = canonical_json_bytes(
            {
                "schema_version": "experiment-005-reasoning-replication-fixture-v1",
                "fixture_id": case["fixture_id"], "family": case["family"],
                "initial_candidate_id": initial.candidate_id, "prefork_candidate_id": prefork.candidate_id,
                "known_good_candidate_id": known.candidate_id, "candidate_files": candidate_rows,
                "required_full_reads": list(case["required"]), "final_target": case["target"],
                "probe_id": None, "probe_body_present": False, "probe_body_sha256": None,
            }
        )
        evaluator = f"evaluator_only/{case['fixture_id']}"
        files[f"{evaluator}/hidden.py"] = case["hidden"]
        files[f"{evaluator}/TRUTH.json"] = canonical_json_bytes(
            {
                "schema_version": "experiment-005-reasoning-replication-truth-v1",
                "fixture_id": case["fixture_id"], "prefork_candidate_id": prefork.candidate_id,
                "known_good_candidate_id": known.candidate_id, "governing_requirement": case["governing"],
                "prefork_patch": case["prefork_patch"], "final_patch": case["final_patch"],
            }
        )
    for relative, data in files.items():
        atomic_write(target / Path(*relative.split("/")), data)
    inventory = [
        {"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)}
        for path, data in sorted(files.items())
    ]
    manifest = {
        "schema_version": BANK_SCHEMA,
        "bank_id": "E5BANK-" + sha256_bytes(canonical_json_bytes(inventory)),
        "case_ids": list(CASE_IDS), "fresh_before_actor_exposure": True,
        "constructed_fork_study": True, "evaluator_separate": True, "files": inventory,
    }
    atomic_write(target / "BANK_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_bank(target: Path) -> dict[str, Any]:
    manifest = load_json_strict((target / "BANK_MANIFEST.json").read_bytes())
    if manifest["schema_version"] != BANK_SCHEMA:
        raise ValueError("replication bank schema differs")
    files = _inventory(target, excluded={"BANK_MANIFEST.json"})
    if files != manifest["files"]:
        raise ValueError("replication bank inventory differs")
    bank_id = "E5BANK-" + sha256_bytes(canonical_json_bytes(files))
    if manifest["bank_id"] != bank_id:
        raise ValueError("replication bank identity differs")
    return {"verified": True, "bank_id": bank_id, "file_count": len(files)}


def progress_pointer(bank: Path, fixture_id: str) -> dict[str, Any]:
    phase = (bank / "model_visible" / fixture_id / "PHASE_B.txt").read_text(encoding="utf-8")
    return {
        "schema_version": "experiment-005-verbatim-progress-pointer-v1",
        "completed_protocol_stage": "phase_a", "active_protocol_stage": "phase_b",
        "active_step_verbatim": phase, "active_step_sha256": sha256_bytes(phase.encode("utf-8")),
        "derivation": "verbatim_user_authored_frozen_task_component", "semantic_host_summary": False,
    }


def prefix_policy(case: dict[str, Any]):
    required_index = 0
    target_read = False
    patched = False
    checked = False

    def policy(request: dict[str, Any]) -> dict[str, Any]:
        nonlocal required_index, target_read, patched, checked
        if request["stage"] == "setup":
            return {"action": "begin"}
        candidate_id = request["candidate_id"]
        if required_index < len(case["required"]):
            path = case["required"][required_index]
            required_index += 1
            return {"action": "read", "path": path, "start_line": 1, "line_count": 500}
        if not target_read:
            target_read = True
            return {"action": "read", "path": "stage/gate.py", "start_line": 1, "line_count": 100}
        if not patched:
            patched = True
            latest = request["history"][-1]["result"]
            patch = case["prefork_patch"]
            return {
                "action": "patch", "path": patch["path"], "old": patch["old"], "new": patch["new"],
                "expected_candidate_id": candidate_id, "expected_file_sha256": latest["file_sha256"],
            }
        if not checked:
            checked = True
            return {"action": "check", "check_id": "prefork", "expected_candidate_id": candidate_id}
        return {"action": "fork_ready", "expected_candidate_id": candidate_id}

    return policy


def construct_prefix(*, bank: Path, fixture_id: str, seed: int, profile: RuntimeProfile, output: Path):
    case = next(value for value in case_definitions() if value["fixture_id"] == fixture_id)
    fixture = load_fixture(bank, fixture_id)
    actor = ScriptedActor(profile, seed, prefix_policy(case))
    return run_prefix(
        fixture, seed=seed, actor=actor, output_dir=output, profile=profile,
        fixed_record_timestamp="2026-08-28T00:00:00Z",
        prefix_call_limit=PREFIX_CALL_LIMIT, continuation_call_limit=BRANCH_CALL_LIMIT,
        one_shot_probe=True,
    )


def _branch_first_request(fixture, prefix, *, bank: Path) -> bytes:
    return build_request(
        fixture_id=fixture.fixture_id, task=fixture.task, candidate=prefix.state.candidate,
        stage="continuation", visible_history=[prefix.history[-1]],
        prefix_calls_used=prefix.calls, continuation_calls_used=0, probe_id=None,
        observations=prefix.observations, reconstructed=True, fork_binding=prefix.binding,
        progress_pointer=progress_pointer(bank, fixture.fixture_id),
        prefix_call_limit=PREFIX_CALL_LIMIT, continuation_call_limit=BRANCH_CALL_LIMIT,
    )


def construct_package(target: Path, *, bank: Path, schedule_path: Path, profile: RuntimeProfile) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True)
    schedule = load_json_strict(schedule_path.read_bytes())
    cells = []
    with tempfile.TemporaryDirectory(prefix="e5-package-") as raw:
        temporary = Path(raw)
        prefixes = {}
        for row in schedule["cases"]:
            fixture = load_fixture(bank, row["fixture_id"])
            prefix = construct_prefix(
                bank=bank, fixture_id=row["fixture_id"], seed=row["seed"], profile=profile,
                output=temporary / f"prefix-{row['ordinal']:02d}",
            )
            prefixes[row["fixture_id"]] = prefix
            request = _branch_first_request(fixture, prefix, bank=bank)
            for condition in row["branch_order"]:
                enabled = condition == "R1"
                endpoint = endpoint_request(
                    profile, request, stage="continuation", probe_id=None, seed=row["seed"],
                    reasoning_enabled=enabled,
                )
                rendered = render_reasoning_prompt(request, enabled=enabled) if enabled else render_prompt(request)
                admission = guard(profile, request, active_total_ceiling=25_000, reasoning_enabled=enabled)
                if not admission["authorized"]:
                    raise ValueError("replication first branch request is not admitted")
                cell_name = f"case-{row['ordinal']:02d}-{condition}"
                atomic_write(target / cell_name / "initial-coding-request.json", request)
                atomic_write(target / cell_name / "initial-endpoint-request.json", endpoint)
                atomic_write(target / cell_name / "initial-rendered-prompt.txt", rendered)
                cells.append(
                    {
                        "fixture_id": row["fixture_id"], "condition": condition, "seed": row["seed"],
                        "cell": cell_name,
                        "expected_call_id": f"{row['fixture_id']}-S{row['seed']}-{condition}-01",
                        "coding_request_sha256": sha256_bytes(request),
                        "endpoint_request_sha256": sha256_bytes(endpoint),
                        "rendered_prompt_sha256": sha256_bytes(rendered), "admission": admission,
                    }
                )
    files = _inventory(target)
    manifest = {
        "schema_version": PACKAGE_SCHEMA, "bank_id": verify_bank(bank)["bank_id"],
        "schedule_sha256": sha256_file(schedule_path), "conditions": ["R0", "R1"],
        "server_reasoning_budget_tokens": REASONING_BUDGET, "cells": cells, "files": files,
        "package_id": "E5PKG-" + sha256_bytes(canonical_json_bytes(files)), "evaluator_bytes_present": False,
    }
    atomic_write(target / "PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_package(target: Path, *, bank: Path, schedule_path: Path, profile: RuntimeProfile) -> dict[str, Any]:
    manifest = load_json_strict((target / "PACKAGE_MANIFEST.json").read_bytes())
    files = _inventory(target, excluded={"PACKAGE_MANIFEST.json"})
    if manifest["schema_version"] != PACKAGE_SCHEMA or files != manifest["files"]:
        raise ValueError("replication package differs")
    if manifest["package_id"] != "E5PKG-" + sha256_bytes(canonical_json_bytes(files)):
        raise ValueError("replication package identity differs")
    with tempfile.TemporaryDirectory(prefix="e5-verify-") as raw:
        rebuilt = Path(raw) / "package"
        expected = construct_package(rebuilt, bank=bank, schedule_path=schedule_path, profile=profile)
        if canonical_json_bytes(expected) != canonical_json_bytes(manifest):
            raise ValueError("replication package reconstruction differs")
        for row in files:
            relative = Path(*row["path"].split("/"))
            if (rebuilt / relative).read_bytes() != (target / relative).read_bytes():
                raise ValueError("replication package bytes differ")
    return {"verified": True, "package_id": manifest["package_id"], "file_count": len(files)}


def build_closure(repo: Path) -> dict[str, Any]:
    paths = sorted((repo / "src" / "working_set_exp").glob("*.py"))
    paths.append(repo / "scripts" / "run_reasoning_replication.py")
    rows = [
        {"path": path.relative_to(repo).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in paths
        if path.is_file() and not path.is_symlink()
    ]
    if len(rows) != len(paths):
        raise ValueError("replication closure path differs")
    return {"schema_version": CLOSURE_SCHEMA, "files": rows, "aggregate_sha256": sha256_bytes(canonical_json_bytes(rows))}


def verify_closure(repo: Path, path: Path) -> dict[str, Any]:
    expected = load_json_strict(path.read_bytes())
    observed = build_closure(repo)
    if canonical_json_bytes(expected) != canonical_json_bytes(observed):
        raise ValueError("replication executable closure differs")
    return {"verified": True, "aggregate_sha256": observed["aggregate_sha256"], "file_count": len(observed["files"])}


def expected_authorization(*, experiment: Path) -> dict[str, Any]:
    bank = load_json_strict((experiment / "fresh_bank" / "BANK_MANIFEST.json").read_bytes())
    package = load_json_strict((experiment / "execution_package" / "PACKAGE_MANIFEST.json").read_bytes())
    closure = load_json_strict((experiment / "EXECUTABLE_CLOSURE.json").read_bytes())
    profile = load_json_strict((experiment / "RUNTIME_PROFILE.json").read_bytes())
    return {
        "schema_version": AUTHORIZATION_SCHEMA,
        "status": "owner_authorized_exact_fresh_constructed_fork_replication",
        "owner_statement": "Great, proceed as you recommended",
        "bank_id": bank["bank_id"], "bank_manifest_sha256": sha256_file(experiment / "fresh_bank" / "BANK_MANIFEST.json"),
        "execution_package_id": package["package_id"],
        "execution_package_manifest_sha256": sha256_file(experiment / "execution_package" / "PACKAGE_MANIFEST.json"),
        "executable_closure_manifest_sha256": sha256_file(experiment / "EXECUTABLE_CLOSURE.json"),
        "executable_closure_aggregate_sha256": closure["aggregate_sha256"],
        "schedule_sha256": sha256_file(experiment / "SCHEDULE.json"),
        "runtime_profile_sha256": sha256_file(experiment / "RUNTIME_PROFILE.json"),
        "actor_sha256": profile["model_sha256"], "conditions": ["R0", "R1"],
        "server_reasoning_budget_tokens": REASONING_BUDGET,
        "constructed_forks": 2, "branches": 4, "maximum_completion_calls": MAXIMUM_COMPLETION_CALLS,
        "attempts_per_call": 1, "retries": 0, "repairs": 0, "rescues": 0,
        "output_root": OUTPUT_ROOT, "response_seal_before_evaluator_access": True,
        "automatic_successor": False,
    }


def validate_authorization(experiment: Path) -> dict[str, Any]:
    observed = load_json_strict((experiment / "MEASURED_AUTHORIZATION.json").read_bytes())
    expected = expected_authorization(experiment=experiment)
    if canonical_json_bytes(observed) != canonical_json_bytes(expected):
        raise ValueError("replication authorization differs")
    return {"verified": True, "authorization_sha256": sha256_file(experiment / "MEASURED_AUTHORIZATION.json")}


@dataclass
class FrozenBranchActor:
    inner: LiveActor
    expected_call_id: str
    package_cell: Path
    checked: bool = False

    def prepare(self, request: bytes, *, stage: str, probe_id: str | None, call_id: str, active_total_ceiling: int) -> PreparedCall:
        prepared = self.inner.prepare(
            request, stage=stage, probe_id=probe_id, call_id=call_id,
            active_total_ceiling=active_total_ceiling,
        )
        if not self.checked:
            if call_id != self.expected_call_id or stage != "continuation":
                raise ValueError("replication first call identity differs")
            for observed, name in (
                (request, "initial-coding-request.json"),
                (prepared.endpoint_request, "initial-endpoint-request.json"),
                (prepared.rendered_prompt, "initial-rendered-prompt.txt"),
            ):
                if observed != (self.package_cell / name).read_bytes():
                    raise ValueError(f"replication first {name} differs")
            self.checked = True
        return prepared

    def invoke(self, prepared: PreparedCall):
        return self.inner.invoke(prepared)
