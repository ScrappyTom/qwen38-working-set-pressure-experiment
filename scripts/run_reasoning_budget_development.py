from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from working_set_exp.fixture import load_fixture
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.reasoning import BRANCH_CALL_LIMIT, PREFIX_CALL_LIMIT, progress_pointer, verify_bank
from working_set_exp.reasoning_measured import seal_response_tree
from working_set_exp.runner import ScriptedActor, run_branch, run_prefix, verify_run
from working_set_exp.runtime import LiveActor, OwnedServer, PORT, REASONING_BUDGET, load_runtime, port_free, tokenizer_count


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "004_reasoning_transition_diagnostic"
BANK = EXPERIMENT / "fresh_bank"
AUTHORIZATION = EXPERIMENT / "SERVER_BUDGET_DEVELOPMENT_AUTHORIZATION.json"
OUTPUT = Path(r"C:\e4r-budget-dev")


def _clean_checkout() -> None:
    completed = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, check=True, text=True)
    if completed.stdout:
        raise RuntimeError("server-budget development check requires a clean checkout")


def _prefix_policy(fixture):
    required_index = 0
    target_read = False
    patched = False
    checked = False

    def policy(request: dict[str, Any]) -> dict[str, Any]:
        nonlocal required_index, target_read, patched, checked
        if request["stage"] == "setup":
            return {"action": "begin"}
        candidate_id = request["candidate_id"]
        if required_index < len(fixture.required_full_reads):
            path = fixture.required_full_reads[required_index]
            required_index += 1
            return {"action": "read", "path": path, "start_line": 1, "line_count": 500}
        if not target_read:
            target_read = True
            return {"action": "read", "path": "staging/gate.py", "start_line": 1, "line_count": 100}
        if not patched:
            patched = True
            latest = request["history"][-1]["result"]
            return {
                "action": "patch", "path": "staging/gate.py",
                "old": "    return 0", "new": "    return len(RELEASE_GROUPS)",
                "expected_candidate_id": candidate_id, "expected_file_sha256": latest["file_sha256"],
            }
        if not checked:
            checked = True
            return {"action": "check", "check_id": "prefork", "expected_candidate_id": candidate_id}
        return {"action": "fork_ready", "expected_candidate_id": candidate_id}

    return policy


def _action_records(run_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for line in (run_dir / "records.jsonl").read_bytes().splitlines():
        row = load_json_strict(line)
        if row["record_type"] == "action_result":
            rows.append(row)
    return rows


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError("server-budget development output root already exists")
    _clean_checkout()
    authorization = load_json_strict(AUTHORIZATION.read_bytes())
    if authorization != {
        "actor_sha256": "d416fa422c9035605c778f60d90a94b288c38b4f9ec2126b58ef938ce8d5f716",
        "attempts_per_call": 1,
        "authorized": True,
        "conditions": ["R0", "R1"],
        "fixture_exposure_status": "already_exposed_experiment_004_source_fixture_development_only",
        "fixture_id": "E4-SOURCE",
        "maximum_completion_calls": 16,
        "owner_statement": "Great, proceed as you recommended",
        "reasoning_budget_enforcement": "llama_server_launch_flag_512",
        "reasoning_budget_tokens": 512,
        "repairs": 0,
        "rescues": 0,
        "retries": 0,
        "schema_version": "experiment-004-server-budget-development-authorization-v1",
    }:
        raise RuntimeError("server-budget development authorization differs")
    bank = verify_bank(BANK)
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    if profile.model_sha256 != authorization["actor_sha256"] or not port_free(PORT):
        raise RuntimeError("server-budget development runtime preflight differs")
    OUTPUT.mkdir(parents=True)
    receipt: dict[str, Any] = {
        "schema_version": "experiment-004-server-budget-development-receipt-v1",
        "started_at_utc": utc_now(), "status": "started",
        "authorization_sha256": sha256_file(AUTHORIZATION), "bank": bank,
        "fixture_id": "E4-SOURCE", "fixture_exposure_status": authorization["fixture_exposure_status"],
        "reasoning_budget_tokens": REASONING_BUDGET, "model_calls": 0,
    }
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    fixture = load_fixture(BANK, "E4-SOURCE")
    scripted = ScriptedActor(profile, 57721, _prefix_policy(fixture))
    prefix = run_prefix(
        fixture, seed=57721, actor=scripted, output_dir=OUTPUT / "scripted_prefix",
        profile=profile, fixed_record_timestamp="2026-08-28T00:00:00Z",
        prefix_call_limit=PREFIX_CALL_LIMIT, continuation_call_limit=BRANCH_CALL_LIMIT,
        one_shot_probe=True,
    )
    verify_run(prefix.output_dir)
    summaries: dict[str, Any] = {}
    try:
        with OwnedServer(
            profile, OUTPUT, port=PORT, reasoning_mode="auto", reasoning_budget=REASONING_BUDGET
        ):
            for condition in ("R0", "R1"):
                summaries[condition] = run_branch(
                    fixture, prefix, condition=condition, seed=57721,
                    actor=LiveActor(profile, seed=57721, reasoning_enabled=condition == "R1"),
                    output_dir=OUTPUT / condition,
                    progress_pointer=progress_pointer(BANK, fixture.fixture_id),
                    prefix_call_limit=PREFIX_CALL_LIMIT, branch_call_limit=BRANCH_CALL_LIMIT,
                )
                verify_run(OUTPUT / condition)
        profiles: dict[str, Any] = {}
        total_calls = 0
        for condition in ("R0", "R1"):
            rows = _action_records(OUTPUT / condition)
            total_calls += len(rows)
            reasoning_paths = sorted((OUTPUT / condition / "transcript").glob("*-assistant-reasoning.txt"))
            reasoning_tokens = [tokenizer_count(profile, path.read_bytes()) for path in reasoning_paths]
            profiles[condition] = {
                "calls": len(rows),
                "actions": [row["payload"]["action"].get("action") for row in rows],
                "reasoning_artifacts": len(reasoning_paths),
                "reasoning_tokens_per_call": reasoning_tokens,
                "maximum_reasoning_tokens": max(reasoning_tokens, default=0),
                "server_budget_respected": all(count <= REASONING_BUDGET for count in reasoning_tokens),
            }
        if profiles["R0"]["reasoning_artifacts"] != 0:
            raise RuntimeError("reasoning-off branch emitted private reasoning")
        if profiles["R1"]["reasoning_artifacts"] != profiles["R1"]["calls"]:
            raise RuntimeError("reasoning-on branch lacks private reasoning")
        if not profiles["R1"]["server_budget_respected"]:
            raise RuntimeError("server reasoning budget was exceeded")
        seal = seal_response_tree(OUTPUT)
        receipt.update(
            {
                "status": "completed_and_response_sealed", "completed_at_utc": utc_now(),
                "summaries": summaries, "profiles": profiles, "model_calls": total_calls,
                "response_seal_sha256": sha256_file(OUTPUT / "RESPONSE_SEAL.json"),
                "response_aggregate_sha256": seal["aggregate_sha256"],
                "server_shutdown_verified": port_free(PORT),
            }
        )
    except Exception as exc:
        receipt.update(
            {
                "status": "infrastructure_or_integrity_stopped", "completed_at_utc": utc_now(),
                "error_type": type(exc).__name__, "error": str(exc),
                "server_shutdown_verified": port_free(PORT),
            }
        )
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        raise
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
