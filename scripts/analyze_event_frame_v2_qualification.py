from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from working_set_exp.candidate import Candidate
from working_set_exp.event_frame_v2_qualification import (
    branch_inputs,
    verify_package,
    verify_source_closure,
)
from working_set_exp.jsonutil import (
    atomic_write,
    canonical_json_bytes,
    load_json_strict,
    sha256_bytes,
    sha256_file,
)
from working_set_exp.runner import verify_run
from working_set_exp.runtime import load_runtime
from working_set_exp.unified_receipts import hidden_grade


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "017_signal_bearing_event_frame_v2"
RUN = EXPERIMENT / "development_run"
DONOR_BANK = ROOT / "experiments" / "014_unified_active_phase_receipts" / "fresh_bank"
MARKER = "ARCHIVE-Z7"


def _verify_seal() -> dict[str, Any]:
    saved = load_json_strict((RUN / "RESPONSE_SEAL.json").read_bytes())
    for row in saved["files"]:
        path = RUN / Path(*row["path"].split("/"))
        if not path.is_file():
            raise RuntimeError(f"sealed file absent: {row['path']}")
        if path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise RuntimeError(f"sealed file differs: {row['path']}")
    aggregate = sha256_bytes(canonical_json_bytes(saved["files"]))
    if aggregate != saved["aggregate_sha256"]:
        raise RuntimeError("response-seal aggregate differs")
    return {
        "verified": True,
        "file_count": len(saved["files"]),
        "aggregate_sha256": aggregate,
        "seal_sha256": sha256_file(RUN / "RESPONSE_SEAL.json"),
    }


def _terminal_candidate(branch: Path, candidate_id: str) -> Candidate:
    matches = sorted(
        path
        for path in branch.rglob(candidate_id[:32])
        if path.is_dir() and path.parent.name == "snap"
    )
    for snapshot in reversed(matches):
        candidate = Candidate.create(
            {
                path.relative_to(snapshot).as_posix(): path.read_bytes()
                for path in snapshot.rglob("*")
                if path.is_file()
            }
        )
        if candidate.candidate_id == candidate_id:
            return candidate
    values = branch_inputs(DONOR_BANK, load_json_strict((branch / "SUMMARY.json").read_bytes())["fixture_id"])
    if values["state"].candidate.candidate_id == candidate_id:
        return values["state"].candidate
    raise RuntimeError(f"terminal candidate absent: {branch} {candidate_id}")


def _reasoning_excerpt(text: str, *, closing: bool = False) -> str:
    normalized = " ".join(text.split())
    limit = 700
    if len(normalized) <= limit:
        return normalized
    return normalized[-limit:] if closing else normalized[:limit]


def _event_signal(event: dict[str, Any]) -> dict[str, Any]:
    action = event["action"]
    result = event["result"]
    return {
        "sequence": event["sequence"],
        "event_handle": event["event_handle"],
        "action": action["action"],
        "path": action.get("path"),
        "check_id": action.get("check_id"),
        "action_payload_residency": event["action_payload"]["residency"],
        "action_payload_field_names": event["action_payload"]["field_names"],
        "result_accepted": result.get("accepted"),
        "result_passed": result.get("passed"),
        "result_candidate_id": result.get("candidate_id", result.get("checked_candidate_id")),
        "result_previous_candidate_id": result.get("previous_candidate_id"),
        "result_submitted_candidate_id": result.get("submitted_candidate_id"),
        "result_body_residency": event["result_body"]["residency"],
        "result_body_field_names": event["result_body"]["field_names"],
        "result_body_handle": event["result_body"].get("handle"),
    }


def _result_summary(result: dict[str, Any]) -> dict[str, Any]:
    kept = {
        key: result[key]
        for key in (
            "accepted",
            "error_code",
            "detail",
            "path",
            "handle",
            "check_id",
            "passed",
            "candidate_id",
            "previous_candidate_id",
            "checked_candidate_id",
            "submitted_candidate_id",
            "file_sha256",
            "complete",
            "returned_start_line",
            "returned_end_line",
            "next_start_line",
            "size_bytes",
            "action_payload_sha256",
            "exact_result_sha256",
        )
        if key in result
    }
    for key in ("content", "action_payload", "exact_result_utf8", "stdout", "stderr", "diff"):
        if key in result:
            body = canonical_json_bytes(result[key]) if isinstance(result[key], (dict, list)) else str(result[key]).encode("utf-8")
            kept[f"{key}_size_bytes"] = len(body)
            kept[f"{key}_sha256"] = sha256_bytes(body)
    return kept


