from __future__ import annotations

from pathlib import Path
from typing import Any

from working_set_exp.candidate import Candidate
from working_set_exp.ecological_pilot import hidden_grade, load_fixture
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.runner import verify_run


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "019_owner_controlled_ecological_pilot"
RUN = EXPERIMENT / "measured_run"
BANK = EXPERIMENT / "fresh_bank"


def _verify_partial_seal() -> dict[str, Any]:
    seal_path = RUN / "RESPONSE_SEAL.json"
    seal = load_json_strict(seal_path.read_bytes())
    for row in seal["files"]:
        path = RUN / Path(*row["path"].split("/"))
        if not path.is_file() or path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise RuntimeError(f"sealed partial artifact differs: {row['path']}")
    aggregate = sha256_bytes(canonical_json_bytes(seal["files"]))
    if aggregate != seal["aggregate_sha256"] or seal["evaluator_truth_opened"] is not False:
        raise RuntimeError("partial response seal differs")
    return {
        "verified": True,
        "file_count": len(seal["files"]),
        "aggregate_sha256": aggregate,
        "seal_sha256": sha256_file(seal_path),
    }


def _candidate_from_snapshot(path: Path, candidate_id: str) -> Candidate:
    snapshot = path / "snap" / candidate_id[:32]
    candidate = Candidate.create(
        {item.relative_to(snapshot).as_posix(): item.read_bytes() for item in snapshot.rglob("*") if item.is_file()}
    )
    if candidate.candidate_id != candidate_id:
        raise RuntimeError("candidate snapshot differs")
    return candidate


def _result_summary(result: dict[str, Any]) -> dict[str, Any]:
    kept = {
        key: result[key]
        for key in (
            "accepted", "error_code", "detail", "path", "handle", "check_id", "passed",
            "candidate_id", "previous_candidate_id", "checked_candidate_id", "submitted_candidate_id",
            "file_sha256", "complete", "returned_start_line", "returned_end_line", "next_start_line",
        )
        if key in result
    }
    for key in ("content", "diff", "stdout", "stderr", "exact_result_utf8"):
        if key in result:
            raw = str(result[key]).encode("utf-8")
            kept[f"{key}_size_bytes"] = len(raw)
            kept[f"{key}_sha256"] = sha256_bytes(raw)
    return kept


def _call_rows(cell: str) -> list[dict[str, Any]]:
    transcript = RUN / cell / "shared" / "transcript"
    rows: list[dict[str, Any]] = []
    for request_path in sorted(transcript.glob("*-coding-request.json")):
        number = request_path.name.split("-", 1)[0]
        companions = {
            "coding_request": request_path,
            "endpoint_request": transcript / f"{number}-endpoint-request.json",
            "rendered_prompt": transcript / f"{number}-rendered-prompt.txt",
            "endpoint_response": transcript / f"{number}-endpoint-response.json",
            "assistant_content": transcript / f"{number}-assistant-content.json",
            "assistant_reasoning": transcript / f"{number}-assistant-reasoning.txt",
            "result": transcript / f"{number}-result.json",
        }
        if not all(path.is_file() for path in companions.values()):
            raise RuntimeError(f"incomplete saved call: {cell} {number}")
        request = load_json_strict(request_path.read_bytes())
        endpoint = load_json_strict(companions["endpoint_response"].read_bytes())
        action = load_json_strict(companions["assistant_content"].read_bytes())
        result = load_json_strict(companions["result"].read_bytes())
        reasoning = companions["assistant_reasoning"].read_text(encoding="utf-8")
        message = endpoint["choices"][0]["message"]
        if load_json_strict(message["content"].encode("utf-8")) != action:
            raise RuntimeError(f"assistant action differs: {cell} {number}")
        if message.get("reasoning_content", "") != reasoning:
            raise RuntimeError(f"assistant reasoning differs: {cell} {number}")
        events = request["active_phase_event_frame"]["events"]
        rows.append(
            {
                "cell": cell,
                "call_number": int(number),
                "fixture_id": request["fixture_id"],
                "candidate_id_before": request["candidate_id"],
                "calls_used_before": request["resource_state"]["calls_used"],
                "calls_remaining_before": request["resource_state"]["calls_remaining"],
                "visible_event_count": len(events),
                "externalized_payload_through_sequence": request["active_phase_event_frame"]["externalized_payload_through_sequence"],
                "visible_observation_entries": request["observation_directory"]["entries"],
                "action": action,
                "result": _result_summary(result),
                "reasoning_text": reasoning,
                "usage": endpoint["usage"],
                "finish_reason": endpoint["choices"][0]["finish_reason"],
                "artifact_paths": {key: path.relative_to(RUN).as_posix() for key, path in companions.items()},
                "artifact_sha256": {key: sha256_file(path) for key, path in companions.items()},
                "direct_review_status": "reviewed_condition_aware_by_primary_agent_2026-08-30",
            }
        )
    return rows


