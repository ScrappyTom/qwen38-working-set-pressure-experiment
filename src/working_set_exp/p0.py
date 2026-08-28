from __future__ import annotations

import ast
from typing import Any

from .candidate import Candidate
from .jsonutil import canonical_json_bytes


MAX_P0_BYTES = 8_000
MAX_SYMBOLS = 48


class P0Error(RuntimeError):
    pass


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> str:
    if isinstance(node, ast.ClassDef):
        bases = ", ".join(ast.unparse(base) for base in node.bases)
        return f"class {node.name}({bases})" if bases else f"class {node.name}"
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    returns = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    return f"{prefix} {node.name}({ast.unparse(node.args)}){returns}"


def build_p0(candidate: Candidate) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    symbol_count = 0
    for path, data in candidate.files:
        symbols: list[dict[str, Any]] = []
        if path.endswith(".py"):
            try:
                module = ast.parse(data.decode("utf-8"), filename=path)
            except (SyntaxError, UnicodeDecodeError) as exc:
                raise P0Error(f"Python file is not parseable: {path}") from exc
            for node in module.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    signature = _signature(node)
                    if len(signature.encode("utf-8")) > 240:
                        raise P0Error("signature exceeds bound")
                    symbols.append(
                        {
                            "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                            "name": node.name,
                            "signature": signature,
                            "start_line": node.lineno,
                            "end_line": getattr(node, "end_lineno", node.lineno),
                        }
                    )
                    symbol_count += 1
        files.append({"path": path, "size_bytes": len(data), "symbols": symbols})
    if symbol_count > MAX_SYMBOLS:
        raise P0Error("symbol count exceeds bound")
    value = {
        "schema_version": "p0-readable-localization-v1",
        "candidate_id": candidate.candidate_id,
        "task_independent": True,
        "ranking": None,
        "fields": ["path", "symbol", "signature", "line_range"],
        "files": files,
    }
    if len(canonical_json_bytes(value)) > MAX_P0_BYTES:
        raise P0Error("P0 projection exceeds byte bound")
    return value
