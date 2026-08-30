from __future__ import annotations

from collections import Counter
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
from working_set_exp.large_world_event_v2 import (
    hidden_grade,
    load_fixture,
    verify_bank,
    verify_package,
    verify_source_closure,
)
from working_set_exp.runner import verify_run
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "018_large_world_event_frame_v2"
RUN = EXPERIMENT / "measured_run"
BANK = EXPERIMENT / "fresh_bank"
MARKER = "HARBOR-K9"


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


def _candidate_from_custody(branch: Path, fixture: Any, candidate_id: str) -> Candidate:
    matches = sorted(
        path for path in branch.rglob(candidate_id[:32])
        if path.is_dir() and path.parent.name == "snap"
    )
    for snapshot in reversed(matches):
        candidate = Candidate.create({
            path.relative_to(snapshot).as_posix(): path.read_bytes()
            for path in snapshot.rglob("*") if path.is_file()
        })
        if candidate.candidate_id == candidate_id:
            return candidate
    if fixture.initial.candidate_id == candidate_id:
        return fixture.initial
    raise RuntimeError(f"terminal candidate absent: {branch} {candidate_id}")


def _records_by_response(branch: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line in (branch / "records.jsonl").read_bytes().splitlines():
        record = load_json_strict(line)
        if record["record_type"] == "action_result":
            rows[record["payload"]["response_id"]] = record["payload"]
    return rows


def _reasoning_excerpt(text: str, *, closing: bool = False) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= 700:
        return normalized
    return normalized[-700:] if closing else normalized[:700]


def _event_signal(event: dict[str, Any]) -> dict[str, Any]:
    action = event["action"]
    result = event["result"]
    return {
        "sequence": event["sequence"],
        "event_handle": event["event_handle"],
        "action": action["action"],
        "target": action.get("path", action.get("handle", action.get("check_id"))),
        "start_line": action.get("start_line"),
        "result_accepted": result.get("accepted"),
        "result_complete": result.get("complete"),
        "returned_start_line": result.get("returned_start_line"),
        "returned_end_line": result.get("returned_end_line"),
        "next_start_line": result.get("next_start_line"),
        "result_passed": result.get("passed"),
        "result_candidate_id": result.get("candidate_id", result.get("checked_candidate_id")),
        "previous_candidate_id": result.get("previous_candidate_id"),
        "submitted_candidate_id": result.get("submitted_candidate_id"),
        "action_payload_residency": event["action_payload"]["residency"],
        "action_payload_fields": event["action_payload"]["field_names"],
        "result_body_residency": event["result_body"]["residency"],
        "result_body_fields": event["result_body"]["field_names"],
        "result_body_handle": event["result_body"].get("handle"),
    }


def _result_summary(result: dict[str, Any]) -> dict[str, Any]:
    kept = {
        key: result[key]
        for key in (
            "accepted", "error_code", "detail", "path", "handle", "check_id", "passed",
            "candidate_id", "previous_candidate_id", "checked_candidate_id",
            "submitted_candidate_id", "file_sha256", "complete", "returned_start_line",
            "returned_end_line", "next_start_line", "size_bytes", "exact_result_sha256",
        ) if key in result
    }
    for key in ("content", "action_payload", "exact_result_utf8", "stdout", "stderr", "diff"):
        if key in result:
            value = result[key]
            body = canonical_json_bytes(value) if isinstance(value, (dict, list)) else str(value).encode("utf-8")
            kept[f"{key}_size_bytes"] = len(body)
            kept[f"{key}_sha256"] = sha256_bytes(body)
    return kept


def _review_segment(
    *, ordinal: int, fixture_id: str, seed: int, condition: str, segment: str, path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    verification = verify_run(path)
    metrics_by_response = _records_by_response(path)
    calls: list[dict[str, Any]] = []
    transcript = path / "transcript"
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
        if not all(item.is_file() for item in companions.values()):
            raise RuntimeError(f"incomplete call custody: cell {ordinal} {segment} call {call_number}")
        request = load_json_strict(request_path.read_bytes())
        endpoint_response = load_json_strict(companions["endpoint_response"].read_bytes())
        action = load_json_strict(companions["assistant_content"].read_bytes())
        result = load_json_strict(companions["result"].read_bytes())
        reasoning = companions["assistant_reasoning"].read_text(encoding="utf-8")
        message = endpoint_response["choices"][0]["message"]
        if load_json_strict(message["content"].encode("utf-8")) != action:
            raise RuntimeError(f"saved action differs from endpoint content: {companions['assistant_content']}")
        if message.get("reasoning_content", "") != reasoning:
            raise RuntimeError(f"saved reasoning differs from endpoint content: {companions['assistant_reasoning']}")
        response_id = endpoint_response["id"]
        metrics = metrics_by_response[response_id]
        frame = request["active_phase_event_frame"]
        if request["event_frame_verification"]["verified"] is not True:
            raise RuntimeError(f"unverified model-facing event frame: {request_path}")
        complete_reads = [
            {"sequence": event["sequence"], "path": event["action"].get("path")}
            for event in frame["events"]
            if event["action"]["action"] == "read" and event["result"].get("complete") is True
        ]
        row = {
            "ordinal": ordinal,
            "fixture_id": fixture_id,
            "seed": seed,
            "condition": condition,
            "segment": segment,
            "call_number": int(call_number),
            "call_id": metrics["call_id"],
            "response_id": response_id,
            "candidate_id_before": request["candidate_id"],
            "calls_used_before": request["resource_state"]["calls_used"],
            "event_count_visible": len(frame["events"]),
            "externalized_payload_through_sequence": frame["externalized_payload_through_sequence"],
            "complete_reads_visible": complete_reads,
            "event_signals": [_event_signal(event) for event in frame["events"]],
            "observation_directory": request["observation_directory"],
            "resident_signal_contract": frame["resident_signal_contract"],
            "action": action,
            "result": _result_summary(result),
            "reasoning_opening_excerpt": _reasoning_excerpt(reasoning),
            "reasoning_closing_excerpt": _reasoning_excerpt(reasoning, closing=True),
            "reasoning_sha256": sha256_file(companions["assistant_reasoning"]),
            "reasoning_size_bytes": companions["assistant_reasoning"].stat().st_size,
            "usage": {
                key: metrics[key] for key in (
                    "offline_prompt_tokens", "server_reported_prompt_tokens", "accounting_delta",
                    "completion_tokens", "elapsed_ms", "reasoning_content_bytes", "reasoning_content_sha256",
                )
            },
            "artifact_sha256": {name: sha256_file(item) for name, item in companions.items()},
            "direct_review_status": "reviewed_condition_aware_by_primary_agent_2026-08-30",
        }
        calls.append(row)
    return calls, {
        "path": path.relative_to(RUN).as_posix(),
        "verified": verification["verified"],
        "record_count": verification["record_count"],
        "disposition": verification["disposition"],
    }


def main() -> None:
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    if receipt["status"] != "completed_and_response_sealed":
        raise RuntimeError("Experiment 018 response set is not sealed")
    if receipt["retries"] or receipt["repairs"] or receipt["rescues"]:
        raise RuntimeError("Experiment 018 execution policy differs")

    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    bank = verify_bank(BANK)
    package = verify_package(EXPERIMENT / "execution_package", bank=BANK, profile=profile)
    closure = verify_source_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json")
    seal = _verify_seal()
    grades = load_json_strict((RUN / "POSTSEAL_HIDDEN_GRADING.json").read_bytes())
    saved_grades = {(row["ordinal"], row["condition"]): row for row in grades["rows"]}

    calls: list[dict[str, Any]] = []
    trajectories: list[dict[str, Any]] = []
    verified_runs: list[dict[str, Any]] = []
    for cell in receipt["cells"]:
        ordinal = cell["ordinal"]
        fixture_id = cell["fixture_id"]
        seed = cell["seed"]
        fixture = load_fixture(BANK, fixture_id, include_evaluator=True)
        shared_path = RUN / f"cell-{ordinal:02d}" / "shared"
        shared_calls, shared_verification = _review_segment(
            ordinal=ordinal, fixture_id=fixture_id, seed=seed, condition="SHARED", segment="shared", path=shared_path,
        )
        calls.extend(shared_calls)
        verified_runs.append(shared_verification)
        shared_prompt_tokens = sum(row["usage"]["server_reported_prompt_tokens"] for row in shared_calls)

        for condition in ("R50", "X25"):
            branch_path = RUN / f"cell-{ordinal:02d}" / condition
            branch_summary = load_json_strict((branch_path / "SUMMARY.json").read_bytes())
            branch_calls, branch_verification = _review_segment(
                ordinal=ordinal, fixture_id=fixture_id, seed=seed, condition=condition,
                segment=condition, path=branch_path,
            )
            calls.extend(branch_calls)
            verified_runs.append(branch_verification)
            candidate = _candidate_from_custody(branch_path, fixture, branch_summary["candidate_id"])
            fresh_hidden = hidden_grade(fixture, candidate)
            saved_hidden = saved_grades[(ordinal, condition)]["hidden"]
            if fresh_hidden["passed"] != saved_hidden["passed"]:
                raise RuntimeError(f"hidden grade differs for cell {ordinal} {condition}")
            combined_calls = shared_calls + branch_calls
            counts = Counter(row["action"]["action"] for row in combined_calls)
            trajectories.append({
                "ordinal": ordinal,
                "fixture_id": fixture_id,
                "seed": seed,
                "condition": condition,
                "disposition": branch_summary["disposition"],
                "candidate_id": candidate.candidate_id,
                "hidden_passed": fresh_hidden["passed"],
                "public_check_passed": branch_summary["public_check_passed"],
                "submitted": branch_summary["submitted"],
                "capacity_stops": branch_summary["capacity_stops"],
                "shared_calls": len(shared_calls),
                "branch_http_calls": len(branch_calls),
                "total_http_calls": len(combined_calls),
                "action_sequence": [row["action"]["action"] for row in combined_calls],
                "action_counts": dict(sorted(counts.items())),
                "prompt_tokens_sum": sum(row["usage"]["server_reported_prompt_tokens"] for row in combined_calls),
                "shared_prompt_tokens": shared_prompt_tokens,
                "branch_prompt_tokens": sum(row["usage"]["server_reported_prompt_tokens"] for row in branch_calls),
                "completion_tokens_sum": sum(row["usage"]["completion_tokens"] for row in combined_calls),
                "elapsed_ms_sum": sum(row["usage"]["elapsed_ms"] for row in combined_calls),
                "maximum_prompt_tokens": max(row["usage"]["server_reported_prompt_tokens"] for row in combined_calls),
                "externalized_payload_count": branch_summary["externalized_payload_count"],
                "result_reopens": counts["reopen_result"],
                "observation_reopens": counts["reopen_observation"],
                "p0_pages": counts["p0_page"],
                "reads": counts["read"],
                "patches": counts["patch"],
                "checks": counts["check"],
                "submits": counts["submit"],
            })

    if len(calls) != receipt["http_completion_calls"]:
        raise RuntimeError(f"direct transcript coverage differs: {len(calls)} != {receipt['http_completion_calls']}")
    if len({row["response_id"] for row in calls}) != len(calls):
        raise RuntimeError("endpoint response IDs are not unique")
    if any(row["usage"]["accounting_delta"] != 0 for row in calls):
        raise RuntimeError("nonzero runtime token-accounting delta")

    source = [row for row in trajectories if row["fixture_id"] == "E18-SOURCE-LANTERN"]
    observation = [row for row in trajectories if row["fixture_id"] == "E18-OBS-HARBOR"]
    results = {
        "schema_version": "experiment-018-mechanical-results-v1",
        "scope": "fresh large-world R50 versus X25 signal-bearing event-frame V2 comparison",
        "run_status": receipt["status"],
        "bank": bank,
        "package": package,
        "executable_closure": closure,
        "response_seal": seal,
        "prepared_invocations": receipt["prepared_invocations"],
        "http_completion_calls": receipt["http_completion_calls"],
        "directly_reviewed_completion_calls": len(calls),
        "verified_runs": verified_runs,
        "all_runtime_accounting_deltas_zero": True,
        "all_response_ids_unique": True,
        "server_shutdown_verified": receipt["server_shutdown_verified"],
        "retries": receipt["retries"],
        "repairs": receipt["repairs"],
        "rescues": receipt["rescues"],
        "aggregate": {
            condition: {
                "trajectories": len(rows),
                "hidden_passes": sum(row["hidden_passed"] for row in rows),
                "submissions": sum(row["submitted"] for row in rows),
                "capacity_stops": sum(row["capacity_stops"] for row in rows),
                "total_http_calls": sum(row["total_http_calls"] for row in rows),
                "prompt_tokens_sum": sum(row["prompt_tokens_sum"] for row in rows),
                "elapsed_ms_sum": sum(row["elapsed_ms_sum"] for row in rows),
                "result_reopens": sum(row["result_reopens"] for row in rows),
                "observation_reopens": sum(row["observation_reopens"] for row in rows),
            }
            for condition in ("R50", "X25")
            for rows in [[row for row in trajectories if row["condition"] == condition]]
        },
        "source_family": {
            condition: {
                "trajectories": len(rows),
                "hidden_passes": sum(row["hidden_passed"] for row in rows),
                "submissions": sum(row["submitted"] for row in rows),
                "capacity_stops": sum(row["capacity_stops"] for row in rows),
            }
            for condition in ("R50", "X25")
            for rows in [[row for row in source if row["condition"] == condition]]
        },
        "observation_family": {
            condition: {
                "trajectories": len(rows),
                "hidden_passes": sum(row["hidden_passed"] for row in rows),
                "submissions": sum(row["submitted"] for row in rows),
                "capacity_stops": sum(row["capacity_stops"] for row in rows),
            }
            for condition in ("R50", "X25")
            for rows in [[row for row in observation if row["condition"] == condition]]
        },
        "trajectories": trajectories,
    }
    index = {
        "schema_version": "experiment-018-transcript-index-v1",
        "reviewer": "Codex primary project agent",
        "review_mode": "condition-aware post-seal direct request/reasoning/action/result and host-path audit",
        "actor": "Qwen3.8-27B-AD-IQ2_S",
        "coverage": "all 87 completed live calls in the sealed Experiment 018 run",
        "calls": calls,
    }
    atomic_write(EXPERIMENT / "MECHANICAL_RESULTS.json", canonical_json_bytes(results))
    atomic_write(EXPERIMENT / "TRANSCRIPT_INDEX.json", canonical_json_bytes(index))


if __name__ == "__main__":
    main()