def _records_by_response(branch: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line in (branch / "records.jsonl").read_bytes().splitlines():
        record = load_json_strict(line)
        if record["record_type"] == "action_result":
            rows[record["payload"]["response_id"]] = record["payload"]
    return rows


def main() -> None:
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    if receipt["status"] != "completed_and_response_sealed":
        raise RuntimeError("Experiment 017 response set is not sealed")
    if receipt["retries"] or receipt["repairs"] or receipt["rescues"]:
        raise RuntimeError("Experiment 017 execution policy differs")

    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    package = verify_package(EXPERIMENT / "execution_package", donor_bank=DONOR_BANK, profile=profile)
    closure = verify_source_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
    seal = _verify_seal()
    grades = load_json_strict((RUN / "POSTSEAL_HIDDEN_GRADING.json").read_bytes())
    saved_grades = {row["ordinal"]: row for row in grades["rows"]}

    calls: list[dict[str, Any]] = []
    branches: list[dict[str, Any]] = []
    verified_runs: list[dict[str, Any]] = []
    for cell in receipt["cells"]:
        ordinal = cell["ordinal"]
        branch = RUN / f"cell-{ordinal:02d}"
        summary = load_json_strict((branch / "SUMMARY.json").read_bytes())
        verification = verify_run(branch)
        verified_runs.append(
            {
                "ordinal": ordinal,
                "path": branch.relative_to(RUN).as_posix(),
                "verified": verification["verified"],
                "record_count": verification["record_count"],
                "disposition": verification["disposition"],
            }
        )
        candidate = _terminal_candidate(branch, summary["candidate_id"])
        values = branch_inputs(DONOR_BANK, summary["fixture_id"])
        fresh_grade = hidden_grade(values["fixture"], candidate)
        saved_grade = saved_grades[ordinal]["hidden"]
        if fresh_grade["passed"] != saved_grade["passed"]:
            raise RuntimeError(f"hidden grade differs for cell {ordinal}")

        by_response = _records_by_response(branch)
        branch_calls: list[dict[str, Any]] = []
        transcript = branch / "transcript"
        for request_path in sorted(transcript.glob("*-coding-request.json")):
            call_number = request_path.name.split("-", 1)[0]
            companions = {
                "coding_request": request_path,
                "endpoint_request": transcript / f"{call_number}-endpoint-request.json",
                "rendered_prompt": transcript / f"{call_number}-rendered-prompt.txt",
                "endpoint_response": transcript / f"{call_number}-endpoint-response.json",
                "assistant_content": transcript / f"{call_number}-assistant-content.json",
                "assistant_reasoning": transcript / f"{call_number}-assistant-reasoning.txt",
                "result": transcript / f"{call_number}-result.json",
            }
            if not all(path.is_file() for path in companions.values()):
                raise RuntimeError(f"incomplete call custody: cell {ordinal} call {call_number}")
            request = load_json_strict(request_path.read_bytes())
            endpoint_response = load_json_strict(companions["endpoint_response"].read_bytes())
            action = load_json_strict(companions["assistant_content"].read_bytes())
            result = load_json_strict(companions["result"].read_bytes())
            reasoning = companions["assistant_reasoning"].read_text(encoding="utf-8")
            metrics = by_response[endpoint_response["id"]]
            frame = request["active_phase_event_frame"]
            row = {
                "ordinal": ordinal,
                "call_number": int(call_number),
                "call_id": metrics["call_id"],
                "response_id": endpoint_response["id"],
                "fixture_id": summary["fixture_id"],
                "seed": summary["seed"],
                "candidate_id_before": request["candidate_id"],
                "phase_calls_used": request["resource_state"]["phase_calls_used"],
                "event_count_visible": len(frame["events"]),
                "event_signals": [_event_signal(event) for event in frame["events"]],
                "resident_signal_contract": frame["resident_signal_contract"],
                "event_frame_verification": request["event_frame_verification"],
                "action": action,
                "result": _result_summary(result),
                "reasoning_opening_excerpt": _reasoning_excerpt(reasoning),
                "reasoning_closing_excerpt": _reasoning_excerpt(reasoning, closing=True),
                "reasoning_sha256": sha256_file(companions["assistant_reasoning"]),
                "usage": {
                    key: metrics[key]
                    for key in (
                        "offline_prompt_tokens",
                        "server_reported_prompt_tokens",
                        "accounting_delta",
                        "completion_tokens",
                        "elapsed_ms",
                        "reasoning_content_bytes",
                        "reasoning_content_sha256",
                    )
                },
                "artifact_sha256": {name: sha256_file(path) for name, path in companions.items()},
                "direct_review_status": "reviewed_condition_aware_by_primary_agent_2026-08-30",
            }
            calls.append(row)
            branch_calls.append(row)

        counts = Counter(row["action"]["action"] for row in branch_calls)
        first_request = (transcript / "001-coding-request.json").read_bytes()
        first_endpoint = (transcript / "001-endpoint-request.json").read_bytes()
        first_prompt = (transcript / "001-rendered-prompt.txt").read_bytes()
        marker_absent_before_reopen = all(MARKER.encode("utf-8") not in data for data in (first_request, first_endpoint, first_prompt))
        branches.append(
            {
                "ordinal": ordinal,
                "fixture_id": summary["fixture_id"],
                "seed": summary["seed"],
                "disposition": summary["disposition"],
                "submitted": summary["submitted"],
                "public_check_passed": summary["public_check_passed"],
                "hidden_passed": fresh_grade["passed"],
                "candidate_id": candidate.candidate_id,
                "http_completion_calls": len(branch_calls),
                "action_sequence": [row["action"]["action"] for row in branch_calls],
                "action_counts": dict(sorted(counts.items())),
                "accepted_actions": sum(row["result"].get("accepted") is True for row in branch_calls),
                "rejected_actions": sum(row["result"].get("accepted") is not True for row in branch_calls),
                "prompt_tokens_sum": sum(row["usage"]["server_reported_prompt_tokens"] for row in branch_calls),
                "completion_tokens_sum": sum(row["usage"]["completion_tokens"] for row in branch_calls),
                "elapsed_ms_sum": sum(row["usage"]["elapsed_ms"] for row in branch_calls),
                "maximum_prompt_tokens": max(row["usage"]["server_reported_prompt_tokens"] for row in branch_calls),
                "marker_absent_from_initial_model_input": marker_absent_before_reopen if summary["fixture_id"].startswith("E17-") else None,
                "event_reopen_count": counts["reopen_event"],
                "result_reopen_count": counts["reopen_result"],
            }
        )

    if len(calls) != receipt["http_completion_calls"]:
        raise RuntimeError("direct transcript coverage differs")
    if len({row["response_id"] for row in calls}) != len(calls):
        raise RuntimeError("endpoint response IDs are not unique")

    signal_branches = [row for row in branches if row["fixture_id"] == "E17-HISTORICAL-ACTION-SIGNAL"]
    closure_branches = [row for row in branches if row["fixture_id"].startswith("E14-")]
    results = {
        "schema_version": "experiment-017-mechanical-results-v1",
        "scope": "exposed development-only placement and exact-payload-use qualification",
        "fresh_large_world_or_measured_claim": False,
        "run_status": receipt["status"],
        "package": package,
        "executable_closure": closure,
        "response_seal": seal,
        "prepared_invocations": receipt["prepared_invocations"],
        "http_completion_calls": receipt["http_completion_calls"],
        "directly_reviewed_completion_calls": len(calls),
        "verified_branch_runs": verified_runs,
        "all_runtime_accounting_deltas_zero": all(row["usage"]["accounting_delta"] == 0 for row in calls),
        "all_response_ids_unique": True,
        "server_shutdown_verified": receipt["server_shutdown_verified"],
        "retries": receipt["retries"],
        "repairs": receipt["repairs"],
        "rescues": receipt["rescues"],
        "all_branches_hidden_correct": all(row["hidden_passed"] for row in branches),
        "all_branches_checked_and_submitted": all(row["public_check_passed"] and row["submitted"] for row in branches),
        "closure_and_stale_check_branches": {
            "branch_count": len(closure_branches),
            "hidden_passes": sum(row["hidden_passed"] for row in closure_branches),
            "submissions": sum(row["submitted"] for row in closure_branches),
            "event_payload_reopens": sum(row["event_reopen_count"] for row in closure_branches),
            "exact_result_reopens": sum(row["result_reopen_count"] for row in closure_branches),
        },
        "historical_action_signal_branches": {
            "branch_count": len(signal_branches),
            "hidden_passes": sum(row["hidden_passed"] for row in signal_branches),
            "submissions": sum(row["submitted"] for row in signal_branches),
            "event_payload_reopens": sum(row["event_reopen_count"] for row in signal_branches),
            "marker_absent_from_every_initial_model_input": all(row["marker_absent_from_initial_model_input"] for row in signal_branches),
            "rejected_action_count": sum(row["rejected_actions"] for row in signal_branches),
        },
        "branches": branches,
    }
    index = {
        "schema_version": "experiment-017-transcript-index-v1",
        "reviewer": "Codex primary project agent",
        "review_mode": "condition-aware post-seal direct request/reasoning/action/result and host-path audit",
        "actor": "Qwen3.8-27B-AD-IQ2_S",
        "coverage": "all 21 completed live calls in the sealed Experiment 017 development run",
        "calls": calls,
    }
    atomic_write(EXPERIMENT / "MECHANICAL_RESULTS.json", canonical_json_bytes(results))
    atomic_write(EXPERIMENT / "TRANSCRIPT_INDEX.json", canonical_json_bytes(index))


if __name__ == "__main__":
    main()
