from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from .observation_recurrence import _fresh_observation_case
from .recurrent_pressure import (
    FINAL_CALL_LIMIT,
    MIDDLE_CALL_LIMIT,
    PREFIX_CALL_LIMIT,
    _inventory,
    load_recurrent_fixture,
    verify_bank,
)
from .request import build_request, render_reasoning_prompt
from .runtime import PHYSICAL_CONTEXT, REASONING_BUDGET, RuntimeProfile, endpoint_request, guard


EXPERIMENT_ID = "011_recurrent_acquisition_granularity"
CASE_IDS = ("E11-OBS-IOTA", "E11-OBS-KAPPA")
SEEDS = (173205, 223607)
CONDITIONS = ("T25-L0", "T25-L1")
READ_MODES = {"T25-L0": "actor_selected_count", "T25-L1": "maximal_bounded_page"}
OUTPUT_ROOT = r"C:\e11-primary"
PORT = 18113
MAXIMUM_HTTP_COMPLETION_CALLS = 140


def case_definitions() -> tuple[dict[str, Any], ...]:
    return (
        _fresh_observation_case(
            fixture_id=CASE_IDS[0], namespace="harbor", label_name="harbor_label",
            header_name="harbor_header", codec_name="encoded_harbor",
            archive_names=("agate", "birch", "coral"),
            bridge_names=("dahlia", "ebony", "flax", "garnet"),
            marker_v1="H2@@", marker_v2="J7@@",
        ),
        _fresh_observation_case(
            fixture_id=CASE_IDS[1], namespace="vector", label_name="vector_label",
            header_name="vector_header", codec_name="encoded_vector",
            archive_names=("hazel", "ivory", "jade"),
            bridge_names=("kelp", "linen", "moss", "nickel"),
            marker_v1="Q5^^", marker_v2="X8^^",
        ),
    )


def schedule() -> dict[str, Any]:
    cells = []
    ordinal = 0
    for case_index, fixture_id in enumerate(CASE_IDS):
        for seed_index, seed in enumerate(SEEDS):
            ordinal += 1
            order = CONDITIONS if (case_index + seed_index) % 2 == 0 else tuple(reversed(CONDITIONS))
            cells.append({"ordinal": ordinal, "fixture_id": fixture_id, "seed": seed, "branch_order": list(order)})
    return {
        "schema_version": "experiment-011-recurrent-acquisition-schedule-v1",
        "cases": list(CASE_IDS), "seeds": list(SEEDS), "conditions": list(CONDITIONS),
        "prefixes": 4, "branches": 8, "cells": cells, "attempts_per_branch": 1,
        "retries": 0, "repairs": 0, "rescues": 0, "reasoning_budget_tokens": REASONING_BUDGET,
    }


