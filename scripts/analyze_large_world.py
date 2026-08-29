from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.large_world import hidden_grade, load_fixture
from working_set_exp.runner import verify_run
from working_set_exp.tools import run_checker


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "012_large_world_recurrent_continuity"
RUN = EXPERIMENT / "measured_run"
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


def candidate_from_branch(branch: Path, candidate_id: str) -> Candidate:
    matches = sorted(path for path in branch.rglob(candidate_id[:32]) if path.is_dir() and path.parent.name == "snap")
    if not matches:
        raise RuntimeError(f"candidate snapshot absent: {branch} {candidate_id}")
    candidates: list[Candidate] = []
    for base in matches:
        value = Candidate.create(
            {path.relative_to(base).as_posix(): path.read_bytes() for path in base.rglob("*") if path.is_file()}
        )
        if value.candidate_id != candidate_id:
            raise RuntimeError(f"snapshot candidate identity differs: {base}")
        candidates.append(value)
    return candidates[-1]


def result_summary(result: dict[str, Any]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "accepted": result.get("accepted"),
        "candidate_id": result.get("candidate_id", result.get("checked_candidate_id")),
    }
    for key in (
        "path",
        "kind",
        "offset",
        "next_offset",
        "total_entries",
        "complete",
        "requested_start_line",
        "returned_start_line",
        "returned_end_line",
        "next_start_line",
        "check_id",
        "passed",
        "probe_id",
        "fork_ready",
        "submitted",
        "handle",
    ):
        if key in result:
            value[key] = result[key]
    if "entries" in result:
        value["entry_count"] = len(result["entries"])
    if "content" in result:
        body = result["content"].encode("utf-8")
        value["content_size_bytes"] = len(body)
        value["content_sha256"] = sha256_bytes(body)
    if "body" in result:
        body_value = result["body"]
        body = body_value.encode("utf-8") if isinstance(body_value, str) else canonical_json_bytes(body_value)
        value["body_size_bytes"] = len(body)
        value["body_sha256"] = sha256_bytes(body)
    return value


def action_label(action: dict[str, Any]) -> str:
    name = action["action"]
    target = action.get("path") or action.get("handle") or action.get("check_id") or action.get("probe_id")
    if target is not None:
        return f"{name}({target})"
    return name


