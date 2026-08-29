from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.recurrent_pressure import hidden_grade, load_recurrent_fixture
from working_set_exp.runner import verify_run


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "011_recurrent_acquisition_granularity"
RUN = EXPERIMENT / "partial_measured_run"
BANK = EXPERIMENT / "fresh_bank"


def verify_seal() -> dict[str, Any]:
    seal_path = RUN / "RESPONSE_SEAL.json"
    seal = load_json_strict(seal_path.read_bytes())
    for row in seal["files"]:
        path = RUN / Path(*row["path"].split("/"))
        if not path.is_file() or path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise RuntimeError(f"sealed file differs: {row['path']}")
    aggregate = sha256_bytes(canonical_json_bytes(seal["files"]))
    if aggregate != seal["aggregate_sha256"]:
        raise RuntimeError("response-seal aggregate differs")
    return {
        "verified": True,
        "file_count": len(seal["files"]),
        "aggregate_sha256": aggregate,
        "seal_sha256": sha256_file(seal_path),
    }


def candidate_from_snapshot(run: Path, candidate_id: str) -> Candidate:
    matches = [path for path in (run / "snap").iterdir() if path.is_dir() and path.name == candidate_id[:32]]
    if len(matches) != 1:
        raise RuntimeError((run, candidate_id, matches))
    base = matches[0]
    candidate = Candidate.create({path.relative_to(base).as_posix(): path.read_bytes() for path in base.rglob("*") if path.is_file()})
    if candidate.candidate_id != candidate_id:
        raise RuntimeError(f"snapshot candidate identity differs: {run}")
    return candidate


def transcript_metrics(run: Path) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    prompt_tokens = completion_tokens = reasoning_bytes = elapsed_ms = 0
    maximum_prompt_tokens = 0
    read_pages: list[dict[str, Any]] = []
    for action_path in sorted((run / "transcript").glob("*-assistant-content.json")):
        stem = action_path.name.removesuffix("-assistant-content.json")
        response_path = action_path.with_name(stem + "-endpoint-response.json")
        reasoning_path = action_path.with_name(stem + "-assistant-reasoning.txt")
        result_path = action_path.with_name(stem + "-result.json")
        if not all(path.is_file() for path in (response_path, reasoning_path, result_path)):
            raise RuntimeError(f"completed call lacks exact custody: {action_path}")
        action = load_json_strict(action_path.read_bytes())
        result = load_json_strict(result_path.read_bytes())
        response = load_json_strict(response_path.read_bytes())
        if result.get("accepted") is not True:
            raise RuntimeError(f"completed action was not accepted: {action_path}")
        actions.append(action)
        usage = response["usage"]
        prompt_tokens += int(usage["prompt_tokens"])
        completion_tokens += int(usage["completion_tokens"])
        maximum_prompt_tokens = max(maximum_prompt_tokens, int(usage["prompt_tokens"]))
        reasoning_bytes += reasoning_path.stat().st_size
        if action["action"] == "read":
            read_pages.append(
                {
                    "path": action["path"],
                    "start_line": action["start_line"],
                    "requested_line_count": action.get("line_count"),
                    "returned_start_line": result["returned_start_line"],
                    "returned_end_line": result["returned_end_line"],
                    "complete": result["complete"],
                }
            )
    for line in (run / "records.jsonl").read_bytes().splitlines():
        record = load_json_strict(line)
        if record["record_type"] == "action_result":
            elapsed_ms += int(record["payload"]["elapsed_ms"])
    return {
        "calls": len(actions),
        "actions": actions,
        "read_pages": read_pages,
        "prompt_tokens_sum": prompt_tokens,
        "completion_tokens_sum": completion_tokens,
        "reasoning_bytes": reasoning_bytes,
        "endpoint_elapsed_ms_sum": elapsed_ms,
        "maximum_server_prompt_tokens": maximum_prompt_tokens,
    }


