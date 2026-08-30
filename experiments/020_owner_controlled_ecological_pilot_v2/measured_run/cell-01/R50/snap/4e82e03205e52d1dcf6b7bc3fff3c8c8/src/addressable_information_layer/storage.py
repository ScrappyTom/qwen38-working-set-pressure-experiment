"""Persist offline audit outputs to a directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from .availability import build_availability_audit, render_markdown_report
from .serialization import to_plain

if TYPE_CHECKING:
    from .runner import FixtureRunResult


def write_run_result(result: "FixtureRunResult", output_dir: str | Path) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "audit_report.json", result.audit_report)
    _write_json(root / "context_receipts.json", result.context_receipts)
    _write_json(root / "transition_receipts.json", result.transition_receipts)
    _write_json(root / "readiness_decisions.json", result.readiness_decisions)
    _write_json(root / "state_deltas.json", result.state_deltas)
    _write_json(root / "reopen_receipts.json", result.reopen_receipts)
    _write_json(root / "patch_previews.json", result.patch_previews)
    _write_json(root / "apply_receipts.json", result.apply_receipts)
    _write_json(root / "verifier_receipts.json", result.verifier_receipts)
    _write_json(root / "decompositions.json", result.decompositions)
    _write_json(root / "rejection_routes.json", result.rejection_routes)
    _write_json(root / "artifacts.json", result.artifacts)
    _write_json(root / "address_maps.json", result.address_maps)
    _write_json(root / "summaries.json", result.summaries)
    _write_json(root / "summary_graph.json", result.summary_graph)
    _write_json(root / "summary_graph_status.json", result.summary_graph_status)
    _write_json(root / "episode_state.json", result.state)
    _write_json(root / "availability_audit.json", build_availability_audit(result))
    (root / "audit_summary.md").write_text(render_markdown_report(result), encoding="utf-8")

    prompts_dir = root / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    for index, prompt in enumerate(result.prompts, start=1):
        (prompts_dir / f"model_call_{index:04d}.txt").write_text(prompt, encoding="utf-8")

    blobs_dir = root / "blobs"
    blobs_dir.mkdir(exist_ok=True)
    for blob_ref, text in result.log.blobs.items():
        safe_name = blob_ref.replace(":", "_")
        (blobs_dir / f"{safe_name}.txt").write_text(text, encoding="utf-8")

    events_path = root / "layer0_events.jsonl"
    with events_path.open("w", encoding="utf-8") as handle:
        for event in result.log.events:
            handle.write(json.dumps(to_plain(event), sort_keys=True) + "\n")
    return root


def _write_json(path: Path, value) -> None:
    path.write_text(json.dumps(to_plain(value), indent=2, sort_keys=True), encoding="utf-8")
