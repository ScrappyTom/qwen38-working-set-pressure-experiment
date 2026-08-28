from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .candidate import Candidate
from .fixture import load_fixture
from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from .request import build_request, render_reasoning_prompt
from .runtime import PHYSICAL_CONTEXT, REASONING_BUDGET, RuntimeProfile, endpoint_request, guard


BANK_SCHEMA = "experiment-006-authentic-pressure-bank-v1"
PACKAGE_SCHEMA = "experiment-006-authentic-pressure-package-v1"
CLOSURE_SCHEMA = "experiment-006-authentic-pressure-closure-v1"
AUTHORIZATION_SCHEMA = "experiment-006-authentic-pressure-authorization-v1"
CASE_IDS = ("E6-SOURCE", "E6-OBSERVATION")
SEEDS = {"E6-SOURCE": 101031, "E6-OBSERVATION": 141421}
PREFIX_CALL_LIMIT = 12
BRANCH_CALL_LIMIT = 8
OUTPUT_ROOT = r"C:\e6-primary"
MAXIMUM_HTTP_COMPLETION_CALLS = 56


def _ledger(module: str, marker: str, *, fact: str | None = None) -> bytes:
    lines = [f'"""Exact {module} custody ledger; every row is part of Phase A."""\n']
    if fact:
        lines.append(fact.rstrip("\n") + "\n")
    lines.append("CUSTODY_ROWS = (\n")
    for index in range(185):
        digest = sha256_bytes(f"e6:{module}:{marker}:{index:04d}".encode("utf-8"))[:24]
        lines.append(f'    ("{marker}-{index:04d}", "{digest}", "retain-{(index * 31 + 17) % 997:03d}"),\n')
    lines.extend([")\n", "\n", f"def {module}_custody_size() -> int:\n", "    return len(CUSTODY_ROWS)\n"])
    data = "".join(lines).encode("utf-8")
    if not 10_000 <= len(data) <= 14_000:
        raise AssertionError(f"ledger geometry differs: {module} {len(data)}")
    return data


def _source_case() -> dict[str, Any]:
    files = {
        "archive/aurora.py": _ledger("aurora", "EA"),
        "archive/boreal.py": _ledger("boreal", "EB"),
        "policy/route.py": _ledger("route", "ER", fact='ROUTE_STEM = "nebula-"')
        + b'\n\ndef route_stem() -> str:\n    """Return the exact current delivery stem."""\n    return ROUTE_STEM\n',
        "stage/ready.py": b'PHASE_A_GROUPS = ("aurora", "boreal", "route")\n\n\ndef completed_groups() -> int:\n    return 0\n',
        "delivery/key.py": b"def delivery_key(name: str) -> str:\n    return name.strip().casefold()\n",
        "delivery/render.py": b'from delivery.key import delivery_key\n\ndef render_delivery(name: str) -> str:\n    return f"delivery={delivery_key(name)}"\n',
    }
    required = ("archive/aurora.py", "archive/boreal.py", "policy/route.py")
    phase_b = (
        "Phase B: repair `delivery/key.py` so the normalized name is prefixed by the exact current route stem audited in Phase A. "
        "Preserve trimming, case folding, and `delivery/render.py` behavior. Run check `public` and submit."
    )
    return {
        "fixture_id": "E6-SOURCE",
        "family": "authentic_source_reacquisition",
        "files": files,
        "required": required,
        "task": (
            "Perform the two phases in order. Phase A: read each exact custody file completely: "
            + ", ".join(f"`{path}`" for path in required)
            + ". Preserve their contents. Then read and repair `stage/ready.py` so `completed_groups()` returns the number of `PHASE_A_GROUPS`, "
            "run check `prefork`, and call `fork_ready`. Do not change the Phase B target before `fork_ready`. "
            + phase_b
        ),
        "phase_b": phase_b,
        "prefork": b"from stage.ready import completed_groups\nassert completed_groups() == 3\nprint('prefork check passed')\n",
        "public": (
            b"from delivery.key import delivery_key\nfrom delivery.render import render_delivery\n"
            b"assert delivery_key(' Blue ') == 'nebula-blue'\n"
            b"assert render_delivery('X') == 'delivery=nebula-x'\nprint('public check passed')\n"
        ),
        "hidden": (
            b"from delivery.key import delivery_key\nfrom delivery.render import render_delivery\n"
            b"assert delivery_key(' Blue ') == 'nebula-blue'\n"
            b"assert render_delivery('X') == 'delivery=nebula-x'\n"
            b"assert delivery_key(' MiXeD ') == 'nebula-mixed'\nprint('hidden check passed')\n"
        ),
        "probe_id": None,
        "probe_body": None,
        "target": "delivery/key.py",
        "prefork_patch": {"path": "stage/ready.py", "old": "    return 0", "new": "    return len(PHASE_A_GROUPS)"},
        "final_patch": {"path": "delivery/key.py", "old": "    return name.strip().casefold()", "new": '    return "nebula-" + name.strip().casefold()'},
        "governing": {"kind": "current_source", "path": "policy/route.py", "fact": 'ROUTE_STEM = "nebula-"'},
    }


