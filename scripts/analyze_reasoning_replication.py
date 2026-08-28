from __future__ import annotations

from pathlib import Path
from typing import Any

from working_set_exp.fixture import load_fixture
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes
from working_set_exp.reasoning_measured import _inventory
from working_set_exp.reasoning_replication import progress_pointer
from working_set_exp.runner import replay_prefix, verify_run
from working_set_exp.runtime import REASONING_BUDGET, load_runtime, tokenizer_count
from working_set_exp.tools import ToolExecutor


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "005_bounded_reasoning_source_replication"
RUN = EXPERIMENT / "measured_run"


def _records(run_dir: Path) -> list[dict[str, Any]]:
    return [load_json_strict(line) for line in (run_dir / "records.jsonl").read_bytes().splitlines()]


def _replay(fixture, prefix, run_dir: Path):
    verify_run(run_dir)
    state = prefix.state.clone_for_branch()
    executor = ToolExecutor(
        state, required_full_reads=fixture.required_full_reads,
        prefork_checker=fixture.prefork_checker, public_checker=fixture.public_checker,
        final_target=fixture.final_target, probe_id=None, probe_body=None,
        reopenable=prefix.reopenable,
    )
    for record in _records(run_dir):
        if record["record_type"] != "action_result":
            continue
        observed = executor.execute(record["payload"]["action"])
        if canonical_json_bytes(observed) != canonical_json_bytes(record["payload"]["result"]):
            raise ValueError("replication branch replay differs")
    return state


def main() -> None:
    seal = load_json_strict((RUN / "RESPONSE_SEAL.json").read_bytes())
    files = _inventory(RUN, excluded={"RECEIPT.json", "RESPONSE_SEAL.json"})
    if files != seal["files"] or sha256_bytes(canonical_json_bytes(files)) != seal["aggregate_sha256"]:
        raise ValueError("replication response tree differs from seal")
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    schedule = load_json_strict((EXPERIMENT / "SCHEDULE.json").read_bytes())
    results = []
    actual_http_calls = 0
    prepared_invocations = 0
    for row in schedule["cases"]:
        fixture = load_fixture(EXPERIMENT / "fresh_bank", row["fixture_id"])
        prefix = replay_prefix(fixture, RUN / f"case-{row['ordinal']:02d}" / "constructed_prefix")
        hidden = (EXPERIMENT / "fresh_bank" / "evaluator_only" / row["fixture_id"] / "hidden.py").read_bytes()
        truth = load_json_strict((EXPERIMENT / "fresh_bank" / "evaluator_only" / row["fixture_id"] / "TRUTH.json").read_bytes())
        for condition in ("R0", "R1"):
            run_dir = RUN / f"case-{row['ordinal']:02d}" / condition
            state = _replay(fixture, prefix, run_dir)
            records = _records(run_dir)
            action_rows = [record["payload"] for record in records if record["record_type"] == "action_result"]
            prepared = [record for record in records if record["record_type"] == "external_call_prepared"]
            capacity = [record["payload"] for record in records if record["record_type"] == "capacity_stopped"]
            actual_http_calls += len(action_rows)
            prepared_invocations += len(prepared)
            reasoning_paths = sorted((run_dir / "transcript").glob("*-assistant-reasoning.txt"))
            reasoning_tokens = [tokenizer_count(profile, path.read_bytes()) for path in reasoning_paths]
            read_results = [payload["result"] for payload in action_rows if payload["action"].get("action") == "read"]
            first_request = load_json_strict((run_dir / "transcript" / "001-coding-request.json").read_bytes())
            results.append(
                {
                    "fixture_id": row["fixture_id"], "condition": condition,
                    "seed": row["seed"], "branch_order": row["branch_order"],
                    "disposition": load_json_strict((run_dir / "SUMMARY.json").read_bytes())["disposition"],
                    "candidate_id": state.candidate.candidate_id,
                    "known_good_candidate_id": truth["known_good_candidate_id"],
                    "exact_known_good_candidate": state.candidate.candidate_id == truth["known_good_candidate_id"],
                    "submitted": state.submitted, "public_check_passed": state.public_check_passed,
                    "hidden_passed": run_checker(state.candidate, hidden)["passed"],
                    "http_calls": len(action_rows), "prepared_invocations": len(prepared),
                    "capacity_stops": capacity,
                    "actions": [payload["action"] for payload in action_rows],
                    "action_names": [payload["action"].get("action") for payload in action_rows],
                    "read_paths": [payload["action"].get("path") for payload in action_rows if payload["action"].get("action") == "read"],
                    "read_content_bytes": sum(len(result.get("content", "").encode("utf-8")) for result in read_results),
                    "prompt_tokens_sum_http_calls": sum(payload["offline_prompt_tokens"] for payload in action_rows),
                    "completion_tokens_sum": sum(payload["completion_tokens"] for payload in action_rows),
                    "elapsed_ms_sum": sum(payload["elapsed_ms"] for payload in action_rows),
                    "maximum_completed_call_prompt_tokens": max(payload["offline_prompt_tokens"] for payload in action_rows),
                    "maximum_prospective_prompt_tokens": max(
                        [payload["offline_prompt_tokens"] for payload in action_rows]
                        + [record["payload"]["offline_prompt_tokens"] for record in prepared]
                    ),
                    "reasoning_tokens_per_call": reasoning_tokens,
                    "reasoning_tokens_sum": sum(reasoning_tokens),
                    "reasoning_budget_respected": all(value <= REASONING_BUDGET for value in reasoning_tokens),
                    "first_request_pointer_exact": first_request.get("progress_pointer") == progress_pointer(EXPERIMENT / "fresh_bank", row["fixture_id"]),
                    "first_request_older_chronology_present": first_request["older_chronology_present"],
                }
            )
    result = {
        "schema_version": "experiment-005-reasoning-replication-mechanical-results-v1",
        "response_seal_verified": True,
        "response_aggregate_sha256": seal["aggregate_sha256"],
        "actor_sha256": receipt["actor_sha256"],
        "server_reasoning_budget_tokens": REASONING_BUDGET,
        "receipt_reported_model_calls": receipt["model_calls"],
        "actual_http_completion_calls": actual_http_calls,
        "prepared_invocations": prepared_invocations,
        "receipt_call_count_note": "receipt sums branch call counters and therefore includes one capacity-denied prepared invocation",
        "infrastructure_failures": 0,
        "results": results,
    }
    atomic_write(EXPERIMENT / "MECHANICAL_RESULTS.json", canonical_json_bytes(result))
    print(canonical_json_bytes(result).decode("utf-8"))


if __name__ == "__main__":
    main()
