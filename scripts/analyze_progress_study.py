from __future__ import annotations

from pathlib import Path
from typing import Any

from working_set_exp.fixture import load_fixture
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.progress import progress_pointer
from working_set_exp.progress_measured import _inventory
from working_set_exp.runner import replay_prefix, verify_run
from working_set_exp.tools import ToolExecutor


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "003_progress_pointer_diagnostic"
RUN = EXPERIMENT / "mrun"


def _verify_seal() -> dict[str, Any]:
    seal = load_json_strict((RUN / "RESPONSE_SEAL.json").read_bytes())
    files = _inventory(RUN, excluded={"RECEIPT.json", "RESPONSE_SEAL.json"})
    if files != seal["files"] or sha256_bytes(canonical_json_bytes(files)) != seal["aggregate_sha256"]:
        raise ValueError("copied response tree differs from pre-evaluator seal")
    if seal["evaluator_truth_opened"] is not False:
        raise ValueError("response seal evaluator state differs")
    return {"verified": True, "aggregate_sha256": seal["aggregate_sha256"], "file_count": len(files)}


def _branch_replay(fixture, prefix, run_dir: Path):
    verify_run(run_dir)
    state = prefix.state.clone_for_branch()
    executor = ToolExecutor(
        state, required_full_reads=fixture.required_full_reads, prefork_checker=fixture.prefork_checker,
        public_checker=fixture.public_checker, final_target=fixture.final_target,
        probe_id=fixture.probe_id, probe_body=fixture.probe_body, reopenable=prefix.reopenable,
    )
    actions = []
    for raw in (run_dir / "records.jsonl").read_text(encoding="utf-8").splitlines():
        record = load_json_strict(raw.encode("utf-8"))
        if record["record_type"] != "action_result":
            continue
        action = record["payload"]["action"]
        expected = record["payload"]["result"]
        observed = executor.execute(action)
        if canonical_json_bytes(observed) != canonical_json_bytes(expected):
            raise ValueError("branch replay result differs")
        actions.append(
            {
                "action": action, "accepted": expected.get("accepted"),
                "offline_prompt_tokens": record["payload"]["offline_prompt_tokens"],
                "completion_tokens": record["payload"]["completion_tokens"],
            }
        )
    return state, actions


def _transcript_index() -> list[dict[str, Any]]:
    rows = []
    for request_path in sorted(RUN.rglob("*-coding-request.json")):
        stem = request_path.name.removesuffix("-coding-request.json")
        transcript = request_path.parent
        assistant_path = transcript / f"{stem}-assistant-content.json"
        result_path = transcript / f"{stem}-result.json"
        request_bytes = request_path.read_bytes()
        request = load_json_strict(request_bytes)
        assistant = load_json_strict(assistant_path.read_bytes()) if assistant_path.is_file() else None
        result = load_json_strict(result_path.read_bytes()) if result_path.is_file() else None
        relative = request_path.relative_to(RUN).as_posix()
        rows.append(
            {
                "request_path": relative,
                "request_sha256": sha256_bytes(request_bytes),
                "stage": request["stage"],
                "fixture_id": request["fixture_id"],
                "progress_pointer_present": "progress_pointer" in request,
                "pointer_exact": (
                    request.get("progress_pointer") == progress_pointer(EXPERIMENT / "fresh_bank", request["fixture_id"])
                    if "progress_pointer" in request else None
                ),
                "older_chronology_present": request["older_chronology_present"],
                "history_entries": len(request["history"]),
                "assistant": assistant,
                "assistant_sha256": sha256_file(assistant_path) if assistant_path.is_file() else None,
                "result": result,
                "result_sha256": sha256_file(result_path) if result_path.is_file() else None,
                "http_call_occurred": assistant_path.is_file(),
            }
        )
    return rows


def main() -> None:
    seal = _verify_seal()
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    if receipt["status"] != "completed_and_response_sealed" or receipt["evaluator_reads_before_seal"] is not False:
        raise ValueError("measured receipt state differs")
    results = []
    for ordinal, fixture_id in ((1, "E3-SOURCE"), (2, "E3-OBSERVATION")):
        fixture = load_fixture(EXPERIMENT / "fresh_bank", fixture_id)
        prefix_dir = RUN / f"prefix-{ordinal:02d}" / "shared_prefix"
        prefix = replay_prefix(fixture, prefix_dir)
        verify_run(prefix_dir)
        for condition in ("T25-M", "T25-P"):
            branch_dir = RUN / f"prefix-{ordinal:02d}" / condition
            state, actions = _branch_replay(fixture, prefix, branch_dir)
            hidden = (EXPERIMENT / "fresh_bank" / "evaluator_only" / fixture_id / "hidden.py").read_bytes()
            grade = run_checker(state.candidate, hidden)
            summary = load_json_strict((branch_dir / "SUMMARY.json").read_bytes())
            action_names = [row["action"]["action"] for row in actions]
            paths = [row["action"].get("path") for row in actions if row["action"].get("path")]
            results.append(
                {
                    "fixture_id": fixture_id, "condition": condition, "disposition": summary["disposition"],
                    "candidate_id": state.candidate.candidate_id, "submitted": state.submitted,
                    "public_check_passed": state.public_check_passed, "hidden_passed": grade["passed"],
                    "actions": actions, "action_names": action_names, "paths": paths,
                    "reopened_observation": "reopen_observation" in action_names,
                    "mutated": "patch" in action_names, "calls_attempted": summary["calls"],
                    "http_calls": len(actions), "maximum_offline_prompt_tokens": summary["maximum_offline_prompt_tokens"],
                    "prompt_tokens_sum": sum(row["offline_prompt_tokens"] for row in actions),
                    "completion_tokens_sum": sum(row["completion_tokens"] for row in actions),
                }
            )
    index = _transcript_index()
    if any(row["progress_pointer_present"] and row["pointer_exact"] is not True for row in index):
        raise ValueError("progress pointer bytes differ in transcript")
    mechanical = {
        "schema_version": "experiment-003-progress-mechanical-results-v1",
        "response_seal": seal,
        "actor_sha256": receipt["actor_sha256"],
        "infrastructure_failures": 0,
        "completion_calls": sum(1 for row in index if row["http_call_occurred"]),
        "prospective_requests": len(index),
        "results": results,
    }
    atomic_write(EXPERIMENT / "TRANSCRIPT_INDEX.json", canonical_json_bytes(index))
    atomic_write(EXPERIMENT / "MECHANICAL_RESULTS.json", canonical_json_bytes(mechanical))
    print(canonical_json_bytes(mechanical).decode("utf-8"))


if __name__ == "__main__":
    main()
