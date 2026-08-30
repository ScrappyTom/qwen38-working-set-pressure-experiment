from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import analyze_phase_receipts as shared

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict
from working_set_exp.phase_receipts import hidden_grade, load_fixture
from working_set_exp.runner import verify_run
from working_set_exp.tools import run_checker


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "014_unified_active_phase_receipts"
RUN = EXPERIMENT / "measured_run"
BANK = EXPERIMENT / "fresh_bank"
CONDITIONS = ("T25-SPLIT", "T25-UNIFIED")


def _ledger_details(call: dict[str, Any]) -> None:
    request_path = RUN / f"{call['call']}-coding-request.json"
    request = load_json_strict(request_path.read_bytes())
    ledger = request.get("active_phase_receipt_ledger") or {}
    call["receipt_externalized_body_through_sequence"] = ledger.get(
        "externalized_body_through_sequence", 0
    )
    call["receipt_recent_history_receipts_included"] = ledger.get(
        "recent_history_receipts_included", False
    )
    call["receipt_entries"] = ledger.get("entries", [])
    call["direct_review_status"] = "reviewed_condition_aware_by_primary_agent_2026-08-29"


def _branch_calls(calls: list[dict[str, Any]], ordinal: int, condition: str) -> list[dict[str, Any]]:
    prefix = f"cell-{ordinal:02d}/{condition}/"
    return [row for row in calls if row["call"].startswith(prefix)]


