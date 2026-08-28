from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .candidate import Candidate
from .jsonutil import load_json_strict, sha256_bytes


@dataclass(frozen=True)
class Fixture:
    fixture_id: str
    family: str
    task: str
    initial: Candidate
    prefork_checker: bytes
    public_checker: bytes
    required_full_reads: tuple[str, ...]
    final_target: str
    probe_id: str | None
    probe_body: str | None


def load_fixture(root: Path, fixture_id: str) -> Fixture:
    base = root / "model_visible" / fixture_id
    execution = root / "execution_only" / fixture_id
    manifest = load_json_strict((execution / "FIXTURE.json").read_bytes())
    if manifest["fixture_id"] != fixture_id:
        raise ValueError("fixture identity differs")
    files: dict[str, bytes] = {}
    candidate_root = base / "candidate"
    for row in manifest["candidate_files"]:
        data = (candidate_root / Path(*row["path"].split("/"))).read_bytes()
        if len(data) != row["size_bytes"] or sha256_bytes(data) != row["sha256"]:
            raise ValueError("fixture candidate file identity differs")
        files[row["path"]] = data
    initial = Candidate.create(files)
    if initial.candidate_id != manifest["initial_candidate_id"]:
        raise ValueError("fixture candidate identity differs")
    task = (base / "TASK.txt").read_text(encoding="utf-8")
    prefork = (execution / "checks" / "prefork.py").read_bytes()
    public = (execution / "checks" / "public.py").read_bytes()
    probe_path = execution / "PROBE.txt"
    probe_body = probe_path.read_text(encoding="utf-8") if probe_path.exists() else None
    if (probe_body is not None) != manifest["probe_body_present"]:
        raise ValueError("fixture probe presence differs")
    expected_probe_sha256 = manifest["probe_body_sha256"]
    if probe_body is not None and sha256_bytes(probe_body.encode("utf-8")) != expected_probe_sha256:
        raise ValueError("fixture probe identity differs")
    return Fixture(
        fixture_id=fixture_id,
        family=manifest["family"],
        task=task,
        initial=initial,
        prefork_checker=prefork,
        public_checker=public,
        required_full_reads=tuple(manifest["required_full_reads"]),
        final_target=manifest["final_target"],
        probe_id=manifest["probe_id"],
        probe_body=probe_body,
    )


def load_truth(root: Path, fixture_id: str) -> dict[str, Any]:
    return load_json_strict((root / "evaluator_only" / fixture_id / "TRUTH.json").read_bytes())
