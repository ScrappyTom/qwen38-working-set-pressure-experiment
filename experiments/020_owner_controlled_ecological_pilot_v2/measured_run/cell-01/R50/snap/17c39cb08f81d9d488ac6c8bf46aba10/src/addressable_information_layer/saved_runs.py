"""Saved-run importers for offline audit fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .importers import fixture_from_directory

JSONL_EVENT_NAME_HINTS = (
    "artifact",
    "assembly",
    "controller",
    "event",
    "evidence",
    "layer0",
    "message",
    "plan",
    "provider",
    "receipt",
    "result",
    "run",
    "task_state",
    "tool",
    "trace",
    "usage",
    "view",
)

EMBEDDED_ARTIFACT_RECORD_TYPES = {"artifacts", "evidence"}
MAX_JSONL_BYTES = 2_000_000
MAX_JSONL_LINES = 1000
MAX_EMBEDDED_ARTIFACTS = 80
MAX_EMBEDDED_TEXT_CHARS = 80_000


def fixture_from_saved_run(
    directory: str | Path,
    *,
    kind: str = "auto",
    objective: str | None = None,
) -> dict[str, Any]:
    root = Path(directory).resolve()
    detected = _detect_kind(root) if kind == "auto" else kind
    fixture = fixture_from_directory(root, objective=objective or f"Offline audit for {detected} saved run {root}")
    fixture["saved_run_kind"] = detected
    fixture["events"].extend(_events_from_jsonl(root, detected))
    fixture["artifacts"].extend(_embedded_artifacts_from_jsonl(root))
    return fixture


def _detect_kind(root: Path) -> str:
    names = {path.name.lower() for path in root.rglob("*") if path.is_file()}
    joined = " ".join(sorted(names))
    if "provider" in joined or "prompt" in joined or "working_brief" in joined:
        return "minimalist"
    if "layer0" in joined or "reconstitution" in joined or "spar_harness" in joined:
        return "spar_harness"
    return "generic"


def _events_from_jsonl(root: Path, detected: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.jsonl")):
        if path.stat().st_size > MAX_JSONL_BYTES:
            continue
        if not _looks_like_saved_run_jsonl(path):
            continue
        for idx, item in enumerate(_read_jsonl_lines(path), start=1):
            if idx > MAX_JSONL_LINES:
                break
            event = _event_from_item(item, path, detected)
            if event is not None:
                events.append(event)
    return events


def _event_from_item(item: dict[str, Any], path: Path, detected: str) -> dict[str, Any] | None:
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else item
    record_type = str(item.get("record_type") or "").lower()
    event_type = str(item.get("event_type") or "").lower()
    kind = str(item.get("kind") or item.get("event_kind") or item.get("type") or record_type or event_type or "").lower()
    role = str(item.get("role") or payload.get("role") or "").lower()
    actor = str(item.get("actor") or item.get("actor_kind") or item.get("actor_id") or role or "host")

    if role == "user" or "user" in kind or actor == "user":
        event_kind = "user_instruction"
    elif role == "system":
        event_kind = "system_instruction"
    elif role == "assistant":
        event_kind = "model_response"
    elif role == "tool":
        event_kind = "tool_result"
    elif item.get("event_kind"):
        event_kind = str(item["event_kind"])
    elif event_type in {"request", "response"}:
        event_kind = f"provider_{event_type}"
    elif record_type:
        event_kind = _event_kind_from_record_type(record_type, payload, path)
    elif "verifier" in kind or "test" in kind:
        event_kind = "verifier_result"
    elif "tool" in kind:
        event_kind = "tool_result"
    elif kind:
        event_kind = kind
    else:
        event_kind = _event_kind_from_path(path)
    if event_kind is None:
        return None

    normalized_payload = dict(payload)
    if "content" in item and "content" not in normalized_payload:
        normalized_payload["content"] = item["content"]
    if role and "role" not in normalized_payload:
        normalized_payload["role"] = role
    if "record_id" in item and "record_id" not in normalized_payload:
        normalized_payload["record_id"] = item["record_id"]
    if record_type and "record_type" not in normalized_payload:
        normalized_payload["record_type"] = record_type
    if event_type and "event_type" not in normalized_payload:
        normalized_payload["event_type"] = event_type
    return {
        "kind": event_kind,
        "actor": actor,
        "payload": {
            "saved_run_kind": detected,
            "source_file": str(path),
            **normalized_payload,
        },
    }


def _event_kind_from_record_type(record_type: str, payload: dict[str, Any], path: Path) -> str:
    if record_type == "artifacts":
        artifact_kind = str(payload.get("artifact_kind") or "").lower()
        if artifact_kind in {"provider_request", "provider_response"}:
            return f"{artifact_kind}_artifact"
        return "artifact_record"
    if record_type == "provider_io":
        return "provider_io_record"
    if record_type == "evidence":
        nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
        if nested.get("tool_name"):
            return "tool_result"
        return "evidence_record"
    if record_type == "task_states":
        return "task_state"
    if record_type == "views":
        return "view_record"
    if record_type == "receipts":
        return "receipt_record"
    if record_type == "plan_candidates":
        return "plan_candidate"
    return _event_kind_from_path(path) or record_type


def _event_kind_from_path(path: Path) -> str | None:
    lower = path.name.lower()
    if "assembly_receipt" in lower:
        return "reconstitution_receipt"
    if "usage_record" in lower:
        return "usage_record"
    if "tool_result" in lower:
        return "tool_result"
    if "tool_call" in lower:
        return "tool_call"
    if "tool_execution" in lower:
        return "tool_execution"
    if "controller" in lower:
        return "controller_event"
    if "message" in lower:
        return "message"
    if "provider" in lower:
        return "provider_io_record"
    if "receipt" in lower:
        return "receipt_record"
    if "evidence" in lower:
        return "evidence_record"
    if "view" in lower:
        return "view_record"
    if "task_state" in lower:
        return "task_state"
    if "plan" in lower:
        return "plan_candidate"
    if "run" in lower:
        return "run_record"
    if "event" in lower or "layer0" in lower:
        return "event"
    return None


def _embedded_artifacts_from_jsonl(root: Path) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.jsonl")):
        if len(artifacts) >= MAX_EMBEDDED_ARTIFACTS:
            break
        if path.stat().st_size > MAX_JSONL_BYTES:
            continue
        if not _looks_like_saved_run_jsonl(path):
            continue
        for idx, item in enumerate(_read_jsonl_lines(path), start=1):
            if idx >= MAX_JSONL_LINES or len(artifacts) >= MAX_EMBEDDED_ARTIFACTS:
                break
            embedded = _embedded_artifact_from_item(item, path, idx)
            if embedded is not None:
                artifacts.append(embedded)
    return artifacts


def _embedded_artifact_from_item(item: dict[str, Any], path: Path, line_number: int) -> dict[str, Any] | None:
    record_type = str(item.get("record_type") or "").lower()
    if record_type not in EMBEDDED_ARTIFACT_RECORD_TYPES:
        return None
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
    if record_type == "artifacts":
        if payload.get("content_available") is False or "content" not in payload:
            return None
        name = str(payload.get("artifact_ref") or item.get("record_id") or f"{path.stem}_{line_number}")
        kind = str(payload.get("artifact_kind") or "artifact")
        text = _stringify_embedded_content(payload.get("content"))
        suffix = ".json" if text.lstrip().startswith(("{", "[")) else ".txt"
        return {
            "kind": "json" if suffix == ".json" else "text",
            "path_or_name": f"embedded/{name}_{kind}{suffix}",
            "text": _truncate_embedded_text(text),
        }
    nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    content = nested.get("content")
    if not isinstance(content, str) or not content:
        return None
    name = str(payload.get("evidence_id") or item.get("record_id") or f"{path.stem}_{line_number}")
    return {
        "kind": "text",
        "path_or_name": f"embedded/{name}_evidence.txt",
        "text": _truncate_embedded_text(content),
    }


def _stringify_embedded_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, indent=2, sort_keys=True)


def _truncate_embedded_text(text: str) -> str:
    if len(text) <= MAX_EMBEDDED_TEXT_CHARS:
        return text
    return text[:MAX_EMBEDDED_TEXT_CHARS] + "\n[truncated saved-run embedded artifact]"


def _looks_like_saved_run_jsonl(path: Path) -> bool:
    lower = path.name.lower()
    return any(token in lower for token in JSONL_EVENT_NAME_HINTS)


def _read_jsonl_lines(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            items.append(item)
    return items
