"""Five-section working brief renderer and context receipt creation."""

from __future__ import annotations

from .artifact_units import exact_text_for_unit, resolve_address
from .hashing import sha256_text, stable_id
from .policy import audit_summary_claims, classify_criteria, classify_focus_information_need
from .records import (
    AddressMap,
    ContextReceipt,
    CurrentFocus,
    EpisodeState,
    ResponseType,
    SummaryNode,
)


PROMPT_TEMPLATE_VERSION = "working_brief.v0.1"
ALLOWED_RESPONSE_MENU = [item.value for item in ResponseType]
TOP_LEVEL_SECTIONS = ["TASK", "STATE", "ARTIFACT", "LATEST RESULT", "RESPONSE"]


def render_working_brief(
    state: EpisodeState,
    focus: CurrentFocus,
    *,
    artifacts: dict[str, object] | None = None,
    address_maps: dict[str, AddressMap],
    summaries: dict[str, SummaryNode],
    model_call_id: str = "model_call_0001",
    model_profile_ref: str | None = None,
    output_contract_ref: str | None = None,
) -> tuple[str, ContextReceipt]:
    sections = {
        "TASK": _render_task(state, focus),
        "STATE": _render_state(state),
        "ARTIFACT": _render_artifact(state, focus, artifacts or {}, address_maps, summaries),
        "LATEST RESULT": _render_latest_result(state, focus),
        "RESPONSE": _render_response(focus),
    }
    rendered = "\n\n".join(f"{name}\n{body}".rstrip() for name, body in sections.items())
    receipt_payload = {
        "episode": state.episode_id,
        "model_call_id": model_call_id,
        "rendered_hash": sha256_text(rendered),
        "focus": focus.focus_id,
        "sections": list(sections),
    }
    receipt = ContextReceipt(
        receipt_id=stable_id("context_receipt", receipt_payload),
        episode_id=state.episode_id,
        model_call_id=model_call_id,
        objective_ref=stable_id("objective", state.objective),
        layer1_state_ref=state.layer1.state_id,
        plan_state_ref=state.plan.plan_id if state.plan else None,
        current_focus_ref=focus.focus_id,
        artifact_state_refs=list(state.artifacts),
        exact_window_refs=focus.exact_window_refs,
        latest_event_refs=state.layer1.latest_event_refs,
        allowed_response_menu=ALLOWED_RESPONSE_MENU,
        permitted_action_class=focus.permitted_action_class,
        prompt_template_version=PROMPT_TEMPLATE_VERSION,
        model_profile_ref=model_profile_ref,
        output_contract_ref=output_contract_ref,
        rendered_context_hash=sha256_text(rendered),
        shown_sections=list(sections),
        candidate_dispositions=_candidate_dispositions(state, focus, address_maps, summaries),
        information_need_classification=classify_focus_information_need(state, focus, address_maps=address_maps),
        criterion_classifications=classify_criteria(state.criteria),
        summary_claim_audit=audit_summary_claims(summaries),
    )
    return rendered, receipt


def _render_task(state: EpisodeState, focus: CurrentFocus) -> str:
    return "\n".join(
        [
            f"Objective: {state.objective}",
            f"Current focus reason: {focus.reason_code.value}",
            f"Active address: {focus.active_address or 'none'}",
        ]
    )


def _render_state(state: EpisodeState) -> str:
    lines: list[str] = []
    if state.layer1.constraints:
        lines.append("Constraints:")
        lines.extend(f"- {item}" for item in state.layer1.constraints)
    if state.criteria:
        lines.append("Criteria:")
        classifications = {item["criterion_id"]: item for item in classify_criteria(state.criteria)}
        lines.extend(
            (
                f"- {criterion.status}: {criterion.statement} "
                f"[{criterion.check_type}; {classifications[criterion.criterion_id]['classification']}]"
            )
            for criterion in state.criteria
        )
    if state.layer1.blockers:
        lines.append("Blockers:")
        lines.extend(f"- {item}" for item in state.layer1.blockers)
    if state.layer1.attempt_history:
        lines.append("Attempt history:")
        lines.extend(f"- {item}" for item in state.layer1.attempt_history[-4:])
    if state.layer1.open_questions:
        lines.append("Open questions:")
        lines.extend(f"- {item}" for item in state.layer1.open_questions)
    return "\n".join(lines) if lines else "No compact state has been accepted yet."


