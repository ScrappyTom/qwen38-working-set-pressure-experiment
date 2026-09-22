"""Read-only reconciliation of frozen E019/E020 custody; no project imports.

Writes only ENTRY_INVENTORY.json beside this script. It does not execute a
checker, model, tokenizer, runtime, preparation path, or historical harness.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = "src/addressable_information_layer/"
E19_READS = {
    "E19-SOURCE-REOPEN": ["artifact_units.py", "reopen.py", "records.py", "hashing.py"],
    "E19-OBS-SUMMARY-GRAPH": ["summary_graph.py", "summaries.py", "records.py", "policy.py"],
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path):
    return json.loads(path.read_bytes())


def binding(path: Path) -> dict:
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": digest(data), "size_bytes": len(data)}


def candidate_rows(path: Path) -> list[dict]:
    return [
        {"path": p.relative_to(path).as_posix(), "sha256": digest(p.read_bytes()), "size_bytes": p.stat().st_size}
        for p in sorted(path.rglob("*")) if p.is_file()
    ]


def candidate_id(rows: list[dict]) -> str:
    return digest(json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def main() -> None:
    entries = []
    experiments = []
    for name in ("019_owner_controlled_ecological_pilot", "020_owner_controlled_ecological_pilot_v2"):
        exp = ROOT / "experiments" / name
        bank = exp / "fresh_bank"
        manifest = read(bank / "BANK_MANIFEST.json")
        for row in manifest["files"]:
            actual = binding(bank / row["path"])
            assert (actual["sha256"], actual["size_bytes"]) == (row["sha256"], row["size_bytes"])
        actual_bank = sorted(p.relative_to(bank).as_posix() for p in bank.rglob("*") if p.is_file() and p.name != "BANK_MANIFEST.json")
        assert actual_bank == sorted(row["path"] for row in manifest["files"])
        schedule = read(exp / "SCHEDULE.json")
        experiments.append({"experiment": name, "bank": binding(bank / "BANK_MANIFEST.json"),
                            "verified_bank_files": len(actual_bank), "bank_id": manifest["bank_id"],
                            "schedule": schedule, "runtime_profile": binding(exp / "RUNTIME_PROFILE.json")})
        for fixture_id in schedule["cases"]:
            fixture_path = bank / "execution_only" / fixture_id / "FIXTURE.json"
            fixture = read(fixture_path)
            visible = bank / "model_visible" / fixture_id
            rows = candidate_rows(visible / "candidate")
            assert rows == fixture["candidate_files"]
            assert candidate_id(rows) == fixture["candidate_id"]
            cells = [cell for cell in schedule["cells"] if cell["fixture_id"] == fixture_id]
            exposure = []
            for cell in cells:
                cell_path = exp / "measured_run" / f"cell-{cell['ordinal']:02d}"
                segments = []
                for segment in ("shared", "R50", "X25"):
                    folder = cell_path / segment
                    responses = sorted((folder / "transcript").glob("*-endpoint-response.json"))
                    results = sorted((folder / "transcript").glob("*-result.json"))
                    summary = read(folder / "SUMMARY.json") if (folder / "SUMMARY.json").exists() else None
                    if not responses and summary is None:
                        continue
                    facts = {"segment": segment, "saved_responses": len(responses), "saved_results": len(results),
                             "summary_path": binding(folder / "SUMMARY.json") if summary is not None else None,
                             "summary": summary, "terminal_artifact": None}
                    if summary is not None:
                        snapshot = folder / "snap" / summary["candidate_id"][:32]
                        assert snapshot.exists(), snapshot
                        if snapshot.exists():
                            final_rows = candidate_rows(snapshot)
                            assert candidate_id(final_rows) == summary["candidate_id"]
                            old = {row["path"]: row for row in rows}
                            changed = [row for row in final_rows if row != old.get(row["path"])]
                            facts["terminal_artifact"] = {"path": snapshot.relative_to(ROOT).as_posix(),
                                                           "candidate_id": summary["candidate_id"],
                                                           "verified_file_count": len(final_rows), "changed_files": changed}
                    segments.append(facts)
                exposure.append({**cell, "segments": segments})
            required = fixture.get("required_inspection_paths", [PREFIX + p for p in E19_READS.get(fixture_id, [])])
            inspection_bytes = sum(row["size_bytes"] for row in rows if row["path"] in required)
            entries.append({"fixture_id": fixture_id, "experiment": name, "family": fixture["family"],
                            "task": binding(visible / "TASK.txt"), "fixture": binding(fixture_path),
                            "candidate_id": fixture["candidate_id"], "candidate_path": (visible / "candidate").relative_to(ROOT).as_posix(),
                            "candidate_files": rows, "candidate_total_bytes": sum(row["size_bytes"] for row in rows),
                            "required_inspection_paths": required, "required_source_bytes": inspection_bytes,
                            "inspection_wording": "exact complete reads before first mutation" if name.startswith("020") else "inspect exact current source before mutation",
                            "public_checker": binding(bank / "execution_only" / fixture_id / "public.py"),
                            "hidden_checker": binding(bank / "evaluator_only" / fixture_id / "hidden.py"),
                            "observations": [{**o, "body": binding(bank / "execution_only" / fixture_id / "observations" / (o["handle"] + ".json"))} for o in fixture["observations"]],
                            "provenance": fixture["provenance"], "historical_cells": exposure,
                            "new_host_status": "not prepared or executed by this reconciliation"})
    result = {"schema": "ecological-entry-reconciliation-v1", "scope": "CPU read/hash reconciliation only; not full historical seal verification or new grading",
              "script": binding(Path(__file__)), "checker_executions": 0, "model_calls": 0, "runtime_launches": 0,
              "experiments": experiments, "entries": entries}
    destination = HERE / "ENTRY_INVENTORY.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"entries": len(entries), "verified_bank_files": sum(e["verified_bank_files"] for e in experiments),
                      "verified_initial_candidates": len(entries), "output": destination.relative_to(ROOT).as_posix()}))


if __name__ == "__main__":
    main()
