from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .fixture import load_fixture
from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from .progress import BRANCH_CALL_LIMIT, PREFIX_CALL_LIMIT, progress_pointer, verify_bank
from .request import build_request
from .runtime import PHYSICAL_CONTEXT, RuntimeProfile, endpoint_request, guard, render_prompt


PACKAGE_SCHEMA = "experiment-003-progress-execution-package-v1"
CLOSURE_SCHEMA = "experiment-003-progress-executable-closure-v1"
AUTHORIZATION_SCHEMA = "experiment-003-progress-measured-authorization-v1"
OUTPUT_ROOT = r"C:\e3m-primary"
MAXIMUM_COMPLETION_CALLS = 68


def _inventory(root: Path, *, excluded: set[str] | None = None) -> list[dict[str, Any]]:
    excluded = excluded or set()
    rows = []
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


def _profile(value: dict[str, Any]) -> RuntimeProfile:
    return RuntimeProfile(
        model_alias=value["model_alias"], model_path=Path(value["model_path"]), model_sha256=value["model_sha256"],
        tokenizer_path=Path(value["tokenizer_path"]), tokenizer_sha256=value["tokenizer_sha256"],
        server_path=Path(value["server_path"]), server_sha256=value["server_sha256"],
        runtime_root=Path(value["runtime_root"]), build=value["build"],
    )


