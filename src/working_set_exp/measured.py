from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .bank import verify_bank
from .fixture import load_fixture
from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from .request import build_request
from .runtime import PHYSICAL_CONTEXT, LiveActor, PreparedCall, RuntimeProfile, endpoint_request, guard, render_prompt


PACKAGE_SCHEMA = "experiment-002-measured-execution-package-v1"
CLOSURE_SCHEMA = "experiment-002-executable-closure-v1"
AUTHORIZATION_SCHEMA = "experiment-002-measured-execution-authorization-v1"
OUTPUT_ROOT = r"C:\e2m-primary"
MAXIMUM_COMPLETION_CALLS = 120


def _inventory(root: Path, *, excluded: set[str] | None = None) -> list[dict[str, Any]]:
    excluded = excluded or set()
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        if path.is_symlink():
            raise ValueError("linked files are prohibited")
        rows.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return rows


def package_identity(files: list[dict[str, Any]]) -> str:
    return sha256_bytes(canonical_json_bytes(files))


def construct_execution_package(
    target: Path,
    *,
    bank_root: Path,
    schedule_path: Path,
    runtime_profile_path: Path,
) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True)
    bank = verify_bank(bank_root)
    schedule_bytes = schedule_path.read_bytes()
    schedule = load_json_strict(schedule_bytes)
    profile = RuntimeProfile(**_runtime_kwargs(load_json_strict(runtime_profile_path.read_bytes())))
    cells: list[dict[str, Any]] = []
    for row in schedule["fork_order"]:
        fixture = load_fixture(bank_root, row["fixture_id"])
        request = build_request(
            fixture_id=fixture.fixture_id,
            task=fixture.task,
            candidate=fixture.initial,
            stage="setup",
            visible_history=[],
            prefix_calls_used=0,
            continuation_calls_used=0,
            probe_id=fixture.probe_id,
            observations=[],
            reconstructed=False,
            fork_binding=None,
        )
        endpoint = endpoint_request(profile, request, stage="setup", probe_id=fixture.probe_id, seed=row["seed"])
        rendered = render_prompt(request)
        admission = guard(profile, request, active_total_ceiling=PHYSICAL_CONTEXT)
        if not admission["authorized"]:
            raise ValueError("frozen initial request is not admitted")
        cell = f"fork-{row['ordinal']:02d}"
        atomic_write(target / cell / "initial-coding-request.json", request)
        atomic_write(target / cell / "initial-endpoint-request.json", endpoint)
        atomic_write(target / cell / "initial-rendered-prompt.txt", rendered)
        cells.append(
            {
                "ordinal": row["ordinal"],
                "fixture_id": fixture.fixture_id,
                "seed": row["seed"],
                "initial_call_id": f"{fixture.fixture_id}-S{row['seed']}-P01",
                "initial_admission": admission,
                "coding_request_sha256": sha256_bytes(request),
                "endpoint_request_sha256": sha256_bytes(endpoint),
                "rendered_prompt_sha256": sha256_bytes(rendered),
            }
        )
    files = _inventory(target)
    manifest = {
        "schema_version": PACKAGE_SCHEMA,
        "bank_id": bank["bank_id"],
        "bank_manifest_sha256": sha256_file(bank_root / "BANK_MANIFEST.json"),
        "schedule_sha256": sha256_bytes(schedule_bytes),
        "runtime_profile_sha256": sha256_file(runtime_profile_path),
        "branch_order_within_fork": schedule["branch_order_within_fork"],
        "cells": cells,
        "files": files,
        "package_id": "E2PKG-" + package_identity(files),
        "evaluator_bytes_present": False,
    }
    atomic_write(target / "PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def _runtime_kwargs(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "server_path": Path(value["server_path"]),
        "tokenizer_path": Path(value["tokenizer_path"]),
        "runtime_root": Path(value["runtime_root"]),
        "model_path": Path(value["model_path"]),
        "model_alias": value["model_alias"],
        "model_sha256": value["model_sha256"],
        "server_sha256": value["server_sha256"],
        "tokenizer_sha256": value["tokenizer_sha256"],
        "build": value["build"],
    }


def verify_execution_package(
    target: Path,
    *,
    bank_root: Path,
    schedule_path: Path,
    runtime_profile_path: Path,
) -> dict[str, Any]:
    manifest = load_json_strict((target / "PACKAGE_MANIFEST.json").read_bytes())
    if manifest["schema_version"] != PACKAGE_SCHEMA:
        raise ValueError("execution package schema differs")
    files = _inventory(target, excluded={"PACKAGE_MANIFEST.json"})
    if files != manifest["files"] or manifest["package_id"] != "E2PKG-" + package_identity(files):
        raise ValueError("execution package inventory differs")
    with __import__("tempfile").TemporaryDirectory(prefix="e2-pkg-") as raw:
        rebuilt = Path(raw) / "package"
        expected = construct_execution_package(
            rebuilt,
            bank_root=bank_root,
            schedule_path=schedule_path,
            runtime_profile_path=runtime_profile_path,
        )
        if canonical_json_bytes(expected) != canonical_json_bytes(manifest):
            raise ValueError("execution package reconstruction differs")
        for row in files:
            relative = Path(*row["path"].split("/"))
            if (rebuilt / relative).read_bytes() != (target / relative).read_bytes():
                raise ValueError("execution package bytes differ")
    return {"verified": True, "package_id": manifest["package_id"], "file_count": len(files)}