def _render_artifact(
    state: EpisodeState,
    focus: CurrentFocus,
    artifacts: dict[str, object],
    address_maps: dict[str, AddressMap],
    summaries: dict[str, SummaryNode],
) -> str:
    if not focus.active_artifact_ref:
        return "No active artifact."
    artifact_state = state.artifacts.get(focus.active_artifact_ref)
    summary = summaries.get(focus.active_artifact_ref)
    lines = [
        f"Artifact: {artifact_state.path_or_name if artifact_state else focus.active_artifact_ref}",
        f"Review status: {artifact_state.review_status.value if artifact_state else 'unknown'}",
    ]
    if summary:
        axes = summary.axes
        lines.append(f"Summary policy: {summary.policy_id} (awareness only)")
        lines.append(f"Purpose: {axes.get('purpose', 'unknown')}")
        if axes.get("unit_titles"):
            lines.append("Available units:")
            lines.extend(f"- {item}" for item in axes["unit_titles"][:8])
        if axes.get("available_exact_descents"):
            lines.append("Available exact handles:")
            lines.extend(f"- {item}" for item in axes["available_exact_descents"][:8])
    if focus.exact_window_refs:
        lines.append("Visible exact refs:")
        lines.extend(f"- {ref}" for ref in focus.exact_window_refs)
        exact_blocks = _render_exact_blocks(focus.exact_window_refs, artifacts, address_maps)
        if exact_blocks:
            lines.append("Visible exact material:")
            lines.extend(exact_blocks)
    elif focus.active_address:
        unit = resolve_address(address_maps, focus.active_address)
        if unit:
            lines.append(f"Visible exact ref: {unit.exact_ref}")
            exact_blocks = _render_exact_blocks([unit.exact_ref], artifacts, address_maps)
            if exact_blocks:
                lines.append("Visible exact material:")
                lines.extend(exact_blocks)
    return "\n".join(lines)


def _render_exact_blocks(exact_refs: list[str], artifacts: dict[str, object], address_maps: dict[str, AddressMap]) -> list[str]:
    blocks: list[str] = []
    for exact_ref in exact_refs[:3]:
        unit = resolve_address(address_maps, exact_ref)
        if unit is None:
            continue
        artifact = artifacts.get(unit.artifact_id)
        if artifact is None:
            continue
        text = exact_text_for_unit(artifact, unit)  # type: ignore[arg-type]
        if len(text) > 1200:
            text = text[:1200] + "\n[truncated]"
        blocks.append(f"--- {exact_ref} ({unit.start_line}-{unit.end_line}) ---")
        blocks.append(text)
    return blocks


def _render_latest_result(state: EpisodeState, focus: CurrentFocus) -> str:
    refs = focus.latest_result_refs or state.layer1.latest_event_refs[-1:]
    if not refs:
        return "No prior result."
    return "\n".join(f"- {ref}" for ref in refs)


def _render_response(focus: CurrentFocus) -> str:
    return "\n".join(
        [
            "Allowed response types:",
            *[f"- {item}" for item in ALLOWED_RESPONSE_MENU],
            f"Permitted action class: {focus.permitted_action_class or 'proposal_only'}",
            "The model proposes only. The host gates actions and commits state.",
        ]
    )


def _candidate_dispositions(
    state: EpisodeState,
    focus: CurrentFocus,
    address_maps: dict[str, AddressMap],
    summaries: dict[str, SummaryNode],
) -> list[dict[str, str]]:
    dispositions: list[dict[str, str]] = []
    for artifact_id, artifact_state in state.artifacts.items():
        target_address_missing = (
            artifact_id == focus.active_artifact_ref
            and bool(focus.active_address)
            and resolve_address(address_maps, focus.active_address or "") is None
        )
        if target_address_missing:
            disposition = "block_if_missing"
            reason = "active_address_missing_from_map"
        elif artifact_id == focus.active_artifact_ref and focus.exact_window_refs:
            disposition = "show_exact"
            reason = focus.reason_code.value
        elif artifact_id == focus.active_artifact_ref:
            disposition = "show_card"
            reason = "active_artifact_summary"
        elif artifact_id in summaries:
            disposition = "available_by_handle"
            reason = "available_summary"
        else:
            disposition = "omit"
            reason = "not_selected"
        dispositions.append(
            {
                "candidate_ref": artifact_id,
                "path_or_name": artifact_state.path_or_name,
                "disposition": disposition,
                "reason_code": reason,
                "address_map_ref": artifact_state.address_map_ref or "",
            }
        )
    return dispositions
