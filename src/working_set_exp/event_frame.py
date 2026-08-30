from __future__ import annotations

from typing import Any

from .jsonutil import canonical_json_bytes, sha256_bytes


BODY_FIELDS = frozenset(
    {
        "content",
        "diff",
        "entries",
        "exact_result_utf8",
        "matches",
        "observation",
        "stderr",
        "stdout",
    }
)


def event_from_pair(
    action: dict[str, Any],
    result: dict[str, Any],
    *,
    sequence: int,
    handle: str,
    body_residency: str,
) -> dict[str, Any]:
    """Represent one action/result once while allowing exact bodies to leave context."""
    if body_residency not in {"resident", "external"}:
        raise ValueError("invalid event-body residency")
    if sequence < 1 or handle != f"RES-{sequence:04d}":
        raise ValueError("event identity differs from monotonic sequence")
    body = canonical_json_bytes(result)
    structural = {key: value for key, value in result.items() if key not in BODY_FIELDS}
    body_values = {key: value for key, value in result.items() if key in BODY_FIELDS}
    return {
        "sequence": sequence,
        "action": action,
        "result": structural,
        "result_body": {
            "residency": body_residency,
            "handle": handle,
            "size_bytes": len(body),
            "sha256": sha256_bytes(body),
            "fields": body_values if body_residency == "resident" else None,
        },
    }


def resident_pair(event: dict[str, Any]) -> dict[str, Any]:
    body = event["result_body"]
    if body["residency"] != "resident" or not isinstance(body["fields"], dict):
        raise ValueError("event body is not resident")
    result = {**event["result"], **body["fields"]}
    encoded = canonical_json_bytes(result)
    if len(encoded) != body["size_bytes"] or sha256_bytes(encoded) != body["sha256"]:
        raise ValueError("resident event result identity differs")
    return {"response": event["action"], "result": result}


def verify_event_sequence(events: list[dict[str, Any]]) -> dict[str, Any]:
    resident = external = 0
    for expected, event in enumerate(events, 1):
        if event["sequence"] != expected:
            raise ValueError("event sequence is not contiguous")
        body = event["result_body"]
        if body["handle"] != f"RES-{expected:04d}":
            raise ValueError("event handle is not sequence-bound")
        if body["residency"] == "resident":
            resident_pair(event)
            resident += 1
        elif body["residency"] == "external":
            if body["fields"] is not None:
                raise ValueError("external event exposes result-body fields")
            external += 1
        else:
            raise ValueError("event residency differs")
    return {
        "verified": True,
        "event_count": len(events),
        "resident_body_count": resident,
        "external_body_count": external,
    }
