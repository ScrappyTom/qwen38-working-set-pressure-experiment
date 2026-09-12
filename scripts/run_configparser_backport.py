"""Freeze or run one bounded larger-source pilot under the continuing owner goal.

Reference edits and scripted routes are offline evidence, never action selectors.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import time

import configparser_backport as task
import configparser_work as work
import run_compiler_incident as host
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.measurement import check_opportunities

base, pilot, require = work.pilot.base, work.pilot, work.require
AREA, ROOT = task.AREA, task.ROOT
PACKAGE = AREA / "input-qualification-003"
RUN = AREA / "run-001"
MANIFEST = AREA / "EXECUTION_MANIFEST.json"


def verified_package():
    seal = task.read(PACKAGE / "SEAL.json")
    require(seal["status"] == "offline_inputs_and_feedback_qualified" and seal["completion_requests"] == 0,
            "input qualification is incomplete")
    require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "input seal aggregate differs")
    for row in seal["files"]:
        path = PACKAGE / row["path"]
        require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"],
                "qualified artifact differs: " + row["path"])
    for name, digest in {**seal["source_sha256"], **seal["source_host_sha256"]}.items():
        require(sha256_file(ROOT / name) == digest, "qualified source differs: " + name)
    qualified = task.read(PACKAGE / "QUALIFICATION.json")
    require(qualified["every_scripted_action_validated_against_actual_request_schema"], "route grammar was not qualified")
    require(all(r["operations"] <= work.CALL_LIMIT and r["all_immediate_feedback_delivered"] for r in qualified["routes"]),
            "route allowance or delivery failed")
    value = new_state("initial", task.fixture())
    require(pilot.reference.candidate_bytes(value.state.candidate) == (PACKAGE / "candidate.json").read_bytes() and
            task.checker() == (PACKAGE / "PUBLIC_CHECK.py").read_bytes(), "task content differs from qualification")
    require(canonical_json_bytes(work.request_for(value)) == (PACKAGE / "initial-request.json").read_bytes(),
            "initial input differs from qualification")
    return qualified


def source_identities():
    # Bind the existing local helpers, including their transitive dependencies.
    # Offline preparation sources are custody identities, not model input.
    paths = list((ROOT / "scripts").glob("*.py")) + list((ROOT / "src").rglob("*.py"))
    paths += [ROOT / "tests/test_configparser_execution.py", AREA / "SPEC.md", AREA / "TASK.txt",
              AREA / "PUBLIC_CHECK.py", AREA / "PREPARATION_REVIEW.md", AREA / "TESTING.md"]
    paths += [PACKAGE / "SEAL.json", AREA / "reference-qualification-002/SEAL.json"]
    return {p.relative_to(ROOT).as_posix(): sha256_file(p) for p in sorted(set(paths))}


def proposed_manifest():
    q = verified_package()
    return dict(schema="configparser-backport-execution-v1", actor=work.ACTOR, memory_policy=pilot.cont.POLICY,
        input_ceiling=work.INPUT_CEILING, maximum_completion_requests=work.CALL_LIMIT, seed=work.SEED,
        selected_file_limit=task.FILE_LIMIT, initial_candidate=q["candidate_id"],
        initial_request_sha256=q["initial"]["request_sha256"], initial_native_sha256=q["initial"]["native_sha256"],
        initial_prompt_tokens=q["initial"]["prompt_tokens"], preparation_seal_sha256=sha256_file(PACKAGE / "SEAL.json"),
        source_sha256=source_identities(), authorization_basis="owner_continuing_goal_and_proceed",
        retries=0, automatic_successors=False, latest_result_delivery_required=True,
        private_thinking_in_subsequent_inputs=False, source_and_target_pinning=False)


def check_sources(plan):
    for name, digest in plan["source_sha256"].items():
        require(sha256_file(ROOT / name) == digest, "execution source drift: " + name)
    require(sha256_file(PACKAGE / "SEAL.json") == plan["preparation_seal_sha256"], "preparation seal drift")


class RunLog(RecordLog):
    def append(self, kind, payload, artifacts):
        if kind == "runtime_prepared":
            payload = {**payload, "runtime_helper_actor": payload["actor"],
                       "actor": work.ACTOR, "memory_policy": pilot.cont.POLICY}
        if kind == "invocation_completed":
            payload = {**payload,
                "runtime_helper_within_proposed_generation_reserve": payload["within_proposed_generation_reserve"],
                "selected_generation_reserve": work.ACTOR["generation_reserve"],
                "within_proposed_generation_reserve": payload["usage"]["completion_tokens"] <= work.ACTOR["generation_reserve"]}
        return super().append(kind, payload, artifacts)


class Loop:
    def __init__(self, plan, output, store, log, *, url="offline", post=base.post,
                 render=None, health=None, source_check=None):
        self.plan, self.output, self.store, self.log, self.url = plan, output, store, log, url
        self.post = self.native_post = post
        self.render = render
        self.health = health or (lambda: pilot.health(output))
        self.source_check = source_check or (lambda: check_sources(plan))
        self.sent, self.prefix = 0, 0

    def save_state(self, value, stem):
        artifacts = [self.store.put(stem + "-snapshot.json", canonical_json_bytes(host.snapshot(value))),
                     self.store.put(stem + "-candidate.json", pilot.reference.candidate_bytes(value.state.candidate))]
        artifacts += host.payloads.save_payloads(value, stem, self.store)
        self.log.append("working_state_saved", {"stem": stem, "selected_file_limit": value.state.candidate.max_file_bytes}, artifacts)

    def prepare(self, value):
        require(self.sent == len(value.pairs) and self.sent < work.CALL_LIMIT, "action accounting differs")
        tag = f"C{self.sent+1:02d}"

        def render(request, prefix):
            self.source_check()
            self.health()
            stem = f"admission/{tag}-x{prefix:03d}"
            raw = canonical_json_bytes(request)
            self.log.append("input_reconstructed", {"id": tag, "prefix": prefix, "completion_sent": False},
                            [self.store.put(stem + "-endpoint-request.json", raw)])
            template, native, tokens, count = (self.render(self.url, request) if self.render else
                host.Comparison.render_with_custody(self, request, stem))
            require(canonical_json_bytes(request) == raw and load_json_strict(template)["prompt"].encode() == native and
                    len(load_json_strict(tokens)["tokens"]) == count and type(count) is int and count > 0,
                    "native evidence differs")
            artifacts = [self.store.put(stem + "-native.txt", native)]
            if self.render:
                artifacts += [self.store.put(stem + suffix, data) for suffix, data in
                              (("-template.json", template), ("-tokens.json", tokens))]
            row = dict(id=tag, sequence=self.sent+1, calls_remaining_before=work.CALL_LIMIT-self.sent,
                prompt_tokens=count, externalized_through=prefix, physical_generation_space=work.ACTOR["context"]-count,
                native_input_sha256=sha256_bytes(native), endpoint_request_sha256=sha256_bytes(raw))
            self.log.append("native_input_prepared", {**row, "completion_sent": False}, artifacts)
            if self.sent == 0:
                require(row["endpoint_request_sha256"] == self.plan["initial_request_sha256"] and
                        row["native_input_sha256"] == self.plan["initial_native_sha256"] and
                        count == self.plan["initial_prompt_tokens"], "initial input differs from qualified package")
            return row

        selected = work.select_input(value, previous=self.prefix, render=render)
        if selected is None:
            self.log.append("input_capacity_denied", {"sent": self.sent, "next_request_sent": False}, [])
            return None
        self.prefix = selected["externalized"]
        if not work.latest_result_delivered(selected["request"], value):
            self.log.append("immediate_feedback_withheld", {"sent": self.sent, "next_request_sent": False}, [])
            return None
        self.log.append("delivery_assessed", {"id": tag, "sequence": len(value.pairs), "latest_result_delivered": True}, [])
        self.source_check()
        self.health()
        return selected

    def invoke(self, value, prepared):
        require(self.sent < work.CALL_LIMIT and self.sent == len(value.pairs) and not value.state.submitted,
                "terminal or allowance boundary")
        raw = canonical_json_bytes(prepared["request"])
        require(sha256_bytes(raw) == prepared["endpoint_request_sha256"] and
                prepared["prompt_tokens"] <= work.INPUT_CEILING, "prepared request changed or exceeds admission")
        row = {k: v for k, v in prepared.items() if k != "request"}
        self.source_check()
        self.log.append("invocation_started", {**row, "completion_sent": True, **self.health()}, [])
        self.sent += 1
        print(f"Starting {row['id']}: {row['prompt_tokens']} input", flush=True)
        start = time.monotonic()
        try:
            response = self.post(self.url, "/v1/chat/completions", raw, base.HTTP_TIMEOUT_SECONDS)
        except base.ResponseFailure as error:
            self.log.append("transport_stopped", {"id": row["id"], "status": error.status, "error": str(error),
                "received_bytes_not_asserted_complete": True},
                [self.store.put("calls/" + row["id"] + "-transport-body.bin", error.data)])
            raise

        def after_response():
            usage = load_json_strict(response)["usage"]
            require(all(type(usage[k]) is int for k in ("prompt_tokens", "completion_tokens", "total_tokens")) and
                    usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"], "token accounting differs")
            self.source_check()
            return self.health()

        count_before = len(value.pairs)
        received = time.monotonic()
        host.shared.receive_and_execute(host.CheckedReceiver(value, prepared["request"], self.log, row["id"]),
            row, response, received-start, self.store, self.log, after_response)
        require(len(value.pairs) == count_before+1, "response did not execute exactly one action")
        pair = value.pairs[-1]
        self.log.append("action_feedback_recorded", {"id": row["id"], "sequence": len(value.pairs),
            "response_processing_seconds": time.monotonic()-received, "next_request_sent": False}, [])
        self.save_state(value, "after/" + row["id"])
        print(f"Completed {row['id']}: {pair['response']['action']}, accepted={pair['result'].get('accepted')}", flush=True)
        return pair

    def execute(self):
        start = time.monotonic()
        value = new_state("configparser-backport", task.fixture())
        self.save_state(value, "starting")
        disposition = "action_allowance_exhausted"
        for _ in range(work.CALL_LIMIT):
            prepared = self.prepare(value)
            if prepared is None:
                disposition = "host_capacity_or_feedback_denied"
                break
            self.invoke(value, prepared)
            if value.state.submitted:
                disposition = ("submitted_with_current_public_check" if value.state.public_check_passed
                               else "submitted_without_current_public_check")
                break
        self.save_state(value, "final")
        summary = dict(disposition=disposition, sent_requests=self.sent, final_candidate=value.state.candidate.candidate_id,
            current_public_check_passed=value.state.public_check_passed, submitted=value.state.submitted,
            task_loop_seconds=time.monotonic()-start,
            check_opportunities=check_opportunities(value.pairs, call_limit=work.CALL_LIMIT))
        self.log.append("task_loop_completed", summary, [])
        return summary


def run_once(args):
    require(bool(args.owner_direction.strip()), "record the existing owner direction")
    require(args.execution_sha256 == sha256_file(MANIFEST), "execution manifest differs")
    plan = task.read(MANIFEST)
    require(plan == proposed_manifest(), "frozen execution plan differs")
    require(not RUN.exists(), "attempt exists; no retry or resume")
    require(args.model is not None and args.server is not None, "pinned runtime paths required")
    RUN.mkdir(parents=True, exist_ok=False)
    args.output = RUN
    store, log = ArtifactStore(RUN), RunLog(RUN / "records.jsonl", "configparser-backport-001")
    log.append("attempt_reserved", {"owner_direction": args.owner_direction, "manifest_sha256": args.execution_sha256},
        [store.put("EXECUTION_MANIFEST.json", MANIFEST.read_bytes()), store.put("SPEC.md", (AREA / "SPEC.md").read_bytes())])
    problem, result = None, None
    try:
        with base.owned_runtime(args, store, log) as url:
            result = Loop(plan, RUN, store, log, url=url).execute()
            check_sources(plan)
            pilot.health(RUN)
        closed = verify_records(RUN / "records.jsonl", RUN)[-1]
        require(closed["record_type"] == "runtime_closed" and closed["payload"]["owned_server_shutdown_verified"] and
                closed["payload"]["dedicated_port_free"], "runtime lifecycle incomplete")
    except BaseException as error:
        problem = error
        detail = str(error)
        for path in (args.model, args.server, RUN):
            detail = detail.replace(str(path), "<local path>")
        log.append("stage_stopped", {"error_type": type(error).__name__, "error": detail, "no_retry": True}, [])
    finally:
        log.append("stage_closed", {"result": result, "stopped_without_retry": problem is not None}, [])
        records = verify_records(RUN / "records.jsonl", RUN)
        files = base.file_inventory(RUN)
        seal = dict(disposition="stopped_without_retry" if problem else "closed_development_attempt",
            actor=work.ACTOR, memory_policy=pilot.cont.POLICY, execution_manifest_sha256=args.execution_sha256,
            sent_requests=sum(r["record_type"] == "invocation_started" for r in records),
            received_responses=sum(r["record_type"] == "response_received" for r in records),
            completed_responses=sum(r["record_type"] == "invocation_completed" for r in records),
            record_count=len(records), files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),
            memory=base.memory_stats(RUN / "memory.csv"), effective_runtime=base.runtime_evidence(RUN / "private-runtime/server.stderr.log"),
            private_runtime_files_local_only={p.name: sha256_file(p) for p in (RUN / "private-runtime").glob("*") if p.is_file()})
        store.put("RESPONSE_SEAL.json", canonical_json_bytes(seal))
    if problem:
        raise problem
    return seal


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("freeze", "run"), required=True)
    parser.add_argument("--execution-sha256")
    parser.add_argument("--owner-direction", default="")
    parser.add_argument("--model", type=Path)
    parser.add_argument("--server", type=Path)
    args = parser.parse_args()
    if args.mode == "freeze":
        require(not MANIFEST.exists(), "manifest already frozen")
        with MANIFEST.open("xb") as stream:
            stream.write(canonical_json_bytes(proposed_manifest()))
        print(dict(completion_calls=0, execution_manifest_sha256=sha256_file(MANIFEST)))
    else:
        run_once(args)
