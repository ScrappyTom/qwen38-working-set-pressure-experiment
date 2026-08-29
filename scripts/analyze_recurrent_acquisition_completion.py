from __future__ import annotations

from pathlib import Path
from typing import Any

from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.recurrent_pressure import hidden_grade, load_recurrent_fixture
from working_set_exp.runner import verify_run


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "011_recurrent_acquisition_granularity"
RUN = EXPERIMENT / "completion_supplement_run"
BANK = EXPERIMENT / "fresh_bank"


def verify_launcher_custody() -> dict[str, Any]:
    custody = load_json_strict((EXPERIMENT / "COMPLETION_LAUNCHER_CUSTODY.json").read_bytes())
    for row in custody["artifacts"]:
        path = EXPERIMENT / Path(*row["path"].split("/"))
        if not path.is_file() or path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise RuntimeError(f"launcher custody differs: {row['path']}")
    return {"verified": True, "artifact_count": len(custody["artifacts"])}


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
    accounting_deltas: list[int] = []
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
                    "paging_mode": result.get("paging_mode", "actor_selected_line_count"),
                    "returned_start_line": result["returned_start_line"],
                    "returned_end_line": result["returned_end_line"],
                    "complete": result["complete"],
                }
            )
    for line in (run / "records.jsonl").read_bytes().splitlines():
        record = load_json_strict(line)
        if record["record_type"] == "action_result":
            elapsed_ms += int(record["payload"]["elapsed_ms"])
            accounting_deltas.append(int(record["payload"]["accounting_delta"]))
    return {
        "calls": len(actions),
        "actions": actions,
        "read_pages": read_pages,
        "prompt_tokens_sum": prompt_tokens,
        "completion_tokens_sum": completion_tokens,
        "reasoning_bytes": reasoning_bytes,
        "endpoint_elapsed_ms_sum": elapsed_ms,
        "runtime_accounting_deltas": accounting_deltas,
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
        rows.append(
            {
                "call": action_path.relative_to(RUN).as_posix().removesuffix("-assistant-content.json"),
                "response_id": endpoint["id"],
                "action": action["action"],
                "accepted": result.get("accepted"),
                "artifact_sha256": {name: sha256_file(path) for name, path in companions.items()},
                "direct_review_status": "reviewed_condition_aware_by_primary_agent_2026-08-29",
            }
        )
    if len(rows) != receipt["http_completion_calls"]:
        raise RuntimeError(f"transcript index coverage differs: {len(rows)}")
    return rows


def branch_total(stages: list[dict[str, Any]], condition: str) -> dict[str, Any]:
    selected = [row for row in stages if f"/{condition}/" in f"/{row['path']}/"]
    final = next(row for row in selected if row["path"].endswith("/phase-c"))
    return {
        "ordinal": 4,
        "condition": condition,
        "calls": sum(row["calls"] for row in selected),
        "read_calls": sum(len(row["read_pages"]) for row in selected),
        "prompt_tokens": sum(row["prompt_tokens_sum"] for row in selected),
        "completion_tokens": sum(row["completion_tokens_sum"] for row in selected),
        "elapsed_ms": sum(row["endpoint_elapsed_ms_sum"] for row in selected),
        "stage_dispositions": [{"path": row["path"], "disposition": row["disposition"]} for row in selected],
        "reached_second_boundary": True,
        "submitted": final["submitted"] is True,
        "hidden_passed": final["hidden_grade"]["passed"] is True,
    }


def main() -> None:
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    if receipt["status"] != "completed_and_response_sealed":
        raise RuntimeError("completion supplement is not complete and sealed")
    if receipt["classification"] != "post_interruption_completion_supplement_not_rewrite_of_primary_attempt":
        raise RuntimeError("completion classification differs")
    seal = verify_seal()
    launcher = verify_launcher_custody()
    fixture_id = receipt["cell"]["fixture_id"]
    stages = [stage_row(path, fixture_id) for path in sorted(RUN.glob("cell-*/**/SUMMARY.json"))]
    calls = transcript_index(receipt)
    phase_c = [row for row in stages if row["path"].endswith("/phase-c")]
    l0 = branch_total(stages, "T25-L0")
    l1 = branch_total(stages, "T25-L1")
    pair = {
        "ordinal": 4,
        "fixture_id": fixture_id,
        "seed": receipt["cell"]["seed"],
        "l0": l0,
        "l1": l1,
        "l1_minus_l0_calls": l1["calls"] - l0["calls"],
        "l1_minus_l0_read_calls": l1["read_calls"] - l0["read_calls"],
        "l1_minus_l0_prompt_tokens": l1["prompt_tokens"] - l0["prompt_tokens"],
        "l1_minus_l0_completion_tokens": l1["completion_tokens"] - l0["completion_tokens"],
        "l1_minus_l0_elapsed_ms": l1["elapsed_ms"] - l0["elapsed_ms"],
    }
    results = {
        "schema_version": "experiment-011-completion-mechanical-results-v1",
        "classification": receipt["classification"],
        "formal_primary_comparison_scorable": False,
        "reason_not_primary": "the original exact run remains interrupted; this separately authorized fresh-prefix run supplies only the missing descriptive pair",
        "prior_partial_response_seal_sha256": receipt["prior_partial"]["seal_sha256"],
        "response_seal": seal,
        "prepared_invocations": receipt["prepared_invocations"],
        "http_completion_calls": receipt["http_completion_calls"],
        "verified_stage_runs": len(stages),
        "directly_reviewed_completion_calls": len(calls),
        "phase_c_trajectories": len(phase_c),
        "phase_c_hidden_passes": sum(row["hidden_grade"]["passed"] for row in phase_c),
        "phase_c_submissions": sum(row["submitted"] is True for row in phase_c),
        "stages": stages,
        "pair": pair,
        "apparatus": {
            "all_completed_actions_accepted": all(row["accepted"] is True for row in calls),
            "all_complete_stage_runs_replayed": all(row["replay_verified"] for row in stages),
            "runtime_accounting_deltas": sorted(
                {delta for row in stages for delta in row["runtime_accounting_deltas"]}
            ),
            "server_shutdown_verified": receipt["server_shutdown_verified"],
            "launcher_custody": launcher,
            "retries": receipt["retries"],
            "repairs": receipt["repairs"],
            "rescues": receipt["rescues"],
        },
    }
    grading = {
        "schema_version": "experiment-011-completion-postseal-hidden-grading-v1",
        "classification": receipt["classification"],
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
        "schema_version": "experiment-011-completion-transcript-index-v1",
        "reviewer": "Codex primary project agent",
        "review_mode": "condition-aware post-seal direct prompt/reasoning/action/result audit",
        "actor": "Qwen3.8-27B-AD-IQ2_S",
        "coverage": "all 35 completed calls in the sealed completion supplement",
        "completed_call_count": len(calls),
        "calls": calls,
    }
    prior = load_json_strict((EXPERIMENT / "MECHANICAL_RESULTS.json").read_bytes())
    combined_pairs = list(prior["complete_observed_pairs"]) + [pair]
    combined = {
        "schema_version": "experiment-011-combined-descriptive-synthesis-v1",
        "classification": "mixed_source_descriptive_synthesis_not_original_primary_completion",
        "formal_primary_comparison_scorable": False,
        "sources": {
            "original_partial_seal_sha256": prior["response_seal"]["seal_sha256"],
            "completion_supplement_seal_sha256": seal["seal_sha256"],
        },
        "pairs": combined_pairs,
        "descriptive_totals": {
            "pairs": len(combined_pairs),
            "l0_hidden_passes": sum(row["l0"]["hidden_passed"] for row in combined_pairs),
            "l1_hidden_passes": sum(row["l1"]["hidden_passed"] for row in combined_pairs),
            "l0_submissions": sum(row["l0"]["submitted"] for row in combined_pairs),
            "l1_submissions": sum(row["l1"]["submitted"] for row in combined_pairs),
            "l0_calls": sum(row["l0"]["calls"] for row in combined_pairs),
            "l1_calls": sum(row["l1"]["calls"] for row in combined_pairs),
            "l0_read_calls": sum(row["l0"]["read_calls"] for row in combined_pairs),
            "l1_read_calls": sum(row["l1"]["read_calls"] for row in combined_pairs),
            "l0_prompt_tokens": sum(row["l0"]["prompt_tokens"] for row in combined_pairs),
            "l1_prompt_tokens": sum(row["l1"]["prompt_tokens"] for row in combined_pairs),
        },
    }
    atomic_write(EXPERIMENT / "COMPLETION_MECHANICAL_RESULTS.json", canonical_json_bytes(results))
    atomic_write(EXPERIMENT / "COMPLETION_POSTSEAL_HIDDEN_GRADING.json", canonical_json_bytes(grading))
    atomic_write(EXPERIMENT / "COMPLETION_TRANSCRIPT_INDEX.json", canonical_json_bytes(index))
    atomic_write(EXPERIMENT / "COMBINED_DESCRIPTIVE_SYNTHESIS.json", canonical_json_bytes(combined))


if __name__ == "__main__":
    main()
