from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import (
    atomic_write,
    canonical_json_bytes,
    load_json_strict,
    sha256_bytes,
    sha256_file,
)
from working_set_exp.recurrent_pressure import hidden_grade, load_recurrent_fixture
from working_set_exp.runner import verify_run


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "009_recurrent_observation_validity"
RUN = EXPERIMENT / "measured_run"
BANK = EXPERIMENT / "fresh_bank"


def verify_seal() -> dict[str, Any]:
    seal_path = RUN / "RESPONSE_SEAL.json"
    seal = load_json_strict(seal_path.read_bytes())
    for row in seal["files"]:
        path = RUN / Path(*row["path"].split("/"))
        if not path.is_file():
            raise RuntimeError(f"sealed file missing: {row['path']}")
        if path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise RuntimeError(f"sealed file differs: {row['path']}")
    aggregate = sha256_bytes(canonical_json_bytes(seal["files"]))
    if aggregate != seal["aggregate_sha256"]:
        raise RuntimeError("response seal aggregate differs")
    return {
        "verified": True,
        "file_count": len(seal["files"]),
        "aggregate_sha256": aggregate,
        "seal_sha256": sha256_file(seal_path),
    }


def candidate_from_snapshot(run: Path, candidate_id: str) -> Candidate:
    matches = [
        path
        for path in (run / "snap").iterdir()
        if path.is_dir() and path.name == candidate_id[:32]
    ]
    if len(matches) != 1:
        raise RuntimeError((run, candidate_id, matches))
    base = matches[0]
    files = {
        path.relative_to(base).as_posix(): path.read_bytes()
        for path in base.rglob("*")
        if path.is_file()
    }
    candidate = Candidate.create(files)
    if candidate.candidate_id != candidate_id:
        raise RuntimeError(f"snapshot candidate identity differs: {run}")
    return candidate


def transcript_metrics(run: Path) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    prompt_tokens = 0
    completion_tokens = 0
    endpoint_ms = 0.0
    reasoning_bytes = 0
    maximum_server_prompt_tokens = 0
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
            raise RuntimeError(f"measured action was not accepted: {action_path}")
        actions.append(action)
        usage = response["usage"]
        prompt_tokens += int(usage["prompt_tokens"])
        completion_tokens += int(usage["completion_tokens"])
        maximum_server_prompt_tokens = max(maximum_server_prompt_tokens, int(usage["prompt_tokens"]))
        timings = response.get("timings", {})
        endpoint_ms += float(timings.get("prompt_ms", 0.0)) + float(timings.get("predicted_ms", 0.0))
        reasoning_bytes += reasoning_path.stat().st_size
    counts: dict[str, int] = {}
    for action in actions:
        counts[action["action"]] = counts.get(action["action"], 0) + 1
    return {
        "calls": len(actions),
        "actions": actions,
        "action_counts": counts,
        "prompt_tokens_sum": prompt_tokens,
        "completion_tokens_sum": completion_tokens,
        "maximum_server_prompt_tokens": maximum_server_prompt_tokens,
        "endpoint_compute_ms_sum": round(endpoint_ms, 3),
        "reasoning_bytes": reasoning_bytes,
    }


def stage_row(summary_path: Path, fixture_id: str) -> dict[str, Any]:
    run = summary_path.parent
    verification = verify_run(run)
    if not verification["verified"]:
        raise RuntimeError(f"run replay failed: {run}")
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
        "replay_verified": True,
    }
    row.update(transcript_metrics(run))
    return row


def transcript_index(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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
        rows.append(
            {
                "call": action_path.relative_to(RUN).as_posix().removesuffix("-assistant-content.json"),
                "action": action["action"],
                "accepted": result.get("accepted"),
                "artifact_sha256": {name: sha256_file(path) for name, path in companions.items()},
                "direct_review_status": "reviewed_condition_aware_by_primary_agent_2026-08-29",
            }
        )
    if len(rows) != receipt["http_completion_calls"]:
        raise RuntimeError("transcript index does not cover every HTTP completion")
    return rows


def main() -> None:
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    if receipt["status"] != "completed_and_response_sealed":
        raise RuntimeError("measured run is not complete and sealed")
    seal = verify_seal()
    cell_fixtures = {f"cell-{row['ordinal']:02d}": row["fixture_id"] for row in receipt["cells"]}
    stages = [
        stage_row(path, cell_fixtures[path.relative_to(RUN).parts[0]])
        for path in sorted(RUN.glob("cell-*/**/SUMMARY.json"))
    ]
    calls = transcript_index(receipt)
    rejected_actions = [row["call"] for row in calls if row["accepted"] is not True]
    check_results: list[dict[str, Any]] = []
    for result_path in sorted(RUN.glob("cell-*/**/transcript/*-result.json")):
        result = load_json_strict(result_path.read_bytes())
        if "check_id" in result:
            check_results.append(
                {
                    "path": result_path.relative_to(RUN).as_posix(),
                    "check_id": result["check_id"],
                    "checked_candidate_id": result["checked_candidate_id"],
                    "passed": result["passed"],
                }
            )
    phase_c = [row for row in stages if "/phase-c" in row["path"]]
    results = {
        "schema_version": "experiment-009-mechanical-results-v1",
        "run_status": receipt["status"],
        "response_seal": seal,
        "prepared_invocations": receipt["prepared_invocations"],
        "http_completion_calls": receipt["http_completion_calls"],
        "retries": receipt["retries"],
        "repairs": receipt["repairs"],
        "rescues": receipt["rescues"],
        "server_shutdown_verified": receipt["server_shutdown_verified"],
        "verified_stage_runs": len(stages),
        "directly_reviewed_completion_calls": len(calls),
        "rejected_completed_actions": rejected_actions,
        "public_checks": check_results,
        "all_public_checks_passed": all(row["passed"] for row in check_results),
        "phase_c_trajectories": len(phase_c),
        "phase_c_hidden_passes": sum(1 for row in phase_c if row["hidden_grade"]["passed"]),
        "phase_c_submissions": sum(1 for row in phase_c if row["submitted"] is True),
        "stages": stages,
    }
    grading = {
        "schema_version": "experiment-009-postseal-hidden-grading-v1",
        "response_seal_sha256": seal["seal_sha256"],
        "evaluator_opened_only_after_response_seal": True,
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
        "schema_version": "experiment-009-transcript-index-v1",
        "reviewer": "Codex primary project agent",
        "review_mode": "condition-aware post-seal direct prompt/reasoning/action/result audit",
        "actor": "Qwen3.8-27B-AD-IQ2_S",
        "coverage": "all completed calls in the sealed Experiment 009 measured run",
        "completed_call_count": len(calls),
        "calls": calls,
    }
    atomic_write(EXPERIMENT / "MECHANICAL_RESULTS.json", canonical_json_bytes(results))
    atomic_write(EXPERIMENT / "POSTSEAL_HIDDEN_GRADING.json", canonical_json_bytes(grading))
    atomic_write(EXPERIMENT / "TRANSCRIPT_INDEX.json", canonical_json_bytes(index))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
