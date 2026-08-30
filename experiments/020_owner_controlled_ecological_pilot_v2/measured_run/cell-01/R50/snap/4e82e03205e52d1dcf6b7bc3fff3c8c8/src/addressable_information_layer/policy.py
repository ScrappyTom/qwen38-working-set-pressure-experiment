"""Offline policy classifications for context and acceptance audits."""

from __future__ import annotations

from .artifact_units import resolve_address
from .records import (
    AcceptanceCriterionClass,
    AddressMap,
    ArtifactReviewStatus,
    CriterionArtifact,
    CurrentFocus,
    EpisodeState,
    InformationNeedClass,
    SummaryNode,
)

MECHANICAL_CHECK_TYPES = {
    "python_syntax",
    "contains",
    "not_contains",
    "regex",
    "verifier_log_passed",
    "required_headings",
    "section_contains",
    "no_unresolved_markers",
    "word_count_min",
    "command",
    "shell_command",
}

SEMANTIC_CHECK_TYPES = {"semantic_review", "model_review", "llm_review"}
OPERATOR_CHECK_TYPES = {"human", "human_review", "operator", "operator_review", "manual_review"}
UNVERIFIABLE_CHECK_TYPES = {"unverifiable", "unknown"}


def classify_focus_information_need(
    state: EpisodeState,
    focus: CurrentFocus,
    *,
    address_maps: dict[str, AddressMap],
) -> dict[str, str]:
    """Classify the context need for the next model call.

    This is deterministic scaffolding, not a prediction of model quality. It
    tells the host whether the current focus is exact-ready, summary/card-ready,
    handle-only, under-specified, or needs decomposition before useful work.
    """

    if not state.artifacts:
        return _need(InformationNeedClass.NEEDS_DECOMPOSITION, "no artifacts are mapped for the episode")
    if focus.active_artifact_ref is None:
        return _need(InformationNeedClass.HANDLE_SUFFICIENT, "artifacts exist but no active artifact is selected")
    artifact_state = state.artifacts.get(focus.active_artifact_ref)
    if artifact_state is None:
        return _need(InformationNeedClass.INSUFFICIENT_CONTEXT, "active artifact is missing from EpisodeState")
    if artifact_state.review_status == ArtifactReviewStatus.STALE:
        return _need(InformationNeedClass.EXACT_REQUIRED, "active artifact is stale and must be refreshed or reopened")
    if focus.active_address and resolve_address(address_maps, focus.active_address) is None:
        return _need(InformationNeedClass.INSUFFICIENT_CONTEXT, "active address does not resolve in the current artifact map")
    if focus.exact_window_refs:
        return _need(InformationNeedClass.EXACT_REQUIRED, "current focus has visible exact material")
    if artifact_state.address_map_ref:
        return _need(InformationNeedClass.CARD_SUFFICIENT, "active artifact has a map and summary but no exact window")
    return _need(InformationNeedClass.INSUFFICIENT_CONTEXT, "active artifact lacks a usable map or exact window")


def classify_criterion(criterion: CriterionArtifact) -> dict[str, str]:
    check_type = criterion.check_type
    if check_type in MECHANICAL_CHECK_TYPES:
        criterion_class = AcceptanceCriterionClass.MECHANICAL
        reason = "deterministic host-verifiable criterion"
    elif check_type in SEMANTIC_CHECK_TYPES:
        criterion_class = AcceptanceCriterionClass.SEMANTIC_ADVISORY
        reason = "requires semantic judgment; model output is advisory until confirmed"
    elif check_type in OPERATOR_CHECK_TYPES:
        criterion_class = AcceptanceCriterionClass.OPERATOR_REQUIRED
        reason = "requires operator or human confirmation"
    elif check_type in UNVERIFIABLE_CHECK_TYPES:
        criterion_class = AcceptanceCriterionClass.UNVERIFIABLE
        reason = "no deterministic verifier is available"
    else:
        criterion_class = AcceptanceCriterionClass.UNVERIFIABLE
        reason = f"unsupported check_type {check_type}"
    return {
        "criterion_id": criterion.criterion_id,
        "check_type": check_type,
        "classification": criterion_class.value,
        "reason": reason,
    }


def classify_criteria(criteria: list[CriterionArtifact]) -> list[dict[str, str]]:
    return [classify_criterion(criterion) for criterion in criteria]


def audit_summary_claims(summaries: dict[str, SummaryNode]) -> list[dict[str, object]]:
    """Check that non-empty summary claim axes have exact descent handles.

    The summaries remain non-authoritative. This audit catches the failure mode
    where a compact parent view starts making claims without any path back to
    exact child evidence.
    """

    audits: list[dict[str, object]] = []
    for summary in summaries.values():
        claim_axes = _non_empty_claim_axes(summary)
        evidence_refs = list(summary.exact_descents)
        missing_evidence = bool(claim_axes) and not evidence_refs
        bad_refs = [ref for ref in evidence_refs if not ref.startswith("exact:")]
        status = "failed" if missing_evidence or bad_refs else "passed"
        reason = "summary claim axes have exact descent refs"
        if missing_evidence:
            reason = "summary has claim-like axes without exact descent refs"
        elif bad_refs:
            reason = "summary exact descents contain invalid refs"
        audits.append(
            {
                "summary_id": summary.summary_id,
                "policy_id": summary.policy_id,
                "status": status,
                "claim_axes": claim_axes,
                "evidence_refs": evidence_refs[:12],
                "reason": reason,
            }
        )
    return audits


def _need(need_class: InformationNeedClass, reason: str) -> dict[str, str]:
    return {"classification": need_class.value, "reason": reason}


def _non_empty_claim_axes(summary: SummaryNode) -> list[str]:
    axes = summary.axes
    claim_axes: list[str] = []
    for key in ("claims_facts", "interfaces_dependencies", "constraints", "current_state", "risks_unknowns"):
        value = axes.get(key)
        if value:
            claim_axes.append(key)
    return claim_axes