def stage_row(summary_path: Path, fixture_id: str) -> dict[str, Any]:
    run = summary_path.parent
    verification = verify_run(run)
    summary = load_json_strict(summary_path.read_bytes())
    fixture = load_recurrent_fixture(BANK, fixture_id)
    candidate = candidate_from_snapshot(run, summary["candidate_id"])
    row = {
        "path": run.relative_to(RUN).as_posix(),
        "fixture_id": fixture_id,
        "condition": summary.get("condition", "shared-prefix"),
        "disposition": summary["disposition"],
        "candidate_id": summary["candidate_id"],
        "hidden_grade": hidden_grade(fixture, candidate),
        "public_check_passed": summary.get("public_check_passed"),
        "submitted": summary.get("submitted"),
        "maximum_offline_prompt_tokens": summary.get("maximum_offline_prompt_tokens"),
        "prepared_invocations": summary.get("prepared_invocations"),
        "http_completion_calls": summary.get("http_completion_calls"),
        "capacity_stop": summary.get("capacity_stop"),
        "replay_verified": verification["verified"],
    }
    row.update(transcript_metrics(run))
    return row


def transcript_index(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    completed_ids: set[str] = set()
    for action_path in sorted(RUN.glob("cell-*/**/transcript/*-assistant-content.json")):
        stem = action_path.name.removesuffix("-assistant-content.json")
        companions = {
            "coding_request": action_path.with_name(stem + "-coding-request.json"),
            "rendered_prompt": action_path.with_name(stem + "-rendered-prompt.txt"),
            "endpoint_request": action_path.with_name(stem + "-endpoint-request.json"),
            "endpoint_response": action_path.with_name(stem + "-endpoint-response.json"),
            "assistant_content": action_path,
            "assistant_reasoning": action_path.with_name(stem + "-assistant-reasoning.txt"),
            "result": action_path.with_name(stem + "-result.json"),
        }
        if not all(path.is_file() for path in companions.values()):
            raise RuntimeError(f"call custody incomplete: {action_path}")
        action = load_json_strict(action_path.read_bytes())
        result = load_json_strict(companions["result"].read_bytes())
        endpoint = load_json_strict(companions["endpoint_response"].read_bytes())
        call_id = endpoint["id"]
        completed_ids.add(call_id)
        rows.append(
            {
                "call": action_path.relative_to(RUN).as_posix().removesuffix("-assistant-content.json"),
                "response_id": call_id,
                "action": action["action"],
                "accepted": result.get("accepted"),
                "artifact_sha256": {name: sha256_file(path) for name, path in companions.items()},
                "direct_review_status": "reviewed_condition_aware_by_primary_agent_2026-08-29",
            }
        )
    if len(rows) != receipt["http_completion_calls"]:
        raise RuntimeError(f"transcript index coverage differs: {len(rows)}")
    return rows


def main() -> None:
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    if receipt["status"] != "external_execution_host_terminated_mid_http_call":
        raise RuntimeError("unexpected partial-run disposition")
    seal = verify_seal()
    schedule = load_json_strict((EXPERIMENT / "SCHEDULE.json").read_bytes())
    fixtures = {f"cell-{row['ordinal']:02d}": row["fixture_id"] for row in schedule["cells"]}
    stages = [stage_row(path, fixtures[path.relative_to(RUN).parts[0]]) for path in sorted(RUN.glob("cell-*/**/SUMMARY.json"))]
    calls = transcript_index(receipt)
    phase_c = [row for row in stages if "/phase-c" in row["path"]]

    branch_totals: dict[tuple[int, str], dict[str, Any]] = {}
    for row in stages:
        parts = row["path"].split("/")
        if len(parts) < 3 or not parts[1].startswith("T25-"):
            continue
        key = (int(parts[0].split("-")[1]), parts[1])
        agg = branch_totals.setdefault(
            key,
            {"ordinal": key[0], "condition": key[1], "calls": 0, "read_calls": 0, "prompt_tokens": 0, "elapsed_ms": 0, "stage_dispositions": []},
        )
        agg["calls"] += row["calls"]
        agg["read_calls"] += len(row["read_pages"])
        agg["prompt_tokens"] += row["prompt_tokens_sum"]
        agg["elapsed_ms"] += row["endpoint_elapsed_ms_sum"]
        agg["stage_dispositions"].append({"path": row["path"], "disposition": row["disposition"]})
    for (ordinal, condition), agg in branch_totals.items():
        final = next((row for row in phase_c if row["path"].startswith(f"cell-{ordinal:02d}/{condition}/")), None)
        agg["reached_second_boundary"] = final is not None
        agg["submitted"] = bool(final and final["submitted"] is True)
        agg["hidden_passed"] = bool(final and final["hidden_grade"]["passed"])

    pairs = []
    for ordinal in sorted({key[0] for key in branch_totals}):
        l0 = branch_totals.get((ordinal, "T25-L0"))
        l1 = branch_totals.get((ordinal, "T25-L1"))
        if l0 and l1:
            pairs.append(
                {
                    "ordinal": ordinal,
                    "l0": l0,
                    "l1": l1,
                    "l1_minus_l0_calls": l1["calls"] - l0["calls"],
                    "l1_minus_l0_read_calls": l1["read_calls"] - l0["read_calls"],
                    "l1_minus_l0_prompt_tokens": l1["prompt_tokens"] - l0["prompt_tokens"],
                    "l1_minus_l0_elapsed_ms": l1["elapsed_ms"] - l0["elapsed_ms"],
                }
            )

    results = {
        "schema_version": "experiment-011-partial-mechanical-results-v1",
        "research_disposition": receipt["research_disposition"],
        "run_status": receipt["status"],
        "formal_primary_comparison_scorable": False,
        "reason_unscorable": "execution host terminated during cell 4 shared-prefix call 4 before treatment exposure in that cell",
        "response_seal": seal,
        "prepared_invocations": receipt["prepared_invocations"],
        "http_completion_calls": receipt["http_completion_calls"],
        "terminal_prepared_call_id": receipt["terminal_prepared_call_id"],
        "verified_stage_runs": len(stages),
        "directly_reviewed_completion_calls": len(calls),
        "phase_c_trajectories": len(phase_c),
        "phase_c_hidden_passes": sum(row["hidden_grade"]["passed"] for row in phase_c),
        "phase_c_submissions": sum(row["submitted"] is True for row in phase_c),
        "stages": stages,
        "completed_branch_totals": list(branch_totals.values()),
        "complete_observed_pairs": pairs,
        "apparatus": {
            "all_completed_actions_accepted": all(row["accepted"] is True for row in calls),
            "all_complete_stage_runs_replayed": all(row["replay_verified"] for row in stages),
            "server_port_free_post_termination": receipt["server_shutdown_verified"],
            "orderly_runner_shutdown_record_present": receipt["orderly_runner_shutdown_record_present"],
            "retries": receipt["retries"],
            "repairs": receipt["repairs"],
            "rescues": receipt["rescues"],
        },
    }
    grading = {
        "schema_version": "experiment-011-partial-postseal-hidden-grading-v1",
        "formal_primary_comparison_scorable": False,
        "response_seal_sha256": seal["seal_sha256"],
        "evaluator_opened_only_after_partial_response_seal": True,
        "phase_c": [
            {
                "path": row["path"],
                "fixture_id": row["fixture_id"],
                "condition": row["condition"],
                "candidate_id": row["candidate_id"],
                "submitted": row["submitted"],
                "hidden_grade": row["hidden_grade"],
            }
            for row in phase_c
        ],
    }
    index = {
        "schema_version": "experiment-011-partial-transcript-index-v1",
        "reviewer": "Codex primary project agent",
        "review_mode": "condition-aware post-seal direct prompt/reasoning/action/result audit",
        "actor": "Qwen3.8-27B-AD-IQ2_S",
        "coverage": "all 108 completed calls in the sealed partial run; terminal prepared call separately identified",
        "completed_call_count": len(calls),
        "terminal_prepared_call": {
            "call_id": receipt["terminal_prepared_call_id"],
            "coding_request": "cell-04/shared-prefix/transcript/004-coding-request.json",
            "endpoint_request": "cell-04/shared-prefix/transcript/004-endpoint-request.json",
            "rendered_prompt": "cell-04/shared-prefix/transcript/004-rendered-prompt.txt",
            "endpoint_response_present": False,
        },
        "calls": calls,
    }
    atomic_write(EXPERIMENT / "MECHANICAL_RESULTS.json", canonical_json_bytes(results))
    atomic_write(EXPERIMENT / "POSTSEAL_HIDDEN_GRADING.json", canonical_json_bytes(grading))
    atomic_write(EXPERIMENT / "TRANSCRIPT_INDEX.json", canonical_json_bytes(index))


if __name__ == "__main__":
    main()
