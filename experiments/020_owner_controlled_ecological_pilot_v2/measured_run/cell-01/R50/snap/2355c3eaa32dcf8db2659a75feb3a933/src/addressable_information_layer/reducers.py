"""Reducer contracts and state-delta acceptance rules."""

from __future__ import annotations

from .hashing import stable_id
from .records import (
    DeltaStatus,
    ModelResponse,
    ReadinessDecision,
    ReadinessStatus,
    ReducerRun,
    StateAuthority,
    StateDelta,
)


TERMINAL_STATUS_VALUES = {"done", "verified"}


def model_assisted_reducer(response: ModelResponse, input_refs: list[str]) -> tuple[list[StateDelta], ReducerRun]:
    deltas: list[StateDelta] = []
    for idx, proposal in enumerate(response.state_update_proposals):
        delta = StateDelta(
            delta_id=stable_id(
                "delta",
                {
                    "idx": idx,
                    "response": response.response_type.value,
                    "proposal": proposal,
                    "input_refs": input_refs,
                },
            ),
            target_state=str(proposal.get("target_state", "layer1")),
            operation=str(proposal.get("operation", "add")),
            proposed_value=proposal.get("proposed_value"),
            source_refs=list(proposal.get("source_refs", input_refs)),
            authority=StateAuthority.MODEL_PROPOSED,
            status=DeltaStatus.PROVISIONAL,
            reason="model-assisted proposal; not deterministic truth",
        )
        deltas.append(delta)

    run = ReducerRun(
        reducer_run_id=stable_id("reducer", {"name": "model_assisted", "deltas": [d.delta_id for d in deltas]}),
        reducer_name="model_assisted_reducer",
        reducer_type="model_assisted",
        input_refs=input_refs,
        output_delta_refs=[delta.delta_id for delta in deltas],
        decision=DeltaStatus.PROVISIONAL if deltas else DeltaStatus.REJECTED,
        reason="model proposals are provisional until confirmed" if deltas else "no state proposals",
    )
    return deltas, run


def deterministic_readiness_reducer(decision: ReadinessDecision) -> tuple[list[StateDelta], ReducerRun]:
    if decision.status == ReadinessStatus.READY:
        run = ReducerRun(
            reducer_run_id=stable_id("reducer", {"name": "readiness", "decision": decision.decision_id}),
            reducer_name="deterministic_readiness_reducer",
            reducer_type="deterministic",
            input_refs=[decision.decision_id],
            output_delta_refs=[],
            decision=DeltaStatus.ACCEPTED,
            reason="readiness passed; no state delta needed",
        )
        return [], run

    delta = StateDelta(
        delta_id=stable_id("delta", {"blocked": decision.decision_id, "route": decision.route.value}),
        target_state="layer1",
        operation="add",
        proposed_value={"blocker": decision.reason, "route": decision.route.value},
        source_refs=[decision.decision_id],
        authority=StateAuthority.DETERMINISTIC,
        status=DeltaStatus.ACCEPTED,
        reason="blocked readiness is deterministic host state",
    )
    run = ReducerRun(
        reducer_run_id=stable_id("reducer", {"name": "readiness", "decision": decision.decision_id, "delta": delta.delta_id}),
        reducer_name="deterministic_readiness_reducer",
        reducer_type="deterministic",
        input_refs=[decision.decision_id],
        output_delta_refs=[delta.delta_id],
        decision=DeltaStatus.ACCEPTED,
        reason="readiness failure recorded as blocker",
    )
    return [delta], run


def accept_state_delta(delta: StateDelta) -> StateDelta:
    proposed = delta.proposed_value
    if delta.authority == StateAuthority.MODEL_PROPOSED and _contains_terminal_status(proposed):
        return StateDelta(
            delta_id=delta.delta_id,
            target_state=delta.target_state,
            operation=delta.operation,
            proposed_value=delta.proposed_value,
            source_refs=delta.source_refs,
            authority=delta.authority,
            status=DeltaStatus.REJECTED,
            reason="model-proposed deltas cannot mark work done or verified",
        )
    if delta.authority == StateAuthority.MODEL_PROPOSED:
        return StateDelta(
            delta_id=delta.delta_id,
            target_state=delta.target_state,
            operation=delta.operation,
            proposed_value=delta.proposed_value,
            source_refs=delta.source_refs,
            authority=delta.authority,
            status=DeltaStatus.PROVISIONAL,
            reason=delta.reason,
        )
    return StateDelta(
        delta_id=delta.delta_id,
        target_state=delta.target_state,
        operation=delta.operation,
        proposed_value=delta.proposed_value,
        source_refs=delta.source_refs,
        authority=delta.authority,
        status=DeltaStatus.ACCEPTED,
        reason=delta.reason,
    )


def _contains_terminal_status(value) -> bool:
    if isinstance(value, str):
        return value.lower() in TERMINAL_STATUS_VALUES
    if isinstance(value, dict):
        return any(_contains_terminal_status(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_terminal_status(item) for item in value)
    return False

