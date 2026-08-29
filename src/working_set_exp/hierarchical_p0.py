from __future__ import annotations

import ast
from pathlib import PurePosixPath
from typing import Any

from .candidate import Candidate, canonical_path
from .jsonutil import canonical_json_bytes
from .p0 import P0Error, _signature


MAX_ROOT_BYTES = 6_000
MAX_PAGE_BYTES = 12_000
MAX_PAGE_ROWS = 24


def _top_level(candidate: Candidate) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for path, data in candidate.files:
        first = PurePosixPath(path).parts[0]
        row = grouped.setdefault(first, {"path": first, "kind": "directory", "file_count": 0, "total_bytes": 0})
        row["file_count"] += 1
        row["total_bytes"] += len(data)
        if "/" not in path:
            row["kind"] = "file"
    return [grouped[key] for key in sorted(grouped)]


def build_p0_root(candidate: Candidate) -> dict[str, Any]:
    value = {
        "schema_version": "p0-readable-hierarchical-root-v1",
        "candidate_id": candidate.candidate_id,
        "task_independent": True,
        "complete_for_top_level": True,
        "complete_for_repository": False,
        "ranking": None,
        "access": "p0_page",
        "entries": _top_level(candidate),
    }
    if len(canonical_json_bytes(value)) > MAX_ROOT_BYTES:
        raise P0Error("hierarchical P0 root exceeds byte bound")
    return value


def _symbols(path: str, data: bytes) -> list[dict[str, Any]]:
    if not path.endswith(".py"):
        return []
    try:
        module = ast.parse(data.decode("utf-8"), filename=path)
    except (SyntaxError, UnicodeDecodeError) as exc:
        raise P0Error(f"Python file is not parseable: {path}") from exc
    rows: list[dict[str, Any]] = []
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            signature = _signature(node)
            if len(signature.encode("utf-8")) > 240:
                raise P0Error("signature exceeds bound")
            rows.append({
                "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                "name": node.name,
                "signature": signature,
                "start_line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
            })
    return rows


def p0_page(candidate: Candidate, *, path: str, offset: int) -> dict[str, Any]:
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise P0Error("P0 offset invalid")
    if path == ".":
        rows = _top_level(candidate)
        kind = "root"
    else:
        path = canonical_path(path)
        data = candidate.file_map.get(path)
        if data is not None:
            rows = _symbols(path, data)
            kind = "file_outline"
        else:
            children = candidate.directories(path)
            rows = []
            for child, child_kind in children:
                if child_kind == "file":
                    child_data = candidate.file_map[child]
                    rows.append({
                        "path": child,
                        "kind": "file",
                        "size_bytes": len(child_data),
                        "symbol_count": len(_symbols(child, child_data)),
                    })
                else:
                    prefix = child + "/"
                    descendants = [(p, d) for p, d in candidate.files if p.startswith(prefix)]
                    rows.append({
                        "path": child,
                        "kind": "directory",
                        "file_count": len(descendants),
                        "total_bytes": sum(len(d) for _, d in descendants),
                    })
            kind = "directory"
    page: list[dict[str, Any]] = []
    for row in rows[offset:offset + MAX_PAGE_ROWS]:
        prospective = {
            "accepted": True,
            "path": path,
            "kind": kind,
            "offset": offset,
            "total_entries": len(rows),
            "next_offset": None,
            "entries": [*page, row],
            "candidate_id": candidate.candidate_id,
        }
        if len(canonical_json_bytes(prospective)) > MAX_PAGE_BYTES:
            break
        page.append(row)
    if offset < len(rows) and not page:
        raise P0Error("one P0 row cannot fit the page bound")
    next_offset = offset + len(page) if offset + len(page) < len(rows) else None
    return {
        "accepted": True,
        "path": path,
        "kind": kind,
        "offset": offset,
        "total_entries": len(rows),
        "next_offset": next_offset,
        "entries": page,
        "candidate_id": candidate.candidate_id,
    }