def _observation_case() -> dict[str, Any]:
    files = {
        "archive/cinder.py": _ledger("cinder", "EC"),
        "archive/delta.py": _ledger("delta", "ED"),
        "archive/ember.py": _ledger("ember", "EE"),
        "stage/ready.py": b'PHASE_A_GROUPS = ("cinder", "delta", "ember")\n\n\ndef completed_groups() -> int:\n    return 0\n',
        "session/label.py": b"def session_label(name: str) -> str:\n    return name.strip().upper()\n",
        "session/wire.py": b"from session.label import session_label\n\ndef encoded_label(name: str) -> bytes:\n    return session_label(name).encode('ascii')\n",
    }
    required = ("archive/cinder.py", "archive/delta.py", "archive/ember.py")
    phase_b = (
        "Phase B: repair `session/label.py` so it prepends the exact marker returned by the Phase A compatibility probe. "
        "The marker is not present in candidate source. Preserve trimming, uppercasing, and `session/wire.py` ASCII behavior. "
        "Run check `public` and submit."
    )
    return {
        "fixture_id": "E6-OBSERVATION",
        "family": "authentic_observation_reacquisition",
        "files": files,
        "required": required,
        "task": (
            "Perform the two phases in order. Phase A: call compatibility probe `session`, then read each exact custody file completely: "
            + ", ".join(f"`{path}`" for path in required)
            + ". Preserve their contents. Then read and repair `stage/ready.py` so `completed_groups()` returns the number of `PHASE_A_GROUPS`, "
            "run check `prefork`, and call `fork_ready`. Do not change the Phase B target before `fork_ready`. "
            + phase_b
        ),
        "phase_b": phase_b,
        "prefork": b"from stage.ready import completed_groups\nassert completed_groups() == 3\nprint('prefork check passed')\n",
        "public": (
            b"from session.label import session_label\nfrom session.wire import encoded_label\n"
            b"assert session_label(' blue ') == 'K4::BLUE'\n"
            b"assert encoded_label('x') == b'K4::X'\nprint('public check passed')\n"
        ),
        "hidden": (
            b"from session.label import session_label\nfrom session.wire import encoded_label\n"
            b"assert session_label(' blue ') == 'K4::BLUE'\n"
            b"assert encoded_label('x') == b'K4::X'\n"
            b"assert session_label(' MiXeD ') == 'K4::MIXED'\nprint('hidden check passed')\n"
        ),
        "probe_id": "session",
        "probe_body": "compatibility runtime observation\nsession_marker=K4::\nsource=external_handshake\n",
        "target": "session/label.py",
        "prefork_patch": {"path": "stage/ready.py", "old": "    return 0", "new": "    return len(PHASE_A_GROUPS)"},
        "final_patch": {"path": "session/label.py", "old": "    return name.strip().upper()", "new": '    return "K4::" + name.strip().upper()'},
        "governing": {"kind": "historical_observation", "probe_id": "session", "fact": "session_marker=K4::"},
    }


