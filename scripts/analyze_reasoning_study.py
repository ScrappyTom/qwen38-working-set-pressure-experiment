from __future__ import annotations

from pathlib import Path
from typing import Any

from working_set_exp.fixture import load_fixture
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.reasoning_measured import _inventory
from working_set_exp.runner import replay_prefix, verify_run
from working_set_exp.tools import ToolExecutor


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "004_reasoning_transition_diagnostic"
RUN = EXPERIMENT / "measured_attempt1"


def _verify_seal() -> dict[str, Any]:
    seal = load_json_strict((RUN / "RESPONSE_SEAL.json").read_bytes())
    files = _inventory(RUN, excluded={"RECEIPT.json", "RESPONSE_SEAL.json"})
    if files != seal["files"] or sha256_bytes(canonical_json_bytes(files)) != seal["aggregate_sha256"]:
        raise ValueError("copied response tree differs from pre-evaluator seal")
    if seal["evaluator_truth_opened"] is not False:
        raise ValueError("response seal evaluator state differs")
    return {"verified": True, "aggregate_sha256": seal["aggregate_sha256"], "file_count": len(files)}


def _action_rows(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in (run_dir / "records.jsonl").read_text(encoding="utf-8").splitlines():
        record = load_json_strict(raw.encode("utf-8"))
        if record["record_type"] != "action_result":
            continue
        payload = record["payload"]
        rows.append(
            {
                "action": payload["action"],
                "result": payload["result"],
                "offline_prompt_tokens": payload["offline_prompt_tokens"],
                "server_reported_prompt_tokens": payload["server_reported_prompt_tokens"],
                "completion_tokens": payload["completion_tokens"],
                "accounting_delta": payload["accounting_delta"],
                "elapsed_ms": payload["elapsed_ms"],
                "reasoning_content_bytes": payload.get("reasoning_content_bytes", 0),
                "reasoning_content_sha256": payload.get("reasoning_content_sha256"),
            }
        )
    return rows


def _branch_replay(fixture, prefix, run_dir: Path):
    verify_run(run_dir)
    state = prefix.state.clone_for_branch()
    executor = ToolExecutor(
        state,
        required_full_reads=fixture.required_full_reads,
        prefork_checker=fixture.prefork_checker,
        public_checker=fixture.public_checker,
        final_target=fixture.final_target,
        probe_id=fixture.probe_id,
        probe_body=fixture.probe_body,
        reopenable=prefix.reopenable,
    )
    for raw in (run_dir / "records.jsonl").read_text(encoding="utf-8").splitlines():
        record = load_json_strict(raw.encode("utf-8"))
        if record["record_type"] != "action_result":
            continue
        expected = record["payload"]["result"]
        observed = executor.execute(record["payload"]["action"])
        if canonical_json_bytes(observed) != canonical_json_bytes(expected):
            raise ValueError("branch replay result differs")
    return state


def _transcript_index() -> list[dict[str, Any]]:
    rows = []
    for request_path in sorted(RUN.rglob("*-coding-request.json")):
        stem = request_path.name.removesuffix("-coding-request.json")
        transcript = request_path.parent
        assistant_path = transcript / f"{stem}-assistant-content.json"
        reasoning_path = transcript / f"{stem}-assistant-reasoning.txt"
        result_path = transcript / f"{stem}-result.json"
        request_bytes = request_path.read_bytes()
        request = load_json_strict(request_bytes)
        rows.append(
            {
                "request_path": request_path.relative_to(RUN).as_posix(),
                "request_sha256": sha256_bytes(request_bytes),
                "stage": request["stage"],
                "fixture_id": request["fixture_id"],
                "history_entries": len(request["history"]),
                "assistant": load_json_strict(assistant_path.read_bytes()) if assistant_path.is_file() else None,
                "assistant_sha256": sha256_file(assistant_path) if assistant_path.is_file() else None,
                "reasoning_present": reasoning_path.is_file(),
                "reasoning_size_bytes": reasoning_path.stat().st_size if reasoning_path.is_file() else 0,
                "reasoning_sha256": sha256_file(reasoning_path) if reasoning_path.is_file() else None,
                "result": load_json_strict(result_path.read_bytes()) if result_path.is_file() else None,
                "result_sha256": sha256_file(result_path) if result_path.is_file() else None,
                "http_call_occurred": assistant_path.is_file(),
            }
        )
    return rows


def main() -> None:
    seal = _verify_seal()
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    if receipt["status"] != "completed_and_response_sealed" or receipt["evaluator_reads_before_seal"] is not False:
        raise ValueError("measured receipt state differs")

    prefix_results = []
    for ordinal, fixture_id in ((1, "E4-SOURCE"), (2, "E4-OBSERVATION")):
        prefix_dir = RUN / f"prefix-{ordinal:02d}" / "shared_prefix"
        verify_run(prefix_dir)
        rows = _action_rows(prefix_dir)
        summary = load_json_strict((prefix_dir / "SUMMARY.json").read_bytes())
        prefix_results.append(
            {
                "fixture_id": fixture_id,
                "disposition": summary["disposition"],
                "calls": summary["calls"],
                "action_names": [row["action"].get("action") for row in rows],
                "read_paths": [row["action"].get("path") for row in rows if row["action"].get("action") == "read"],
                "prompt_tokens_sum": sum(row["offline_prompt_tokens"] for row in rows),
                "completion_tokens_sum": sum(row["completion_tokens"] for row in rows),
                "elapsed_ms_sum": sum(row["elapsed_ms"] for row in rows),
                "maximum_offline_prompt_tokens": max(row["offline_prompt_tokens"] for row in rows),
            }
        )

    fixture = load_fixture(EXPERIMENT / "fresh_bank", "E4-OBSERVATION")
    prefix = replay_prefix(fixture, RUN / "prefix-02" / "shared_prefix")
    branch_results = []
    hidden = (EXPERIMENT / "fresh_bank" / "evaluator_only" / "E4-OBSERVATION" / "hidden.py").read_bytes()
    truth = load_json_strict((EXPERIMENT / "fresh_bank" / "evaluator_only" / "E4-OBSERVATION" / "TRUTH.json").read_bytes())
    for condition in ("R0", "R1"):
        branch_dir = RUN / "prefix-02" / condition
        state = _branch_replay(fixture, prefix, branch_dir)
        rows = _action_rows(branch_dir)
        summary = load_json_strict((branch_dir / "SUMMARY.json").read_bytes())
        grade = run_checker(state.candidate, hidden)
        branch_results.append(
            {
                "fixture_id": "E4-OBSERVATION",
                "condition": condition,
                "reasoning_mode": "off" if condition == "R0" else "low_bounded_512",
                "disposition": summary["disposition"],
                "candidate_id": state.candidate.candidate_id,
                "known_good_candidate_id": truth["known_good_candidate_id"],
                "exact_known_good_candidate": state.candidate.candidate_id == truth["known_good_candidate_id"],
                "submitted": state.submitted,
                "public_check_passed": state.public_check_passed,
                "hidden_passed": grade["passed"],
                "actions": rows,
                "action_names": [row["action"].get("action") for row in rows],
                "read_paths": [row["action"].get("path") for row in rows if row["action"].get("action") == "read"],
                "reopened_observation_at_call": next(
                    (index for index, row in enumerate(rows, start=1) if row["action"].get("action") == "reopen_observation"),
                    None,
                ),
                "patched_at_call": next(
                    (index for index, row in enumerate(rows, start=1) if row["action"].get("action") == "patch"), None
                ),
                "calls": summary["calls"],
                "prompt_tokens_sum": sum(row["offline_prompt_tokens"] for row in rows),
                "completion_tokens_sum": sum(row["completion_tokens"] for row in rows),
                "reasoning_content_bytes_sum": sum(row["reasoning_content_bytes"] for row in rows),
                "elapsed_ms_sum": sum(row["elapsed_ms"] for row in rows),
                "maximum_offline_prompt_tokens": summary["maximum_offline_prompt_tokens"],
                "accounting_deltas": [row["accounting_delta"] for row in rows],
            }
        )

    index = _transcript_index()
    mechanical = {
        "schema_version": "experiment-004-reasoning-mechanical-results-v1",
        "response_seal": seal,
        "actor_sha256": receipt["actor_sha256"],
        "infrastructure_failures": 0,
        "completion_calls": sum(1 for row in index if row["http_call_occurred"]),
        "prospective_requests": len(index),
        "prefix_results": prefix_results,
        "branch_results": branch_results,
        "formal_scope": "one_matched_observation_pair_only; source_pair_not_exposed",
    }
    atomic_write(EXPERIMENT / "TRANSCRIPT_INDEX_ATTEMPT1.json", canonical_json_bytes(index))
    atomic_write(EXPERIMENT / "MECHANICAL_RESULTS_ATTEMPT1.json", canonical_json_bytes(mechanical))
    print(canonical_json_bytes(mechanical).decode("utf-8"))


if __name__ == "__main__":
    main()
