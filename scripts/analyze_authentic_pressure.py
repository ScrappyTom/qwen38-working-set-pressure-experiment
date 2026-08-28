from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from working_set_exp.authentic_pressure import CASE_IDS, verify_bank
from working_set_exp.candidate import Candidate
from working_set_exp.custody import verify_records
from working_set_exp.fixture import load_fixture, load_truth
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.request import fork_binding
from working_set_exp.runner import PrefixOutcome
from working_set_exp.tools import SessionState, ToolExecutor


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "006_authentic_bounded_pressure"
RUN = EXPERIMENT / "measured_run"
BANK = EXPERIMENT / "fresh_bank"
OUTPUT = EXPERIMENT / "MECHANICAL_RESULTS.json"
INDEX = EXPERIMENT / "TRANSCRIPT_INDEX.json"


def verify_seal() -> dict[str, Any]:
    seal = load_json_strict((RUN / "RESPONSE_SEAL.json").read_bytes())
    for row in seal["files"]:
        path = RUN / Path(*row["path"].split("/"))
        if not path.is_file() or path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise ValueError(f"sealed artifact differs: {row['path']}")
    aggregate = sha256_bytes(canonical_json_bytes(seal["files"]))
    if aggregate != seal["aggregate_sha256"]:
        raise ValueError("response seal aggregate differs")
    return {"verified": True, "file_count": len(seal["files"]), "aggregate_sha256": aggregate}


def replay_prefix(fixture, run_dir: Path) -> PrefixOutcome:
    records = verify_records(run_dir / "records.jsonl", run_dir)
    summary = load_json_strict((run_dir / "SUMMARY.json").read_bytes())
    state = SessionState(fixture.initial)
    executor = ToolExecutor(
        state, required_full_reads=fixture.required_full_reads,
        prefork_checker=fixture.prefork_checker, public_checker=fixture.public_checker,
        final_target=fixture.final_target, probe_id=fixture.probe_id, probe_body=fixture.probe_body,
    )
    history: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    reopenable: dict[str, bytes] = {}
    last_action_record = ""
    for record in records:
        if record["record_type"] != "action_result":
            continue
        action = record["payload"]["action"]
        expected = record["payload"]["result"]
        observed = executor.execute(action)
        if canonical_json_bytes(observed) != canonical_json_bytes(expected):
            raise ValueError("prefix action/result replay differs")
        history.append({"response": action, "result": expected})
        if action.get("action") in {"probe", "check", "fork_ready"} and expected.get("accepted"):
            body = canonical_json_bytes(expected)
            handle = f"OBS-{len(observations) + 1:04d}"
            target = action.get("probe_id", action.get("check_id", "continuation_boundary"))
            reopenable[handle] = body
            observations.append({
                "handle": handle, "sequence": len(history), "action": action["action"], "target": target,
                "candidate_id": expected.get("checked_candidate_id", expected.get("candidate_id", state.candidate.candidate_id)),
                "size_bytes": len(body), "sha256": sha256_bytes(body),
            })
        last_action_record = record["record_sha256"]
    binding = fork_binding(
        fixture_id=fixture.fixture_id, seed=summary["seed"], task=fixture.task,
        candidate=state.candidate, prefix_history=history, observations=observations,
        last_record_sha256=last_action_record,
    )
    if canonical_json_bytes(binding) != canonical_json_bytes(summary["fork_binding"]):
        raise ValueError("prefix binding replay differs")
    return PrefixOutcome(state, history, observations, reopenable, binding, summary["calls"], run_dir)


def replay_branch(fixture, prefix: PrefixOutcome, run_dir: Path) -> Candidate:
    records = verify_records(run_dir / "records.jsonl", run_dir)
    summary = load_json_strict((run_dir / "SUMMARY.json").read_bytes())
    state = prefix.state.clone_for_branch()
    executor = ToolExecutor(
        state, required_full_reads=fixture.required_full_reads,
        prefork_checker=fixture.prefork_checker, public_checker=fixture.public_checker,
        final_target=fixture.final_target, probe_id=fixture.probe_id, probe_body=fixture.probe_body,
        reopenable=prefix.reopenable,
    )
    for record in records:
        if record["record_type"] != "action_result":
            continue
        expected = record["payload"]["result"]
        observed = executor.execute(record["payload"]["action"])
        if canonical_json_bytes(observed) != canonical_json_bytes(expected):
            raise ValueError("branch action/result replay differs")
    if state.candidate.candidate_id != summary["candidate_id"]:
        raise ValueError("branch candidate replay differs")
    return state.candidate


