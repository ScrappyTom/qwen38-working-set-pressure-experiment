"""Run one explicitly approved saved-work development attempt; no oracle import."""
from __future__ import annotations

import argparse
from pathlib import Path
import time

import saved_work_continuation as work
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

base, pilot, require = work.pilot.base, work.pilot, work.require
RUN = work.AREA / "run-001"
MANIFEST = work.AREA / "EXECUTION_MANIFEST.json"


def verify_package():
    seal = work.read(work.PACKAGE / "SEAL.json")
    require(seal["status"] == "qualified_without_completion", "offline path is unqualified")
    require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "package aggregate differs")
    for row in seal["files"]:
        p = work.PACKAGE / row["path"]
        require(p.stat().st_size == row["size_bytes"] and sha256_file(p) == row["sha256"], "prepared artifact changed")
    qualification = work.read(work.PACKAGE / "QUALIFICATION.json")
    require(qualification["source_sha256"] == work.sources(), "qualified source differs")
    return qualification


def proposed_manifest():
    qualification = verify_package()
    initial = qualification["routes"][0]["rows"][0]
    return dict(schema="saved-work-continuation-execution-v1", actor=work.ACTOR,
        memory_policy=pilot.cont.POLICY, input_ceiling=work.INPUT_CEILING,
        phase_action_limit=work.PHASE_LIMIT, maximum_completion_requests=work.MAX_CALLS, seed=work.SEED,
        starting_candidate=work.SUCCESSOR, proposal_seal_sha256=sha256_file(work.PROPOSAL / "SEAL.json"),
        preparation_seal_sha256=sha256_file(work.PACKAGE / "SEAL.json"),
        initial_request_sha256=sha256_file(work.PACKAGE / "initial-request.json"),
        initial_native_sha256=sha256_file(work.PACKAGE / "initial-native.txt"), initial_prompt_tokens=initial["prompt_tokens"],
        source_sha256=qualification["source_sha256"], completion_calls_during_preparation=0,
        requires_separate_owner_execution_decision=True, retries=0, automatic_successors=False)


def check_sources(plan):
    for name, digest in plan["source_sha256"].items():
        require(sha256_file(work.ROOT / name) == digest, "execution source drift: " + name)
    require(sha256_file(work.PACKAGE / "SEAL.json") == plan["preparation_seal_sha256"], "preparation seal drift")


class RunLog(RecordLog):
    def append(self, kind, payload, artifacts):
        if kind == "runtime_prepared":
            payload = {**payload, "runtime_helper_actor":payload["actor"], "actor":work.ACTOR, "memory_policy":pilot.cont.POLICY}
        if kind == "invocation_completed":
            payload = {**payload, "selected_generation_reserve":work.ACTOR["generation_reserve"],
                "within_selected_generation_reserve":payload["usage"]["completion_tokens"] <= work.ACTOR["generation_reserve"]}
        return super().append(kind, payload, artifacts)


