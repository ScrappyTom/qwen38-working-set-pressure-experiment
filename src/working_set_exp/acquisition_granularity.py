from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .candidate import Candidate
from .fixture import Fixture, load_fixture
from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from .request import build_request, render_reasoning_prompt
from .runner import ScriptedActor, replay_prefix, run_prefix, verify_run
from .runtime import PHYSICAL_CONTEXT, RuntimeProfile, endpoint_request, guard


EXPERIMENT_ID = "010_acquisition_granularity"
CASE_IDS = ("E10-PAGE-ALPHA", "E10-PAGE-BETA")
SEEDS = (173205, 223607)
CONDITIONS = ("L0", "L1")
READ_MODES = {"L0": "actor_selected_count", "L1": "maximal_bounded_page"}
CALL_LIMIT = 10


def _ledger(namespace: str, token: str) -> bytes:
    lines = [f"{namespace.upper()}_{index:03d} = {f'{token}-{index:03d}-exact-custody'!r}\n" for index in range(1, 199)]
    return "".join(lines).encode("utf-8")


def _case(
    fixture_id: str,
    *,
    first: str,
    second: str,
    token: str,
    target: str,
) -> dict[str, Any]:
    files = {
        f"ledger/{first}.py": _ledger(first, token),
        f"ledger/{second}.py": _ledger(second, token[::-1]),
        target: b"def completed_ledgers() -> int:\n    return 0\n",
    }
    task = (
        f"Read both exact ledger files completely: `ledger/{first}.py` and `ledger/{second}.py`. "
        f"Then repair `{target}` so `completed_ledgers()` returns the number of completed ledger files. "
        "Run check `prefork`, then call `fork_ready`. Do not infer ledger contents from P0; acquire the exact files."
    )
    checker = (
        f"from {target[:-3].replace('/', '.')} import completed_ledgers\n"
        "assert completed_ledgers() == 2\n"
        "print('pass')\n"
    ).encode("utf-8")
    return {
        "fixture_id": fixture_id,
        "family": "fresh_exact_full-file-acquisition",
        "task": task,
        "files": files,
        "required_full_reads": (f"ledger/{first}.py", f"ledger/{second}.py"),
        "target": target,
        "checker": checker,
        "patch": {"path": target, "old": "    return 0\n", "new": "    return 2\n"},
    }


def case_definitions() -> tuple[dict[str, Any], ...]:
    return (
        _case("E10-PAGE-ALPHA", first="topaz", second="walnut", token="R7~", target="stage/tally.py"),
        _case("E10-PAGE-BETA", first="velvet", second="zephyr", token="Q4%", target="state/count.py"),
    )


def schedule() -> dict[str, Any]:
    cells = []
    ordinal = 0
    for case_index, case_id in enumerate(CASE_IDS):
        for seed_index, seed in enumerate(SEEDS):
            order = CONDITIONS if (case_index + seed_index) % 2 == 0 else tuple(reversed(CONDITIONS))
            for condition in order:
                ordinal += 1
                cells.append(
                    {
                        "ordinal": ordinal,
                        "fixture_id": case_id,
                        "seed": seed,
                        "condition": condition,
                        "read_mode": READ_MODES[condition],
                    }
                )
    return {
        "schema_version": "experiment-010-acquisition-schedule-v1",
        "conditions": list(CONDITIONS),
        "cases": list(CASE_IDS),
        "seeds": list(SEEDS),
        "cells": cells,
        "attempts_per_cell": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
        "reasoning_budget_tokens": 512,
    }


def _inventory(root: Path, *, excluded: set[str]) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        rows.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return rows


