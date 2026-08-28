from __future__ import annotations

from pathlib import Path
from typing import Any

from working_set_exp.fixture import load_fixture
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes
from working_set_exp.reasoning_measured import _inventory
from working_set_exp.runner import replay_prefix, verify_run
from working_set_exp.runtime import REASONING_BUDGET, load_runtime, tokenizer_count
from working_set_exp.tools import ToolExecutor


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "004_reasoning_transition_diagnostic"
RUN = EXPERIMENT / "server_budget_development_run"


def _rows(run_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for line in (run_dir / "records.jsonl").read_bytes().splitlines():
        record = load_json_strict(line)
        if record["record_type"] == "action_result":
            rows.append(record["payload"])
    return rows


def _replay_branch(fixture, prefix, run_dir: Path):
    verify_run(run_dir)
    state = prefix.state.clone_for_branch()
    executor = ToolExecutor(
        state, required_full_reads=fixture.required_full_reads,
        prefork_checker=fixture.prefork_checker, public_checker=fixture.public_checker,
        final_target=fixture.final_target, probe_id=fixture.probe_id,
        probe_body=fixture.probe_body, reopenable=prefix.reopenable,
    )
    for line in (run_dir / "records.jsonl").read_bytes().splitlines():
        record = load_json_strict(line)
        if record["record_type"] != "action_result":
            continue
        observed = executor.execute(record["payload"]["action"])
        if canonical_json_bytes(observed) != canonical_json_bytes(record["payload"]["result"]):
            raise ValueError("development branch replay differs")
    return state


def main() -> None:
    seal = load_json_strict((RUN / "RESPONSE_SEAL.json").read_bytes())
    files = _inventory(RUN, excluded={"RECEIPT.json", "RESPONSE_SEAL.json"})
    if files != seal["files"] or sha256_bytes(canonical_json_bytes(files)) != seal["aggregate_sha256"]:
        raise ValueError("development response tree differs from seal")
    fixture = load_fixture(EXPERIMENT / "fresh_bank", "E4-SOURCE")
    prefix = replay_prefix(fixture, RUN / "scripted_prefix")
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    hidden = (EXPERIMENT / "fresh_bank" / "evaluator_only" / "E4-SOURCE" / "hidden.py").read_bytes()
    results = []
    for condition in ("R0", "R1"):
        run_dir = RUN / condition
        state = _replay_branch(fixture, prefix, run_dir)
        rows = _rows(run_dir)
        reasoning_paths = sorted((run_dir / "transcript").glob("*-assistant-reasoning.txt"))
        reasoning_tokens = [tokenizer_count(profile, path.read_bytes()) for path in reasoning_paths]
        read_results = [row["result"] for row in rows if row["action"].get("action") == "read"]
        results.append(
            {
                "condition": condition,
                "disposition": load_json_strict((run_dir / "SUMMARY.json").read_bytes())["disposition"],
                "candidate_id": state.candidate.candidate_id,
                "submitted": state.submitted,
                "public_check_passed": state.public_check_passed,
                "hidden_passed": run_checker(state.candidate, hidden)["passed"],
                "calls": len(rows),
                "actions": [row["action"] for row in rows],
                "read_paths": [row["action"].get("path") for row in rows if row["action"].get("action") == "read"],
                "read_content_bytes": sum(len(row.get("content", "").encode("utf-8")) for row in read_results),
                "prompt_tokens_sum": sum(row["offline_prompt_tokens"] for row in rows),
                "completion_tokens_sum": sum(row["completion_tokens"] for row in rows),
                "elapsed_ms_sum": sum(row["elapsed_ms"] for row in rows),
                "maximum_offline_prompt_tokens": max(row["offline_prompt_tokens"] for row in rows),
                "reasoning_tokens_per_call": reasoning_tokens,
                "reasoning_tokens_sum": sum(reasoning_tokens),
                "reasoning_budget_respected": all(value <= REASONING_BUDGET for value in reasoning_tokens),
            }
        )
    result = {
        "schema_version": "experiment-004-server-budget-development-results-v1",
        "response_seal_verified": True,
        "fixture_id": "E4-SOURCE",
        "fixture_exposure_status": "already_exposed_development_only",
        "server_reasoning_budget_tokens": REASONING_BUDGET,
        "results": results,
    }
    atomic_write(EXPERIMENT / "SERVER_BUDGET_DEVELOPMENT_RESULTS.json", canonical_json_bytes(result))
    print(canonical_json_bytes(result).decode("utf-8"))


if __name__ == "__main__":
    main()
