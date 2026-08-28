from __future__ import annotations

from pathlib import Path
from typing import Any

from working_set_exp.candidate import Candidate
from working_set_exp.custody import verify_records
from working_set_exp.fixture import load_fixture, load_truth
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.measured import package_identity
from working_set_exp.request import fork_binding
from working_set_exp.runner import PrefixOutcome
from working_set_exp.tools import SessionState, ToolExecutor


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "002_single_boundary_reconstruction"
RUN = EXPERIMENT / "mrun"
BANK = EXPERIMENT / "fresh_bank"
OUTPUT = EXPERIMENT / "MECHANICAL_RESULTS.json"


def verify_seal() -> dict[str, Any]:
    seal = load_json_strict((RUN / "RESPONSE_SEAL.json").read_bytes())
    for row in seal["files"]:
        path = RUN / Path(*row["path"].split("/"))
        if not path.is_file() or path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise ValueError(f"response-seal file differs: {row['path']}")
    if package_identity(seal["files"]) != seal["aggregate_sha256"]:
        raise ValueError("response-seal aggregate differs")
    return {"verified": True, "file_count": len(seal["files"]), "aggregate_sha256": seal["aggregate_sha256"]}


def replay_prefix_any(fixture, run_dir: Path) -> PrefixOutcome:
    records = verify_records(run_dir / "records.jsonl", run_dir)
    summary = load_json_strict((run_dir / "SUMMARY.json").read_bytes())
    state = SessionState(fixture.initial)
    executor = ToolExecutor(
        state,
        required_full_reads=fixture.required_full_reads,
        prefork_checker=fixture.prefork_checker,
        public_checker=fixture.public_checker,
        final_target=fixture.final_target,
        probe_id=fixture.probe_id,
        probe_body=fixture.probe_body,
    )
    history: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    reopenable: dict[str, bytes] = {}
    last_action_record_sha256 = ""
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
            observations.append(
                {
                    "handle": handle,
                    "sequence": len(history),
                    "action": action["action"],
                    "target": target,
                    "candidate_id": expected.get(
                        "checked_candidate_id", expected.get("candidate_id", state.candidate.candidate_id)
                    ),
                    "size_bytes": len(body),
                    "sha256": sha256_bytes(body),
                }
            )
        last_action_record_sha256 = record["record_sha256"]
    if state.candidate.candidate_id != summary["candidate_id"]:
        raise ValueError("prefix final candidate differs")
    binding: dict[str, Any] = {}
    if summary["disposition"] == "fork_eligible":
        binding = fork_binding(
            fixture_id=fixture.fixture_id,
            seed=summary["seed"],
            task=fixture.task,
            candidate=state.candidate,
            prefix_history=history,
            observations=observations,
            last_record_sha256=last_action_record_sha256,
        )
        if canonical_json_bytes(binding) != canonical_json_bytes(summary["fork_binding"]):
            raise ValueError("fork binding replay differs")
    return PrefixOutcome(state, history, observations, reopenable, binding, summary["calls"], run_dir)


def replay_branch(fixture, prefix: PrefixOutcome, run_dir: Path) -> dict[str, Any]:
    records = verify_records(run_dir / "records.jsonl", run_dir)
    summary = load_json_strict((run_dir / "SUMMARY.json").read_bytes())
    state = prefix.state.clone_for_branch()
    executor = ToolExecutor(
        state,
        required_full_reads=fixture.required_full_reads,
        prefork_checker=fixture.prefork_checker,
        public_checker=fixture.public_checker,
        final_target=fixture.final_target,
        probe_id=fixture.probe_id,
        probe_body=fixture.probe_body,
        reopenable=prefix.reopenable,
    )
    actions = 0
    for record in records:
        if record["record_type"] != "action_result":
            continue
        expected = record["payload"]["result"]
        observed = executor.execute(record["payload"]["action"])
        if canonical_json_bytes(observed) != canonical_json_bytes(expected):
            raise ValueError("branch action/result replay differs")
        actions += 1
    if state.candidate.candidate_id != summary["candidate_id"]:
        raise ValueError("branch final candidate differs")
    return {"verified": True, "action_results": actions, "candidate_id": state.candidate.candidate_id}


def candidate_from_snapshot(run_dir: Path, candidate_id: str) -> Candidate:
    root = run_dir / "snap" / candidate_id[:32]
    files = {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    candidate = Candidate.create(files)
    if candidate.candidate_id != candidate_id:
        raise ValueError("snapshot candidate identity differs")
    return candidate


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    seal = verify_seal()
    receipt = load_json_strict((RUN / "RECEIPT.json").read_bytes())
    rows: list[dict[str, Any]] = []
    completion_calls = 0
    prospective_calls = 0
    for cell in receipt["forks"]:
        fixture = load_fixture(BANK, cell["fixture_id"])
        truth = load_truth(BANK, cell["fixture_id"])
        fork_root = RUN / f"fork-{cell['ordinal']:02d}"
        prefix = replay_prefix_any(fixture, fork_root / "prefix")
        stages = ["prefix", *cell["branches"].keys()]
        for stage in stages:
            stage_root = fork_root / stage
            summary = load_json_strict((stage_root / "SUMMARY.json").read_bytes())
            replay = {"verified": True, "action_results": len(prefix.history), "candidate_id": prefix.state.candidate.candidate_id}
            if stage != "prefix":
                replay = replay_branch(fixture, prefix, stage_root)
            records = verify_records(stage_root / "records.jsonl", stage_root)
            action_count = sum(row["record_type"] == "action_result" for row in records)
            prepared_count = sum(row["record_type"] == "external_call_prepared" for row in records)
            completion_calls += action_count
            prospective_calls += prepared_count
            candidate = candidate_from_snapshot(stage_root, summary["candidate_id"])
            hidden = (BANK / "evaluator_only" / fixture.fixture_id / "hidden.py").read_bytes()
            grade = run_checker(candidate, hidden)
            rows.append(
                {
                    "ordinal": cell["ordinal"],
                    "fixture_id": fixture.fixture_id,
                    "family": fixture.family,
                    "seed": cell["seed"],
                    "stage": stage,
                    "condition": None if stage == "prefix" else stage,
                    "disposition": summary["disposition"],
                    "candidate_id": summary["candidate_id"],
                    "known_good_identity": summary["candidate_id"] == truth["known_good_candidate_id"],
                    "hidden_pass": grade["passed"],
                    "hidden_returncode": grade["returncode"],
                    "hidden_stdout_sha256": grade["stdout_sha256"],
                    "hidden_stderr_sha256": grade["stderr_sha256"],
                    "completion_calls": action_count,
                    "prospective_calls": prepared_count,
                    "replay": replay,
                }
            )
    result = {
        "schema_version": "experiment-002-mechanical-results-v1",
        "response_seal": seal,
        "evaluator_opened_only_after_response_seal": True,
        "completion_calls": completion_calls,
        "prospective_calls": prospective_calls,
        "rows": rows,
    }
    atomic_write(OUTPUT, canonical_json_bytes(result))
    print(result)


if __name__ == "__main__":
    main()
