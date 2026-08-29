from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from working_set_exp.candidate import Candidate
from working_set_exp.custody import verify_records
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
EXPERIMENT = ROOT / "experiments" / "008_recurrent_bounded_pressure_primary"
RUN = EXPERIMENT / "partial_measured_run"
INDEX = EXPERIMENT / "TRANSCRIPT_INDEX.json"


def _verify_seal() -> dict[str, Any]:
    seal = load_json_strict((RUN / "RESPONSE_SEAL.json").read_bytes())
    for row in seal["files"]:
        path = RUN / Path(*row["path"].split("/"))
        if not path.is_file() or path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise RuntimeError(f"sealed artifact differs: {row['path']}")
    aggregate = sha256_bytes(canonical_json_bytes(seal["files"]))
    if aggregate != seal["aggregate_sha256"]:
        raise RuntimeError("response seal aggregate differs")
    return {"verified": True, "file_count": len(seal["files"]), "aggregate_sha256": aggregate}


def _candidate_from_snapshot(run: Path, candidate_id: str) -> Candidate:
    matches = [path for path in (run / "snap").iterdir() if path.is_dir() and path.name == candidate_id[:32]]
    if len(matches) != 1:
        raise RuntimeError((run, candidate_id, matches))
    base = matches[0]
    files = {path.relative_to(base).as_posix(): path.read_bytes() for path in base.rglob("*") if path.is_file()}
    candidate = Candidate.create(files)
    if candidate.candidate_id != candidate_id:
        raise RuntimeError("snapshot candidate identity differs")
    return candidate


def _stage_metrics(run: Path, fixture_id: str) -> dict[str, Any]:
    summary = load_json_strict((run / "SUMMARY.json").read_bytes())
    fixture = load_recurrent_fixture(EXPERIMENT / "fresh_bank", fixture_id)
    candidate = _candidate_from_snapshot(run, summary["candidate_id"])
    actions: list[dict[str, Any]] = []
    prompt_tokens = 0
    completion_tokens = 0
    endpoint_ms = 0.0
    reasoning_bytes = 0
    for path in sorted((run / "transcript").glob("*-assistant-content.json")):
        actions.append(load_json_strict(path.read_bytes()))
        stem = path.name.replace("-assistant-content.json", "")
        reasoning_path = path.with_name(stem + "-assistant-reasoning.txt")
        reasoning_bytes += reasoning_path.stat().st_size
        response = load_json_strict(path.with_name(stem + "-endpoint-response.json").read_bytes())
        prompt_tokens += response["usage"]["prompt_tokens"]
        completion_tokens += response["usage"]["completion_tokens"]
        timings = response.get("timings", {})
        endpoint_ms += float(timings.get("prompt_ms", 0)) + float(timings.get("predicted_ms", 0))
    action_counts: dict[str, int] = {}
    for action in actions:
        name = action["action"]
        action_counts[name] = action_counts.get(name, 0) + 1
    return {
        "path": run.relative_to(RUN).as_posix(), "fixture_id": fixture_id,
        "condition": summary.get("condition", "shared-prefix"), "disposition": summary["disposition"],
        "candidate_id": summary["candidate_id"], "hidden_pass_at_stage_end": hidden_grade(fixture, candidate)["passed"],
        "calls": len(actions), "actions": actions, "action_counts": action_counts,
        "prompt_tokens_sum": prompt_tokens, "completion_tokens_sum": completion_tokens,
        "endpoint_compute_ms_sum": round(endpoint_ms, 3), "reasoning_bytes": reasoning_bytes,
        "maximum_offline_prompt_tokens": summary.get("maximum_offline_prompt_tokens"),
        "public_check_passed": summary.get("public_check_passed"), "submitted": summary.get("submitted"),
        "capacity_stop": summary.get("capacity_stop"),
    }