class Loop:
    def __init__(self, plan, output, store, log, *, url="offline", post=base.post, render=None, health=None, source_check=None):
        self.plan, self.output, self.store, self.log, self.url = plan,output,store,log,url
        self.post = self.native_post = post
        self.render = render
        self.health = health or (lambda:pilot.health(output))
        self.source_check = source_check or (lambda:check_sources(plan))
        self.sent, self.prefix, self.ranges = 0, 0, [[1, 3]]

    def save_state(self, value, stem):
        artifacts = [self.store.put(stem+"-snapshot.json", canonical_json_bytes(work.compiler.snapshot(value))),
            self.store.put(stem+"-candidate.json", pilot.reference.candidate_bytes(value.state.candidate))]
        artifacts += work.compiler.payloads.save_payloads(value, stem, self.store)
        self.log.append("working_state_saved", {"stem":stem}, artifacts)

    def setup(self, value, phase):
        start = len(value.pairs)+1
        def record(action, result):
            self.log.append("assisted_acquisition", {"phase":phase, "sequence":len(value.pairs),
                "model_action":False, "completion_sent":False},
                [self.store.put(f"setup/P{phase}-{len(value.pairs):03d}-pair.json", canonical_json_bytes(value.pairs[-1]))])
        group = work.assemble(value, phase, record=record)
        self.ranges.append([start, len(value.pairs)])
        self.save_state(value, f"setup/P{phase}")
        return group

    def prepare(self, value, phase, used):
        tag = f"P{phase}-{used+1:02d}-C{self.sent+1:02d}"
        def render(req, prefix):
            self.source_check()
            self.health()
            stem = f"admission/{tag}-x{prefix:03d}"
            raw = canonical_json_bytes(req)
            self.log.append("input_reconstructed", {"id":tag, "prefix":prefix, "completion_sent":False},
                [self.store.put(stem+"-endpoint-request.json", raw)])
            template,native,tokens,count = (self.render(self.url, req) if self.render else
                work.compiler.Comparison.render_with_custody(self, req, stem))
            require(canonical_json_bytes(req) == raw and work.read_bytes(template)["prompt"].encode() == native and
                    len(work.read_bytes(tokens)["tokens"]) == count, "native evidence differs")
            artifacts = [self.store.put(stem+"-native.txt", native)]
            if self.render:
                artifacts += [self.store.put(stem+suffix, data) for suffix,data in (("-template.json",template),("-tokens.json",tokens))]
            row = dict(id=tag, phase=phase, phase_calls_used=used, calls_remaining_before=work.PHASE_LIMIT-used,
                prompt_tokens=count, externalized_through=prefix, physical_generation_space=work.ACTOR["context"]-count,
                native_input_sha256=sha256_bytes(native), endpoint_request_sha256=sha256_bytes(raw))
            self.log.append("native_input_prepared", {**row, "completion_sent":False}, artifacts)
            if self.sent == 0:
                require(row["endpoint_request_sha256"] == self.plan["initial_request_sha256"] and
                        row["native_input_sha256"] == self.plan["initial_native_sha256"] and count == self.plan["initial_prompt_tokens"],
                        "initial input differs from qualified package")
            return row
        selected = work.select_input(value, previous=self.prefix, phase=phase, phase_used=used,
            total_used=self.sent, setup_ranges=self.ranges, render=render)
        if selected is None:
            self.log.append("input_capacity_denied", {"phase":phase, "sent":self.sent, "next_request_sent":False}, [])
            return None
        self.prefix = selected["externalized"]
        if not work.result_delivered(selected["request"], value, len(value.pairs)):
            self.log.append("immediate_feedback_withheld", {"phase":phase, "sent":self.sent, "next_request_sent":False}, [])
            return None
        self.source_check()
        self.health()
        return selected

    def invoke(self, value, prepared):
        require(self.sent < work.MAX_CALLS and not value.state.submitted, "terminal/allowance boundary")
        raw = canonical_json_bytes(prepared["request"])
        row = {k:v for k,v in prepared.items() if k != "request"}
        self.source_check()
        self.log.append("invocation_started", {**row, "completion_sent":True, **self.health()}, [])
        self.sent += 1
        print(f"Starting {row['id']}: {row['prompt_tokens']} input", flush=True)
        start = time.monotonic()
        try:
            response = self.post(self.url, "/v1/chat/completions", raw, base.HTTP_TIMEOUT_SECONDS)
        except base.ResponseFailure as error:
            self.log.append("transport_stopped", {"id":row["id"], "status":error.status, "error":str(error),
                "received_bytes_not_asserted_complete":True},
                [self.store.put("calls/"+row["id"]+"-transport-body.bin", error.data)])
            raise
        def after_response():
            usage = work.read_bytes(response)["usage"]
            require(all(type(usage[k]) is int for k in ("prompt_tokens","completion_tokens","total_tokens")) and
                    usage["total_tokens"] == usage["prompt_tokens"]+usage["completion_tokens"], "token accounting differs")
            self.source_check()
            return self.health()
        count_before = len(value.pairs)
        received = time.monotonic()
        work.compiler.shared.receive_and_execute(
            work.compiler.CheckedReceiver(value, prepared["request"], self.log, row["id"]), row, response,
            received-start, self.store, self.log, after_response)
        require(len(value.pairs) == count_before+1, "response did not execute one action")
        pair = value.pairs[-1]
        self.log.append("action_feedback_recorded", {"id":row["id"], "sequence":len(value.pairs),
            "response_processing_seconds":time.monotonic()-received, "next_request_sent":False}, [])
        self.save_state(value, "after/"+row["id"])
        print(f"Completed {row['id']}: {pair['response']['action']}, accepted={pair['result'].get('accepted')}", flush=True)
        return pair

    def execute(self):
        started = time.monotonic()
        value = work.starting_state()
        self.save_state(value, "starting")
        group = self.setup(value, 1)
        disposition = "phase_allowance_exhausted"
        for phase in (1, 2):
            edited, transition = False, False
            for used in range(work.PHASE_LIMIT):
                prepared = self.prepare(value, phase, used)
                if prepared is None:
                    disposition = "host_capacity_or_feedback_denied"
                    break
                self.log.append("delivery_assessed", {"id":prepared["id"],
                    "assembled_group_sequences":group, "assembled_group_delivered":work.delivered(prepared["request"],value,group),
                    "report_edited_in_phase":edited}, [])
                pair = self.invoke(value, prepared)
                edited = edited or work.report_changed(pair["response"], pair["result"])
                if value.state.submitted:
                    disposition = ("submitted_with_current_public_check" if value.state.public_check_passed else "submitted_without_current_public_check")
                    break
                if phase == 1 and work.phase_finished(pair["response"], pair["result"], edited):
                    transition = True
                    self.prefix = len(value.pairs)
                    self.log.append("deliberate_working_context_restart", {"prefix":self.prefix, "semantic_assessment_used":False,
                        "candidate_id":value.state.candidate.candidate_id, "prior_thinking_reintroduced":False}, [])
                    group = self.setup(value, 2)
                    break
            if phase == 1 and transition:
                continue
            break
        summary = dict(disposition=disposition, sent_requests=self.sent, final_candidate=value.state.candidate.candidate_id,
            current_public_check_passed=value.state.public_check_passed, submitted=value.state.submitted,
            task_loop_seconds=time.monotonic()-started)
        self.log.append("continuation_completed", summary, [])
        return summary