def construct_bank(target: Path) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True)
    cases = []
    for case in case_definitions():
        fixture_id = case["fixture_id"]
        model = target / "model_visible" / fixture_id
        execution = target / "execution_only" / fixture_id
        evaluator = target / "evaluator_only" / fixture_id
        atomic_write(model / "TASK.txt", case["task"].encode("utf-8"))
        for path, data in case["files"].items():
            atomic_write(model / "candidate" / Path(*path.split("/")), data)
        atomic_write(execution / "checks" / "prefork.py", case["checker"])
        atomic_write(execution / "checks" / "public.py", case["checker"])
        initial = Candidate.create(case["files"])
        patch = case["patch"]
        known_good, _ = initial.patch(
            path=patch["path"],
            old=patch["old"],
            new=patch["new"],
            expected_candidate_id=initial.candidate_id,
            expected_file_sha256=initial.file_sha256(patch["path"]),
        )
        fixture_manifest = {
            "schema_version": "experiment-010-fixture-v1",
            "fixture_id": fixture_id,
            "family": case["family"],
            "candidate_files": [
                {"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)}
                for path, data in sorted(case["files"].items())
            ],
            "initial_candidate_id": initial.candidate_id,
            "required_full_reads": list(case["required_full_reads"]),
            "final_target": "unavailable/final.py",
            "probe_id": None,
            "probe_body_present": False,
            "probe_body_sha256": None,
        }
        atomic_write(execution / "FIXTURE.json", canonical_json_bytes(fixture_manifest))
        atomic_write(evaluator / "hidden.py", case["checker"])
        atomic_write(
            evaluator / "TRUTH.json",
            canonical_json_bytes(
                {
                    "fixture_id": fixture_id,
                    "known_good_candidate_id": known_good.candidate_id,
                    "required_full_reads": list(case["required_full_reads"]),
                    "patch": patch,
                }
            ),
        )
        cases.append(
            {
                "fixture_id": fixture_id,
                "task_sha256": sha256_bytes(case["task"].encode("utf-8")),
                "initial_candidate_id": initial.candidate_id,
            }
        )
    files = _inventory(target, excluded={"BANK_MANIFEST.json"})
    manifest = {
        "schema_version": "experiment-010-fresh-bank-v1",
        "status": "sealed_offline_not_actor_exposed",
        "cases": cases,
        "files": files,
        "bank_id": "E10BANK-" + sha256_bytes(canonical_json_bytes(files)),
        "evaluator_model_visible_overlap": False,
    }
    atomic_write(target / "BANK_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_bank(target: Path) -> dict[str, Any]:
    observed = load_json_strict((target / "BANK_MANIFEST.json").read_bytes())
    if observed["files"] != _inventory(target, excluded={"BANK_MANIFEST.json"}):
        raise ValueError("Experiment 010 bank inventory differs")
    with tempfile.TemporaryDirectory(prefix="e10-bank-") as raw:
        rebuilt = construct_bank(Path(raw) / "bank")
        if canonical_json_bytes(rebuilt) != canonical_json_bytes(observed):
            raise ValueError("Experiment 010 bank reconstruction differs")
    return {"verified": True, "bank_id": observed["bank_id"], "file_count": len(observed["files"])}


def _scripted_actions(fixture: Fixture, read_mode: str) -> list[dict[str, Any]]:
    truth_patch = next(case["patch"] for case in case_definitions() if case["fixture_id"] == fixture.fixture_id)
    successor, _ = fixture.initial.patch(
        path=truth_patch["path"],
        old=truth_patch["old"],
        new=truth_patch["new"],
        expected_candidate_id=fixture.initial.candidate_id,
        expected_file_sha256=fixture.initial.file_sha256(truth_patch["path"]),
    )
    reads = []
    for path in fixture.required_full_reads:
        action = {"action": "read", "path": path, "start_line": 1}
        if read_mode == "actor_selected_count":
            action["line_count"] = 500
        reads.append(action)
    return [
        {"action": "begin"},
        *reads,
        {
            "action": "patch",
            "path": truth_patch["path"],
            "old": truth_patch["old"],
            "new": truth_patch["new"],
            "expected_candidate_id": fixture.initial.candidate_id,
            "expected_file_sha256": fixture.initial.file_sha256(truth_patch["path"]),
        },
        {"action": "check", "check_id": "prefork", "expected_candidate_id": successor.candidate_id},
        {"action": "fork_ready", "expected_candidate_id": successor.candidate_id},
    ]


def qualify_scripted(*, bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    results = []
    with tempfile.TemporaryDirectory(prefix="e10-scripted-") as raw:
        root = Path(raw)
        for case_id in CASE_IDS:
            fixture = load_fixture(bank, case_id)
            for condition in CONDITIONS:
                read_mode = READ_MODES[condition]
                actions = _scripted_actions(fixture, read_mode)
                actor = ScriptedActor(
                    profile,
                    SEEDS[0],
                    lambda _request, queue=actions: queue.pop(0),
                    read_mode=read_mode,
                )
                outcome = run_prefix(
                    fixture,
                    seed=SEEDS[0],
                    actor=actor,
                    output_dir=root / f"{case_id}-{condition}",
                    profile=profile,
                    prefix_call_limit=CALL_LIMIT,
                    continuation_call_limit=1,
                    reasoning_enabled=False,
                    read_mode=read_mode,
                    acquisition_contract=True,
                    require_pressure_eligible=False,
                )
                verification = verify_run(outcome.output_dir)
                replayed = replay_prefix(
                    fixture,
                    outcome.output_dir,
                    read_mode=read_mode,
                    require_pressure_eligible=False,
                )
                if not outcome.state.fork_ready or not outcome.state.prefork_check_passed:
                    raise ValueError("scripted acquisition path did not close")
                if replayed.state.candidate.candidate_id != outcome.state.candidate.candidate_id:
                    raise ValueError("scripted acquisition replay candidate differs")
                results.append(
                    {
                        "fixture_id": case_id,
                        "condition": condition,
                        "calls": outcome.calls,
                        "candidate_id": outcome.state.candidate.candidate_id,
                        "verified_records": verification["record_count"],
                    }
                )
    return {"verified": True, "paths": results, "model_calls": 0}


def construct_package(target: Path, *, bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True)
    cells = []
    for row in schedule()["cells"]:
        fixture = load_fixture(bank, row["fixture_id"])
        request = build_request(
            fixture_id=fixture.fixture_id,
            task=fixture.task,
            candidate=fixture.initial,
            stage="setup",
            visible_history=[],
            prefix_calls_used=0,
            continuation_calls_used=0,
            probe_id=None,
            observations=[],
            reconstructed=False,
            fork_binding=None,
            prefix_call_limit=CALL_LIMIT,
            continuation_call_limit=1,
            read_mode=row["read_mode"],
            acquisition_contract=True,
        )
        endpoint = endpoint_request(
            profile,
            request,
            stage="setup",
            probe_id=None,
            seed=row["seed"],
            reasoning_enabled=True,
            read_mode=row["read_mode"],
        )
        rendered = render_reasoning_prompt(request, enabled=True)
        admission = guard(profile, request, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True)
        cell_root = target / f"cell-{row['ordinal']:02d}"
        atomic_write(cell_root / "initial-coding-request.json", request)
        atomic_write(cell_root / "initial-endpoint-request.json", endpoint)
        atomic_write(cell_root / "initial-rendered-prompt.txt", rendered)
        cells.append(
            {
                **row,
                "coding_request_sha256": sha256_bytes(request),
                "endpoint_request_sha256": sha256_bytes(endpoint),
                "rendered_prompt_sha256": sha256_bytes(rendered),
                "initial_admission": admission,
            }
        )
    files = _inventory(target, excluded={"PACKAGE_MANIFEST.json"})
    manifest = {
        "schema_version": "experiment-010-execution-package-v1",
        "bank_id": verify_bank(bank)["bank_id"],
        "schedule_sha256": sha256_bytes(canonical_json_bytes(schedule())),
        "cells": cells,
        "files": files,
        "package_id": "E10PKG-" + sha256_bytes(canonical_json_bytes(files)),
        "evaluator_bytes_present": False,
    }
    atomic_write(target / "PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_package(target: Path, *, bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    observed = load_json_strict((target / "PACKAGE_MANIFEST.json").read_bytes())
    if observed["files"] != _inventory(target, excluded={"PACKAGE_MANIFEST.json"}):
        raise ValueError("Experiment 010 package inventory differs")
    with tempfile.TemporaryDirectory(prefix="e10-package-") as raw:
        rebuilt = construct_package(Path(raw) / "package", bank=bank, profile=profile)
        if canonical_json_bytes(rebuilt) != canonical_json_bytes(observed):
            raise ValueError("Experiment 010 package reconstruction differs")
    return {"verified": True, "package_id": observed["package_id"], "file_count": len(observed["files"])}