def construct_package(target: Path, *, bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True)
    cells = []
    for row in schedule()["cells"]:
        fixture = load_recurrent_fixture(bank, row["fixture_id"])
        base = fixture.prefix_fixture()
        request = build_request(
            fixture_id=base.fixture_id, task=base.task, candidate=base.initial, stage="setup",
            visible_history=[], prefix_calls_used=0, continuation_calls_used=0, probe_id=base.probe_id,
            observations=[], reconstructed=False, fork_binding=None, prefix_call_limit=PREFIX_CALL_LIMIT,
            continuation_call_limit=MIDDLE_CALL_LIMIT,
        )
        endpoint = endpoint_request(
            profile, request, stage="setup", probe_id=base.probe_id, seed=row["seed"], reasoning_enabled=True,
        )
        rendered = render_reasoning_prompt(request, enabled=True)
        admission = guard(profile, request, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True)
        cell_root = target / f"cell-{row['ordinal']:02d}"
        atomic_write(cell_root / "initial-coding-request.json", request)
        atomic_write(cell_root / "initial-endpoint-request.json", endpoint)
        atomic_write(cell_root / "initial-rendered-prompt.txt", rendered)
        cells.append({
            **row, "expected_call_id": f"{row['fixture_id']}-S{row['seed']}-P01",
            "coding_request_sha256": sha256_bytes(request), "endpoint_request_sha256": sha256_bytes(endpoint),
            "rendered_prompt_sha256": sha256_bytes(rendered), "initial_admission": admission,
        })
    files = _inventory(target, excluded={"PACKAGE_MANIFEST.json"})
    manifest = {
        "schema_version": "experiment-011-recurrent-acquisition-package-v1",
        "bank_id": verify_bank(bank)["bank_id"],
        "schedule_sha256": sha256_bytes(canonical_json_bytes(schedule())),
        "conditions": list(CONDITIONS), "treatment_begins_after_shared_prefix": True,
        "read_modes": READ_MODES, "observation_directory_version": 2,
        "server_reasoning_budget_tokens": REASONING_BUDGET,
        "prefix_call_limit": PREFIX_CALL_LIMIT, "middle_call_limit": MIDDLE_CALL_LIMIT,
        "final_call_limit": FINAL_CALL_LIMIT, "cells": cells, "files": files,
        "evaluator_bytes_present": False,
        "package_id": "E11PKG-" + sha256_bytes(canonical_json_bytes(files)),
    }
    atomic_write(target / "PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_package(target: Path, *, bank: Path, profile: RuntimeProfile) -> dict[str, Any]:
    observed = load_json_strict((target / "PACKAGE_MANIFEST.json").read_bytes())
    if observed["files"] != _inventory(target, excluded={"PACKAGE_MANIFEST.json"}):
        raise ValueError("Experiment 011 package inventory differs")
    with tempfile.TemporaryDirectory(prefix="e11-package-") as raw:
        rebuilt = construct_package(Path(raw) / "package", bank=bank, profile=profile)
        if canonical_json_bytes(rebuilt) != canonical_json_bytes(observed):
            raise ValueError("Experiment 011 package reconstruction differs")
    return {"verified": True, "package_id": observed["package_id"], "file_count": len(observed["files"])}


def expected_authorization(experiment: Path) -> dict[str, Any]:
    bank = load_json_strict((experiment / "fresh_bank" / "BANK_MANIFEST.json").read_bytes())
    package = load_json_strict((experiment / "execution_package" / "PACKAGE_MANIFEST.json").read_bytes())
    closure = load_json_strict((experiment / "EXECUTABLE_CLOSURE.json").read_bytes())
    profile = load_json_strict((experiment / "RUNTIME_PROFILE.json").read_bytes())
    return {
        "schema_version": "experiment-011-measured-authorization-v1",
        "status": "owner_authorized_exact_recurrent_acquisition_execution",
        "owner_statement": "Proceed as recommended with the fresh recurrent L0/L1 comparison.",
        "bank_id": bank["bank_id"],
        "bank_manifest_sha256": sha256_file(experiment / "fresh_bank" / "BANK_MANIFEST.json"),
        "package_id": package["package_id"],
        "package_manifest_sha256": sha256_file(experiment / "execution_package" / "PACKAGE_MANIFEST.json"),
        "closure_manifest_sha256": sha256_file(experiment / "EXECUTABLE_CLOSURE.json"),
        "closure_aggregate_sha256": closure["aggregate_sha256"],
        "schedule_sha256": sha256_file(experiment / "SCHEDULE.json"),
        "runtime_profile_sha256": sha256_file(experiment / "RUNTIME_PROFILE.json"),
        "actor_sha256": profile["model_sha256"], "conditions": list(CONDITIONS),
        "shared_prefixes": 4, "postboundary_branches": 8, "attempts_per_branch": 1,
        "retries": 0, "repairs": 0, "rescues": 0,
        "maximum_http_completion_calls": MAXIMUM_HTTP_COMPLETION_CALLS,
        "treatment_begins_after_shared_prefix": True, "observation_directory_version": 2,
        "no_read_suppression_or_result_reuse": True, "response_seal_before_evaluator_access": True,
        "output_root": OUTPUT_ROOT, "port": PORT, "automatic_successor": False,
        "server_reasoning_budget_tokens": REASONING_BUDGET,
    }


def validate_authorization(experiment: Path) -> dict[str, Any]:
    observed = load_json_strict((experiment / "MEASURED_AUTHORIZATION.json").read_bytes())
    expected = expected_authorization(experiment)
    if canonical_json_bytes(observed) != canonical_json_bytes(expected):
        raise ValueError("Experiment 011 authorization differs")
    return {"verified": True, "authorization_sha256": sha256_file(experiment / "MEASURED_AUTHORIZATION.json")}
