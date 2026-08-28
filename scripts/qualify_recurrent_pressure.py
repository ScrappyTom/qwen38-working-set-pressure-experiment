from __future__ import annotations

import json
from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, sha256_bytes
from working_set_exp.recurrent_pressure import (
    FINAL_CALL_LIMIT,
    MIDDLE_CALL_LIMIT,
    PREFIX_CALL_LIMIT,
    CandidateBoundProbeExecutor,
    _capture_observation,
    build_recurrent_request,
    hidden_grade,
    load_recurrent_fixture,
    recurrent_binding,
    verify_bank,
    verify_closure,
    verify_package,
)
from working_set_exp.request import build_request, fork_binding
from working_set_exp.runtime import PHYSICAL_CONTEXT, T25_TOTAL_CEILING, guard, load_runtime
from working_set_exp.tools import SessionState, ToolExecutor


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "007_recurrent_bounded_pressure"


def _bound(action: dict, state: SessionState, path: str) -> dict:
    return {
        **action,
        "expected_candidate_id": state.candidate.candidate_id,
        "expected_file_sha256": state.candidate.file_sha256(path),
    }


def _run_case(fixture_id: str, seed: int) -> dict:
    fixture = load_recurrent_fixture(EXPERIMENT / "fresh_bank", fixture_id)
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    state = SessionState(fixture.initial)
    prefix_executor = ToolExecutor(
        state, required_full_reads=fixture.phase_a_required, prefork_checker=fixture.phase_a_checker,
        public_checker=fixture.final_checker, final_target=fixture.phase_b_target,
        probe_id=fixture.probe_id, probe_body=fixture.probe_v1,
    )
    prefix_history = []
    observations = []
    reopenable = {}

    def apply(executor: ToolExecutor, action: dict, history: list[dict]) -> dict:
        result = executor.execute(action)
        if not result.get("accepted"):
            raise AssertionError((fixture_id, action, result))
        history.append({"response": action, "result": result})
        _capture_observation(
            action, result, sequence=len(history), state=executor.state,
            observations=observations, reopenable=reopenable,
        )
        return result

    apply(prefix_executor, {"action": "begin"}, prefix_history)
    for path in fixture.phase_a_required:
        apply(prefix_executor, {"action": "read", "path": path, "start_line": 1, "line_count": 500}, prefix_history)
    stage_result = apply(prefix_executor, {"action": "read", "path": "stage/ready.py", "start_line": 1, "line_count": 100}, prefix_history)
    apply(prefix_executor, _bound({
        "action": "patch", "path": "stage/ready.py", "old": "    return 0", "new": "    return len(PHASE_A_GROUPS)"
    }, state, "stage/ready.py"), prefix_history)
    apply(prefix_executor, {"action": "check", "check_id": "prefork", "expected_candidate_id": state.candidate.candidate_id}, prefix_history)
    if fixture.probe_id:
        apply(prefix_executor, {"action": "probe", "probe_id": fixture.probe_id}, prefix_history)
    apply(prefix_executor, {"action": "fork_ready", "expected_candidate_id": state.candidate.candidate_id}, prefix_history)
    binding1 = fork_binding(
        fixture_id=fixture.fixture_id, seed=seed, task=fixture.task, candidate=state.candidate,
        prefix_history=prefix_history, observations=observations, last_record_sha256=sha256_bytes(b"qualified-boundary-1"),
    )
    next1 = build_recurrent_request(
        fixture, candidate=state.candidate, phase="B", history=prefix_history, observations=observations,
        reconstructed=False, boundary_binding=binding1, calls_used=0,
    )
    boundary1_t25 = guard(profile, next1, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
    boundary1_c50 = guard(profile, next1, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True)
    if boundary1_t25["authorized"] or not boundary1_c50["authorized"]:
        raise AssertionError((fixture_id, "boundary1", boundary1_t25, boundary1_c50))

    middle_state = state.clone_for_branch()
    middle_state.stage = "recurrent"
    middle_state.fork_ready = False
    middle_state.public_check_passed = False
    middle_state.probe_done = False
    truth = json.loads((EXPERIMENT / "fresh_bank" / "evaluator_only" / fixture_id / "TRUTH.json").read_text())
    executor = CandidateBoundProbeExecutor(
        middle_state, required_full_reads=fixture.phase_b_required, prefork_checker=fixture.phase_a_checker,
        public_checker=fixture.phase_b_checker, final_target=fixture.phase_c_target,
        probe_id=fixture.probe_id, probe_body=fixture.probe_v1, reopenable=reopenable,
        baseline_candidate_id=state.candidate.candidate_id, probe_v1=fixture.probe_v1, probe_v2=fixture.probe_v2,
    )
    middle_history = [prefix_history[-1]]
    guards = []

    def middle_apply(action: dict) -> dict:
        request = build_recurrent_request(
            fixture, candidate=middle_state.candidate, phase="B", history=middle_history,
            observations=observations, reconstructed=True, boundary_binding=binding1,
            calls_used=len(middle_history) - 1,
        )
        admission = guard(profile, request, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
        guards.append(admission)
        if not admission["authorized"]:
            raise AssertionError((fixture_id, "phase B scripted action not admitted", action, admission))
        return apply(executor, action, middle_history)

    if fixture.family == "recurrent_source_continuity":
        governing_path = truth["governing"]["path"]
        middle_apply({"action": "read", "path": governing_path, "start_line": 1, "line_count": 500})
    else:
        handle = next(row["handle"] for row in observations if row["action"] == "probe")
        middle_apply({"action": "reopen_observation", "handle": handle})
    target = fixture.phase_b_target
    middle_apply({"action": "read", "path": target, "start_line": 1, "line_count": 100})
    patch = truth["phase_b_patch"]
    middle_apply(_bound({"action": "patch", "path": target, "old": patch["old"], "new": patch["new"]}, middle_state, target))
    middle_apply({"action": "check", "check_id": "public", "expected_candidate_id": middle_state.candidate.candidate_id})
    if fixture.probe_id:
        middle_apply({"action": "probe", "probe_id": fixture.probe_id})
    for path in fixture.phase_b_required:
        middle_apply({"action": "read", "path": path, "start_line": 1, "line_count": 500})
    middle_apply({"action": "fork_ready", "expected_candidate_id": middle_state.candidate.candidate_id})
    binding2 = recurrent_binding(
        fixture, seed=seed, condition="T25", candidate=middle_state.candidate,
        active_history=middle_history, observations=observations, prior_binding=binding1,
        last_record_sha256=sha256_bytes(b"qualified-boundary-2"),
    )
    next2 = build_recurrent_request(
        fixture, candidate=middle_state.candidate, phase="C", history=middle_history,
        observations=observations, reconstructed=True, boundary_binding=binding2, calls_used=0,
    )
    boundary2_t25 = guard(profile, next2, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
    boundary2_c50 = guard(profile, next2, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True)
    if boundary2_t25["authorized"] or not boundary2_c50["authorized"]:
        raise AssertionError((fixture_id, "boundary2", boundary2_t25, boundary2_c50))

    final_state = SessionState(middle_state.candidate, stage="continuation")
    final_executor = ToolExecutor(
        final_state, required_full_reads=(), prefork_checker=fixture.phase_a_checker,
        public_checker=fixture.final_checker, final_target=fixture.phase_c_target,
        probe_id=fixture.probe_id, probe_body=fixture.probe_v2, reopenable=reopenable,
    )
    final_history = [middle_history[-1]]

    def final_apply(action: dict) -> dict:
        request = build_recurrent_request(
            fixture, candidate=final_state.candidate, phase="C", history=final_history,
            observations=observations, reconstructed=True, boundary_binding=binding2,
            calls_used=len(final_history) - 1,
        )
        admission = guard(profile, request, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
        if not admission["authorized"]:
            raise AssertionError((fixture_id, "phase C scripted action not admitted", action, admission))
        return apply(final_executor, action, final_history)

    if fixture.family == "recurrent_source_continuity":
        final_apply({"action": "read", "path": governing_path, "start_line": 1, "line_count": 500})
    else:
        current = next(row["handle"] for row in reversed(observations) if row["action"] == "probe" and row["candidate_id"] == final_state.candidate.candidate_id)
        final_apply({"action": "reopen_observation", "handle": current})
    target = fixture.phase_c_target
    final_apply({"action": "read", "path": target, "start_line": 1, "line_count": 100})
    patch = truth["phase_c_patch"]
    final_apply(_bound({"action": "patch", "path": target, "old": patch["old"], "new": patch["new"]}, final_state, target))
    final_apply({"action": "check", "check_id": "public", "expected_candidate_id": final_state.candidate.candidate_id})
    final_apply({"action": "submit", "expected_candidate_id": final_state.candidate.candidate_id})
    hidden = hidden_grade(fixture, final_state.candidate)
    if not hidden["passed"]:
        raise AssertionError((fixture_id, hidden))
    return {
        "fixture_id": fixture_id, "seed": seed, "boundary1_t25": boundary1_t25,
        "boundary1_c50": boundary1_c50, "phase_b_admitted_calls": len(guards),
        "phase_b_peak_prompt_tokens": max(row["offline_prompt_tokens"] for row in guards),
        "boundary2_t25": boundary2_t25, "boundary2_c50": boundary2_c50,
        "final_hidden_pass": True, "final_candidate_id": final_state.candidate.candidate_id,
    }


def main() -> None:
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    result = {
        "schema_version": "experiment-007-recurrent-mechanical-qualification-v1",
        "bank": verify_bank(EXPERIMENT / "fresh_bank"),
        "package": verify_package(
            EXPERIMENT / "execution_package", bank=EXPERIMENT / "fresh_bank",
            schedule_path=EXPERIMENT / "SCHEDULE.json", profile=profile,
        ),
        "closure": verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json"),
        "cases": [_run_case(fixture_id, 173205) for fixture_id in ("E7-SOURCE", "E7-OBSERVATION")],
        "model_calls": 0,
    }
    atomic_write(EXPERIMENT / "MECHANICAL_QUALIFICATION.json", canonical_json_bytes(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
