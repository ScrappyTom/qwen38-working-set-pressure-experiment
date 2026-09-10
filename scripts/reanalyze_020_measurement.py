"""Read sealed E020 evidence and write a separate prospective measurement addendum.

This is a mechanical reanalysis, not an automatic direct-transcript review and
not a model run. Never invoke the historical analyzer to overwrite its reports.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

from working_set_exp.candidate import Candidate
from working_set_exp.ecological_pilot_v2 import (
    CASE_IDS, admitted_donor_candidate, hidden_grade, inspection_status, load_fixture, verify_bank,
)
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.measurement import check_opportunity
from working_set_exp.runner import verify_run


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "020_owner_controlled_ecological_pilot_v2"
RUN = EXPERIMENT / "measured_run"
BANK = EXPERIMENT / "fresh_bank"
PROBE = ROOT / "maintenance" / "resume_after_020" / "import_boundary_probe.py"


def read_json(path: Path) -> Any:
    return load_json_strict(path.read_bytes())


def verify_seal() -> dict[str, Any]:
    path = RUN / "RESPONSE_SEAL.json"
    seal = read_json(path)
    for row in seal["files"]:
        item = RUN / row["path"]
        if item.stat().st_size != row["size_bytes"] or sha256_file(item) != row["sha256"]:
            raise ValueError(f"sealed artifact differs: {row['path']}")
    if sha256_bytes(canonical_json_bytes(seal["files"])) != seal["aggregate_sha256"]:
        raise ValueError("response-seal aggregate differs")
    if seal["evaluator_truth_opened"] is not False:
        raise ValueError("response seal does not precede evaluator access")
    return {"file_count": len(seal["files"]), "seal_sha256": sha256_file(path), "aggregate_sha256": seal["aggregate_sha256"]}


def calls(segment: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((segment / "transcript").glob("*-coding-request.json")):
        stem = path.name.split("-", 1)[0]
        paths = {
            "request": path,
            "response": path.with_name(f"{stem}-assistant-content.json"),
            "result": path.with_name(f"{stem}-result.json"),
            "endpoint_response": path.with_name(f"{stem}-endpoint-response.json"),
            "reasoning": path.with_name(f"{stem}-assistant-reasoning.txt"),
        }
        row = {key: read_json(item) for key, item in paths.items() if key != "reasoning"}
        message = row["endpoint_response"]["choices"][0]["message"]
        if load_json_strict(message["content"].encode("utf-8")) != row["response"]:
            raise ValueError(f"final response custody differs: {path}")
        if message.get("reasoning_content", "").encode("utf-8") != paths["reasoning"].read_bytes():
            raise ValueError(f"reasoning custody differs: {path}")
        row["paths"] = {key: item.relative_to(ROOT).as_posix() for key, item in paths.items()}
        rows.append(row)
    return rows


def independent_coverage(rows: list[dict[str, Any]], fixture: Any) -> list[dict[str, Any]]:
    # Independent per-line bitmap, not the repaired interval-merging predicate.
    covered = {path: [False] * len(fixture.initial.file_map[path].decode("utf-8").splitlines(keepends=True))
               for path in fixture.required_inspection_paths}
    empty_seen: set[str] = set()
    for row in rows:
        action, result = row["response"], row["result"]
        if action.get("action") == "patch" and result.get("accepted"):
            break
        path = action.get("path")
        if action.get("action") != "read" or result.get("accepted") is not True or path not in covered:
            continue
        if row["request"]["candidate_id"] != fixture.initial.candidate_id:
            raise ValueError("pre-mutation request changed candidate")
        if result["candidate_id"] != fixture.initial.candidate_id or result["file_sha256"] != fixture.initial.file_sha256(path):
            raise ValueError("pre-mutation read binding differs")
        lines = fixture.initial.file_map[path].decode("utf-8").splitlines(keepends=True)
        if not lines and action["start_line"] == 1 and result["content"] == "":
            empty_seen.add(path)
        elif result["returned_start_line"] is not None:
            first, last = result["returned_start_line"], result["returned_end_line"]
            if not 1 <= first <= last <= len(lines) or result["content"] != "".join(lines[first-1:last]):
                raise ValueError("read bytes disagree with exact source")
            for index in range(first - 1, last):
                covered[path][index] = True
    return [{"path": path, "file_sha256": fixture.initial.file_sha256(path),
             "line_count": len(bits), "missing_lines": [i + 1 for i, present in enumerate(bits) if not present],
             "complete": all(bits) if bits else path in empty_seen}
            for path, bits in covered.items()]


def terminal_candidate(branch: Path, candidate_id: str, initial: Candidate) -> Candidate:
    if candidate_id == initial.candidate_id:
        return initial
    for snapshot in branch.rglob(candidate_id[:32]):
        if snapshot.is_dir() and snapshot.parent.name == "snap":
            candidate = Candidate.create({path.relative_to(snapshot).as_posix(): path.read_bytes()
                                          for path in snapshot.rglob("*") if path.is_file()})
            if candidate.candidate_id == candidate_id:
                return candidate
    raise ValueError(f"exact terminal candidate unavailable: {branch}")


def boundary_probe(candidate: Candidate) -> dict[str, Any]:
    result = run_checker(candidate, PROBE.read_bytes())
    if result["streams_truncated"] or result["stderr"] or result["returncode"] not in (0, 1):
        raise ValueError(f"contract probe did not complete: {result}")
    checks = load_json_strict(result["stdout"].encode("utf-8"))
    return {"candidate_id": candidate.candidate_id, "contract_passed": result["passed"], "checks": checks}


def analyze() -> dict[str, Any]:
    seal = verify_seal()
    bank = verify_bank(BANK)
    branches = []
    segments = []
    completion_count = 0
    for cell in read_json(EXPERIMENT / "SCHEDULE.json")["cells"]:
        base = RUN / f"cell-{cell['ordinal']:02d}"
        fixture = load_fixture(BANK, cell["fixture_id"], include_evaluator=True)
        shared = calls(base / "shared")
        completion_count += len(shared)
        for name in ("shared", "R50", "X25"):
            verification = verify_run(base / name)
            segments.append({"path": (base / name).relative_to(ROOT).as_posix(), **verification})
        for condition in ("R50", "X25"):
            branch = base / condition
            continuation = calls(branch)
            completion_count += len(continuation)
            rows = [*shared, *continuation]
            pairs = [{"response": row["response"], "result": row["result"]} for row in rows]
            inspections = inspection_status(pairs, fixture.required_inspection_paths, initial_candidate=fixture.initial)
            independent = independent_coverage(rows, fixture)
            if inspections["invalid_read_sequences"] or inspections["all_completed_before_first_mutation"] != all(row["complete"] for row in independent):
                raise ValueError("coverage audits disagree or read evidence is invalid")
            opportunities = []
            for sequence, row in enumerate(rows, 1):
                resource = row["request"]["resource_state"]
                if resource["calls_used"] != sequence - 1 or resource["calls_remaining"] != resource["call_limit"] - resource["calls_used"]:
                    raise ValueError("request action accounting differs")
                if row["response"].get("action") == "check":
                    opportunities.append({
                        "sequence": sequence, "first_check": not opportunities, "artifact_paths": row["paths"],
                        **check_opportunity(calls_used=resource["calls_used"], call_limit=resource["call_limit"], result=row["result"]),
                    })
            summary = read_json(branch / "SUMMARY.json")
            candidate = terminal_candidate(branch, summary["candidate_id"], fixture.initial)
            value = {
                "cell": cell["ordinal"], "condition": condition, "fixture_id": fixture.fixture_id,
                "historical_inspection_status": summary["inspection_status"], "corrected_inspection_status": inspections,
                "independent_line_coverage": independent, "check_opportunities": opportunities,
                "frozen_hidden_replay": hidden_grade(fixture, candidate),
            }
            if fixture.fixture_id == CASE_IDS[0]:
                value["additional_import_contract_probe"] = boundary_probe(candidate)
            branches.append(value)
    if sum("additional_import_contract_probe" in row for row in branches) != 4:
        raise ValueError("the additional contract probe must cover all four source branches")
    code_paths = [Path(__file__), ROOT / "src/working_set_exp/ecological_pilot_v2.py",
                  ROOT / "src/working_set_exp/measurement.py", ROOT / "src/working_set_exp/isolation.py", PROBE]
    return {
        "schema_version": "e020-prospective-measurement-reanalysis-v1",
        "scope": "offline mechanical reanalysis; original reports and scores are preserved",
        "direct_transcript_review_claim": "none; targeted interpretation is recorded separately in FINDING.md",
        "base_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "analysis_code_sha256": {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in code_paths},
        "response_seal": seal, "bank_verification": bank, "record_chain_verification": segments,
        "actual_completion_count": completion_count, "branches": branches,
        "donor_additional_import_contract_probe": boundary_probe(admitted_donor_candidate(BANK)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = analyze()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(canonical_json_bytes(result))
    print(f"Saved {len(result['branches'])} branch measurements from {result['actual_completion_count']} sealed completions to {args.output}")


if __name__ == "__main__":
    main()
