"""CurrentFocus selection for the v0.1 workbench."""

from __future__ import annotations

from .hashing import stable_id
from .records import ArtifactReviewStatus, CurrentFocus, EpisodeState, FocusReason, PlanStepStatus


def select_current_focus(state: EpisodeState) -> CurrentFocus:
    layer1 = state.layer1
    active_artifact_id, active_address, exact_refs = _active_target(state)

    if layer1.user_instruction_refs:
        reason = FocusReason.EXPLICIT_USER_INSTRUCTION
        source_refs = [layer1.user_instruction_refs[-1]]
    elif layer1.verifier_failure_refs:
        reason = FocusReason.VERIFIER_FAILURE
        source_refs = [layer1.verifier_failure_refs[-1]]
    elif layer1.blockers:
        reason = FocusReason.UNRESOLVED_BLOCKER
        source_refs = layer1.latest_event_refs[-1:] or []
    else:
        stale = next((artifact for artifact in state.artifacts.values() if artifact.review_status == ArtifactReviewStatus.STALE), None)
        if stale is not None:
            reason = FocusReason.STALE_TARGET
            source_refs = [stale.artifact_id]
            active_artifact_id = stale.artifact_id
            active_address = stale.last_touched_address
            exact_refs = stale.exact_window_refs
        else:
            active_step = _active_plan_step(state)
            if active_step is not None:
                reason = FocusReason.CURRENT_PLAN_STEP
                source_refs = [active_step.step_id] + active_step.source_refs
                active_artifact_id = active_step.target_artifact_ref or active_artifact_id
                active_address = active_step.target_address or active_address
            elif active_artifact_id:
                reason = FocusReason.LAST_CHANGED_ARTIFACT
                source_refs = [active_artifact_id]
            else:
                reason = FocusReason.MODEL_ASSISTED_PLANNING_NEEDED
                source_refs = layer1.latest_event_refs[-1:] or []

    focus_payload = {
        "episode_id": state.episode_id,
        "reason": reason.value,
        "source_refs": source_refs,
        "active_artifact": active_artifact_id,
        "active_address": active_address,
    }
    return CurrentFocus(
        focus_id=stable_id("focus", focus_payload),
        reason_code=reason,
        source_refs=source_refs,
        active_artifact_ref=active_artifact_id,
        active_address=active_address,
        exact_window_refs=exact_refs[:4],
        latest_result_refs=layer1.verifier_failure_refs[-1:] or layer1.latest_event_refs[-1:],
        permitted_action_class="proposal_only",
    )


def _active_plan_step(state: EpisodeState):
    if state.plan is None:
        return None
    for step in state.plan.steps:
        if step.status == PlanStepStatus.ACTIVE:
            return step
    for step in state.plan.steps:
        if step.status == PlanStepStatus.PENDING:
            return step
    return None


def _active_target(state: EpisodeState) -> tuple[str | None, str | None, list[str]]:
    active_step = _active_plan_step(state)
    if active_step is not None and active_step.target_artifact_ref:
        artifact = state.artifacts.get(active_step.target_artifact_ref)
        if artifact is not None:
            return artifact.artifact_id, active_step.target_address, artifact.exact_window_refs

    if not state.artifacts:
        return None, None, []
    changed = next((item for item in state.artifacts.values() if item.review_status == ArtifactReviewStatus.CHANGED), None)
    artifact = changed or next(iter(state.artifacts.values()))
    return artifact.artifact_id, artifact.last_touched_address, artifact.exact_window_refs
