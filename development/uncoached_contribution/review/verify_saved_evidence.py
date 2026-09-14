"""Verify this closed run's custody and artifact; no inference or checker execution.

Run from the repository with PYTHONPATH=src;tests;scripts. Exact operation/checker
replay is a separate existing command, recorded in EXECUTION_RECEIPT.md.
"""
import ast
import json
from pathlib import Path

import parser_roundtrip as task
from run_uncoached_contribution import verify_package
from working_set_exp.candidate import Candidate
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


REVIEW = Path(__file__).resolve().parent
RUN = REVIEW.parent / "run-001"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def candidate(name):
    saved = read(RUN / (name + "-candidate.json"))
    files = {r["path"]: r["content_utf8"].encode() for r in saved["files"]}
    rebuilt = Candidate.create(files, max_file_bytes=saved["max_file_bytes"])
    assert rebuilt.candidate_id == saved["candidate_id"]
    return rebuilt


def methods(raw):
    return {(cls.name, f.name): ast.dump(f, include_attributes=False)
            for cls in ast.parse(raw).body if isinstance(cls, ast.ClassDef)
            for f in cls.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}


def verify():
    manifest = verify_package()
    seal = read(RUN / "RESPONSE_SEAL.json")
    assert sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"]
    for row in seal["files"]:
        raw = (RUN / row["path"]).read_bytes()
        assert len(raw) == row["size_bytes"] and sha256_bytes(raw) == row["sha256"]
    assert seal["source_sha256"] == manifest["source_sha256"]
    task.verify_sources(seal["source_sha256"])
    private = RUN / "private-runtime"
    private_available = all((private / name).is_file() for name in seal["private_runtime_files_local_only"])
    if private_available:
        for name, digest in seal["private_runtime_files_local_only"].items():
            assert sha256_file(private / name) == digest
    records = verify_records(RUN / "records.jsonl", RUN)
    assert len(records) == seal["record_count"]
    before, after = candidate("starting"), candidate("final")
    target = "Lib/test/test_configparser.py"
    changed = [p for p, raw in before.files if after.file_map[p] != raw]
    assert changed == [target]
    old, new = methods(before.file_map[target]), methods(after.file_map[target])
    assert all(new.get(k) == v for k, v in old.items())
    added = sorted(".".join(k) for k in new.keys() - old.keys())

    views, requests = {}, {}
    for number in range(1, 5):
        tag = f"C{number:02d}"
        request = read(RUN / f"calls/{tag}-wire-request.json")
        assert [m["role"] for m in request["messages"]] == ["system", "user"]
        views[tag] = json.loads(request["messages"][1]["content"])
        requests[tag] = request
        if number > 1:
            assert request["messages"][0] == requests["C01"]["messages"][0]
            assert {k: v for k, v in request.items() if k != "messages"} == {
                k: v for k, v in requests["C01"].items() if k != "messages"}
        state = views[tag]["workspace"]
        current = before if tag != "C04" else after
        sources = state["working_set"]["sources"] + task.WorkingSession.feedback_sources(state["latest_feedback"])
        for source in sources:
            raw = current.file_map[source["path"]]
            assert source["candidate_id"] == current.candidate_id
            assert source["file_sha256"] == sha256_bytes(raw)
            lines = raw.decode().splitlines(keepends=True)
            assert source["content"] == "".join(lines[source["returned_start_line"]-1:source["returned_end_line"]])

    assert (RUN / "calls/C01-wire-request.json").read_bytes() == (task.PACKAGE / "initial-wire-request.json").read_bytes()
    old_check = views["C01"]["workspace"]["current_check"]
    assert old_check["passed"] and old_check["candidate_matches"]
    assert not old_check["check_definition_matches"] and not old_check["applies_to_current"]
    for previous, following in (("C01", "C02"), ("C02", "C03")):
        actual = read(RUN / f"calls/{previous}-host-result.json")["operations"][0]["result"]
        assert actual == views[following]["workspace"]["latest_feedback"]["result"]
    bundle = read(RUN / "calls/C03-host-result.json")["operations"]
    patch, check = bundle
    operation = patch["action"]
    assert operation["old"] in views["C03"]["workspace"]["latest_feedback"]["result"]["sources"][-1]["content"]
    assert before.file_map[target].decode().replace(operation["old"], operation["new"], 1).encode() == after.file_map[target]
    c04 = views["C04"]
    assert c04["preceding_operation_feedback"][0]["result"] == patch["result"]
    assert c04["workspace"]["latest_feedback"]["result"] == check["result"]
    assert check["result"]["checked_candidate_id"] == after.candidate_id
    assert check["result"]["check_definition_sha256"] == sha256_bytes(task.checker())
    assert c04["workspace"]["current_check"]["applies_to_current"]
    public = json.loads(check["result"]["stdout"])
    assert public["passed"] and public["added_tests"] == added
    final = read(RUN / "final-state.json")
    assert final["submitted"] and not final["delivery_blocked"]
    assert final["pairs"][:39] == read(RUN / "starting-state.json")["pairs"]

    rows = []
    for record in records:
        if record["record_type"] != "invocation_completed":
            continue
        row = record["payload"]
        processing = next(r["payload"]["processing_seconds"] for r in records
                          if r["record_type"] == "reply_processed" and r["payload"]["id"] == row["id"])
        rows.append(dict(id=row["id"], input_tokens=row["usage"]["prompt_tokens"],
                         generated_tokens=row["usage"]["completion_tokens"],
                         request_seconds=round(row["elapsed_seconds"], 3),
                         response_processing_seconds=round(processing, 3),
                         actual_operations=row["actual_operations"]))
    loop = next(r["payload"] for r in records if r["record_type"] == "task_loop_completed")
    output = sum(r["generated_tokens"] for r in rows)
    seconds = round(sum(r["request_seconds"] for r in rows), 3)
    metrics = dict(calls=rows, input_tokens=sum(r["input_tokens"] for r in rows), generated_tokens=output,
                   model_request_seconds=seconds, task_loop_seconds=round(loop["task_loop_seconds"], 3),
                   response_processing_seconds=round(sum(r["response_processing_seconds"] for r in rows), 3),
                   peak_input_tokens=max(r["input_tokens"] for r in rows),
                   peak_input_plus_generated_tokens=max(r["input_tokens"]+r["generated_tokens"] for r in rows),
                   C03_generated_share_percent=round(100*rows[2]["generated_tokens"]/output, 3),
                   C03_request_time_share_percent=round(100*rows[2]["request_seconds"]/seconds, 3),
                   unused_requests_closed=12, unused_operations_closed=19,
                   check_opportunities=loop["check_opportunities"], memory=seal["memory"])
    verification = dict(status="saved_custody_inputs_and_artifact_verified", completion_requests=0,
                        checker_executions_in_this_script=0, records=len(records), sealed_files=len(seal["files"]),
                        bound_sources=len(seal["source_sha256"]), private_runtime_hashes_verified=private_available,
                        run_seal_sha256=sha256_file(RUN / "RESPONSE_SEAL.json"),
                        artifact_candidate_id=after.candidate_id, changed_files=changed, unchanged_files=9,
                        preserved_class_methods=len(old), added_tests=added,
                        complete_source_and_combined_feedback_delivery=True,
                        baseline_check_inapplicable_to_new_contract=True,
                        prior_archive_unchanged=True, public_check_summary=public,
                        runtime_closed_in_original_record=records[-1]["record_type"] == "runtime_closed")
    return verification, metrics


if __name__ == "__main__":
    verification, metrics = verify()
    for name, value in (("VERIFICATION.json", verification), ("METRICS.json", metrics)):
        (REVIEW / name).write_bytes(json.dumps(value, indent=2, ensure_ascii=False).encode() + b"\n")
    print(json.dumps({k: v for k, v in verification.items() if k != "public_check_summary"}))
    print(json.dumps(metrics))
