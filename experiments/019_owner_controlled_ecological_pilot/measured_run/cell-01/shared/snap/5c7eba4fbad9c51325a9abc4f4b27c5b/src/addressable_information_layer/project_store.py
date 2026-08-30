"""Persistent offline session store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from .hashing import stable_id
from .serialization import to_plain
from .storage import write_run_result

if TYPE_CHECKING:
    from .runner import FixtureRunResult


class ProjectStore:
    """File-backed session store for repeated offline audit runs."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.sessions_dir = self.root / "sessions"
        self.sessions_dir.mkdir(exist_ok=True)
        self.manifest_path = self.root / "manifest.jsonl"

    def save(self, result: "FixtureRunResult", *, label: str | None = None) -> Path:
        session_id = stable_id(
            "session",
            {
                "episode": result.audit_report.episode_id,
                "report": result.audit_report.report_id,
                "label": label,
            },
        )
        session_dir = self.sessions_dir / session_id
        write_run_result(result, session_dir)
        entry = {
            "session_id": session_id,
            "label": label,
            "episode_id": result.audit_report.episode_id,
            "report_id": result.audit_report.report_id,
            "passed": result.audit_report.passed,
            "path": str(session_dir),
        }
        with self.manifest_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
        return session_dir

    def list_sessions(self) -> list[dict]:
        if not self.manifest_path.exists():
            return []
        sessions = []
        with self.manifest_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    sessions.append(json.loads(line))
        return sessions

    def load_report(self, session_id: str) -> dict:
        report_path = self.sessions_dir / session_id / "audit_report.json"
        return json.loads(report_path.read_text(encoding="utf-8"))
