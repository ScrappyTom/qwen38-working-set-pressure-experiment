"""Stable hashing helpers for records, blobs, and rendered context."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any


def canonical_json(value: Any) -> str:
    """Return stable JSON for hashable record content."""

    def normalize(item: Any) -> Any:
        if isinstance(item, Enum):
            return item.value
        if is_dataclass(item):
            return normalize(asdict(item))
        if isinstance(item, dict):
            return {str(k): normalize(v) for k, v in sorted(item.items(), key=lambda kv: str(kv[0]))}
        if isinstance(item, (list, tuple, set)):
            return [normalize(v) for v in item]
        return item

    return json.dumps(normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_id(prefix: str, value: Any, length: int = 16) -> str:
    return f"{prefix}_{sha256_text(canonical_json(value))[:length]}"

