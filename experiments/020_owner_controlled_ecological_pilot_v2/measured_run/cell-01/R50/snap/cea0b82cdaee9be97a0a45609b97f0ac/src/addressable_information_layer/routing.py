"""Rejection routing for blocked readiness and rejected deltas."""

from __future__ import annotations

from .hashing import stable_id
from .records import (
    DeltaStatus,
    ReadinessDecision,
    ReadinessStatus,
    RejectionRoute,
    RejectionRouteRecord,
    ResponseType,
    StateDelta,
)


def routes_for_transition(decision: ReadinessDecision, deltas: list[StateDelta]) -> list[RejectionRouteRecord]:
    routes: list[RejectionRouteRecord] = []
    if decision.status == ReadinessStatus.BLOCKED:
        routes.append(
            RejectionRouteRecord(
                route_id=stable_id("route", {"decision": decision.decision_id, "route": decision.route.value}),
                route=decision.route,
                reason=decision.reason,
                source_refs=[decision.decision_id],
                next_response_type=_next_response_for_route(decision.route),
            )
        )

    for delta in deltas:
        if delta.status == DeltaStatus.REJECTED:
            route = RejectionRoute.ASK_USER if "done" in delta.reason else RejectionRoute.FIX_ACTION
            routes.append(
                RejectionRouteRecord(
                    route_id=stable_id("route", {"delta": delta.delta_id, "route": route.value}),
                    route=route,
                    reason=delta.reason,
                    source_refs=[delta.delta_id],
                    next_response_type=_next_response_for_route(route),
                )
            )
    return routes


def _next_response_for_route(route: RejectionRoute) -> ResponseType | None:
    if route in {RejectionRoute.REFRESH_OR_REOPEN_CONTEXT, RejectionRoute.REPAIR_MAP_OR_SUMMARY}:
        return ResponseType.REQUEST_EXACT
    if route == RejectionRoute.REDECOMPOSE_TASK:
        return ResponseType.PLAN_NEXT
    if route == RejectionRoute.ASK_USER:
        return ResponseType.ASK_USER
    if route == RejectionRoute.FIX_ACTION:
        return ResponseType.DRAFT_CHANGE
    return None

