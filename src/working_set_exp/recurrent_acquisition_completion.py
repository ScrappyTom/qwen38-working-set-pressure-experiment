from __future__ import annotations

from pathlib import Path
from typing import Any

from .jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


OUTPUT_ROOT = r"C:\e11-completion"
PORT = 18114
CELL_ORDINAL = 4
FIXTURE_ID = "E11-OBS-KAPPA"
SEED = 223607
BRANCH_ORDER = ("T25-L0", "T25-L1")
MAXIMUM_HTTP_COMPLETION_CALLS = 52
PRIOR_PARTIAL_SEAL_SHA256 = "39d58e0b55c949609ad4c33ad0034219fdf7f35352fda29f4f043d4eb8f75d96"
PRIOR_PARTIAL_AGGREGATE_SHA256 = "2a8151a7e00410d37e57c1cf3fd4a9717eb009dffef55c8eff0d5cac152b2008"


def verify_prior_partial(experiment: Path) -> dict[str, Any]:
    run = experiment / "partial_measured_run"
    seal_path = run / "RESPONSE_SEAL.json"
    receipt_path = run / "RECEIPT.json"
    seal = load_json_strict(seal_path.read_bytes())
    receipt = load_json_strict(receipt_path.read_bytes())
    if sha256_file(seal_path) != PRIOR_PARTIAL_SEAL_SHA256:
        raise ValueError("prior partial response seal identity differs")
    if seal["aggregate_sha256"] != PRIOR_PARTIAL_AGGREGATE_SHA256:
        raise ValueError("prior partial response aggregate differs")
    if receipt["status"] != "external_execution_host_terminated_mid_http_call":
        raise ValueError("prior partial disposition differs")
    if receipt["terminal_prepared_call_id"] != "E11-OBS-KAPPA-S223607-P04":
        raise ValueError("prior partial terminal call differs")
    if not receipt["no_resume_no_rerun_under_consumed_authorization"]:
        raise ValueError("prior partial no-resume boundary differs")
    for row in seal["files"]:
        path = run / Path(*row["path"].split("/"))
        if not path.is_file() or path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise ValueError(f"prior partial artifact differs: {row['path']}")
    if sha256_bytes(canonical_json_bytes(seal["files"])) != PRIOR_PARTIAL_AGGREGATE_SHA256:
        raise ValueError("prior partial seal reconstruction differs")
    return {
        "verified": True,
        "seal_sha256": PRIOR_PARTIAL_SEAL_SHA256,
        "aggregate_sha256": PRIOR_PARTIAL_AGGREGATE_SHA256,
        "http_completion_calls": receipt["http_completion_calls"],
    }


def expected_authorization(experiment: Path, root: Path) -> dict[str, Any]:
    bank = load_json_strict((experiment / "fresh_bank" / "BANK_MANIFEST.json").read_bytes())
    package = load_json_strict((experiment / "execution_package" / "PACKAGE_MANIFEST.json").read_bytes())
    closure = load_json_strict((experiment / "EXECUTABLE_CLOSURE_COMPLETION.json").read_bytes())
    profile = load_json_strict((experiment / "RUNTIME_PROFILE.json").read_bytes())
    return {
        "schema_version": "experiment-011-completion-authorization-v1",
        "status": "owner_authorized_missing_pair_completion_supplement",
        "owner_statement": "Let's finish what didn't get finished.",
        "classification": "post_interruption_completion_supplement_not_rewrite_of_primary_attempt",
        "prior_partial_response_seal_sha256": PRIOR_PARTIAL_SEAL_SHA256,
        "prior_partial_response_aggregate_sha256": PRIOR_PARTIAL_AGGREGATE_SHA256,
        "bank_id": bank["bank_id"],
        "bank_manifest_sha256": sha256_file(experiment / "fresh_bank" / "BANK_MANIFEST.json"),
        "package_id": package["package_id"],
        "package_manifest_sha256": sha256_file(experiment / "execution_package" / "PACKAGE_MANIFEST.json"),
        "closure_manifest_sha256": sha256_file(experiment / "EXECUTABLE_CLOSURE_COMPLETION.json"),
        "closure_aggregate_sha256": closure["aggregate_sha256"],
        "runtime_profile_sha256": sha256_file(experiment / "RUNTIME_PROFILE.json"),
        "actor_sha256": profile["model_sha256"],
        "runner_sha256": sha256_file(root / "scripts" / "run_recurrent_acquisition_completion.py"),
        "launcher_sha256": sha256_file(root / "scripts" / "launch_recurrent_acquisition_completion.ps1"),
        "cell_ordinal": CELL_ORDINAL,
        "fixture_id": FIXTURE_ID,
        "seed": SEED,
        "branch_order": list(BRANCH_ORDER),
        "shared_prefix_attempts": 1,
        "attempts_per_branch": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
        "maximum_http_completion_calls": MAXIMUM_HTTP_COMPLETION_CALLS,
        "output_root": OUTPUT_ROOT,
        "port": PORT,
        "reasoning_budget_tokens": 512,
        "response_seal_before_evaluator_access": True,
        "no_resume_or_rewrite_of_prior_partial": True,
        "automatic_successor": False,
    }


def validate_authorization(experiment: Path, root: Path) -> dict[str, Any]:
    observed = load_json_strict((experiment / "COMPLETION_AUTHORIZATION.json").read_bytes())
    expected = expected_authorization(experiment, root)
    if canonical_json_bytes(observed) != canonical_json_bytes(expected):
        raise ValueError("Experiment 011 completion authorization differs")
    return {
        "verified": True,
        "authorization_sha256": sha256_file(experiment / "COMPLETION_AUTHORIZATION.json"),
    }