def _interrupted_stage_metrics(run: Path, fixture_id: str) -> dict[str, Any]:
    records = verify_records(run / "records.jsonl", run)
    completed = [row for row in records if row["record_type"] == "action_result"]
    if not completed:
        raise RuntimeError("interrupted stage has no completed action")
    candidate_id = completed[-1]["payload"]["candidate_id"]
    fixture = load_recurrent_fixture(EXPERIMENT / "fresh_bank", fixture_id)
    candidate = _candidate_from_snapshot(run, candidate_id)
    actions = [row["payload"]["action"] for row in completed]
    action_counts: dict[str, int] = {}
    for action in actions:
        action_counts[action["action"]] = action_counts.get(action["action"], 0) + 1
    prompt_tokens = sum(int(row["payload"]["server_reported_prompt_tokens"]) for row in completed)
    completion_tokens = sum(int(row["payload"]["completion_tokens"]) for row in completed)
    endpoint_ms = sum(float(row["payload"]["elapsed_ms"]) for row in completed)
    reasoning_bytes = sum(int(row["payload"]["reasoning_content_bytes"]) for row in completed)
    return {
        "path": run.relative_to(RUN).as_posix(), "fixture_id": fixture_id,
        "condition": run.relative_to(RUN).parts[1],
        "disposition": "operator_interrupted_during_http_call_2",
        "candidate_id": candidate_id, "hidden_pass_at_stage_end": hidden_grade(fixture, candidate)["passed"],
        "calls": len(actions), "actions": actions, "action_counts": action_counts,
        "prompt_tokens_sum": prompt_tokens, "completion_tokens_sum": completion_tokens,
        "endpoint_compute_ms_sum": round(endpoint_ms, 3), "reasoning_bytes": reasoning_bytes,
        "maximum_offline_prompt_tokens": max(int(row["payload"]["offline_prompt_tokens"]) for row in completed),
        "public_check_passed": None, "submitted": None, "capacity_stop": None,
        "prepared_without_completion": 1,
    }


def main() -> None:
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    rows = []
    transcript_rows = []
    cell_ids = {f"cell-{row['ordinal']:02d}": row["fixture_id"] for row in receipt["cells"]}
    for summary_path in sorted(RUN.glob("cell-*/**/SUMMARY.json")):
        cell_name = summary_path.relative_to(RUN).parts[0]
        verification = verify_run(summary_path.parent)
        if not verification["verified"]:
            raise RuntimeError(f"run did not replay: {summary_path.parent}")
        rows.append(_stage_metrics(summary_path.parent, cell_ids[cell_name]))
    summarized_dirs = {path.parent for path in RUN.glob("cell-*/**/SUMMARY.json")}
    for records_path in sorted(RUN.glob("cell-*/**/records.jsonl")):
        if records_path.parent in summarized_dirs:
            continue
        cell_name = records_path.relative_to(RUN).parts[0]
        rows.append(_interrupted_stage_metrics(records_path.parent, cell_ids[cell_name]))
    for action_path in sorted(RUN.glob("cell-*/**/transcript/*-assistant-content.json")):
        stem = action_path.name.replace("-assistant-content.json", "")
        reasoning_path = action_path.with_name(stem + "-assistant-reasoning.txt")
        request_path = action_path.with_name(stem + "-coding-request.json")
        endpoint_request_path = action_path.with_name(stem + "-endpoint-request.json")
        response_path = action_path.with_name(stem + "-endpoint-response.json")
        result_path = action_path.with_name(stem + "-result.json")
        required = [reasoning_path, request_path, endpoint_request_path, response_path, result_path]
        if not all(path.is_file() for path in required):
            raise RuntimeError(f"completed call lacks exact custody: {action_path}")
        action = load_json_strict(action_path.read_bytes())
        transcript_rows.append({
            "call": action_path.relative_to(RUN).as_posix().replace("-assistant-content.json", ""),
            "action": action["action"],
            "coding_request_sha256": sha256_file(request_path),
            "endpoint_request_sha256": sha256_file(endpoint_request_path),
            "endpoint_response_sha256": sha256_file(response_path),
            "assistant_content_sha256": sha256_file(action_path),
            "private_reasoning_sha256": sha256_file(reasoning_path),
            "result_sha256": sha256_file(result_path),
            "direct_review_status": "reviewed_condition_aware_by_primary_agent_2026-08-28",
        })
    if len(transcript_rows) != receipt["http_completion_calls"]:
        raise RuntimeError("transcript index does not cover every HTTP completion")
    seal = _verify_seal()
    result = {
        "schema_version": "experiment-008-partial-mechanical-results-v1",
        "run_status": receipt["status"], "research_disposition": receipt["research_disposition"],
        "response_seal_sha256": sha256_file(RUN / "RESPONSE_SEAL.json"),
        "prepared_invocations": receipt["prepared_invocations"],
        "http_completion_calls": receipt["http_completion_calls"],
        "sealed_evidence_verification": seal,
        "verified_completed_stage_runs": len(summarized_dirs),
        "analyzed_stage_rows": len(rows),
        "directly_reviewed_completion_calls": len(transcript_rows),
        "stages": rows,
    }
    atomic_write(EXPERIMENT / "PARTIAL_MECHANICAL_RESULTS.json", canonical_json_bytes(result))
    atomic_write(INDEX, canonical_json_bytes({
        "schema_version": "experiment-008-transcript-index-v1",
        "reviewer": "Codex primary project agent",
        "review_mode": "condition-aware post-seal direct audit",
        "actor": "Qwen3.8-27B-AD-IQ2_S",
        "coverage": "all completed model calls in the immutable partial measured run",
        "completed_call_count": len(transcript_rows),
        "calls": transcript_rows,
    }))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
