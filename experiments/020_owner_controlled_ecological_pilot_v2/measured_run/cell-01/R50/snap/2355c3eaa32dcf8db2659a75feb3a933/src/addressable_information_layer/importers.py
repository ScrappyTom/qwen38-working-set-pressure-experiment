"""Offline import helpers for local artifact directories."""

from __future__ import annotations

from pathlib import Path
from typing import Any


TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".markdown",
    ".txt",
    ".log",
    ".json",
    ".jsonl",
    ".csv",
    ".tsv",
    ".rst",
    ".yaml",
    ".yml",
    ".toml",
    ".html",
    ".htm",
}

DEFAULT_EXCLUDES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    "build",
    ".ail_runs",
}


def fixture_from_directory(
    directory: str | Path,
    *,
    objective: str | None = None,
    max_files: int = 200,
    max_file_bytes: int = 250_000,
) -> dict[str, Any]:
    root = Path(directory).resolve()
    artifacts: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if _is_excluded(path, root):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if path.stat().st_size >= max_file_bytes:
            continue
        rel = path.relative_to(root).as_posix()
        artifacts.append({"path": rel})
        if len(artifacts) > max_files:
            break

    return {
        "episode_id": f"directory_import_{root.name}",
        "objective": objective or f"Offline information audit for directory {root}",
        "events": [
            {
                "kind": "user_instruction",
                "actor": "user",
                "payload": {"text": objective or f"Audit directory {root}."},
            }
        ],
        "artifacts": artifacts,
        "model_responses": [
            {
                "response_type": "PLAN_NEXT",
                "summary": "Directory imported; inspect artifact map and choose the next exact request.",
            }
        ],
    }


def _is_excluded(path: Path, root: Path) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        return True
    return any(part in DEFAULT_EXCLUDES for part in rel_parts)
