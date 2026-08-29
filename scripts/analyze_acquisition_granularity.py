from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from working_set_exp.fixture import load_fixture
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file
from working_set_exp.runner import replay_prefix, verify_run


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "010_acquisition_granularity"
RUN = EXPERIMENT / "measured_run"


def main() -> None:
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    grades = {
        row["ordinal"]: row
        for row in load_json_strict((RUN / "POSTSEAL_HIDDEN_GRADING.json").read_bytes())["cells"]
    }
    cells: list[dict[str, Any]] = []
    index: list[dict[str, Any]] = []
    totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for cell in receipt["cells"]:
        ordinal = cell["ordinal"]
        condition = cell["condition"]
        fixture = load_fixture(EXPERIMENT / "fresh_bank", cell["fixture_id"])
        run_root = RUN / f"cell-{ordinal:02d}"
        replay = replay_prefix(
            fixture,
            run_root,
            read_mode=cell["read_mode"],
            require_pressure_eligible=False,
        )
        verification = verify_run(run_root)
        transcript = run_root / "transcript"
        prompt_tokens = completion_tokens = reasoning_bytes = elapsed_ms = 0
        read_actions = []
        duplicate_exact_reads = 0
        seen_reads: set[tuple[str, int, str]] = set()
        action_count = accepted_count = accounting_max = 0
        for content_path in sorted(transcript.glob("*-assistant-content.json")):
            call = content_path.name[:3]
            action = load_json_strict(content_path.read_bytes())
            request_path = transcript / f"{call}-coding-request.json"
            response_path = transcript / f"{call}-endpoint-response.json"
            reasoning_path = transcript / f"{call}-assistant-reasoning.txt"
            result_path = transcript / f"{call}-result.json"
            request = load_json_strict(request_path.read_bytes())
            response = load_json_strict(response_path.read_bytes())
            result = load_json_strict(result_path.read_bytes())
            usage = response["usage"]
            prompt_tokens += usage["prompt_tokens"]
            completion_tokens += usage["completion_tokens"]
            reasoning_bytes += reasoning_path.stat().st_size
            action_count += 1
            accepted_count += int(result.get("accepted") is True)
            if action["action"] == "read":
                key = (action["path"], action["start_line"], request["candidate_id"])
                if key in seen_reads:
                    duplicate_exact_reads += 1
                seen_reads.add(key)
                read_actions.append(
                    {
                        "call": int(call),
                        "path": action["path"],
                        "start_line": action["start_line"],
                        "requested_line_count": action.get("line_count"),
                        "returned_start_line": result["returned_start_line"],
                        "returned_end_line": result["returned_end_line"],
                        "next_start_line": result["next_start_line"],
                        "complete": result["complete"],
                    }
                )
            index.append(
                {
                    "ordinal": ordinal,
                    "condition": condition,
                    "fixture_id": cell["fixture_id"],
                    "seed": cell["seed"],
                    "call": int(call),
                    "action": action["action"],
                    "request_sha256": sha256_file(request_path),
                    "assistant_content_sha256": sha256_file(content_path),
                    "assistant_reasoning_sha256": sha256_file(reasoning_path),
                    "result_sha256": sha256_file(result_path),
                }
            )
        records = [load_json_strict(line) for line in (run_root / "records.jsonl").read_bytes().splitlines()]
        for record in records:
            if record["record_type"] == "action_result":
                elapsed_ms += record["payload"]["elapsed_ms"]
                accounting_max = max(accounting_max, abs(record["payload"]["accounting_delta"]))
        ledger_reads = sum(row["path"].startswith("ledger/") for row in read_actions)
        row = {
            "ordinal": ordinal,
            "fixture_id": cell["fixture_id"],
            "condition": condition,
            "seed": cell["seed"],
            "read_mode": cell["read_mode"],
            "calls": action_count,
            "accepted_actions": accepted_count,
            "read_actions": read_actions,
            "read_action_count": len(read_actions),
            "ledger_read_action_count": ledger_reads,
            "duplicate_exact_read_count": duplicate_exact_reads,
            "complete_required_reads": sorted(replay.state.complete_reads & set(fixture.required_full_reads)),
            "required_reads_complete": set(fixture.required_full_reads).issubset(replay.state.complete_reads),
            "prefork_check_passed": replay.state.prefork_check_passed,
            "fork_ready": replay.state.fork_ready,
            "candidate_id": replay.state.candidate.candidate_id,
            "hidden_passed": grades[ordinal]["hidden_passed"],
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "reasoning_bytes": reasoning_bytes,
            "elapsed_ms": elapsed_ms,
            "maximum_absolute_runtime_accounting_delta": accounting_max,
            "record_replay": verification,
        }
        cells.append(row)
        for key in (
            "calls",
            "read_action_count",
            "ledger_read_action_count",
            "duplicate_exact_read_count",
            "prompt_tokens",
            "completion_tokens",
            "reasoning_bytes",
            "elapsed_ms",
        ):
            totals[condition][key] += row[key]
        totals[condition]["hidden_passes"] += int(row["hidden_passed"])
        totals[condition]["closures"] += int(row["fork_ready"])
    pairs = []
    by_key = {(row["fixture_id"], row["seed"], row["condition"]): row for row in cells}
    for fixture_id in sorted({row["fixture_id"] for row in cells}):
        for seed in sorted({row["seed"] for row in cells if row["fixture_id"] == fixture_id}):
            l0 = by_key[(fixture_id, seed, "L0")]
            l1 = by_key[(fixture_id, seed, "L1")]
            pairs.append(
                {
                    "fixture_id": fixture_id,
                    "seed": seed,
                    "l1_minus_l0_calls": l1["calls"] - l0["calls"],
                    "l1_minus_l0_read_actions": l1["read_action_count"] - l0["read_action_count"],
                    "l1_minus_l0_ledger_read_actions": l1["ledger_read_action_count"] - l0["ledger_read_action_count"],
                    "l1_minus_l0_prompt_tokens": l1["prompt_tokens"] - l0["prompt_tokens"],
                    "l1_minus_l0_elapsed_ms": l1["elapsed_ms"] - l0["elapsed_ms"],
                    "l0_hidden_passed": l0["hidden_passed"],
                    "l1_hidden_passed": l1["hidden_passed"],
                }
            )
    mechanical = {
        "schema_version": "experiment-010-mechanical-results-v1",
        "run_receipt_sha256": sha256_file(RUN / "RECEIPT.json"),
        "response_seal_sha256": sha256_file(RUN / "RESPONSE_SEAL.json"),
        "cells": cells,
        "condition_totals": {condition: dict(values) for condition, values in totals.items()},
        "paired_differences": pairs,
        "apparatus": {
            "prepared_invocations": receipt["prepared_invocations"],
            "http_completion_calls": receipt["http_completion_calls"],
            "all_actions_accepted": all(row["accepted_actions"] == row["calls"] for row in cells),
            "all_paths_replayed": all(row["record_replay"]["verified"] for row in cells),
            "all_runtime_accounting_deltas_zero": all(row["maximum_absolute_runtime_accounting_delta"] == 0 for row in cells),
            "server_shutdown_verified": receipt["server_shutdown_verified"],
            "evaluator_reads_before_seal": receipt["evaluator_reads_before_seal"],
            "retries": receipt["retries"],
            "repairs": receipt["repairs"],
            "rescues": receipt["rescues"],
        },
    }
    atomic_write(EXPERIMENT / "MECHANICAL_RESULTS.json", canonical_json_bytes(mechanical))
    atomic_write(
        EXPERIMENT / "TRANSCRIPT_INDEX.json",
        canonical_json_bytes(
            {
                "schema_version": "experiment-010-transcript-index-v1",
                "calls": index,
                "call_count": len(index),
            }
        ),
    )


if __name__ == "__main__":
    main()
