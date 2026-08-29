from __future__ import annotations

from pathlib import Path
from typing import Any

from .custody import ArtifactStore, RecordLog
from .jsonutil import atomic_write, canonical_json_bytes, sha256_bytes
from .recurrent_pressure import (
    FINAL_CALL_LIMIT,
    MiddleOutcome,
    RecurrentFixture,
    build_recurrent_request,
    recurrent_binding,
)
from .runner import Actor, _execute_call, _save_candidate, _snapshot_prefix
from .runtime import CapacityStopped, T25_TOTAL_CEILING
from .tools import SessionState, ToolExecutor


def run_t25_final_operational(
    fixture: RecurrentFixture,
    middle: MiddleOutcome,
    *,
    seed: int,
    actor: Actor,
    output_dir: Path,
    read_mode: str = "actor_selected_count",
    observation_directory_version: int = 1,
    acquisition_contract: bool = False,
    condition_label: str | None = None,
) -> dict[str, Any]:
    """Continue admitted T25 work and reconstruct only at an actual pressure event.

    A preflight capacity denial is a controller transition, not a model retry:
    it consumes a prepared-call identity but no HTTP/model-action budget.
    """
    if middle.binding is None or middle.disposition not in {
        "second_boundary_eligible",
        "second_boundary_not_reached",
    }:
        raise ValueError("Phase C requires mechanically completed Phase B")
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    store = ArtifactStore(output_dir)
    log = RecordLog(output_dir / "records.jsonl", f"{fixture.fixture_id}-S{seed}-T25-C-v2")
    state = SessionState(candidate=middle.state.candidate, stage="continuation")
    recorded_condition = condition_label or "T25"
    executor = ToolExecutor(
        state,
        required_full_reads=(),
        prefork_checker=fixture.phase_a_checker,
        public_checker=fixture.final_checker,
        final_target=fixture.phase_c_target,
        probe_id=fixture.probe_id,
        probe_body=fixture.probe_v2,
        reopenable=middle.reopenable,
        read_mode=read_mode,
    )

    initial_reset = middle.disposition == "second_boundary_eligible"
    history = [middle.active_history[-1]] if initial_reset else list(middle.active_history)
    boundary_binding = middle.binding
    boundary_resets = 1 if initial_reset else 0
    log.append(
        "operational_final_started",
        {
            "condition": recorded_condition,
            "candidate_id": state.candidate.candidate_id,
            "middle_disposition": middle.disposition,
            "continued_admitted_history": not initial_reset,
            "initial_boundary_reset": initial_reset,
            "boundary_binding": boundary_binding,
        },
        _save_candidate(store, state.candidate, _snapshot_prefix(state.candidate)),
    )

    prepared_calls = 0
    http_calls = 0
    maximum_prompt = 0
    capacity_events: list[dict[str, Any]] = []
    terminal_capacity_stop: dict[str, Any] | None = None
    while http_calls < FINAL_CALL_LIMIT and not state.submitted:
        prepared_calls += 1
        request = build_recurrent_request(
            fixture,
            candidate=state.candidate,
            phase="C",
            history=history,
            observations=middle.observations,
            reconstructed=True,
            boundary_binding=boundary_binding,
            calls_used=http_calls,
            read_mode=read_mode,
            observation_directory_version=observation_directory_version,
            acquisition_contract=acquisition_contract,
        )
        try:
            action, result, outcome = _execute_call(
                actor=actor,
                request=request,
                stage="continuation",
                probe_id=fixture.probe_id,
                call_id=f"{fixture.fixture_id}-S{seed}-{recorded_condition}-C-P{prepared_calls:02d}",
                active_total_ceiling=T25_TOTAL_CEILING,
                executor=executor,
                store=store,
                log=log,
                artifact_prefix=f"transcript/{prepared_calls:03d}",
            )
        except CapacityStopped as exc:
            maximum_prompt = max(maximum_prompt, int(exc.admission["offline_prompt_tokens"]))
            capacity_events.append(exc.admission)
            if boundary_resets >= 1 or not history:
                terminal_capacity_stop = exc.admission
                break
            boundary_binding = recurrent_binding(
                fixture,
                seed=seed,
                condition=recorded_condition,
                candidate=state.candidate,
                active_history=history,
                observations=middle.observations,
                prior_binding=boundary_binding,
                last_record_sha256=log.previous or "",
            )
            boundary_resets += 1
            history = [history[-1]]
            log.append(
                "runtime_reconstruction_applied",
                {
                    "phase": "C",
                    "candidate_id": state.candidate.candidate_id,
                    "denied_prepared_invocation": prepared_calls,
                    "http_calls_before_reset": http_calls,
                    "boundary_binding": boundary_binding,
                    "active_history_sha256_after_reset": sha256_bytes(canonical_json_bytes(history)),
                },
                [],
            )
            continue
        http_calls += 1
        maximum_prompt = max(maximum_prompt, outcome.offline_prompt_tokens)
        history.append({"response": action, "result": result})

    disposition = (
        "submitted"
        if state.submitted
        else "capacity_stopped_after_reconstruction"
        if terminal_capacity_stop
        else "final_model_action_budget_exhausted"
    )
    stopped = log.append(
        "operational_final_stopped",
        {
            "disposition": disposition,
            "prepared_invocations": prepared_calls,
            "http_completion_calls": http_calls,
            "boundary_resets": boundary_resets,
            "candidate_id": state.candidate.candidate_id,
            "submitted": state.submitted,
            "public_check_passed": state.public_check_passed,
            "terminal_capacity_stop": terminal_capacity_stop,
        },
        [],
    )
    summary = {
        "schema_version": "recurrent-operational-final-summary-v2",
        "fixture_id": fixture.fixture_id,
        "condition": recorded_condition,
        "seed": seed,
        "disposition": disposition,
        "middle_disposition": middle.disposition,
        "continued_admitted_history": not initial_reset,
        "initial_boundary_reset": initial_reset,
        "runtime_boundary_resets": boundary_resets - (1 if initial_reset else 0),
        "total_recurrent_boundary_resets": boundary_resets,
        "prepared_invocations": prepared_calls,
        "http_completion_calls": http_calls,
        "candidate_id": state.candidate.candidate_id,
        "submitted": state.submitted,
        "public_check_passed": state.public_check_passed,
        "capacity_events": capacity_events,
        "maximum_offline_prompt_tokens": maximum_prompt,
        "history_sha256": sha256_bytes(canonical_json_bytes(history)),
        "last_record_sha256": stopped["record_sha256"],
    }
    atomic_write(output_dir / "SUMMARY.json", canonical_json_bytes(summary))
    return summary
