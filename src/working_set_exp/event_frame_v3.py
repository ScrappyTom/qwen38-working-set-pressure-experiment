from __future__ import annotations

from typing import Any

from .event_frame import BODY_FIELDS
from .event_frame_v2 import ACTION_PAYLOAD_FIELDS
from .jsonutil import canonical_json_bytes, sha256_bytes


RESULT_BODY_FIELDS = frozenset({*BODY_FIELDS, "action_payload"})
CANONICAL_REOPEN_ACTIONS = frozenset({"reopen_observation", "reopen_result", "reopen_event"})


def canonical_result_source(action: dict[str, Any], *, sequence: int) -> dict[str, Any]:
    """Return the exact source address for an event's bulky result fields.

    A reopen is an access event, not a new payload.  Its result therefore points
    back to the address the actor selected.  Other results receive the stable
    sequence-bound RES address created for that original result.
    """
    name = action.get("action")
    if name in CANONICAL_REOPEN_ACTIONS:
        handle = action.get("handle")
        if not isinstance(handle, str):
            raise ValueError("reopen action lacks its exact source handle")
        return {"access": name, "handle": handle, "origin": "preexisting_exact_payload"}
    return {
        "access": "reopen_result",
        "handle": f"RES-{sequence:04d}",
        "origin": "event_result",
    }


def _payload_record(
    values: dict[str, Any],
    *,
    residency: str,
    source: dict[str, Any] | None,
) -> dict[str, Any]:
    if residency not in {"resident", "external", "none"}:
        raise ValueError("invalid event payload residency")
    present = bool(values)
    if not present and residency != "none":
        raise ValueError("absent payload must use none residency")
    if present and residency == "none":
        raise ValueError("present payload cannot use none residency")
    if present != (source is not None):
        raise ValueError("payload source presence differs")
    raw = canonical_json_bytes(values)
    return {
        "present": present,
        "field_names": sorted(values),
        "residency": residency,
        "size_bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "canonical_source": source,
        "fields": values if residency == "resident" else None,
    }


def event_from_pair_v3(
    action: dict[str, Any],
    result: dict[str, Any],
    *,
    sequence: int,
    payload_residency: str,
) -> dict[str, Any]:
    """Build one ordered event while preserving canonical payload provenance."""
    if payload_residency not in {"resident", "external"}:
        raise ValueError("invalid event payload residency")
    if sequence < 1:
        raise ValueError("event sequence is invalid")
    event_handle = f"EVT-{sequence:04d}"
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
            source={"access": "reopen_event", "handle": event_handle, "origin": "event_action"}
            if action_payload
            else None,
        ),
        "result": result_signal,
        "result_body": _payload_record(
            result_body,
            residency=payload_residency if result_body else "none",
            source=canonical_result_source(action, sequence=sequence) if result_body else None,
        ),
        "exact_pair_identity": {"size_bytes": len(pair), "sha256": sha256_bytes(pair)},
    }


def resident_pair_v3(event: dict[str, Any]) -> dict[str, Any]:
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


def verify_event_sequence_v3(events: list[dict[str, Any]]) -> dict[str, Any]:
    resident = external = canonical_reuses = 0
    for expected, event in enumerate(events, 1):
        if event["sequence"] != expected or event["event_handle"] != f"EVT-{expected:04d}":
            raise ValueError("event sequence is not contiguous")
        action_name = event["action"].get("action")
        for name, payload in (("action", event["action_payload"]), ("result", event["result_body"])):
            fields = payload["fields"]
            source = payload["canonical_source"]
            if payload["present"]:
                if not isinstance(source, dict) or set(source) != {"access", "handle", "origin"}:
                    raise ValueError(f"{name} payload canonical source differs")
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
            elif payload["residency"] != "none" or fields is not None or source is not None:
                raise ValueError("absent payload record differs")
        if event["result_body"]["present"]:
            expected_source = canonical_result_source(
                {**event["action"], **(event["action_payload"]["fields"] or {})},
                sequence=expected,
            )
            if event["result_body"]["canonical_source"] != expected_source:
                raise ValueError("result payload canonical source differs")
            canonical_reuses += int(action_name in CANONICAL_REOPEN_ACTIONS)
        if not event["action_payload"]["present"] or event["action_payload"]["residency"] == "resident":
            if not event["result_body"]["present"] or event["result_body"]["residency"] == "resident":
                resident_pair_v3(event)
    return {
        "verified": True,
        "event_count": len(events),
        "resident_payload_records": resident,
        "external_payload_records": external,
        "canonical_payload_reuse_events": canonical_reuses,
        "signal_contract": {
            "opaque_handle_is_not_the_progress_signal": True,
            "reopen_is_access_not_new_payload": True,
            "resident_action_fields": "all action fields except old/new",
            "resident_result_fields": "all result fields except exact body fields",
        },
    }


def capture_original_result_payload(
    action: dict[str, Any],
    result: dict[str, Any],
    *,
    sequence: int,
    result_reopenable: dict[str, bytes],
) -> str:
    """Capture a new exact result once; reopen events retain their source ID."""
    source = canonical_result_source(action, sequence=sequence)
    if source["origin"] == "event_result":
        handle = source["handle"]
        raw = canonical_json_bytes(result)
        existing = result_reopenable.get(handle)
        if existing is not None and existing != raw:
            raise ValueError("canonical result handle collision")
        result_reopenable[handle] = raw
    return source["handle"]