def case_definitions() -> tuple[dict[str, Any], ...]:
    return (_source_case(), _observation_case())


def _candidate_after(case: dict[str, Any], *, final: bool) -> Candidate:
    candidate = Candidate.create(case["files"])
    patches = [case["prefork_patch"], *([case["final_patch"]] if final else [])]
    for row in patches:
        candidate, _ = candidate.patch(
            path=row["path"], old=row["old"], new=row["new"],
            expected_candidate_id=candidate.candidate_id,
            expected_file_sha256=candidate.file_sha256(row["path"]),
        )
    return candidate


def _inventory(root: Path, *, excluded: set[str] | None = None) -> list[dict[str, Any]]:
    excluded = excluded or set()
    rows = []
    paths = sorted(root.rglob("*"), key=lambda value: value.relative_to(root).as_posix())
    for path in paths:
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
        known_good = _candidate_after(case, final=True)
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
        if case["probe_body"] is not None:
            files[f"{execution}/PROBE.txt"] = case["probe_body"].encode("utf-8")
        files[f"{execution}/FIXTURE.json"] = canonical_json_bytes({
            "schema_version": "experiment-006-fixture-v1",
            "fixture_id": case["fixture_id"], "family": case["family"],
            "initial_candidate_id": initial.candidate_id,
            "prefork_candidate_id": prefork.candidate_id,
            "known_good_candidate_id": known_good.candidate_id,
            "candidate_files": candidate_rows,
            "required_full_reads": list(case["required"]), "final_target": case["target"],
            "probe_id": case["probe_id"], "probe_body_present": case["probe_body"] is not None,
            "probe_body_sha256": sha256_bytes(case["probe_body"].encode("utf-8")) if case["probe_body"] else None,
        })
        evaluator = f"evaluator_only/{case['fixture_id']}"
        files[f"{evaluator}/hidden.py"] = case["hidden"]
        for path, data in known_good.files:
            files[f"{evaluator}/known_good/{path}"] = data
        files[f"{evaluator}/TRUTH.json"] = canonical_json_bytes({
            "schema_version": "experiment-006-truth-v1", "fixture_id": case["fixture_id"],
            "family": case["family"], "known_good_candidate_id": known_good.candidate_id,
            "prefork_candidate_id": prefork.candidate_id, "governing_requirement": case["governing"],
            "required_full_reads": list(case["required"]), "prefork_patch": case["prefork_patch"],
            "final_patch": case["final_patch"],
        })
    for relative, data in files.items():
        atomic_write(target / Path(*relative.split("/")), data)
    inventory = [{"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)} for path, data in sorted(files.items())]
    manifest = {
        "schema_version": BANK_SCHEMA,
        "bank_id": "E6BANK-" + sha256_bytes(canonical_json_bytes(inventory)),
        "case_ids": list(CASE_IDS), "fresh_before_actor_exposure": True,
        "selected_before_actor_behavior": True, "evaluator_separate": True, "files": inventory,
    }
    atomic_write(target / "BANK_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_bank(target: Path) -> dict[str, Any]:
    manifest = load_json_strict((target / "BANK_MANIFEST.json").read_bytes())
    files = _inventory(target, excluded={"BANK_MANIFEST.json"})
    if manifest["schema_version"] != BANK_SCHEMA or manifest["files"] != files:
        raise ValueError("authentic pressure bank differs")
    expected = "E6BANK-" + sha256_bytes(canonical_json_bytes(files))
    if manifest["bank_id"] != expected:
        raise ValueError("authentic pressure bank identity differs")
    return {"verified": True, "bank_id": expected, "file_count": len(files)}


def progress_pointer(bank: Path, fixture_id: str) -> dict[str, Any]:
    body = (bank / "model_visible" / fixture_id / "PHASE_B.txt").read_text(encoding="utf-8")
    return {
        "schema_version": "experiment-006-verbatim-active-step-v1",
        "source": "prospectively_frozen_user_authored_task_segment",
        "text": body,
        "sha256": sha256_bytes(body.encode("utf-8")),
        "host_inference": False,
    }


def _runtime(value: dict[str, Any]) -> RuntimeProfile:
    return RuntimeProfile(
        model_alias=value["model_alias"], model_path=Path(value["model_path"]), model_sha256=value["model_sha256"],
        tokenizer_path=Path(value["tokenizer_path"]), tokenizer_sha256=value["tokenizer_sha256"],
        server_path=Path(value["server_path"]), server_sha256=value["server_sha256"],
        runtime_root=Path(value["runtime_root"]), build=value["build"],
    )


def construct_package(target: Path, *, bank: Path, schedule_path: Path, profile: RuntimeProfile) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True)
    schedule = load_json_strict(schedule_path.read_bytes())
    cells = []
    for row in schedule["cases"]:
        fixture = load_fixture(bank, row["fixture_id"])
        request = build_request(
            fixture_id=fixture.fixture_id, task=fixture.task, candidate=fixture.initial, stage="setup",
            visible_history=[], prefix_calls_used=0, continuation_calls_used=0,
            probe_id=fixture.probe_id, observations=[], reconstructed=False, fork_binding=None,
            prefix_call_limit=PREFIX_CALL_LIMIT, continuation_call_limit=BRANCH_CALL_LIMIT,
        )
        endpoint = endpoint_request(profile, request, stage="setup", probe_id=fixture.probe_id, seed=row["seed"], reasoning_enabled=True)
        rendered = render_reasoning_prompt(request, enabled=True)
        admission = guard(profile, request, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True)
        if not admission["authorized"]:
            raise ValueError("initial authentic pressure request is not admitted")
        cell = f"case-{row['ordinal']:02d}"
        atomic_write(target / cell / "initial-coding-request.json", request)
        atomic_write(target / cell / "initial-endpoint-request.json", endpoint)
        atomic_write(target / cell / "initial-rendered-prompt.txt", rendered)
        pointer = canonical_json_bytes(progress_pointer(bank, fixture.fixture_id))
        atomic_write(target / cell / "progress-pointer.json", pointer)
        cells.append({
            "ordinal": row["ordinal"], "fixture_id": fixture.fixture_id, "seed": row["seed"],
            "branch_order": row["branch_order"], "expected_call_id": f"{fixture.fixture_id}-S{row['seed']}-P01",
            "coding_request_sha256": sha256_bytes(request), "endpoint_request_sha256": sha256_bytes(endpoint),
            "rendered_prompt_sha256": sha256_bytes(rendered), "progress_pointer_sha256": sha256_bytes(pointer),
            "initial_admission": admission,
        })
    files = _inventory(target)
    manifest = {
        "schema_version": PACKAGE_SCHEMA, "bank_id": verify_bank(bank)["bank_id"],
        "schedule_sha256": sha256_file(schedule_path), "conditions": ["C50-R1", "T25-R1"],
        "server_reasoning_budget_tokens": REASONING_BUDGET,
        "prefix_call_limit": PREFIX_CALL_LIMIT, "branch_call_limit": BRANCH_CALL_LIMIT,
        "cells": cells, "files": files, "evaluator_bytes_present": False,
        "package_id": "E6PKG-" + sha256_bytes(canonical_json_bytes(files)),
    }
    atomic_write(target / "PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_package(target: Path, *, bank: Path, schedule_path: Path, profile: RuntimeProfile) -> dict[str, Any]:
    manifest = load_json_strict((target / "PACKAGE_MANIFEST.json").read_bytes())
    files = _inventory(target, excluded={"PACKAGE_MANIFEST.json"})
    if manifest["schema_version"] != PACKAGE_SCHEMA or manifest["files"] != files:
        raise ValueError("authentic pressure package differs")
    with tempfile.TemporaryDirectory(prefix="e6-package-") as raw:
        rebuilt = Path(raw) / "package"
        expected = construct_package(rebuilt, bank=bank, schedule_path=schedule_path, profile=profile)
        if canonical_json_bytes(expected) != canonical_json_bytes(manifest):
            raise ValueError("authentic pressure package reconstruction differs")
        for row in files:
            rel = Path(*row["path"].split("/"))
            if (rebuilt / rel).read_bytes() != (target / rel).read_bytes():
                raise ValueError("authentic pressure package bytes differ")
    return {"verified": True, "package_id": manifest["package_id"], "file_count": len(files)}


def build_closure(repo: Path) -> dict[str, Any]:
    paths = sorted((repo / "src" / "working_set_exp").glob("*.py"))
    paths.append(repo / "scripts" / "run_authentic_pressure.py")
    rows = []
    for path in paths:
        if not path.is_file() or path.is_symlink():
            raise ValueError("authentic pressure closure path differs")
        rows.append({"path": path.relative_to(repo).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"schema_version": CLOSURE_SCHEMA, "files": rows, "aggregate_sha256": sha256_bytes(canonical_json_bytes(rows))}


def verify_closure(repo: Path, path: Path) -> dict[str, Any]:
    expected = load_json_strict(path.read_bytes())
    observed = build_closure(repo)
    if canonical_json_bytes(expected) != canonical_json_bytes(observed):
        raise ValueError("authentic pressure executable closure differs")
    return {"verified": True, "aggregate_sha256": observed["aggregate_sha256"], "file_count": len(observed["files"])}


def expected_authorization(experiment: Path) -> dict[str, Any]:
    bank = load_json_strict((experiment / "fresh_bank" / "BANK_MANIFEST.json").read_bytes())
    package = load_json_strict((experiment / "execution_package" / "PACKAGE_MANIFEST.json").read_bytes())
    closure = load_json_strict((experiment / "EXECUTABLE_CLOSURE.json").read_bytes())
    profile = load_json_strict((experiment / "RUNTIME_PROFILE.json").read_bytes())
    return {
        "schema_version": AUTHORIZATION_SCHEMA,
        "status": "owner_authorized_exact_authentic_single_boundary_execution",
        "owner_statement": "Proceed",
        "bank_id": bank["bank_id"], "bank_manifest_sha256": sha256_file(experiment / "fresh_bank" / "BANK_MANIFEST.json"),
        "package_id": package["package_id"], "package_manifest_sha256": sha256_file(experiment / "execution_package" / "PACKAGE_MANIFEST.json"),
        "closure_manifest_sha256": sha256_file(experiment / "EXECUTABLE_CLOSURE.json"),
        "closure_aggregate_sha256": closure["aggregate_sha256"],
        "schedule_sha256": sha256_file(experiment / "SCHEDULE.json"),
        "runtime_profile_sha256": sha256_file(experiment / "RUNTIME_PROFILE.json"),
        "actor_sha256": profile["model_sha256"], "conditions": ["C50-R1", "T25-R1"],
        "server_reasoning_budget_tokens": REASONING_BUDGET,
        "cases": 2, "branches": 4, "maximum_http_completion_calls": MAXIMUM_HTTP_COMPLETION_CALLS,
        "attempts_per_call": 1, "retries": 0, "repairs": 0, "rescues": 0,
        "output_root": OUTPUT_ROOT, "response_seal_before_evaluator_access": True,
        "automatic_successor": False,
    }


def validate_authorization(experiment: Path) -> dict[str, Any]:
    observed = load_json_strict((experiment / "MEASURED_AUTHORIZATION.json").read_bytes())
    expected = expected_authorization(experiment)
    if canonical_json_bytes(observed) != canonical_json_bytes(expected):
        raise ValueError("authentic pressure authorization differs")
    return {"verified": True, "authorization_sha256": sha256_file(experiment / "MEASURED_AUTHORIZATION.json")}
