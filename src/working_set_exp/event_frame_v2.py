from __future__ import annotations

from typing import Any

from .event_frame import BODY_FIELDS
from .jsonutil import canonical_json_bytes, sha256_bytes


ACTION_PAYLOAD_FIELDS = frozenset({"old", "new"})
RESULT_BODY_FIELDS = frozenset({*BODY_FIELDS, "action_payload"})


def _payload_record(
    values: dict[str, Any],
    *,
    residency: str,
    access: str | None,
) -> dict[str, Any]:
    if residency not in {"resident", "external", "none"}:
        raise ValueError("invalid event payload residency")
    present = bool(values)
    if not present and residency != "none":
        raise ValueError("absent payload must use none residency")
    if present and residency == "none":
        raise ValueError("present payload cannot use none residency")
    raw = canonical_json_bytes(values)
    return {
        "present": present,
        "field_names": sorted(values),
        "residency": residency,
        "size_bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "access": access if present else None,
        "fields": values if residency == "resident" else None,
    }


def event_from_pair_v2(
    action: dict[str, Any],
    result: dict[str, Any],
    *,
    sequence: int,
    event_handle: str,
    result_handle: str,
    payload_residency: str,
) -> dict[str, Any]:
    """Keep mechanically useful progress resident and move only bulky payloads."""
    if payload_residency not in {"resident", "external"}:
        raise ValueError("invalid event payload residency")
    if sequence < 1 or event_handle != f"EVT-{sequence:04d}" or result_handle != f"RES-{sequence:04d}":
        raise ValueError("event identity differs from monotonic sequence")
    action_signal = {key: value for key, value in action.items() if key not in ACTION_PAYLOAD_FIELDS}
    action_payload = {key: value for key, value in action.items() if key in ACTION_PAYLOAD_FIELDS}
    result_signal = {key: value for key, value in result.items() if key not in RESULT_BODY_FIELDS}
    result_body = {key: value for key, value in result.items() if key in RESULT_BODY_FIELDS}
    pair = canonical_json_bytes({"response": action, "result": result})
    return {
        "sequence": sequence,
        "event_handle": event_handle,
        "action": action_signal,
        "action_payload": _payload_record(
            action_payload,
            residency=payload_residency if action_payload else "none",
            access="reopen_event" if action_payload else None,
        ),
        "result": result_signal,
        "result_body": {
            **_payload_record(
                result_body,
                residency=payload_residency if result_body else "none",
                access="reopen_result" if result_body else None,
            ),
            "handle": result_handle,
        },
        "exact_pair_identity": {"size_bytes": len(pair), "sha256": sha256_bytes(pair)},
    }


def resident_pair_v2(event: dict[str, Any]) -> dict[str, Any]:
    action_payload = event["action_payload"]
    result_body = event["result_body"]
    if action_payload["present"] and action_payload["residency"] != "resident":
        raise ValueError("event action payload is not resident")
    if result_body["present"] and result_body["residency"] != "resident":
        raise ValueError("event result body is not resident")
    action = {**event["action"], **(action_payload["fields"] or {})}
    result = {**event["result"], **(result_body["fields"] or {})}
    pair = {"response": action, "result": result}
    raw = canonical_json_bytes(pair)
    identity = event["exact_pair_identity"]
    if len(raw) != identity["size_bytes"] or sha256_bytes(raw) != identity["sha256"]:
        raise ValueError("resident exact event identity differs")
    return pair


def verify_event_sequence_v2(events: list[dict[str, Any]]) -> dict[str, Any]:
    resident = external = action_payloads = result_bodies = 0
    for expected, event in enumerate(events, 1):
        if event["sequence"] != expected or event["event_handle"] != f"EVT-{expected:04d}":
            raise ValueError("event sequence is not contiguous")
        if event["result_body"]["handle"] != f"RES-{expected:04d}":
            raise ValueError("result handle is not sequence-bound")
        for payload, expected_access in (
            (event["action_payload"], "reopen_event"),
            (event["result_body"], "reopen_result"),
        ):
            fields = payload["fields"]
            if payload["present"]:
                if payload["access"] != expected_access:
                    raise ValueError("event payload access differs")
                if payload["residency"] == "resident":
                    if not isinstance(fields, dict):
                        raise ValueError("resident payload fields are absent")
                    resident += 1
                elif payload["residency"] == "external":
                    if fields is not None:
                        raise ValueError("external payload fields are resident")
                    external += 1
                else:
                    raise ValueError("present payload residency differs")
            elif payload["residency"] != "none" or fields is not None or payload["access"] is not None:
                raise ValueError("absent payload record differs")
        action_payloads += int(event["action_payload"]["present"])
        result_bodies += int(event["result_body"]["present"])
        if not event["action_payload"]["present"] or event["action_payload"]["residency"] == "resident":
            if not event["result_body"]["present"] or event["result_body"]["residency"] == "resident":
                resident_pair_v2(event)
    return {
        "verified": True,
        "event_count": len(events),
        "resident_payload_records": resident,
        "external_payload_records": external,
        "action_payload_count": action_payloads,
        "result_body_count": result_bodies,
        "signal_contract": {
            "resident_action_fields": "all action fields except old/new",
            "resident_result_fields": "all result fields except exact body fields",
            "opaque_handle_is_not_the_progress_signal": True,
        },
    }


def action_payload_bytes(action: dict[str, Any]) -> bytes:
    return canonical_json_bytes({key: value for key, value in action.items() if key in ACTION_PAYLOAD_FIELDS})


def verify_reopened_action_payload(event: dict[str, Any], reopened: dict[str, Any]) -> dict[str, Any]:
    if not reopened.get("accepted") or reopened.get("handle") != event["event_handle"]:
        raise ValueError("reopened event identity differs")
    payload = reopened.get("action_payload")
    if not isinstance(payload, dict):
        raise ValueError("reopened action payload is absent")
    raw = canonical_json_bytes(payload)
    expected = event["action_payload"]
    if len(raw) != expected["size_bytes"] or sha256_bytes(raw) != expected["sha256"]:
        raise ValueError("reopened action payload hash differs")
    return {"verified": True, "handle": event["event_handle"], "field_names": sorted(payload)}
