"""Core records for the v0.1 Stateful Episode Workbench."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PlanStepStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    REVIEW_NEEDED = "review_needed"
    VERIFIED = "verified"
    DONE = "done"
    SUPERSEDED = "superseded"


class ArtifactReviewStatus(str, Enum):
    UNINSPECTED = "uninspected"
    MAPPED = "mapped"
    EXACT_WINDOW_ACTIVE = "exact_window_active"
    DRAFTED = "drafted"
    CHANGED = "changed"
    REVIEW_NEEDED = "review_needed"
    VERIFIED = "verified"
    BLOCKED = "blocked"
    STALE = "stale"


class FocusReason(str, Enum):
    EXPLICIT_USER_INSTRUCTION = "explicit_user_instruction"
    UNRESOLVED_BLOCKER = "unresolved_blocker"
    VERIFIER_FAILURE = "verifier_failure"
    STALE_TARGET = "stale_target"
    CURRENT_PLAN_STEP = "current_plan_step"
    LAST_CHANGED_ARTIFACT = "last_changed_artifact"
    MODEL_ASSISTED_PLANNING_NEEDED = "model_assisted_planning_needed"


class StateAuthority(str, Enum):
    DETERMINISTIC = "deterministic"
    MODEL_PROPOSED = "model_proposed"
    VERIFIER_CONFIRMED = "verifier_confirmed"
    OPERATOR_CONFIRMED = "operator_confirmed"


class DeltaStatus(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PROVISIONAL = "provisional"


class ResponseType(str, Enum):
    PLAN_NEXT = "PLAN_NEXT"
    REQUEST_EXACT = "REQUEST_EXACT"
    DRAFT_CHANGE = "DRAFT_CHANGE"
    APPLY_CHANGE = "APPLY_CHANGE"
    REVIEW_RESULT = "REVIEW_RESULT"
    FINAL_ANSWER = "FINAL_ANSWER"
    ASK_USER = "ASK_USER"


class ReadinessStatus(str, Enum):
    READY = "ready"
    BLOCKED = "blocked"


class RejectionRoute(str, Enum):
    NONE = "none"
    FIX_ACTION = "fix_action"
    REFRESH_OR_REOPEN_CONTEXT = "refresh_or_reopen_context"
    REPAIR_MAP_OR_SUMMARY = "repair_map_or_summary"
    REDECOMPOSE_TASK = "redecompose_task"
    ASK_USER = "ask_user"
    STOP_OR_PAUSE = "stop_or_pause"


class ReopenStatus(str, Enum):
    MATERIALIZED = "materialized"
    BLOCKED = "blocked"


class PatchPreviewStatus(str, Enum):
    PREVIEWED = "previewed"
    BLOCKED = "blocked"


class ApplyStatus(str, Enum):
    APPLIED = "applied"
    BLOCKED = "blocked"


class VerifierStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DecompositionStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class InformationNeedClass(str, Enum):
    EXACT_REQUIRED = "exact_required"
    CARD_SUFFICIENT = "card_sufficient"
    HANDLE_SUFFICIENT = "handle_sufficient"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    NEEDS_DECOMPOSITION = "needs_decomposition"


class AcceptanceCriterionClass(str, Enum):
    MECHANICAL = "mechanical"
    SEMANTIC_ADVISORY = "semantic_advisory"
    OPERATOR_REQUIRED = "operator_required"
    UNVERIFIABLE = "unverifiable"


@dataclass(frozen=True)
class BlobRecord:
    blob_ref: str
    sha256: str
    media_type: str
    size_bytes: int
    name: str | None = None


@dataclass(frozen=True)
class Layer0Event:
    event_ref: str
    seq: int
    kind: str
    actor: str
    payload: dict[str, Any]
    payload_hash: str
    refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    kind: str
    path_or_name: str
    version_hash: str
    blob_ref: str
    text: str


@dataclass(frozen=True)
class ArtifactUnit:
    unit_id: str
    artifact_id: str
    address: str
    unit_kind: str
    title: str
    content_hash: str
    exact_ref: str
    start_line: int
    end_line: int
    parent_address: str | None = None
    child_addresses: list[str] = field(default_factory=list)
    inline_text: str | None = None


@dataclass(frozen=True)
class AddressMap:
    map_id: str
    artifact_id: str
    version_hash: str
    units: dict[str, ArtifactUnit]


@dataclass(frozen=True)
class SummaryNode:
    summary_id: str
    artifact_id: str
    input_unit_ids: list[str]
    input_hashes: list[str]
    policy_id: str
    axes: dict[str, Any]
    exact_descents: list[str]
    authoritative: bool = False


@dataclass(frozen=True)
class ArtifactState:
    artifact_id: str
    kind: str
    path_or_name: str
    version_hash: str
    brief_ref: str | None = None
    address_map_ref: str | None = None
    last_touched_address: str | None = None
    known_issues: list[str] = field(default_factory=list)
    open_decisions: list[str] = field(default_factory=list)
    review_status: ArtifactReviewStatus = ArtifactReviewStatus.UNINSPECTED
    exact_window_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CriterionArtifact:
    criterion_id: str
    statement: str
    check_type: str
    status: str = "pending"
    source_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    target_artifact_ref: str | None = None
    target_path: str | None = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    description: str
    status: PlanStepStatus = PlanStepStatus.PENDING
    target_artifact_ref: str | None = None
    target_address: str | None = None
    source_refs: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass(frozen=True)
class PlanState:
    plan_id: str
    steps: list[PlanStep] = field(default_factory=list)


@dataclass(frozen=True)
class Layer1State:
    state_id: str
    constraints: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    attempt_history: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    latest_event_refs: list[str] = field(default_factory=list)
    user_instruction_refs: list[str] = field(default_factory=list)
    verifier_failure_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CurrentFocus:
    focus_id: str
    reason_code: FocusReason
    source_refs: list[str]
    active_artifact_ref: str | None = None
    active_address: str | None = None
    exact_window_refs: list[str] = field(default_factory=list)
    latest_result_refs: list[str] = field(default_factory=list)
    permitted_action_class: str | None = None


@dataclass(frozen=True)
class EpisodeState:
    episode_id: str
    objective: str
    layer0_head_ref: str | None
    layer1: Layer1State
    artifacts: dict[str, ArtifactState] = field(default_factory=dict)
    plan: PlanState | None = None
    criteria: list[CriterionArtifact] = field(default_factory=list)
    current_focus: CurrentFocus | None = None
    latest_context_receipt_ref: str | None = None
    latest_transition_receipt_ref: str | None = None


@dataclass(frozen=True)
class ContextReceipt:
    receipt_id: str
    episode_id: str
    model_call_id: str
    objective_ref: str
    layer1_state_ref: str
    plan_state_ref: str | None
    current_focus_ref: str
    artifact_state_refs: list[str]
    exact_window_refs: list[str]
    latest_event_refs: list[str]
    allowed_response_menu: list[str]
    permitted_action_class: str | None
    prompt_template_version: str
    model_profile_ref: str | None
    output_contract_ref: str | None
    rendered_context_hash: str
    shown_sections: list[str]
    candidate_dispositions: list[dict[str, Any]] = field(default_factory=list)
    information_need_classification: dict[str, Any] = field(default_factory=dict)
    criterion_classifications: list[dict[str, Any]] = field(default_factory=list)
    summary_claim_audit: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ModelResponse:
    response_type: ResponseType
    summary: str
    requested_ref_or_address: str | None = None
    draft: str | None = None
    review_result: str | None = None
    question_for_user: str | None = None
    state_update_proposals: list[dict[str, Any]] = field(default_factory=list)
    support_refs: list[str] = field(default_factory=list)
    reasoning_only: bool = False
    edit_scope: str | None = None
    preview_id: str | None = None
    operator_confirmed: bool = False
    verifier_confirmed: bool = False
    subtargets: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ReadinessDecision:
    decision_id: str
    status: ReadinessStatus
    response_type: ResponseType
    reason: str
    route: RejectionRoute = RejectionRoute.NONE
    required_refs: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReopenReceipt:
    receipt_id: str
    requested_ref_or_address: str
    status: ReopenStatus
    reason: str
    artifact_id: str | None = None
    address: str | None = None
    exact_ref: str | None = None
    version_hash: str | None = None
    content_hash: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    materialized_text: str | None = None
    truncated: bool = False


@dataclass(frozen=True)
class PatchPreview:
    preview_id: str
    status: PatchPreviewStatus
    reason: str
    artifact_id: str | None
    address: str | None
    exact_ref: str | None
    before_hash: str | None
    before_text: str | None
    proposed_text: str | None
    edit_scope: str | None


@dataclass(frozen=True)
class ApplyReceipt:
    receipt_id: str
    status: ApplyStatus
    reason: str
    preview_id: str
    artifact_id: str | None
    address: str | None
    before_hash: str | None
    after_hash: str | None
    new_artifact_id: str | None = None


@dataclass(frozen=True)
class VerifierReceipt:
    receipt_id: str
    criterion_id: str
    status: VerifierStatus
    reason: str
    artifact_id: str | None = None
    evidence_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DecompositionArtifact:
    decomposition_id: str
    status: DecompositionStatus
    parent_objective: str
    subtargets: list[dict[str, Any]]
    source_refs: list[str]
    reason: str


@dataclass(frozen=True)
class StateDelta:
    delta_id: str
    target_state: str
    operation: str
    proposed_value: Any
    source_refs: list[str]
    authority: StateAuthority
    status: DeltaStatus
    reason: str


@dataclass(frozen=True)
class ReducerRun:
    reducer_run_id: str
    reducer_name: str
    reducer_type: str
    input_refs: list[str]
    output_delta_refs: list[str]
    decision: DeltaStatus
    reason: str


@dataclass(frozen=True)
class TransitionReceipt:
    receipt_id: str
    episode_id: str
    model_call_id: str
    context_receipt_ref: str
    model_response_ref: str
    requested_reopen_refs: list[str]
    proposed_action_ref: str | None
    readiness_decision_refs: list[str]
    action_result_ref: str | None
    reducer_run_refs: list[str]
    state_delta_refs: list[str]
    accepted_delta_refs: list[str]
    rejected_delta_refs: list[str]
    next_focus_ref: str | None
    reopen_receipt_refs: list[str] = field(default_factory=list)
    apply_receipt_refs: list[str] = field(default_factory=list)
    decomposition_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RejectionRouteRecord:
    route_id: str
    route: RejectionRoute
    reason: str
    source_refs: list[str]
    next_response_type: ResponseType | None = None


@dataclass(frozen=True)
class AuditReport:
    report_id: str
    episode_id: str
    passed: bool
    findings: list[str]
    failures: list[str]
    context_receipt_refs: list[str]
    transition_receipt_refs: list[str]
    readiness_decision_refs: list[str]
    accepted_delta_refs: list[str]
    rejected_delta_refs: list[str]
    reopen_receipt_refs: list[str] = field(default_factory=list)
    patch_preview_refs: list[str] = field(default_factory=list)
    apply_receipt_refs: list[str] = field(default_factory=list)
    verifier_receipt_refs: list[str] = field(default_factory=list)
    decomposition_refs: list[str] = field(default_factory=list)
    rejection_routes: list[dict[str, Any]] = field(default_factory=list)