def run_once(args):
    require(bool(args.owner_approval.strip()), "separate owner execution decision required")
    require(args.execution_sha256 == sha256_file(MANIFEST), "approved manifest differs")
    plan = work.read(MANIFEST)
    require(plan == proposed_manifest(), "frozen execution plan differs")
    work.verify_start()
    require(not RUN.exists(), "attempt exists; no retry/resume")
    require(args.model is not None and args.server is not None, "pinned runtime paths required")
    RUN.mkdir(parents=True, exist_ok=False)
    args.output = RUN
    store, log = ArtifactStore(RUN), RunLog(RUN / "records.jsonl", "saved-work-continuation-001")
    log.append("attempt_reserved", {"owner_approval":args.owner_approval, "manifest_sha256":args.execution_sha256},
        [store.put("EXECUTION_MANIFEST.json", MANIFEST.read_bytes()), store.put("SPEC.md", (work.AREA/"SPEC.md").read_bytes())])
    problem, result = None, None
    try:
        with base.owned_runtime(args, store, log) as url:
            result = Loop(plan,RUN,store,log,url=url).execute()
            check_sources(plan)
            pilot.health(RUN)
        closed = verify_records(RUN / "records.jsonl", RUN)[-1]
        require(closed["record_type"] == "runtime_closed" and closed["payload"]["owned_server_shutdown_verified"] and
                closed["payload"]["dedicated_port_free"], "runtime lifecycle incomplete")
    except BaseException as error:
        problem = error
        detail = str(error)
        for path in (args.model,args.server,RUN):
            detail = detail.replace(str(path), "<local path>")
        log.append("stage_stopped", {"error_type":type(error).__name__, "error":detail, "no_retry":True}, [])
    finally:
        log.append("stage_closed", {"result":result, "stopped_without_retry":problem is not None}, [])
        records = verify_records(RUN / "records.jsonl", RUN)
        files = base.file_inventory(RUN)
        seal = dict(disposition="stopped_without_retry" if problem else "closed_development_attempt",
            actor=work.ACTOR, memory_policy=pilot.cont.POLICY, execution_manifest_sha256=args.execution_sha256,
            sent_requests=sum(r["record_type"]=="invocation_started" for r in records),
            received_responses=sum(r["record_type"]=="response_received" for r in records),
            completed_responses=sum(r["record_type"]=="invocation_completed" for r in records),
            record_count=len(records), files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),
            memory=base.memory_stats(RUN / "memory.csv"), effective_runtime=base.runtime_evidence(RUN/"private-runtime/server.stderr.log"),
            private_runtime_files_local_only={p.name:sha256_file(p) for p in (RUN/"private-runtime").glob("*") if p.is_file()})
        store.put("RESPONSE_SEAL.json", canonical_json_bytes(seal))
    if problem:
        raise problem
    return seal


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("freeze", "run"), required=True)
    parser.add_argument("--execution-sha256")
    parser.add_argument("--owner-approval", default="")
    parser.add_argument("--model", type=Path)
    parser.add_argument("--server", type=Path)
    args = parser.parse_args()
    if args.mode == "freeze":
        require(not MANIFEST.exists(), "manifest already frozen")
        with MANIFEST.open("xb") as stream:
            stream.write(canonical_json_bytes(proposed_manifest()))
        print({"completion_calls":0, "execution_manifest_sha256":sha256_file(MANIFEST)})
    else:
        run_once(args)
