"""Owner-authorized Q2/Q3 then conditional D1-D4; Q1 is never repeated."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import time

import run_interface_follow_on as base
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


FOLLOW = base.ROOT / "development/qwen_interface_consultation/follow-on"
CONT = FOLLOW / "continuation"
PACKAGE = FOLLOW / "package"
PRIOR = FOLLOW / "qualification-001"
PRIOR_REVIEW = FOLLOW / "qualification-review/DECISION.json"
SCHEDULE = {"qualification": ["Q2", "Q3"], "design": ["D1", "D2", "D3", "D4"]}
POLICY = {"owner_direction": "Continue q4/56,576 with memory monitoring; preserve Q1 and the original unmet target",
          "reference_free_gpu_mib": 350, "reference_is_advisory": True,
          "numeric_free_memory_stop": None, "sample_interval_ms": 200,
          "stop_on_lost_telemetry_or_runtime_failure": True}
ACTOR = {k: v for k, v in base.ACTOR.items() if k != "minimum_free_gpu_mib"}
require = base.require


class ContinuationLog(RecordLog):
    def append(self, record_type, payload, artifacts):
        if record_type == "runtime_prepared":
            # The reused runtime helper reports its original package policy.
            # Preserve that identity separately from this amendment's policy.
            payload = dict(payload)
            payload["original_package_actor"] = payload.pop("actor")
            payload["actor"] = ACTOR
            payload["memory_policy"] = POLICY
        return super().append(record_type, payload, artifacts)


def verified_seal(folder):
    seal = base.verify_seal(folder)
    for name, digest in seal["private_runtime_files_local_only"].items():
        require(sha256_file(folder / "private-runtime" / name) == digest, "private runtime bytes differ")
    return seal


def reviewed_files(review_path):
    review = load_json_strict(review_path.read_bytes())
    require(review["direct_review_completed_by_reviewer"] is True, "direct review incomplete")
    require(len(review["audit_files"]) == 5, "five existing audit products required")
    for row in review["audit_files"]:
        require(sha256_file(review_path.parent / row["path"]) == row["sha256"], "reviewed audit changed")
    return review


def prior_q1():
    seal = verified_seal(PRIOR)
    require(seal["package_sha256"] == sha256_file(PACKAGE / "PACKAGE_MANIFEST.json"), "Q1 package differs")
    require(seal["disposition"] == "stopped_without_retry", "unexpected original disposition")
    records = verify_records(PRIOR / "records.jsonl", PRIOR)
    completed = [r["payload"] for r in records if r["record_type"] == "invocation_completed"]
    require([r["id"] for r in completed] == ["Q1"], "original exposure is not exactly Q1")
    require(seal["sent_requests"] == seal["received_responses"] == seal["completed_responses"] == 1, "original attempt count differs")
    require(completed[0]["finish_reason"] == "stop" and completed[0]["within_proposed_generation_reserve"], "Q1 output unsuitable")
    stopped = [r["payload"] for r in records if r["record_type"] == "stage_stopped"]
    require(len(stopped) == 1 and stopped[0]["error"] == "ValueError: sampled GPU reserve below frozen target; no next request sent", "original stop differs")
    review = reviewed_files(PRIOR_REVIEW)
    require(review["qualification_seal_sha256"] == sha256_file(PRIOR / "RESPONSE_SEAL.json") and review["q1_correct_fields"] == 4, "Q1 review binding differs")
    return seal


def prepare_plan():
    original = base.validate_package(PACKAGE)
    prior_q1()
    plan = {"original_package_sha256": sha256_file(PACKAGE / "PACKAGE_MANIFEST.json"),
            "prior_q1_seal_sha256": sha256_file(PRIOR / "RESPONSE_SEAL.json"),
            "prior_q1_review_sha256": sha256_file(PRIOR_REVIEW), "amendment_sha256": sha256_file(CONT / "SPEC.md"),
            "actor": ACTOR, "memory_policy": POLICY, "schedule": SCHEDULE,
            "maximum_new_completions": 6, "retries": 0, "preparation_completions": 0,
            "execution_source_sha256": {**original["source_sha256"],
                Path(__file__).relative_to(base.ROOT).as_posix(): sha256_file(Path(__file__))},
            "rows": [r for r in original["rows"] if r["id"] != "Q1"]}
    base.write_json(CONT / "CONTINUATION_MANIFEST.json", plan)
    return plan


def load_plan():
    original = base.validate_package(PACKAGE)
    prior_q1()
    plan = load_json_strict((CONT / "CONTINUATION_MANIFEST.json").read_bytes())
    for key, path in (("original_package_sha256", PACKAGE / "PACKAGE_MANIFEST.json"),
                      ("prior_q1_seal_sha256", PRIOR / "RESPONSE_SEAL.json"),
                      ("prior_q1_review_sha256", PRIOR_REVIEW), ("amendment_sha256", CONT / "SPEC.md")):
        require(plan[key] == sha256_file(path), "continuation parent/amendment differs: " + key)
    require(plan["actor"] == ACTOR and plan["memory_policy"] == POLICY, "amended configuration differs")
    require(plan["schedule"] == SCHEDULE and plan["maximum_new_completions"] == 6 and plan["retries"] == 0, "continuation scope differs")
    require(plan["rows"] == [r for r in original["rows"] if r["id"] != "Q1"], "remaining requests changed")
    for path, digest in plan["execution_source_sha256"].items():
        require(sha256_file(base.ROOT / path) == digest, "continuation source differs: " + path)
    return plan


def monitoring(path, *, now=None):
    stats = base.memory_stats(path)
    require(stats["samples"] > 0, "GPU monitoring is unavailable")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if text and not text.endswith("\n"):
        lines = lines[:-1]
    rows = list(csv.reader(lines))
    require(len(rows[-1]) == 5, "latest GPU sample is malformed")
    sampled_at = datetime.strptime(rows[-1][0].strip(), "%Y/%m/%d %H:%M:%S.%f").timestamp()
    age = (time.time() if now is None else now) - sampled_at
    require(-2 <= age <= 5, "GPU monitoring is stale")
    return {**stats, "latest_free_mib": int(rows[-1][-1]),
            "below_original_reference": stats["min_free_mib"] < 350, "reference_is_advisory": True}


def healthy_runtime(path):
    evidence = base.runtime_evidence(path)
    require(all(evidence[k] for k in ("full_offload", "context_matches", "q4_k_and_v", "mtp_disabled")), "runtime identity differs")
    require(not evidence["truncation_observed"] and not evidence["cuda_failure_observed"], "runtime failure; no further dispatch")
    return evidence


def require_design_review(review_path):
    prior_q1()
    run = CONT / "qualification-001"
    seal = verified_seal(run)
    require(seal["disposition"] == "completed_nonexecuting_stage", "remaining qualification incomplete")
    require(seal["continuation_manifest_sha256"] == sha256_file(CONT / "CONTINUATION_MANIFEST.json"), "qualification amendment differs")
    records = verify_records(run / "records.jsonl", run)
    done = [r["payload"] for r in records if r["record_type"] == "invocation_completed"]
    require([r["id"] for r in done] == SCHEDULE["qualification"], "Q2/Q3 responses incomplete")
    require(all(r["finish_reason"] == "stop" and r["within_proposed_generation_reserve"] for r in done), "qualification generation reserve failed")
    healthy_runtime(run / "private-runtime/server.stderr.log")
    require(seal["memory"]["samples"] > 0, "qualification telemetry missing")
    require(records[-1]["payload"]["owned_server_shutdown_verified"] and records[-1]["payload"]["dedicated_port_free"], "qualification lifecycle incomplete")
    review = reviewed_files(review_path)
    require(review["qualification_seal_sha256"] == sha256_file(run / "RESPONSE_SEAL.json"), "review not bound to Q2/Q3")
    require(review["prior_q1_seal_sha256"] == sha256_file(PRIOR / "RESPONSE_SEAL.json"), "review not bound to Q1")
    require(review["continuation_manifest_sha256"] == seal["continuation_manifest_sha256"], "review amendment differs")
    require(review["continue_to_design"] is True and review["memory_policy"] == POLICY, "review does not support design")
    require((review["q1_correct_fields"], review["q2_correct_fields"], review["q3_operational_criteria_passed"]) == (4, 8, 4), "qualification content criteria failed")


def execute(stage, plan, base_url, output, store, log):
    rows = [r for r in plan["rows"] if r["stage"] == stage]
    require([r["id"] for r in rows] == SCHEDULE[stage], "stage schedule differs; Q1 cannot be repeated")
    for row in rows:
        raw = (PACKAGE / row["request_path"]).read_bytes()
        template, rendered, count = base.native_render(base_url, load_json_strict(raw))
        require(count == row["prompt_tokens"] and sha256_bytes(rendered) == row["rendered_sha256"], "native input changed")
        stem = "calls/" + row["id"]
        log.append("invocation_prepared", row, [store.put(stem + "-endpoint-request.json", raw),
                   store.put(stem + "-rendered-prompt.txt", rendered), store.put(stem + "-template-response.json", template)])
    for row in rows:
        memory = monitoring(output / "memory.csv")
        healthy_runtime(output / "private-runtime/server.stderr.log")
        log.append("invocation_started", {"id": row["id"], "completion_sent": True, "memory_before": memory}, [])
        print(f"Starting {row['id']}: {row['prompt_tokens']} input tokens; memory {memory['latest_free_mib']} MiB free", flush=True)
        started = time.monotonic()
        try:
            raw = base.post(base_url, "/v1/chat/completions", (PACKAGE / row["request_path"]).read_bytes(), base.HTTP_TIMEOUT_SECONDS)
        except base.ResponseFailure as error:
            log.append("transport_stopped", {"id": row["id"], "error": str(error), "http_status": error.status,
                "received_bytes_are_not_asserted_complete": True}, [store.put("calls/" + row["id"] + "-transport-body.bin", error.data)])
            raise
        outcome = base.receive_nonexecuting(store, log, row, raw, time.monotonic() - started)
        memory = monitoring(output / "memory.csv")
        log.append("post_response_monitoring", {"id": row["id"], "memory": memory,
                   "effective_runtime": healthy_runtime(output / "private-runtime/server.stderr.log")}, [])
        print(f"Completed {row['id']}: {outcome['usage']['completion_tokens']} output tokens; {outcome['elapsed_seconds']:.1f}s; minimum free {memory['min_free_mib']} MiB", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("prepare", "qualification", "design"), required=True)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--server", type=Path)
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    if args.stage == "prepare":
        plan = prepare_plan()
        print(json.dumps({"prepared_ids": [r["id"] for r in plan["rows"]], "completion_calls": 0,
                          "manifest_sha256": sha256_file(CONT / "CONTINUATION_MANIFEST.json")}, indent=2))
        return
    plan = load_plan()
    require(args.model is not None and args.server is not None, "pinned model/server paths required")
    if args.stage == "design":
        require(args.review is not None, "design requires direct qualification review")
        require_design_review(args.review)
    args.output = CONT / (args.stage + "-001")
    args.output.mkdir(exist_ok=False)
    store = ArtifactStore(args.output)
    log = ContinuationLog(args.output / "records.jsonl", "interface-continuation-" + args.stage)
    log.append("stage_prepared", {"stage": args.stage, "maximum_completion_calls": len(SCHEDULE[args.stage]),
        "actor": ACTOR, "memory_policy": POLICY, "prior_q1_seal_sha256": plan["prior_q1_seal_sha256"],
        "execution_source_sha256": plan["execution_source_sha256"]}, [
        store.put("CONTINUATION_MANIFEST.json", (CONT / "CONTINUATION_MANIFEST.json").read_bytes()),
        store.put("SPEC.md", (CONT / "SPEC.md").read_bytes())])
    disposition, error_text = "stopped_without_retry", None
    try:
        with base.owned_runtime(args, store, log) as base_url:
            execute(args.stage, plan, base_url, args.output, store, log)
            disposition = "completed_nonexecuting_stage"
    except BaseException as error:
        error_text = type(error).__name__ + ": " + str(error)
        for path in (args.model, args.server, args.output):
            error_text = error_text.replace(str(path), "<local path>")
        log.append("stage_stopped", {"error": error_text, "no_retry": True}, [])
    finally:
        records = verify_records(args.output / "records.jsonl", args.output)
        counts = {key: sum(r["record_type"] == kind for r in records) for key, kind in (
            ("sent_requests", "invocation_started"), ("received_responses", "response_received"), ("completed_responses", "invocation_completed"))}
        log.append("stage_closed", {"disposition": disposition, **counts,
            "owned_server_shutdown_verified": not base.running_process_ids(args.server.name), "dedicated_port_free": base.port_free(base.PORT)}, [])
        records = verify_records(args.output / "records.jsonl", args.output)
        files = base.file_inventory(args.output)
        private = args.output / "private-runtime"
        seal = {"stage": args.stage, "disposition": disposition, **counts,
            "record_count": len(records), "files": files, "aggregate_sha256": sha256_bytes(canonical_json_bytes(files)),
            "package_sha256": plan["original_package_sha256"], "continuation_manifest_sha256": sha256_file(CONT / "CONTINUATION_MANIFEST.json"),
            "prior_q1_seal_sha256": plan["prior_q1_seal_sha256"], "memory_policy": POLICY,
            "memory": base.memory_stats(args.output / "memory.csv"), "effective_runtime": base.runtime_evidence(private / "server.stderr.log"),
            "private_runtime_files_local_only": {p.name: sha256_file(p) for p in sorted(private.glob("*")) if p.is_file()}}
        store.put("RESPONSE_SEAL.json", canonical_json_bytes(seal))
        print(json.dumps({k: v for k, v in seal.items() if k not in ("files", "private_runtime_files_local_only")}, indent=2), flush=True)
    if error_text:
        raise SystemExit(error_text)


if __name__ == "__main__":
    main()