def construct_execution_package(target: Path, *, bank_root: Path, schedule_path: Path, runtime_profile_path: Path) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True)
    bank = verify_bank(bank_root)
    schedule_bytes = schedule_path.read_bytes()
    schedule = load_json_strict(schedule_bytes)
    profile = _profile(load_json_strict(runtime_profile_path.read_bytes()))
    prefixes = []
    for row in schedule["prefix_order"]:
        fixture = load_fixture(bank_root, row["fixture_id"])
        request = build_request(
            fixture_id=fixture.fixture_id, task=fixture.task, candidate=fixture.initial, stage="setup",
            visible_history=[], prefix_calls_used=0, continuation_calls_used=0, probe_id=fixture.probe_id,
            observations=[], reconstructed=False, fork_binding=None,
            prefix_call_limit=PREFIX_CALL_LIMIT, continuation_call_limit=BRANCH_CALL_LIMIT,
        )
        endpoint = endpoint_request(profile, request, stage="setup", probe_id=fixture.probe_id, seed=row["seed"])
        rendered = render_prompt(request)
        admission = guard(profile, request, active_total_ceiling=PHYSICAL_CONTEXT)
        if not admission["authorized"]:
            raise ValueError("initial progress request is not admitted")
        cell = f"prefix-{row['ordinal']:02d}"
        atomic_write(target / cell / "initial-coding-request.json", request)
        atomic_write(target / cell / "initial-endpoint-request.json", endpoint)
        atomic_write(target / cell / "initial-rendered-prompt.txt", rendered)
        pointer = progress_pointer(bank_root, fixture.fixture_id)
        atomic_write(target / cell / "T25-P-progress-pointer.json", canonical_json_bytes(pointer))
        prefixes.append(
            {
                "ordinal": row["ordinal"], "fixture_id": fixture.fixture_id, "seed": row["seed"],
                "branch_order": row["branch_order"], "initial_call_id": f"{fixture.fixture_id}-S{row['seed']}-P01",
                "initial_admission": admission, "coding_request_sha256": sha256_bytes(request),
                "endpoint_request_sha256": sha256_bytes(endpoint), "rendered_prompt_sha256": sha256_bytes(rendered),
                "progress_pointer_sha256": sha256_bytes(canonical_json_bytes(pointer)),
            }
        )
    files = _inventory(target)
    manifest = {
        "schema_version": PACKAGE_SCHEMA, "bank_id": bank["bank_id"],
        "bank_manifest_sha256": sha256_file(bank_root / "BANK_MANIFEST.json"),
        "schedule_sha256": sha256_bytes(schedule_bytes), "runtime_profile_sha256": sha256_file(runtime_profile_path),
        "prefix_call_limit": PREFIX_CALL_LIMIT, "branch_call_limit": BRANCH_CALL_LIMIT,
        "one_shot_probe": True, "conditions": ["T25-M", "T25-P"], "prefixes": prefixes,
        "files": files, "package_id": "E3PKG-" + sha256_bytes(canonical_json_bytes(files)),
        "evaluator_bytes_present": False,
    }
    atomic_write(target / "PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_execution_package(target: Path, *, bank_root: Path, schedule_path: Path, runtime_profile_path: Path) -> dict[str, Any]:
    manifest = load_json_strict((target / "PACKAGE_MANIFEST.json").read_bytes())
    files = _inventory(target, excluded={"PACKAGE_MANIFEST.json"})
    if manifest["schema_version"] != PACKAGE_SCHEMA or files != manifest["files"]:
        raise ValueError("progress execution package differs")
    if manifest["package_id"] != "E3PKG-" + sha256_bytes(canonical_json_bytes(files)):
        raise ValueError("progress execution package identity differs")
    with tempfile.TemporaryDirectory(prefix="e3-pkg-") as raw:
        rebuilt = Path(raw) / "package"
        expected = construct_execution_package(
            rebuilt, bank_root=bank_root, schedule_path=schedule_path, runtime_profile_path=runtime_profile_path
        )
        if canonical_json_bytes(expected) != canonical_json_bytes(manifest):
            raise ValueError("progress package reconstruction differs")
        for row in files:
            relative = Path(*row["path"].split("/"))
            if (rebuilt / relative).read_bytes() != (target / relative).read_bytes():
                raise ValueError("progress package bytes differ")
    return {"verified": True, "package_id": manifest["package_id"], "file_count": len(files)}


def build_executable_closure(repo_root: Path) -> dict[str, Any]:
    paths = sorted((repo_root / "src" / "working_set_exp").glob("*.py"))
    paths.append(repo_root / "scripts" / "run_progress_measured.py")
    rows = []
    for path in paths:
        if not path.is_file() or path.is_symlink():
            raise ValueError("progress closure path is missing or linked")
        rows.append({"path": path.relative_to(repo_root).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"schema_version": CLOSURE_SCHEMA, "files": rows, "aggregate_sha256": sha256_bytes(canonical_json_bytes(rows))}


def verify_executable_closure(repo_root: Path, manifest_path: Path) -> dict[str, Any]:
    expected = load_json_strict(manifest_path.read_bytes())
    observed = build_executable_closure(repo_root)
    if canonical_json_bytes(expected) != canonical_json_bytes(observed):
        raise ValueError("progress executable closure differs")
    return {"verified": True, "aggregate_sha256": observed["aggregate_sha256"], "file_count": len(observed["files"])}


def expected_authorization(*, experiment: Path, closure_path: Path, package_path: Path) -> dict[str, Any]:
    bank = load_json_strict((experiment / "fresh_bank" / "BANK_MANIFEST.json").read_bytes())
    profile = load_json_strict((experiment / "RUNTIME_PROFILE.json").read_bytes())
    closure = load_json_strict(closure_path.read_bytes())
    return {
        "schema_version": AUTHORIZATION_SCHEMA,
        "status": "owner_authorized_exact_progress_pointer_measured_execution",
        "owner_statement": "Run recommendation",
        "study_authorization_sha256": sha256_file(experiment / "STUDY_AUTHORIZATION.json"),
        "execution_package_manifest_sha256": sha256_file(package_path / "PACKAGE_MANIFEST.json"),
        "executable_closure_manifest_sha256": sha256_file(closure_path),
        "executable_closure_aggregate_sha256": closure["aggregate_sha256"],
        "bank_id": bank["bank_id"], "bank_manifest_sha256": sha256_file(experiment / "fresh_bank" / "BANK_MANIFEST.json"),
        "schedule_sha256": sha256_file(experiment / "MEASURED_SCHEDULE.json"),
        "runtime_profile_sha256": sha256_file(experiment / "RUNTIME_PROFILE.json"),
        "actor_sha256": profile["model_sha256"], "conditions": ["T25-M", "T25-P"],
        "prefixes": 2, "branches": 4, "maximum_completion_calls": MAXIMUM_COMPLETION_CALLS,
        "attempts_per_call": 1, "retries": 0, "repairs": 0, "rescues": 0,
        "one_shot_probe": True, "output_root": OUTPUT_ROOT, "response_seal_before_evaluator_access": True,
        "automatic_successor": False,
    }


def validate_authorization(*, experiment: Path, closure_path: Path, package_path: Path, authorization_path: Path) -> dict[str, Any]:
    observed = load_json_strict(authorization_path.read_bytes())
    expected = expected_authorization(experiment=experiment, closure_path=closure_path, package_path=package_path)
    if canonical_json_bytes(observed) != canonical_json_bytes(expected):
        raise ValueError("progress measured authorization differs")
    return {"verified": True, "authorization_sha256": sha256_file(authorization_path)}


def seal_response_tree(output_root: Path) -> dict[str, Any]:
    files = _inventory(output_root, excluded={"RECEIPT.json", "RESPONSE_SEAL.json"})
    seal = {
        "schema_version": "experiment-003-progress-response-seal-v1", "files": files,
        "aggregate_sha256": sha256_bytes(canonical_json_bytes(files)), "evaluator_truth_opened": False,
    }
    atomic_write(output_root / "RESPONSE_SEAL.json", canonical_json_bytes(seal))
    return seal
