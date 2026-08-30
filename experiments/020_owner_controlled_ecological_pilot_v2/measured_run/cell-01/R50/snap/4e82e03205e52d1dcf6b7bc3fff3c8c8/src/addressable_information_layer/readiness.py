"""Readiness matrix for model proposals."""

from __future__ import annotations

from .artifact_units import resolve_address
from .hashing import stable_id
from .records import (
    AddressMap,
    ArtifactReviewStatus,
    CurrentFocus,
    EpisodeState,
    ModelResponse,
    ReadinessDecision,
    ReadinessStatus,
    RejectionRoute,
    ResponseType,
)


VAGUE_REQUESTS = {
    "",
    "more",
    "more context",
    "context",
    "all",
    "everything",
    "the file",
    "source",
    "more info",
}


def check_readiness(
    state: EpisodeState,
    focus: CurrentFocus,
    response: ModelResponse,
    *,
    address_maps: dict[str, AddressMap],
    patch_preview_ids: set[str] | None = None,
) -> ReadinessDecision:
    if response.response_type == ResponseType.REQUEST_EXACT:
        return _check_request_exact(response, address_maps)
    if response.response_type == ResponseType.DRAFT_CHANGE:
        return _check_draft_change(state, focus, response)
    if response.response_type == ResponseType.APPLY_CHANGE:
        return _check_apply_change(response, patch_preview_ids or set())
    if response.response_type == ResponseType.FINAL_ANSWER:
        return _check_final_answer(focus, response)
    if response.response_type == ResponseType.ASK_USER:
        return _ready(response, "user clarification requested")
    if response.response_type in {ResponseType.PLAN_NEXT, ResponseType.REVIEW_RESULT}:
        return _ready(response, "proposal/review response is host-reviewable")
    return _blocked(response, "unsupported response type", RejectionRoute.ASK_USER)


def _check_request_exact(response: ModelResponse, address_maps: dict[str, AddressMap]) -> ReadinessDecision:
    requested = (response.requested_ref_or_address or "").strip()
    if requested.lower() in VAGUE_REQUESTS:
        return _blocked(
            response,
            "REQUEST_EXACT is vague; host must return an address map or ask a narrow question, not run broad retrieval",
            RejectionRoute.REFRESH_OR_REOPEN_CONTEXT,
        )
    if resolve_address(address_maps, requested) is None:
        return _blocked(
            response,
            f"REQUEST_EXACT handle is not visible or resolvable: {requested}",
            RejectionRoute.REFRESH_OR_REOPEN_CONTEXT,
            required_refs=[requested],
        )
    return _ready(response, "exact handle is visible and bounded", required_refs=[requested])


def _check_draft_change(state: EpisodeState, focus: CurrentFocus, response: ModelResponse) -> ReadinessDecision:
    if not focus.active_artifact_ref:
        return _blocked(response, "DRAFT_CHANGE has no active artifact", RejectionRoute.ASK_USER)
    artifact = state.artifacts.get(focus.active_artifact_ref)
    if artifact is None:
        return _blocked(response, "DRAFT_CHANGE active artifact is missing from state", RejectionRoute.REPAIR_MAP_OR_SUMMARY)
    if artifact.review_status == ArtifactReviewStatus.STALE:
        return _blocked(response, "DRAFT_CHANGE target artifact map/hash is stale", RejectionRoute.REFRESH_OR_REOPEN_CONTEXT)
    if not focus.exact_window_refs:
        return _blocked(response, "DRAFT_CHANGE requires an exact active window", RejectionRoute.REFRESH_OR_REOPEN_CONTEXT)
    if not response.draft:
        return _blocked(response, "DRAFT_CHANGE is missing draft text", RejectionRoute.FIX_ACTION)
    return _ready(response, "exact active window and current artifact state are visible", required_refs=focus.exact_window_refs)


def _check_final_answer(focus: CurrentFocus, response: ModelResponse) -> ReadinessDecision:
    if response.reasoning_only:
        return _ready(response, "FINAL_ANSWER explicitly marked reasoning-only")
    visible = set(focus.exact_window_refs)
    if not response.support_refs or not visible.intersection(response.support_refs):
        return _blocked(
            response,
            "FINAL_ANSWER has source-grounded claims without visible exact support",
            RejectionRoute.REFRESH_OR_REOPEN_CONTEXT,
            required_refs=response.support_refs,
        )
    return _ready(response, "FINAL_ANSWER has visible exact support", required_refs=response.support_refs)


def _check_apply_change(response: ModelResponse, patch_preview_ids: set[str]) -> ReadinessDecision:
    if not response.preview_id:
        return _blocked(response, "APPLY_CHANGE requires a preview_id", RejectionRoute.FIX_ACTION)
    if response.preview_id not in patch_preview_ids:
        return _blocked(response, f"APPLY_CHANGE preview_id is unknown or stale: {response.preview_id}", RejectionRoute.FIX_ACTION)
    if not (response.operator_confirmed or response.verifier_confirmed):
        return _blocked(
            response,
            "APPLY_CHANGE requires operator_confirmed or verifier_confirmed",
            RejectionRoute.ASK_USER,
            required_refs=[response.preview_id],
        )
    return _ready(response, "APPLY_CHANGE has known preview and confirmation", required_refs=[response.preview_id])


def _ready(response: ModelResponse, reason: str, required_refs: list[str] | None = None) -> ReadinessDecision:
    return ReadinessDecision(
        decision_id=stable_id("ready", {"type": response.response_type.value, "reason": reason, "refs": required_refs or []}),
        status=ReadinessStatus.READY,
        response_type=response.response_type,
        reason=reason,
        required_refs=required_refs or [],
    )


def _blocked(
    response: ModelResponse,
    reason: str,
    route: RejectionRoute,
    required_refs: list[str] | None = None,
) -> ReadinessDecision:
    return ReadinessDecision(
        decision_id=stable_id("blocked", {"type": response.response_type.value, "reason": reason, "refs": required_refs or []}),
        status=ReadinessStatus.BLOCKED,
        response_type=response.response_type,
        reason=reason,
        route=route,
        required_refs=required_refs or [],
    )