def stage_metrics(stage_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records = verify_records(stage_root / "records.jsonl", stage_root)
    rows = [row for row in records if row["record_type"] == "action_result"]
    prepared = [row for row in records if row["record_type"] == "external_call_prepared"]
    actions = []
    read_bytes = 0
    reopened_bytes = 0
    prompt_tokens = completion_tokens = elapsed_ms = reasoning_bytes = 0
    reasoning_artifacts = 0
    max_prompt = 0
    transcript_rows: list[dict[str, Any]] = []
    for index, record in enumerate(rows, start=1):
        payload = record["payload"]
        action = payload["action"]
        result = payload["result"]
        name = action.get("action", "unparsed")
        actions.append(name)
        if name == "read" and result.get("accepted"):
            read_bytes += len(result.get("content", "").encode("utf-8"))
        if name == "reopen_observation" and result.get("accepted"):
            reopened_bytes += len(result.get("exact_result_utf8", "").encode("utf-8"))
        prompt_tokens += payload["offline_prompt_tokens"]
        completion_tokens += payload["completion_tokens"]
        elapsed_ms += payload["elapsed_ms"]
        max_prompt = max(max_prompt, payload["offline_prompt_tokens"])
        reasoning_bytes += payload.get("reasoning_content_bytes", 0)
        reasoning_artifacts += int("reasoning_content_sha256" in payload)
        transcript = stage_root / "transcript"
        response = load_json_strict((transcript / f"{index:03d}-endpoint-response.json").read_bytes())
        usage = response.get("usage", {})
        request = load_json_strict((transcript / f"{index:03d}-coding-request.json").read_bytes())
        assistant = load_json_strict((transcript / f"{index:03d}-assistant-content.json").read_bytes())
        saved_result = load_json_strict((transcript / f"{index:03d}-result.json").read_bytes())
        if canonical_json_bytes(assistant) != canonical_json_bytes(action) or canonical_json_bytes(saved_result) != canonical_json_bytes(result):
            raise ValueError("transcript artifact differs from record")
        transcript_rows.append({
            "stage_root": stage_root.relative_to(RUN).as_posix(), "call_index": index,
            "stage": request["stage"], "older_chronology_present": request["older_chronology_present"],
            "history_entries": len(request["history"]),
            "progress_pointer_present": "progress_pointer" in request,
            "observation_handles": [entry["handle"] for entry in (request.get("observation_directory") or {}).get("entries", [])],
            "candidate_id": request["candidate_id"], "action": action, "result": result,
            "offline_prompt_tokens": payload["offline_prompt_tokens"],
            "completion_tokens": payload["completion_tokens"],
            "reasoning_sha256": payload.get("reasoning_content_sha256"),
        })
    return ({
        "prepared_invocations": len(prepared), "http_completion_calls": len(rows),
        "actions": actions, "read_bytes": read_bytes, "reopened_observation_bytes": reopened_bytes,
        "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
        "completion_tokens_include_private_reasoning": True,
        "reasoning_artifact_count": reasoning_artifacts, "reasoning_bytes": reasoning_bytes,
        "elapsed_ms": elapsed_ms, "maximum_prompt_tokens": max_prompt,
    }, transcript_rows)


def main() -> None:
    if OUTPUT.exists() or INDEX.exists():
        raise FileExistsError("authentic pressure analysis already exists")
    seal = verify_seal()
    bank = verify_bank(BANK)
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    result_rows = []
    transcript_index = []
    for cell in receipt["cases"]:
        fixture = load_fixture(BANK, cell["fixture_id"])
        truth = load_truth(BANK, cell["fixture_id"])
        root = RUN / f"case-{cell['ordinal']:02d}"
        prefix = replay_prefix(fixture, root / "prefix")
        prefix_metrics, prefix_transcripts = stage_metrics(root / "prefix")
        transcript_index.extend(prefix_transcripts)
        for condition in cell["branch_order"]:
            branch_root = root / condition
            candidate = replay_branch(fixture, prefix, branch_root)
            metrics, transcripts = stage_metrics(branch_root)
            transcript_index.extend(transcripts)
            grade = run_checker(candidate, (BANK / "evaluator_only" / fixture.fixture_id / "hidden.py").read_bytes())
            summary = load_json_strict((branch_root / "SUMMARY.json").read_bytes())
            result_rows.append({
                "ordinal": cell["ordinal"], "fixture_id": fixture.fixture_id, "family": fixture.family,
                "seed": cell["seed"], "condition": condition + "-R1", "disposition": summary["disposition"],
                "candidate_id": candidate.candidate_id,
                "known_good_identity": candidate.candidate_id == truth["known_good_candidate_id"],
                "hidden_pass": grade["passed"], "public_check_passed": summary["public_check_passed"],
                "submitted": summary["submitted"], "metrics": metrics,
                "prefix_metrics": prefix_metrics, "fork_binding": summary["fork_binding"],
            })
    result = {
        "schema_version": "experiment-006-authentic-pressure-mechanical-results-v1",
        "response_seal": seal, "bank": bank, "evaluator_opened_only_after_response_seal": True,
        "prepared_invocations": receipt["prepared_invocations"],
        "http_completion_calls": receipt["http_completion_calls"], "rows": result_rows,
    }
    atomic_write(OUTPUT, canonical_json_bytes(result))
    atomic_write(INDEX, canonical_json_bytes(transcript_index))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
