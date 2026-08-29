from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _rows(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    rows: list[tuple[Path, dict[str, Any]]] = []
    for path in root.rglob("records.jsonl"):
        for raw in path.read_bytes().splitlines():
            if raw.strip():
                rows.append((path, json.loads(raw)))
    return rows


def snapshot(root: Path) -> dict[str, Any]:
    if not root.is_dir():
        raise FileNotFoundError(root)
    rows = _rows(root)
    prepared = [item for item in rows if item[1].get("record_type") == "external_call_prepared"]
    completed = [item for item in rows if item[1].get("record_type") == "action_result"]
    resolved = [
        item for item in rows
        if item[1].get("record_type") in {"action_result", "external_call_stopped", "capacity_stopped"}
    ]
    latest = max(rows, key=lambda item: item[1].get("created_at_utc", "")) if rows else None
    latest_prepared = max(prepared, key=lambda item: item[1].get("created_at_utc", "")) if prepared else None
    prepared_call = latest_prepared[1].get("payload", {}).get("call_id") if latest_prepared else None
    resolved_calls = {item[1].get("payload", {}).get("call_id") for item in resolved}
    in_flight = prepared_call if prepared_call not in resolved_calls else None
    receipt_path = root / "RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.is_file() else None
    return {
        "schema_version": "global-live-run-monitor-v1",
        "root": str(root.resolve()),
        "receipt_status": receipt.get("status") if receipt else None,
        "record_chain_count": len(rows),
        "prepared_invocations_seen": len(prepared),
        "resolved_invocations_seen": len(resolved),
        "completed_actions_seen": len(completed),
        "latest_record": None if latest is None else {
            "records_path": latest[0].relative_to(root).as_posix(),
            "created_at_utc": latest[1].get("created_at_utc"),
            "record_type": latest[1].get("record_type"),
            "run_id": latest[1].get("run_id"),
            "call_id": latest[1].get("payload", {}).get("call_id"),
            "record_sha256": latest[1].get("record_sha256"),
        },
        "in_flight_prepared_call_id": in_flight,
        "interpretation": (
            "one globally latest prepared invocation has no terminal action, transport-stop, or capacity-stop record"
            if in_flight else "no unmatched globally latest prepared invocation"
        ),
        "operator_rule": "never interrupt from a cell-scoped file count; inspect global record progress and the owned server first",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only global progress view for a measured live-run evidence root.")
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(snapshot(args.root), indent=2))


if __name__ == "__main__":
    main()
