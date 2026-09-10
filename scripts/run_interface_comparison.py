"""Run the owner's sixteen frozen matched requests once; never resume or retry."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import prepare_interface_comparison as prep
import continue_interface_follow_on as cont
import run_interface_follow_on as base
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.tools import strict_action


ROOT = base.ROOT
AREA = prep.COMPARISON
PACKAGE = AREA / "preparation-001"
RUN = AREA / "run-001"
MANIFEST = AREA / "EXECUTION_MANIFEST.json"
SPEC = AREA / "EXECUTION_SPEC.md"
PACKAGE_SHA = "f8fab01274a39d12acd24e544d81056d4000a3e1a81652cd05d631c8f5328ca5"
PREPARATION_SEAL_SHA = "c6b78560328cfb86c3a9d3315002b35b493a416dae321218b08d1ebcb9c3f44b"
require = base.require


def verified_preparation():
    require(sha256_file(PACKAGE / "PACKAGE_MANIFEST.json") == PACKAGE_SHA, "prepared package identity differs")
    require(sha256_file(PACKAGE / "PREPARATION_SEAL.json") == PREPARATION_SEAL_SHA, "preparation seal identity differs")
    seal = load_json_strict((PACKAGE / "PREPARATION_SEAL.json").read_bytes())
    for row in seal["files"]:
        path = PACKAGE / row["path"]
        require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"], "sealed preparation artifact differs")
    require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "preparation seal aggregate differs")
    require(len(verify_records(PACKAGE / "records.jsonl", PACKAGE)) == seal["record_count"], "preparation chain differs")
    for name, digest in seal["private_runtime_files_local_only"].items():
        require(sha256_file(PACKAGE / "private-runtime" / name) == digest, "private preparation runtime differs")
    return prep.validate_package(PACKAGE)


def proposed_manifest():
    package = verified_preparation()
    return {"package_sha256": PACKAGE_SHA, "preparation_seal_sha256": PREPARATION_SEAL_SHA,
            "execution_spec_sha256": sha256_file(SPEC), "actor": prep.ACTOR, "memory_policy": cont.POLICY,
            "owner_authorized_completion_calls": 16, "retries": 0, "continuations_per_response": 0,
            "preparation_completion_calls": 0, "rows": package["rows"],
            "reviewed_input_scope_sha256": sha256_file(AREA / "PREPARATION_REVIEW.md"),
            "independent_preparation_verification_sha256": sha256_file(AREA / "VERIFICATION.json"),
            "execution_source_sha256": {**prep.source_identities(),
                Path(__file__).relative_to(ROOT).as_posix(): sha256_file(Path(__file__))},
            "execution_tests_sha256": sha256_file(ROOT / "tests/test_interface_comparison_execution.py")}


def load_manifest():
    plan = load_json_strict(MANIFEST.read_bytes())
    require(plan == proposed_manifest(), "frozen comparison execution manifest differs")
    return plan


def check_sources(plan):
    require(sha256_file(SPEC) == plan["execution_spec_sha256"], "execution specification changed")
    for relative, digest in plan["execution_source_sha256"].items():
        require(sha256_file(ROOT / relative) == digest, "execution source changed: " + relative)


class ComparisonLog(RecordLog):
    def append(self, record_type, payload, artifacts):
        if record_type == "runtime_prepared":
            payload = dict(payload)
            payload["original_helper_actor"] = payload.pop("actor")
            payload["actor"] = prep.ACTOR
            payload["memory_policy"] = cont.POLICY
        return super().append(record_type, payload, artifacts)


def runtime_check(output):
    return {"memory": cont.monitoring(output / "memory.csv"),
            "effective_runtime": cont.healthy_runtime(output / "private-runtime/server.stderr.log")}


def preflight(plan, url, output, store, log):
    require(len(plan["rows"]) == 16 and [r["id"] for r in plan["rows"]] == [r["id"] for r in prep.schedule()], "comparison schedule differs")
    for row in plan["rows"]:
        check_sources(plan)
        runtime_check(output)
        raw = (PACKAGE / row["request_path"]).read_bytes()
        require(sha256_bytes(raw) == row["request_sha256"], "scheduled request changed")
        template, rendered, count = base.native_render(url, load_json_strict(raw))
        require(count == row["prompt_tokens"] and sha256_bytes(rendered) == row["rendered_sha256"], "native preparation differs")
        require(count <= prep.INPUT_CEILING, "input exceeds frozen admission ceiling")
        stem = "calls/" + row["id"]
        log.append("invocation_prepared", {**row, "completion_sent": False}, [
            store.put(stem + "-endpoint-request.json", raw), store.put(stem + "-rendered-prompt.txt", rendered),
            store.put(stem + "-template-response.json", template)])


def fresh_state(row):
    value = prep.development_states(ROOT)[row["state_index"]]
    folder = PACKAGE / "states" / row["state"]
    require(value.request == (folder / "original-request.json").read_bytes(), "rebuilt source request differs")
    require(prep.candidate_bytes(value.state.candidate) == (folder / "candidate.json").read_bytes(), "rebuilt candidate differs")
    require(prep.session_bytes(value.state) == (folder / "session.json").read_bytes(), "rebuilt session differs")
    raw = (PACKAGE / row["request_path"]).read_bytes()
    require(sha256_bytes(raw) == row["request_sha256"], "execution request changed")
    request = load_json_strict(raw)
    expected = canonical_json_bytes(prep.neutral_ids(load_json_strict(value.request), row["state"])).decode("utf-8")
    require(request["messages"][1]["content"] == expected, "execution input and fresh state differ")
    return value, raw


def receive_and_execute(value, row, raw, elapsed, store, log, health_check):
    stem = "calls/" + row["id"]
    log.append("response_received", {"id": row["id"], "elapsed_seconds": elapsed},
               [store.put(stem + "-endpoint-response.json", raw)])
    host = {"execution_attempted": False, "executed": False}
    outcome, problem = None, None
    try:
        require(len(raw) <= base.MAX_HTTP_BYTES, "response exceeds transport bound; preserved bytes are a prefix")
        response = load_json_strict(raw)
        require(len(response["choices"]) == 1, "response choice count differs")
        choice, usage = response["choices"][0], response["usage"]
        message = choice["message"]
        reasoning, content = message.get("reasoning_content") or "", message.get("content") or ""
        require(isinstance(reasoning, str) and isinstance(content, str), "response fields are not text")
        log.append("response_extracted", {"id": row["id"], "usage": usage, "finish_reason": choice.get("finish_reason")}, [
            store.put(stem + "-assistant-reasoning.txt", reasoning.encode("utf-8")),
            store.put(stem + "-assistant-content.txt", content.encode("utf-8"))])
        host["finish_reason"] = choice.get("finish_reason")
        require(choice.get("finish_reason") == "stop" and bool(content), "incomplete output; no action executed")
        require(not message.get("tool_calls") and not message.get("function_call"), "unexpected tool response channel")
        require(usage["prompt_tokens"] == row["prompt_tokens"], "native/endpoint prompt accounting mismatch")
        require(usage.get("prompt_tokens_details", {}).get("cached_tokens") == 0 and response.get("timings", {}).get("cache_n") == 0, "unexpected cache reuse")
        require(type(usage["completion_tokens"]) is int and usage["completion_tokens"] > 0, "invalid completion accounting")
        remaining = prep.ACTOR["context"] - usage["prompt_tokens"] - usage["completion_tokens"]
        require(remaining >= 0, "endpoint tokens exceed physical context")
        health = health_check()
        log.append("post_response_runtime_check", {"id": row["id"], **health}, [])
        action = strict_action(content.encode("utf-8"))
        host["action"] = action
        log.append("action_selected", {"id": row["id"]}, [store.put(stem + "-action.json", canonical_json_bytes(action))])
        host["execution_attempted"] = True
        host["result"] = value.execute(action)
        host["executed"] = True
        outcome = {**row, "usage": usage, "timings": response.get("timings"), "finish_reason": choice["finish_reason"],
                   "elapsed_seconds": elapsed, "physical_tokens_remaining": remaining,
                   "within_proposed_generation_reserve": usage["completion_tokens"] <= prep.ACTOR["generation_reserve"],
                   "host_result": host}
    except BaseException as error:
        problem = error
        host["error_type"], host["error"] = type(error).__name__, str(error)
    finally:
        log.append("host_decision", {"id": row["id"], "processing_stopped": problem is not None}, [
            store.put(stem + "-host-result.json", canonical_json_bytes(host)),
            store.put(stem + "-candidate-after.json", prep.candidate_bytes(value.state.candidate)),
            store.put(stem + "-state-after.json", prep.session_bytes(value.state))])
    if problem is not None:
        raise problem
    log.append("invocation_completed", outcome, [])
    return outcome


def execute(plan, url, output, store, log):
    preflight(plan, url, output, store, log)
    print("All sixteen frozen native requests match; beginning the once-only comparison.", flush=True)
    for row in plan["rows"]:
        check_sources(plan)
        value, raw = fresh_state(row)
        health = runtime_check(output)
        stem = "calls/" + row["id"]
        log.append("invocation_started", {**row, "completion_sent": True, **health}, [
            store.put(stem + "-candidate-before.json", prep.candidate_bytes(value.state.candidate)),
            store.put(stem + "-state-before.json", prep.session_bytes(value.state))])
        print(f"Starting {row['id']}/C16 {row['state']} seed {row['seed']} {row['condition']}: {row['prompt_tokens']} input; {health['memory']['latest_free_mib']} MiB free", flush=True)
        started = time.monotonic()
        try:
            response = base.post(url, "/v1/chat/completions", raw, base.HTTP_TIMEOUT_SECONDS)
        except base.ResponseFailure as error:
            log.append("transport_stopped", {"id": row["id"], "error": str(error), "http_status": error.status,
                       "execution_attempted": False, "received_bytes_are_not_asserted_complete": True},
                       [store.put(stem + "-transport-body.bin", error.data)])
            raise
        outcome = receive_and_execute(value, row, response, time.monotonic() - started, store, log,
                                      lambda: runtime_check(output))
        print(f"Completed {row['id']}: {outcome['usage']['completion_tokens']} output tokens, {outcome['elapsed_seconds']:.1f}s, action {outcome['host_result']['action']['action']}, accepted {outcome['host_result']['result'].get('accepted')}", flush=True)


def run_once(args, plan):
    require(not RUN.exists(), "comparison attempt already reserved; no resume or retry")
    args.output = RUN
    RUN.mkdir(parents=True, exist_ok=False)
    store = ArtifactStore(RUN)
    log = ComparisonLog(RUN / "records.jsonl", "interface-reference-comparison-001")
    log.append("stage_prepared", {"maximum_completion_calls": 16, "actor": prep.ACTOR, "memory_policy": cont.POLICY}, [
        store.put("EXECUTION_MANIFEST.json", MANIFEST.read_bytes()), store.put("SPEC.md", SPEC.read_bytes())])
    disposition, problem = "stopped_without_retry", None
    try:
        with base.owned_runtime(args, store, log) as url:
            execute(plan, url, RUN, store, log)
            check_sources(plan)
            runtime_check(RUN)
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
        seal = {"stage": "matched_reference_comparison", "disposition": disposition, **counts,
                "package_sha256": PACKAGE_SHA, "preparation_seal_sha256": PREPARATION_SEAL_SHA,
                "execution_manifest_sha256": sha256_file(MANIFEST), "record_count": len(records),
                "files": files, "aggregate_sha256": sha256_bytes(canonical_json_bytes(files)),
                "actor": prep.ACTOR, "memory_policy": cont.POLICY,
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
    args = parser.parse_args()
    if args.mode == "freeze":
        base.write_json(MANIFEST, proposed_manifest())
        print(json.dumps({"execution_manifest_sha256": sha256_file(MANIFEST), "prepared_completions": 0}, indent=2))
        return
    require(args.model is not None and args.server is not None, "pinned model and runtime paths required")
    run_once(args, load_manifest())


if __name__ == "__main__":
    main()