def _check_binding_rows(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, call in enumerate(calls):
        if call["action"]["action"] != "check":
            continue
        rows.append(
            {
                "call_index": index + 1,
                "candidate_id_before": call["candidate_id_before"],
                "checked_candidate_id": call["result"].get("candidate_id"),
                "passed": call["result"].get("passed"),
            }
        )
    return rows


def main() -> None:
    shared.RUN = RUN
    shared.BANK = BANK
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    if receipt["status"] != "completed_and_response_sealed":
        raise RuntimeError("unexpected Experiment 014 run status")
    seal = shared.verify_seal()
    calls, denied = shared.transcript_index(receipt)
    for call in calls:
        _ledger_details(call)

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
    grade_rows = {(row["ordinal"], row["condition"]): row for row in grades["rows"]}
    branches: list[dict[str, Any]] = []
    totals: dict[str, Counter[str]] = defaultdict(Counter)
    for cell in receipt["cells"]:
        fixture = load_fixture(BANK, cell["fixture_id"])
        for condition in CONDITIONS:
            summary = cell["branches"][condition]
            branch = RUN / f"cell-{cell['ordinal']:02d}" / condition
            candidate = shared.candidate_from_branch(branch, summary["candidate_id"])
            grade = hidden_grade(fixture, candidate)
            saved_grade = grade_rows[(cell["ordinal"], condition)]["hidden"]
            if saved_grade["passed"] != grade["passed"]:
                raise RuntimeError("post-seal hidden grade differs")
            branch_calls = _branch_calls(calls, cell["ordinal"], condition)
            counts = Counter(row["action"]["action"] for row in branch_calls)
            action_labels = [row["action_label"] for row in branch_calls]
            duplicate_actions = sum(count - 1 for count in Counter(action_labels).values())
            check_bindings = _check_binding_rows(branch_calls)
            current_check_before_submit = False
            submit_index = next(
                (i for i, row in enumerate(branch_calls) if row["action"]["action"] == "submit"), None
            )
            if submit_index is not None:
                submit_candidate = branch_calls[submit_index]["candidate_id_before"]
                current_check_before_submit = any(
                    row["checked_candidate_id"] == submit_candidate and row["passed"] is True
                    for row in check_bindings
                    if row["call_index"] <= submit_index
                )
            row = {
                "ordinal": cell["ordinal"],
                "fixture_id": cell["fixture_id"],
                "seed": cell["seed"],
                "condition": condition,
                "disposition": summary["phase"]["disposition"],
                "submitted": summary["submitted"],
                "public_check_passed": summary["phase"]["public_check_passed"],
                "candidate_id": candidate.candidate_id,
                "hidden_grade": grade,
                "phase_b_checker_postseal": run_checker(candidate, fixture.phases["B"].checker),
                "prepared_invocations": summary["prepared_invocations"],
                "http_completion_calls": summary["http_completion_calls"],
                "runtime_resets": summary["phase"]["runtime_resets"],
                "externalized_receipt_count": summary["phase"]["externalized_receipt_count"],
                "receipt_count": summary["phase"]["receipt_count"],
                "action_counts": dict(sorted(counts.items())),
                "action_sequence": action_labels,
                "duplicate_action_label_count": duplicate_actions,
                "repeated_check_count_after_first": max(0, counts["check"] - 1),
                "check_bindings": check_bindings,
                "current_candidate_checked_before_submit": current_check_before_submit,
                "prompt_tokens_sum": sum(item["usage"]["server_reported_prompt_tokens"] for item in branch_calls),
                "completion_tokens_sum": sum(item["usage"]["completion_tokens"] for item in branch_calls),
                "reasoning_content_bytes_sum": sum(
                    item["usage"].get("reasoning_content_bytes", 0) for item in branch_calls
                ),
                "elapsed_ms_sum": sum(item["usage"]["elapsed_ms"] for item in branch_calls),
                "maximum_server_prompt_tokens": max(
                    (item["usage"]["server_reported_prompt_tokens"] for item in branch_calls), default=0
                ),
            }
            branches.append(row)
            for key in (
                "prepared_invocations", "http_completion_calls", "runtime_resets",
                "externalized_receipt_count", "receipt_count", "duplicate_action_label_count",
                "repeated_check_count_after_first", "prompt_tokens_sum", "completion_tokens_sum",
                "elapsed_ms_sum",
            ):
                totals[condition][key] += row[key]
            totals[condition]["hidden_passes"] += int(grade["passed"])
            totals[condition]["public_check_passes"] += int(row["public_check_passed"])
            totals[condition]["submissions"] += int(row["submitted"])
            totals[condition]["current_candidate_checked_before_submit"] += int(current_check_before_submit)

    by_key = {(row["fixture_id"], row["seed"], row["condition"]): row for row in branches}
    pairs = []
    for cell in receipt["cells"]:
        split = by_key[(cell["fixture_id"], cell["seed"], "T25-SPLIT")]
        unified = by_key[(cell["fixture_id"], cell["seed"], "T25-UNIFIED")]
        pairs.append(
            {
                "ordinal": cell["ordinal"],
                "fixture_id": cell["fixture_id"],
                "seed": cell["seed"],
                "unified_minus_split_http_calls": unified["http_completion_calls"] - split["http_completion_calls"],
                "unified_minus_split_prompt_tokens": unified["prompt_tokens_sum"] - split["prompt_tokens_sum"],
                "split_hidden_passed": split["hidden_grade"]["passed"],
                "unified_hidden_passed": unified["hidden_grade"]["passed"],
                "split_submitted": split["submitted"],
                "unified_submitted": unified["submitted"],
                "split_current_candidate_checked_before_submit": split["current_candidate_checked_before_submit"],
                "unified_current_candidate_checked_before_submit": unified["current_candidate_checked_before_submit"],
            }
        )

    results = {
        "schema_version": "experiment-014-mechanical-results-v1",
        "run_status": receipt["status"],
        "formal_primary_comparison_scorable": True,
        "response_seal": seal,
        "prepared_invocations": receipt["prepared_invocations"],
        "http_completion_calls": receipt["http_completion_calls"],
        "capacity_denied_prepared_invocations": len(denied),
        "directly_reviewed_completion_calls": len(calls),
        "verified_stage_runs": len(verified_runs),
        "all_completed_actions_accepted": all(row["result"]["accepted"] is True for row in calls),
        "accepted_completed_actions": sum(row["result"]["accepted"] is True for row in calls),
        "rejected_completed_actions": sum(row["result"]["accepted"] is not True for row in calls),
        "all_runtime_accounting_deltas_zero": all(row["usage"]["accounting_delta"] == 0 for row in calls),
        "all_response_ids_unique": len({row["response_id"] for row in calls}) == len(calls),
        "server_shutdown_verified": receipt["server_shutdown_verified"],
        "evaluator_reads_before_seal": receipt["evaluator_reads_before_seal"],
        "retries": receipt["retries"],
        "repairs": receipt["repairs"],
        "rescues": receipt["rescues"],
        "branches": branches,
        "condition_totals": {condition: dict(values) for condition, values in totals.items()},
        "paired_differences": pairs,
        "verified_runs": verified_runs,
    }
    index = {
        "schema_version": "experiment-014-transcript-index-v1",
        "reviewer": "Codex primary project agent",
        "review_mode": "condition-aware post-seal direct coding-request/rendered-prompt/reasoning/action/result/host-path audit",
        "actor": "Qwen3.8-27B-AD-IQ2_S",
        "coverage": "all completed calls and all pre-HTTP capacity denials in the sealed Experiment 014 run",
        "completed_call_count": len(calls),
        "capacity_denied_prepared_call_count": len(denied),
        "calls": calls,
        "capacity_denied_prepared_calls": denied,
    }
    atomic_write(EXPERIMENT / "MECHANICAL_RESULTS.json", canonical_json_bytes(results))
    atomic_write(EXPERIMENT / "TRANSCRIPT_INDEX.json", canonical_json_bytes(index))


if __name__ == "__main__":
    main()
