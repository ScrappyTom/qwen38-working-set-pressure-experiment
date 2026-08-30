from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable

from .jsonutil import canonical_json_bytes, sha256_bytes


MAX_FILES = 256
MAX_TOTAL_BYTES = 8_000_000
MAX_FILE_BYTES = 24_000
MAX_PATH_BYTES = 160
MAX_LINE_BYTES = 512


class CandidateError(RuntimeError):
    pass


def canonical_path(value: str, *, allow_root: bool = False) -> str:
    if value == "." and allow_root:
        return value
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise CandidateError("path must be a nonempty canonical candidate-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or value != path.as_posix() or any(part in {"", ".", ".."} for part in path.parts):
        raise CandidateError("path must be canonical and remain inside the candidate")
    if len(value.encode("utf-8")) > MAX_PATH_BYTES:
        raise CandidateError("path exceeds byte bound")
    return value


@dataclass(frozen=True)
class Candidate:
    files: tuple[tuple[str, bytes], ...]
    candidate_id: str

    @classmethod
    def create(cls, files: dict[str, bytes]) -> "Candidate":
        if not files or len(files) > MAX_FILES:
            raise CandidateError("candidate file count is outside bounds")
        rows: list[tuple[str, bytes]] = []
        total = 0
        for path, data in sorted(files.items()):
            canonical_path(path)
            if not isinstance(data, bytes) or len(data) > MAX_FILE_BYTES:
                raise CandidateError(f"file exceeds byte bound: {path}")
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise CandidateError(f"file is not UTF-8: {path}") from exc
            for line in text.splitlines():
                if len(line.encode("utf-8")) > MAX_LINE_BYTES:
                    raise CandidateError(f"source line exceeds byte bound: {path}")
            total += len(data)
            rows.append((path, data))
        if total > MAX_TOTAL_BYTES:
            raise CandidateError("candidate total bytes exceed bound")
        identity = sha256_bytes(
            canonical_json_bytes(
                [{"path": path, "sha256": sha256_bytes(data), "size_bytes": len(data)} for path, data in rows]
            )
        )
        return cls(tuple(rows), identity)

    @property
    def file_map(self) -> dict[str, bytes]:
        return dict(self.files)

    def file_sha256(self, path: str) -> str:
        path = canonical_path(path)
        try:
            return sha256_bytes(self.file_map[path])
        except KeyError as exc:
            raise CandidateError("file does not exist") from exc

    def patch(
        self,
        *,
        path: str,
        old: str,
        new: str,
        expected_candidate_id: str,
        expected_file_sha256: str,
    ) -> tuple["Candidate", str]:
        path = canonical_path(path)
        if expected_candidate_id != self.candidate_id:
            raise CandidateError("stale candidate binding")
        data = self.file_map.get(path)
        if data is None:
            raise CandidateError("patch path does not exist")
        if sha256_bytes(data) != expected_file_sha256:
            raise CandidateError("stale file binding")
        if len(old.encode("utf-8")) > 2_000 or len(new.encode("utf-8")) > 2_000:
            raise CandidateError("patch fragment exceeds bound")
        if old == new:
            raise CandidateError("patch must change exact bytes")
        text = data.decode("utf-8")
        if text.count(old) != 1:
            raise CandidateError("old fragment must occur exactly once")
        successor_text = text.replace(old, new, 1)
        successor_files = self.file_map
        successor_files[path] = successor_text.encode("utf-8")
        successor = Candidate.create(successor_files)
        if successor.candidate_id == self.candidate_id:
            raise CandidateError("patch must change candidate identity")
        diff = "".join(
            difflib.unified_diff(
                text.splitlines(keepends=True),
                successor_text.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
        if len(diff.encode("utf-8")) > 6_000:
            raise CandidateError("effective diff exceeds bound")
        return successor, diff

    def directories(self, path: str) -> list[tuple[str, str]]:
        root = "" if path == "." else canonical_path(path)
        prefix = "" if not root else root + "/"
        children: dict[str, str] = {}
        for file_path, _ in self.files:
            if not file_path.startswith(prefix):
                continue
            rest = file_path[len(prefix):]
            if not rest:
                continue
            name = rest.split("/", 1)[0]
            child_path = f"{root}/{name}" if root else name
            children[child_path] = "directory" if "/" in rest else "file"
        return sorted(children.items())

    def with_files(self, rows: Iterable[tuple[str, bytes]]) -> "Candidate":
        return Candidate.create(dict(rows))
