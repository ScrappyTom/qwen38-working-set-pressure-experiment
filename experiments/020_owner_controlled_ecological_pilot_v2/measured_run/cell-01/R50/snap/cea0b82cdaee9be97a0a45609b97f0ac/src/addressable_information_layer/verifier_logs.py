"""Create deterministic verifier events from recorded log artifacts."""

from __future__ import annotations

from .content_log import ContentLog
from .records import Artifact, Layer0Event


FAIL_TOKENS = ("failed", "failure", "error", "traceback", "exception", "assertionerror")
PASS_TOKENS = ("passed", "success", "ok")


def append_verifier_events_from_artifacts(log: ContentLog, artifacts: dict[str, Artifact]) -> list[Layer0Event]:
    events: list[Layer0Event] = []
    for artifact in artifacts.values():
        if artifact.kind not in {"log", "verifier", "transcript"} and not artifact.path_or_name.lower().endswith((".log", ".out", ".err")):
            continue
        lowered = artifact.text.lower()
        if any(token in lowered for token in FAIL_TOKENS):
            status = "failed"
            message = _first_matching_line(artifact.text, FAIL_TOKENS) or "verifier log contains failure token"
        elif any(token in lowered for token in PASS_TOKENS):
            status = "passed"
            message = _first_matching_line(artifact.text, PASS_TOKENS) or "verifier log contains pass token"
        else:
            continue
        events.append(
            log.append_event(
                kind="verifier_result",
                actor="host",
                payload={
                    "status": status,
                    "message": message,
                    "artifact_id": artifact.artifact_id,
                    "path_or_name": artifact.path_or_name,
                },
                refs=[artifact.blob_ref],
            )
        )
    return events


def _first_matching_line(text: str, tokens: tuple[str, ...]) -> str | None:
    for line in text.splitlines():
        lowered = line.lower()
        if any(token in lowered for token in tokens):
            return line.strip()
    return None