def build_executable_closure(repo_root: Path) -> dict[str, Any]:
    paths = sorted((repo_root / "src" / "working_set_exp").glob("*.py"))
    paths.append(repo_root / "scripts" / "run_measured.py")
    rows = []
    for path in paths:
        if not path.is_file() or path.is_symlink():
            raise ValueError("closure path is missing or linked")
        rows.append(
            {
                "path": path.relative_to(repo_root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "schema_version": CLOSURE_SCHEMA,
        "files": rows,
        "aggregate_sha256": sha256_bytes(canonical_json_bytes(rows)),
    }


def verify_executable_closure(repo_root: Path, manifest_path: Path) -> dict[str, Any]:
    expected = load_json_strict(manifest_path.read_bytes())
    observed = build_executable_closure(repo_root)
    if canonical_json_bytes(expected) != canonical_json_bytes(observed):
        raise ValueError("measured executable closure differs")
    return {"verified": True, "aggregate_sha256": observed["aggregate_sha256"], "file_count": len(observed["files"])}


def expected_authorization(
    *, repo_root: Path, experiment: Path, closure_path: Path, package_path: Path
) -> dict[str, Any]:
    schedule_path = experiment / "MEASURED_SCHEDULE.json"
    bank_root = experiment / "fresh_bank"
    package_manifest = package_path / "PACKAGE_MANIFEST.json"
    profile_path = experiment / "RUNTIME_PROFILE.json"
    closure = load_json_strict(closure_path.read_bytes())
    profile = load_json_strict(profile_path.read_bytes())
    bank = load_json_strict((bank_root / "BANK_MANIFEST.json").read_bytes())
    return {
        "schema_version": AUTHORIZATION_SCHEMA,
        "status": "owner_authorized_exact_primary_measured_execution",
        "owner_statement": "Let's plan it and test it. You have authority to do it all.",
        "study_authorization_sha256": sha256_file(experiment / "STUDY_AUTHORIZATION.json"),
        "execution_package_manifest_sha256": sha256_file(package_manifest),
        "executable_closure_manifest_sha256": sha256_file(closure_path),
        "executable_closure_aggregate_sha256": closure["aggregate_sha256"],
        "bank_id": bank["bank_id"],
        "bank_manifest_sha256": sha256_file(bank_root / "BANK_MANIFEST.json"),
        "schedule_sha256": sha256_file(schedule_path),
        "runtime_profile_sha256": sha256_file(profile_path),
        "actor_sha256": profile["model_sha256"],
        "conditions": ["C50", "T25"],
        "forks": 4,
        "branches": 8,
        "maximum_completion_calls": MAXIMUM_COMPLETION_CALLS,
        "attempts_per_call": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
        "output_root": OUTPUT_ROOT,
        "response_seal_before_evaluator_access": True,
        "automatic_successor": False,
    }


def validate_authorization(
    *, repo_root: Path, experiment: Path, closure_path: Path, package_path: Path, authorization_path: Path
) -> dict[str, Any]:
    observed = load_json_strict(authorization_path.read_bytes())
    expected = expected_authorization(
        repo_root=repo_root,
        experiment=experiment,
        closure_path=closure_path,
        package_path=package_path,
    )
    if canonical_json_bytes(observed) != canonical_json_bytes(expected):
        raise ValueError("measured authorization differs from exact authorized payload")
    return {"verified": True, "authorization_sha256": sha256_file(authorization_path)}


@dataclass
class FrozenInitialActor:
    inner: LiveActor
    expected_call_id: str
    package_cell: Path
    checked: bool = False

    def prepare(
        self,
        request: bytes,
        *,
        stage: str,
        probe_id: str | None,
        call_id: str,
        active_total_ceiling: int,
    ) -> PreparedCall:
        prepared = self.inner.prepare(
            request,
            stage=stage,
            probe_id=probe_id,
            call_id=call_id,
            active_total_ceiling=active_total_ceiling,
        )
        if not self.checked:
            if call_id != self.expected_call_id or stage != "setup":
                raise ValueError("first measured call identity differs")
            comparisons = (
                (request, "initial-coding-request.json"),
                (prepared.endpoint_request, "initial-endpoint-request.json"),
                (prepared.rendered_prompt, "initial-rendered-prompt.txt"),
            )
            for observed, name in comparisons:
                if observed != (self.package_cell / name).read_bytes():
                    raise ValueError(f"first measured {name} differs from freeze")
            self.checked = True
        return prepared

    def invoke(self, prepared: PreparedCall):
        return self.inner.invoke(prepared)


def seal_response_tree(output_root: Path) -> dict[str, Any]:
    files = _inventory(output_root, excluded={"RECEIPT.json", "RESPONSE_SEAL.json"})
    seal = {
        "schema_version": "experiment-002-measured-response-seal-v1",
        "files": files,
        "aggregate_sha256": sha256_bytes(canonical_json_bytes(files)),
        "evaluator_truth_opened": False,
    }
    atomic_write(output_root / "RESPONSE_SEAL.json", canonical_json_bytes(seal))
    return seal
