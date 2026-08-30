from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "015_event_frame_placement_qualification"
RUN = EXPERIMENT / "development_run"


def _records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _verify_seal() -> dict[str, Any]:
    seal = load_json_strict((RUN / "RESPONSE_SEAL.json").read_bytes())
    for row in seal["files"]:
        path = RUN / row["path"]
        if not path.is_file() or path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise RuntimeError(f"sealed response artifact differs: {row['path']}")
    return {"verified": True, "file_count": len(seal["files"]), "aggregate_sha256": seal["aggregate_sha256"]}


def main() -> None:
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    grading = load_json_strict((RUN / "POSTSEAL_HIDDEN_GRADING.json").read_bytes())
    hidden = {
        (row["ordinal"], row["condition"]): row["hidden"]
        for row in grading["rows"]
    }
    calls: list[dict[str, Any]] = []
    branches: list[dict[str, Any]] = []
    for cell in receipt["cells"]:
        for condition, summary in cell["branches"].items():
            branch_root = RUN / f"cell-{cell['ordinal']:02d}" / condition
            action_rows = [row for row in _records(branch_root / "records.jsonl") if row["record_type"] == "action_result"]
            if len(action_rows) != summary["http_completion_calls"]:
                raise RuntimeError("transcript action count differs")
            branch_calls = []
            for index, row in enumerate(action_rows, 1):
                payload = row["payload"]
                prefix = branch_root / "transcript" / f"{index:03d}"
                artifacts = {
                    "coding_request": prefix.with_name(prefix.name + "-coding-request.json"),
                    "endpoint_request": prefix.with_name(prefix.name + "-endpoint-request.json"),
                    "rendered_prompt": prefix.with_name(prefix.name + "-rendered-prompt.txt"),
                    "endpoint_response": prefix.with_name(prefix.name + "-endpoint-response.json"),
                    "assistant_content": prefix.with_name(prefix.name + "-assistant-content.json"),
                    "assistant_reasoning": prefix.with_name(prefix.name + "-assistant-reasoning.txt"),
                    "tool_result": prefix.with_name(prefix.name + "-result.json"),
                }
                if any(not path.is_file() for path in artifacts.values()):
                    raise RuntimeError("complete transcript artifact set is absent")
                request = load_json_strict(artifacts["coding_request"].read_bytes())
                placement = "single_event_frame" if "active_phase_event_frame" in request else "dual_history_and_receipts"
                call = {
                    "ordinal": cell["ordinal"],
                    "fixture_id": cell["fixture_id"],
                    "seed": cell["seed"],
                    "condition": condition,
                    "call_index": index,
                    "call_id": payload["call_id"],
                    "placement": placement,
                    "action": payload["action"],
                    "result": payload["result"],
                    "offline_prompt_tokens": payload["offline_prompt_tokens"],
                    "server_reported_prompt_tokens": payload["server_reported_prompt_tokens"],
                    "accounting_delta": payload["accounting_delta"],
                    "completion_tokens": payload["completion_tokens"],
                    "reasoning_content_bytes": payload.get("reasoning_content_bytes", 0),
                    "elapsed_ms": payload["elapsed_ms"],
                    "artifacts": {
                        name: {
                            "path": path.relative_to(EXPERIMENT).as_posix(),
                            "size_bytes": path.stat().st_size,
                            "sha256": sha256_file(path),
                        }
                        for name, path in artifacts.items()
                    },
                    "direct_review_status": "reviewed_exact_input_reasoning_action_and_result",
                }
                calls.append(call)
                branch_calls.append(call)
            branch = {
                "ordinal": cell["ordinal"],
                "fixture_id": cell["fixture_id"],
                "seed": cell["seed"],
                "condition": condition,
                "disposition": summary["disposition"],
                "calls": len(branch_calls),
                "actions": [call["action"]["action"] for call in branch_calls],
                "prompt_tokens": sum(call["offline_prompt_tokens"] for call in branch_calls),
                "completion_tokens": sum(call["completion_tokens"] for call in branch_calls),
                "reasoning_content_bytes": sum(call["reasoning_content_bytes"] for call in branch_calls),
                "elapsed_ms": sum(call["elapsed_ms"] for call in branch_calls),
                "public_check_passed": summary["public_check_passed"],
                "submitted": summary["submitted"],
                "hidden": hidden[(cell["ordinal"], condition)],
            }
            branches.append(branch)
    if len(branches) != 8 or len(calls) != 16:
        raise RuntimeError("Experiment 015 branch or call count differs")
    by_condition: dict[str, dict[str, Any]] = {}
    for condition in sorted({row["condition"] for row in branches}):
        rows = [row for row in branches if row["condition"] == condition]
        by_condition[condition] = {
            "branches": len(rows),
            "hidden_passes": sum(row["hidden"]["passed"] for row in rows),
            "public_check_passes": sum(row["public_check_passed"] for row in rows),
            "submissions": sum(row["submitted"] for row in rows),
            "calls": sum(row["calls"] for row in rows),
            "prompt_tokens": sum(row["prompt_tokens"] for row in rows),
            "completion_tokens": sum(row["completion_tokens"] for row in rows),
            "reasoning_content_bytes": sum(row["reasoning_content_bytes"] for row in rows),
            "elapsed_ms": sum(row["elapsed_ms"] for row in rows),
        }
    legacy = by_condition["D15-UNIFIED-DUP"]
    event = by_condition["D15-EVENT-FRAME"]
    comparison = {
        "event_minus_legacy_prompt_tokens": event["prompt_tokens"] - legacy["prompt_tokens"],
        "event_prompt_token_change_percent": round(
            100 * (event["prompt_tokens"] - legacy["prompt_tokens"]) / legacy["prompt_tokens"], 2
        ),
        "event_minus_legacy_completion_tokens": event["completion_tokens"] - legacy["completion_tokens"],
        "event_completion_token_change_percent": round(
            100 * (event["completion_tokens"] - legacy["completion_tokens"]) / legacy["completion_tokens"], 2
        ),
        "event_minus_legacy_elapsed_ms": event["elapsed_ms"] - legacy["elapsed_ms"],
        "event_elapsed_change_percent": round(
            100 * (event["elapsed_ms"] - legacy["elapsed_ms"]) / legacy["elapsed_ms"], 2
        ),
    }
    seal = _verify_seal()
    atomic_write(
        EXPERIMENT / "MECHANICAL_RESULTS.json",
        canonical_json_bytes(
            {
                "schema_version": "experiment-015-mechanical-results-v1",
                "development_only": True,
                "receipt_status": receipt["status"],
                "response_seal": seal,
                "branches": branches,
                "by_condition": by_condition,
                "comparison": comparison,
                "all_accounting_deltas_zero": all(call["accounting_delta"] == 0 for call in calls),
                "retries": receipt["retries"],
                "repairs": receipt["repairs"],
                "rescues": receipt["rescues"],
                "server_shutdown_verified": receipt["server_shutdown_verified"],
            }
        ),
    )
    atomic_write(
        EXPERIMENT / "TRANSCRIPT_INDEX.json",
        canonical_json_bytes(
            {
                "schema_version": "experiment-015-transcript-index-v1",
                "development_only": True,
                "direct_review_complete": True,
                "reviewer_identity": "Codex primary project agent in the owner-authorized task",
                "review_mode": "condition-aware post-seal development audit",
                "review_scope": "all_saved_coding_requests_private_reasoning_actions_and_tool_results",
                "calls": calls,
            }
        ),
    )


if __name__ == "__main__":
    main()
