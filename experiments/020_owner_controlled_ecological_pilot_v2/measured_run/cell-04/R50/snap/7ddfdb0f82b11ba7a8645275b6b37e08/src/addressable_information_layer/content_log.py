"""Append-only exact content log for the offline workbench."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .hashing import canonical_json, sha256_text
from .records import BlobRecord, Layer0Event


@dataclass
class ContentLog:
    """Small in-memory content-addressed log.

    v0.1 keeps the store in memory so tests and fixtures stay simple. The IDs
    are stable enough to support receipts and replay within an audit run.
    """

    blobs: dict[str, str] = field(default_factory=dict)
    blob_records: dict[str, BlobRecord] = field(default_factory=dict)
    events: list[Layer0Event] = field(default_factory=list)

    def append_blob(self, text: str, media_type: str = "text/plain", name: str | None = None) -> BlobRecord:
        data = text.encode("utf-8")
        digest = sha256_text(text)
        blob_ref = f"blob:{digest}"
        record = BlobRecord(
            blob_ref=blob_ref,
            sha256=digest,
            media_type=media_type,
            size_bytes=len(data),
            name=name,
        )
        self.blobs[blob_ref] = text
        self.blob_records[blob_ref] = record
        return record

    def append_event(
        self,
        kind: str,
        payload: dict[str, Any],
        actor: str = "host",
        refs: list[str] | None = None,
    ) -> Layer0Event:
        refs = refs or []
        seq = len(self.events) + 1
        payload_hash = sha256_text(canonical_json(payload))
        event_ref = f"event:{seq:06d}:{payload_hash[:12]}"
        event = Layer0Event(
            event_ref=event_ref,
            seq=seq,
            kind=kind,
            actor=actor,
            payload=payload,
            payload_hash=payload_hash,
            refs=refs,
        )
        self.events.append(event)
        return event

    @property
    def head_ref(self) -> str | None:
        if not self.events:
            return None
        return self.events[-1].event_ref

    def read_blob(self, blob_ref: str) -> str:
        return self.blobs[blob_ref]