def record_metrics(run: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line in (run / "records.jsonl").read_bytes().splitlines():
        record = load_json_strict(line)
        if record["record_type"] == "action_result":
            payload = record["payload"]
            rows[payload["response_id"]] = {
                "offline_prompt_tokens": payload["offline_prompt_tokens"],
                "server_reported_prompt_tokens": payload["server_reported_prompt_tokens"],
                "accounting_delta": payload["accounting_delta"],
                "completion_tokens": payload["completion_tokens"],
                "elapsed_ms": payload["elapsed_ms"],
                "reasoning_content_bytes": payload["reasoning_content_bytes"],
                "reasoning_content_sha256": payload["reasoning_content_sha256"],
            }
    return rows


def transcript_index(receipt: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    completed: list[dict[str, Any]] = []
    denied: list[dict[str, Any]] = []
    metrics_by_run: dict[Path, dict[str, dict[str, Any]]] = {}
    action_paths = sorted(RUN.glob("cell-*/**/transcript/*-assistant-content.json"))
    for action_path in action_paths:
        run = action_path.parent.parent
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
        request = load_json_strict(companions["coding_request"].read_bytes())
        action = load_json_strict(action_path.read_bytes())
        result = load_json_strict(companions["result"].read_bytes())
        endpoint = load_json_strict(companions["endpoint_response"].read_bytes())
        call_id = endpoint["id"]
        if run not in metrics_by_run:
            metrics_by_run[run] = record_metrics(run)
        metrics = metrics_by_run[run][call_id]
        history_actions = [action_label(pair["response"]) for pair in request["history"]]
        completed.append(
            {
                "call": action_path.relative_to(RUN).as_posix().removesuffix("-assistant-content.json"),
                "response_id": call_id,
                "fixture_id": request["fixture_id"],
                "condition": action_path.relative_to(RUN).parts[1],
                "phase": request["phase"],
                "stage": request["stage"],
                "candidate_id_before": request["candidate_id"],
                "completed_phase_ids": request["completed_phase_ids"],
                "phase_calls_used": request["resource_state"]["phase_calls_used"],
                "phase_call_limit": request["resource_state"]["phase_call_limit"],
                "older_chronology_present": request["older_chronology_present"],
                "history_action_labels": history_actions,
                "history_pair_count": len(history_actions),
                "observation_directory_entry_count": len(request["observation_directory"]["entries"]),
                "p0_root_entry_count": len(request["current_p0"]["entries"]),
                "action": action,
                "action_label": action_label(action),
                "result": result_summary(result),
                "usage": metrics,
                "artifact_sha256": {name: sha256_file(path) for name, path in companions.items()},
                "direct_review_status": "reviewed_condition_aware_by_primary_agent_2026-08-29",
            }
        )
    if len(completed) != receipt["http_completion_calls"]:
        raise RuntimeError(f"completed transcript coverage differs: {len(completed)}")

    completed_paths = {row["call"] for row in completed}
    for request_path in sorted(RUN.glob("cell-*/**/transcript/*-coding-request.json")):
        call = request_path.relative_to(RUN).as_posix().removesuffix("-coding-request.json")
        if call in completed_paths:
            continue
        prompt_path = request_path.with_name(request_path.name.replace("-coding-request.json", "-rendered-prompt.txt"))
        endpoint_path = request_path.with_name(request_path.name.replace("-coding-request.json", "-endpoint-request.json"))
        if not prompt_path.is_file() or not endpoint_path.is_file():
            raise RuntimeError(f"denied prepared call lacks pre-HTTP custody: {request_path}")
        request = load_json_strict(request_path.read_bytes())
        denied.append(
            {
                "call": call,
                "fixture_id": request["fixture_id"],
                "condition": request_path.relative_to(RUN).parts[1],
                "phase": request["phase"],
                "candidate_id": request["candidate_id"],
                "phase_calls_used": request["resource_state"]["phase_calls_used"],
                "history_action_labels": [action_label(pair["response"]) for pair in request["history"]],
                "artifact_sha256": {
                    "coding_request": sha256_file(request_path),
                    "rendered_prompt": sha256_file(prompt_path),
                    "endpoint_request": sha256_file(endpoint_path),
                },
                "http_attempted": False,
            }
        )
    if len(completed) + len(denied) != receipt["prepared_invocations"]:
        raise RuntimeError("prepared invocation coverage differs")
    return completed, denied


def main() -> None:
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    if receipt["status"] != "completed_and_response_sealed":
        raise RuntimeError("unexpected Experiment 012 run status")
    seal = verify_seal()
    calls, denied = transcript_index(receipt)
    schedule = load_json_strict((EXPERIMENT / "SCHEDULE.json").read_bytes())
    cells = {row["ordinal"]: row for row in schedule["cells"]}

    verified_runs = []
    for summary_path in sorted(RUN.glob("cell-*/**/SUMMARY.json")):
        run = summary_path.parent
        if (run / "records.jsonl").is_file():
            verification = verify_run(run)
            verified_runs.append(
                {
                    "path": run.relative_to(RUN).as_posix(),
                    "verified": verification["verified"],
                    "record_count": verification["record_count"],
                    "disposition": verification["disposition"],
                }
            )

    grades = load_json_strict((RUN / "POSTSEAL_HIDDEN_GRADING.json").read_bytes())
    branch_rows = []
    for cell in receipt["cells"]:
        fixture = load_fixture(BANK, cell["fixture_id"])
        for condition in ("C50", "T25"):
            summary = cell["branches"][condition]
            branch = RUN / f"cell-{cell['ordinal']:02d}" / condition
            candidate = candidate_from_branch(branch, summary["candidate_id"])
            grade = hidden_grade(fixture, candidate)
            matching = [
                row for row in grades["branches"]
                if row["ordinal"] == cell["ordinal"] and row["condition"] == condition
            ]
            if len(matching) != 1 or matching[0]["hidden_passed"] != grade["passed"]:
                raise RuntimeError("post-seal hidden grade differs")
            branch_calls = [
                row for row in calls
                if row["call"].startswith(f"cell-{cell['ordinal']:02d}/{condition}/")
            ]
            counts = Counter(row["action"]["action"] for row in branch_calls)
            branch_rows.append(
                {
                    "ordinal": cell["ordinal"],
                    "fixture_id": cell["fixture_id"],
                    "seed": cell["seed"],
                    "condition": condition,
                    "completed_phase_ids": summary["completed_phase_ids"],
                    "submitted": summary["submitted"],
                    "hidden_grade": grade,
                    "postseal_phase_checker_results": {
                        phase_id: run_checker(candidate, fixture.phases[phase_id].checker)
                        for phase_id in ("A", "B", "C", "D")
                    },
                    "prepared_invocations": summary["prepared_invocations"],
                    "http_completion_calls": summary["http_completion_calls"],
                    "reconstruction_count": summary["reconstruction_count"],
                    "action_counts": dict(sorted(counts.items())),
                    "action_sequence": [row["action_label"] for row in branch_calls],
                    "prompt_tokens_sum": sum(row["usage"]["server_reported_prompt_tokens"] for row in branch_calls),
                    "completion_tokens_sum": sum(row["usage"]["completion_tokens"] for row in branch_calls),
                    "elapsed_ms_sum": sum(row["usage"]["elapsed_ms"] for row in branch_calls),
                    "maximum_server_prompt_tokens": max(
                        (row["usage"]["server_reported_prompt_tokens"] for row in branch_calls), default=0
                    ),
                }
            )

    results = {
        "schema_version": "experiment-012-mechanical-results-v1",
        "run_status": receipt["status"],
        "formal_primary_comparison_scorable": True,
        "response_seal": seal,
        "prepared_invocations": receipt["prepared_invocations"],
        "http_completion_calls": receipt["http_completion_calls"],
        "capacity_denied_prepared_invocations": len(denied),
        "directly_reviewed_completion_calls": len(calls),
        "verified_stage_runs": len(verified_runs),
        "all_completed_actions_accepted": all(row["result"]["accepted"] is True for row in calls),
        "all_runtime_accounting_deltas_zero": all(row["usage"]["accounting_delta"] == 0 for row in calls),
        "all_response_ids_unique": len({row["response_id"] for row in calls}) == len(calls),
        "server_shutdown_verified": receipt["server_shutdown_verified"],
        "evaluator_reads_before_seal": receipt["evaluator_reads_before_seal"],
        "retries": receipt["retries"],
        "repairs": receipt["repairs"],
        "rescues": receipt["rescues"],
        "branches": branch_rows,
        "verified_runs": verified_runs,
    }
    index = {
        "schema_version": "experiment-012-transcript-index-v1",
        "reviewer": "Codex primary project agent",
        "review_mode": "condition-aware post-seal direct coding-request/rendered-prompt/reasoning/action/result/host-path audit",
        "actor": "Qwen3.8-27B-AD-IQ2_S",
        "coverage": "all completed calls and all pre-HTTP capacity denials in the sealed Experiment 012 run",
        "completed_call_count": len(calls),
        "capacity_denied_prepared_call_count": len(denied),
        "calls": calls,
        "capacity_denied_prepared_calls": denied,
    }
    atomic_write(EXPERIMENT / "MECHANICAL_RESULTS.json", canonical_json_bytes(results))
    atomic_write(EXPERIMENT / "TRANSCRIPT_INDEX.json", canonical_json_bytes(index))


if __name__ == "__main__":
    main()