def main() -> None:
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    if receipt["status"] != "infrastructure_or_integrity_stopped" or receipt["error_type"] != "FileExistsError":
        raise RuntimeError("Experiment 019 stop identity differs")
    seal = _verify_partial_seal()
    cell_01_verification = verify_run(RUN / "cell-01" / "shared")
    calls = _call_rows("cell-01") + _call_rows("cell-02")
    if len(calls) != 13:
        raise RuntimeError("Experiment 019 saved completion count differs")
    completed_action_records = sum(
        1
        for cell in ("cell-01", "cell-02")
        for line in (RUN / cell / "shared" / "records.jsonl").read_bytes().splitlines()
        if load_json_strict(line)["record_type"] == "action_result"
    )
    terminal_id = "5c7eba4fbad9c51325a9abc4f4b27c5b8d9eedb5b344558b5921915ed854a49f"
    fixture = load_fixture(BANK, "E19-SOURCE-REOPEN", include_evaluator=True)
    candidate = _candidate_from_snapshot(RUN / "cell-01" / "shared", terminal_id)
    grade = hidden_grade(fixture, candidate)
    grading = {
        "schema_version": "experiment-019-postseal-partial-hidden-grading-v1",
        "response_seal_sha256": seal["seal_sha256"],
        "evaluator_opened_after_partial_seal": True,
        "formal_paired_comparison_scorable": False,
        "rows": [
            {
                "cell": "cell-01",
                "fixture_id": "E19-SOURCE-REOPEN",
                "seed": 173205,
                "candidate_id": terminal_id,
                "submitted": True,
                "public_check_passed": True,
                "hidden": grade,
            }
        ],
    }
    mechanical = {
        "schema_version": "experiment-019-partial-mechanical-results-v1",
        "status": "infrastructure_stopped_unscorable_as_paired_experiment",
        "receipt_reported_http_completions": receipt["http_completion_calls"],
        "saved_exact_http_completions": len(calls),
        "completed_action_result_records": completed_action_records,
        "unrecorded_but_exactly_custodied_terminal_call": {"cell": "cell-02", "call_number": 4},
        "cell_01_run_verification": cell_01_verification,
        "partial_response_seal": seal,
        "submitted_hidden_correct_trajectories": 1,
        "treatment_boundaries_reached": 0,
        "r50_branches_executed": 0,
        "x25_branches_executed": 0,
        "retries": receipt["retries"],
        "repairs": receipt["repairs"],
        "rescues": receipt["rescues"],
        "server_shutdown_verified": receipt["server_shutdown_verified"],
    }
    index = {
        "schema_version": "experiment-019-partial-transcript-index-v1",
        "direct_review_scope": "every saved coding request, endpoint response, private reasoning output, action, and result",
        "condition_awareness": "pre-treatment shared-prefix corrective audit",
        "calls": calls,
    }
    atomic_write(EXPERIMENT / "POSTSEAL_PARTIAL_HIDDEN_GRADING.json", canonical_json_bytes(grading))
    atomic_write(EXPERIMENT / "MECHANICAL_RESULTS.json", canonical_json_bytes(mechanical))
    atomic_write(EXPERIMENT / "TRANSCRIPT_INDEX.json", canonical_json_bytes(index))


if __name__ == "__main__":
    main()
