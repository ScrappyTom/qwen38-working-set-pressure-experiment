from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, utc_now


@dataclass
class ArtifactStore:
    root: Path

    def put(self, relative: str, data: bytes) -> dict[str, Any]:
        target = self.root / Path(*relative.split("/"))
        if target.exists():
            raise FileExistsError(f"artifact already exists: {relative}")
        atomic_write(target, data)
        return {"path": relative, "size_bytes": len(data), "sha256": sha256_bytes(data)}


class RecordLog:
    def __init__(self, path: Path, run_id: str, *, fixed_created_at_utc: str | None = None):
        if path.exists():
            raise FileExistsError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.run_id = run_id
        self.sequence = 0
        self.previous: str | None = None
        self.fixed_created_at_utc = fixed_created_at_utc

    def append(self, record_type: str, payload: dict[str, Any], artifacts: list[dict[str, Any]]) -> dict[str, Any]:
        self.sequence += 1
        body = {
            "sequence": self.sequence,
            "run_id": self.run_id,
            "record_type": record_type,
            "created_at_utc": self.fixed_created_at_utc or utc_now(),
            "previous_record_sha256": self.previous,
            "payload": payload,
            "artifacts": artifacts,
        }
        digest = sha256_bytes(canonical_json_bytes(body))
        record = {**body, "record_sha256": digest}
        with self.path.open("ab") as handle:
            handle.write(canonical_json_bytes(record) + b"\n")
            handle.flush()
        self.previous = digest
        return record


def verify_records(path: Path, artifact_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    previous: str | None = None
    run_id: str | None = None
    for line_number, raw in enumerate(path.read_bytes().splitlines(), 1):
        record = load_json_strict(raw)
        if not isinstance(record, dict):
            raise ValueError("record is not an object")
        digest = record["record_sha256"]
        body = dict(record)
        body.pop("record_sha256")
        if sha256_bytes(canonical_json_bytes(body)) != digest:
            raise ValueError(f"record hash differs at line {line_number}")
        if record["sequence"] != line_number or record["previous_record_sha256"] != previous:
            raise ValueError("record chain differs")
        run_id = record["run_id"] if run_id is None else run_id
        if record["run_id"] != run_id:
            raise ValueError("record run identity differs")
        for artifact in record["artifacts"]:
            data = (artifact_root / Path(*artifact["path"].split("/"))).read_bytes()
            if len(data) != artifact["size_bytes"] or sha256_bytes(data) != artifact["sha256"]:
                raise ValueError("record artifact identity differs")
        records.append(record)
        previous = digest
    if not records:
        raise ValueError("record log is empty")
    return records
