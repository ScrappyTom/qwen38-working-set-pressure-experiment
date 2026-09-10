"""Execute only W01-W08 after owner approval; preserve one attempt without retry."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import prepare_interface_wording as prep
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


ROOT, AREA = prep.ROOT, prep.AREA
PACKAGE = AREA / "preparation-001"
RUN = AREA / "run-001"
MANIFEST = AREA / "EXECUTION_MANIFEST.json"
SPEC = AREA / "EXECUTION_SPEC.md"
PACKAGE_SHA = "b009fe4fdb2e0982c8cb1941791d622fb11cb05f84e80302481453234b4d2112"
PREPARATION_SEAL_SHA = "57074b97fab747c939f689e36678f1088ad7b138a2ea2d6f5370c293586f29fe"
VERIFICATION_SHA = "6703392e1a40570a79ffccd8bb793d9f3328119c49c3f9f5377fc1573aca30a2"
base, shared = prep.reference.base, prep.previous
require = prep.require


def verified_preparation():
    require(sha256_file(PACKAGE / "PACKAGE_MANIFEST.json") == PACKAGE_SHA, "wording package identity differs")
    require(sha256_file(PACKAGE / "PREPARATION_SEAL.json") == PREPARATION_SEAL_SHA, "wording preparation seal differs")
    require(sha256_file(AREA / "VERIFICATION.json") == VERIFICATION_SHA, "independent verification differs")
    seal = load_json_strict((PACKAGE / "PREPARATION_SEAL.json").read_bytes())
    require(seal["completion_calls"] == 0 and seal["disposition"] == "prepared_without_completion", "preparation not unexposed")
    for row in seal["files"]:
        path = PACKAGE / row["path"]
        require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"], "sealed input artifact differs")
    require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "preparation aggregate differs")
    require(len(verify_records(PACKAGE / "records.jsonl", PACKAGE)) == seal["record_count"], "preparation chain differs")
    for name, digest in seal["private_runtime_files_local_only"].items():
        require(sha256_file(PACKAGE / "private-runtime" / name) == digest, "private preparation runtime differs")
    verification = load_json_strict((AREA / "VERIFICATION.json").read_bytes())
    require(verification["package_sha256"] == PACKAGE_SHA and verification["preparation_seal_sha256"] == PREPARATION_SEAL_SHA,
            "independent verification binding differs")
    require(sha256_file(ROOT / "scripts/verify_interface_wording.py") == verification["verifier_sha256"], "preparation verifier changed")
    require(shared.prep.ACTOR == prep.ACTOR, "shared response handler actor differs")
    return prep.validate_package(PACKAGE)


def proposed_manifest():
    package = verified_preparation()
    rows = [r for r in package["rows"] if r["purpose"] == "proposed_comparison"]
    require([r["id"] for r in rows] == package["proposed_completion_ids"], "completion selection differs")
    plan = {"package_sha256": PACKAGE_SHA, "preparation_seal_sha256": PREPARATION_SEAL_SHA,
            "execution_spec_sha256": sha256_file(SPEC), "actor": prep.ACTOR, "memory_policy": prep.reference.cont.POLICY,
            "maximum_completion_calls": 8, "owner_approval_required_before_run": True,
            "retries": 0, "continuations_per_response": 0, "preparation_completion_calls": 0,
            "rows": rows, "excluded_input_ids": [r["id"] for r in package["rows"] if r["purpose"] == "offline_input_regression"],
            "reviewed_input_scope_sha256": sha256_file(AREA / "PREPARATION_REVIEW.md"),
            "independent_preparation_verification_sha256": VERIFICATION_SHA,
            "execution_source_sha256": {**prep.source_identities(),
                Path(__file__).relative_to(ROOT).as_posix(): sha256_file(Path(__file__))},
            "execution_tests_sha256": sha256_file(ROOT / "tests/test_interface_wording_execution.py")}
    validate_scope(plan)
    return plan


def validate_scope(plan):
    require(plan["maximum_completion_calls"] == 8 and len(plan["rows"]) == 8, "wording execution scope differs")
    require(plan["excluded_input_ids"] == ["E01", "E02", "E03", "E04"], "offline exclusions differ")
    for row, expected in zip(plan["rows"], prep.schedule()):
        require(all(row[key] == value for key, value in expected.items()), "wording schedule differs")


def load_manifest():
    plan = load_json_strict(MANIFEST.read_bytes())
    require(plan == proposed_manifest(), "frozen wording execution manifest differs")
    return plan


def check_sources(plan):
    require(sha256_file(SPEC) == plan["execution_spec_sha256"], "execution specification changed")
    for relative, digest in plan["execution_source_sha256"].items():
        require(sha256_file(ROOT / relative) == digest, "execution source changed: " + relative)


def preflight(plan, url, output, store, log):
    validate_scope(plan)
    for row in plan["rows"]:
        check_sources(plan)
        shared.runtime_check(output)
        raw = (PACKAGE / row["request_path"]).read_bytes()
        require(sha256_bytes(raw) == row["request_sha256"], "scheduled request changed")
        template, rendered, count = base.native_render(url, load_json_strict(raw))
        require(count == row["prompt_tokens"] and sha256_bytes(rendered) == row["rendered_sha256"], "native preparation differs")
        require(count <= prep.reference.INPUT_CEILING, "native input exceeds admission ceiling")
        stem = "calls/" + row["id"]
        log.append("invocation_prepared", {**row, "completion_sent": False}, [
            store.put(stem + "-endpoint-request.json", raw), store.put(stem + "-rendered-prompt.txt", rendered),
            store.put(stem + "-template-response.json", template)])


def fresh_state(row):
    require(any(all(row.get(k) == v for k, v in expected.items()) for expected in prep.schedule()),
            "row is outside W01-W08 execution scope")
    value = prep.reference.development_states(ROOT)[row["state_index"]]
    folder = PACKAGE / "states" / row["state"]
    require(value.request == (folder / "original-request.json").read_bytes(), "rebuilt source request differs")
    require(prep.reference.candidate_bytes(value.state.candidate) == (folder / "candidate.json").read_bytes(), "rebuilt candidate differs")
    require(prep.reference.session_bytes(value.state) == (folder / "session.json").read_bytes(), "rebuilt session differs")
    raw = (PACKAGE / row["request_path"]).read_bytes()
    require(sha256_bytes(raw) == row["request_sha256"], "execution input changed")
    reference = (PACKAGE / "TOOL_REFERENCE.txt").read_text(encoding="utf-8")
    require(raw == canonical_json_bytes(prep.request_for(value, row, reference)), "input and fresh host state differ")
    return value, raw


def execute(plan, url, output, store, log):
    preflight(plan, url, output, store, log)
    print("All eight frozen native inputs match; beginning the once-only wording comparison.", flush=True)
    for row in plan["rows"]:
        check_sources(plan)
        value, raw = fresh_state(row)
        health = shared.runtime_check(output)
        stem = "calls/" + row["id"]
        log.append("invocation_started", {**row, "completion_sent": True, **health}, [
            store.put(stem + "-candidate-before.json", prep.reference.candidate_bytes(value.state.candidate)),
            store.put(stem + "-state-before.json", prep.reference.session_bytes(value.state))])
        print(f"Starting {row['id']}/W08 {row['state']} seed {row['seed']} {row['condition']}: {row['prompt_tokens']} input; {health['memory']['latest_free_mib']} MiB free", flush=True)
        started = time.monotonic()
        try:
            response = base.post(url, "/v1/chat/completions", raw, base.HTTP_TIMEOUT_SECONDS)
        except base.ResponseFailure as error:
            log.append("transport_stopped", {"id": row["id"], "error": str(error), "http_status": error.status,
                       "execution_attempted": False, "received_bytes_are_not_asserted_complete": True},
                       [store.put(stem + "-transport-body.bin", error.data)])
            raise
        outcome = shared.receive_and_execute(value, row, response, time.monotonic() - started, store, log,
                                             lambda: shared.runtime_check(output))
        print(f"Completed {row['id']}: {outcome['usage']['completion_tokens']} output tokens, {outcome['elapsed_seconds']:.1f}s, action {outcome['host_result']['action']['action']}, accepted {outcome['host_result']['result'].get('accepted')}", flush=True)


def run_once(args, plan):
    require(isinstance(getattr(args, "owner_approval", None), str) and bool(args.owner_approval.strip()),
            "separate owner approval is required before run")
    require(plan == load_manifest(), "run plan differs from frozen manifest")
    require(not RUN.exists(), "wording attempt already reserved; no resume or retry")
    args.output = RUN
    RUN.mkdir(parents=True, exist_ok=False)
    store = ArtifactStore(RUN)
    log = shared.ComparisonLog(RUN / "records.jsonl", "interface-wording-comparison-001")
    log.append("stage_prepared", {"maximum_completion_calls": 8, "owner_approval": args.owner_approval,
               "actor": prep.ACTOR, "memory_policy": prep.reference.cont.POLICY}, [
        store.put("EXECUTION_MANIFEST.json", MANIFEST.read_bytes()), store.put("SPEC.md", SPEC.read_bytes())])
    disposition, problem = "stopped_without_retry", None
    try:
        with base.owned_runtime(args, store, log) as url:
            execute(plan, url, RUN, store, log)
            check_sources(plan)
            shared.runtime_check(RUN)
        closed = verify_records(RUN / "records.jsonl", RUN)[-1]
        require(closed["record_type"] == "runtime_closed" and closed["payload"]["owned_server_shutdown_verified"]
                and closed["payload"]["dedicated_port_free"], "runtime lifecycle incomplete")
        disposition = "completed_matched_comparison"
    except BaseException as error:
        problem = type(error).__name__ + ": " + str(error)
        for path in (args.model, args.server, RUN):
            problem = problem.replace(str(path), "<local path>")
        log.append("stage_stopped", {"error": problem, "no_retry": True}, [])
    finally:
        records = verify_records(RUN / "records.jsonl", RUN)
        counts = {key: sum(r["record_type"] == kind for r in records) for key, kind in (
            ("sent_requests", "invocation_started"), ("received_responses", "response_received"), ("completed_responses", "invocation_completed"))}
        log.append("stage_closed", {"disposition": disposition, **counts,
                   "owned_server_shutdown_verified": not base.running_process_ids(args.server.name),
                   "dedicated_port_free": base.port_free(base.PORT)}, [])
        records = verify_records(RUN / "records.jsonl", RUN)
        files = base.file_inventory(RUN)
        private = RUN / "private-runtime"
        seal = {"stage": "matched_wording_comparison", "disposition": disposition, **counts,
                "package_sha256": PACKAGE_SHA, "preparation_seal_sha256": PREPARATION_SEAL_SHA,
                "execution_manifest_sha256": sha256_file(MANIFEST), "record_count": len(records),
                "files": files, "aggregate_sha256": sha256_bytes(canonical_json_bytes(files)),
                "actor": prep.ACTOR, "memory_policy": prep.reference.cont.POLICY,
                "memory": base.memory_stats(RUN / "memory.csv"), "effective_runtime": base.runtime_evidence(private / "server.stderr.log"),
                "private_runtime_files_local_only": {p.name: sha256_file(p) for p in sorted(private.glob("*")) if p.is_file()}}
        store.put("RESPONSE_SEAL.json", canonical_json_bytes(seal))
        print(json.dumps({k: v for k, v in seal.items() if k not in {"files", "private_runtime_files_local_only"}}, indent=2), flush=True)
    if problem:
        raise RuntimeError(problem)
    return seal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("freeze", "run"), required=True)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--server", type=Path)
    parser.add_argument("--owner-approval", help="Exact owner execution direction, supplied only after separate approval")
    args = parser.parse_args()
    if args.mode == "freeze":
        base.write_json(MANIFEST, proposed_manifest())
        print(json.dumps({"execution_manifest_sha256": sha256_file(MANIFEST), "completion_calls": 0,
                          "owner_approval_required_before_run": True}, indent=2))
        return
    require(args.model is not None and args.server is not None, "pinned model and runtime paths required")
    run_once(args, load_manifest())


if __name__ == "__main__":
    main()
