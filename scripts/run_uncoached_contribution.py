"""Declared task and actual host feedback only; one monitored, sealed attempt."""
import argparse
from pathlib import Path
import time

import parser_roundtrip as task
from run_bounded_parser import Loop as LegacyLoop, RunLog
from working_set_exp import working_view
from working_set_exp.contribution_reply import completion_request_bytes, process_reply, reply_schema
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.measurement import check_opportunities
from working_set_exp.working_session import INPUT_LIMIT, MAX_ACTION_BYTES


class Adapter:
    def __init__(self, module=task):
        self.module = module
        self.preceding_feedback = []
        self.base = module.base.base
        self.pilot = module.base.pilot

    def __getattr__(self, name):
        return getattr(self.module, name)

    def reply_schema(self):
        return getattr(self.module, "reply_schema", reply_schema)()

    def process_reply(self, *args):
        return getattr(self.module, "process_reply", process_reply)(*args)

    def request_for(self, view):
        request = self.module.base.request_for(view)
        reference = (self.module.operating_reference() if hasattr(self.module, "operating_reference")
                     else working_view.system_prompt().split("\n\n", 1)[1])
        request["messages"] = [dict(role="system", content=(self.AREA / "SYSTEM.txt").read_text(encoding="utf-8") + "\n\n" + reference),
            dict(role="user", content=canonical_json_bytes(dict(workspace=view,
                preceding_operation_feedback=[r for r in self.preceding_feedback
                    if not view["latest_feedback"] or r["sequence"] != view["latest_feedback"]["sequence"]])).decode())]
        request["response_format"] = self.reply_schema()
        request["seed"] = self.SEED
        request["chat_template_kwargs"] = dict(enable_thinking=True, reasoning_effort=self.ACTOR["effort"])
        return request


class Loop(LegacyLoop):
    def __init__(self, *args, task_module=None, **kwargs):
        module = task_module or Adapter()
        super().__init__(*args, task_module=module, **kwargs)
        self.no_operation = False

    def measure(self, view):
        count = super().measure(view)
        key = sha256_bytes(canonical_json_bytes(self.task.request_for(view)))
        selected = self.cache[key]
        if "wire_request_sha256" not in selected:
            wire = completion_request_bytes(selected["request"])
            selected["wire_request_sha256"] = sha256_bytes(wire)
            self.log.append("wire_input_prepared", dict(stem=selected["stem"],
                wire_request_sha256=selected["wire_request_sha256"], request_sha256=key, completion_sent=False),
                [self.store.put(selected["stem"] + "-wire-request.json", wire)])
        return count

    def snapshot(self, session, stem):
        super().snapshot(session, stem)
        self.log.append("contribution_feedback_saved", dict(stem=stem),
            [self.store.put(stem + "-preceding-feedback.json", canonical_json_bytes(self.task.preceding_feedback))])

    def invoke(self, session):
        actor = self.task
        actor.require(not session.submitted and not session.delivery_blocked and self.sent < actor.MAX_REQUESTS,
                      "terminal or request boundary")
        count = self.measure(session.view())
        actor.require(count <= INPUT_LIMIT, "complete next input exceeds admission")
        key = sha256_bytes(canonical_json_bytes(actor.request_for(session.view())))
        selected = self.cache[key]
        if self.sent == 0 and self.initial:
            actor.require(all(selected[k] == self.initial[k] for k in
                ("prompt_tokens", "request_sha256", "native_sha256", "wire_request_sha256")), "first input differs from qualification")
        wire = completion_request_bytes(selected["request"])
        actor.require(sha256_bytes(wire) == selected["wire_request_sha256"] and
                      sha256_bytes(canonical_json_bytes(load_json_strict(wire))) == key, "prepared wire input changed")
        self.source_check()
        if self.stop_requested():
            return None
        session.mark_delivered(session.view())
        if session.request_limit is not None:
            actor.require(session.request_limit == actor.MAX_REQUESTS and session.requests_used == self.sent,
                          "displayed request allowance differs from runner")
            session.begin_request()
        tag = f"C{self.sent + 1:02d}"
        self.log.append("invocation_started", dict(id=tag, input_stem=selected["stem"], prompt_tokens=count,
            wire_request_sha256=sha256_bytes(wire), completion_sent=True, **self.health()),
            [self.store.put(f"calls/{tag}-wire-request.json", wire)])
        self.sent += 1
        print(f"Starting {tag}: {count} input tokens", flush=True)
        started = time.monotonic()
        try:
            raw = self.post(self.url, "/v1/chat/completions", wire, actor.base.HTTP_TIMEOUT_SECONDS)
        except actor.base.ResponseFailure as error:
            self.log.append("transport_stopped", dict(id=tag, status=error.status),
                            [self.store.put(f"calls/{tag}-partial-response.bin", error.data)])
            raise
        elapsed = time.monotonic() - started
        self.log.append("response_received", dict(id=tag, elapsed_seconds=elapsed),
                        [self.store.put(f"calls/{tag}-endpoint-response.json", raw)])
        response = load_json_strict(raw)
        actor.require(len(response["choices"]) == 1, "response choice count differs")
        choice, usage = response["choices"][0], response["usage"]
        message = choice["message"]
        thinking, content = message.get("reasoning_content") or "", message.get("content") or ""
        self.log.append("response_extracted", dict(id=tag, finish_reason=choice.get("finish_reason"), usage=usage),
            [self.store.put(f"calls/{tag}-assistant-reasoning.txt", thinking.encode()),
             self.store.put(f"calls/{tag}-assistant-content.txt", content.encode())])
        actor.require(choice.get("finish_reason") == "stop" and content.strip(), "incomplete response; no operation executed")
        actor.require(not message.get("tool_calls") and not message.get("function_call"), "unexpected action channel")
        actor.require(all(type(usage.get(k)) is int for k in ("prompt_tokens", "completion_tokens", "total_tokens")) and
            usage["prompt_tokens"] == count and usage["completion_tokens"] > 0 and
            usage["total_tokens"] == count + usage["completion_tokens"] <= actor.ACTOR["context"], "token accounting differs")
        actor.require(usage.get("prompt_tokens_details", {}).get("cached_tokens") == 0 and
                      response.get("timings", {}).get("cache_n") == 0, "unexpected cache reuse")
        self.source_check()
        self.log.append("post_response_runtime_check", dict(id=tag, **self.health()), [])
        reply = load_json_strict(content.encode())
        working_view.validate(reply, actor.reply_schema()["json_schema"]["schema"])
        self.log.append("reply_selected", dict(id=tag), [self.store.put(f"calls/{tag}-reply.json", canonical_json_bytes(reply))])
        actor.require("operation" not in reply or len(canonical_json_bytes(reply["operation"])) <= MAX_ACTION_BYTES,
                      "complete operation exceeds host allowance")
        def record(number, operation):
            self.log.append("contribution_operation", dict(id=tag, number=number, origin=operation["origin"]),
                [self.store.put(f"calls/{tag}-operation-{number:02d}.json", canonical_json_bytes(operation))])
            self.snapshot(session, f"after/{tag}-O{number:02d}")
        processing = time.monotonic()
        host = actor.process_reply(session, reply, self.measure, actor.preceding_feedback, record)
        following = self.measure(session.view())
        self.no_operation = not host["executed"]
        self.log.append("reply_processed", dict(id=tag, processing_seconds=time.monotonic() - processing,
            feedback_input_tokens=following, feedback_admitted=following <= INPUT_LIMIT and not session.delivery_blocked,
            no_next_model_receipt_yet=True), [self.store.put(f"calls/{tag}-host-result.json", canonical_json_bytes(host))])
        row = dict(id=tag, usage=usage, elapsed_seconds=elapsed, actual_operations=len(host["operations"]),
                   within_generation_reserve=usage["completion_tokens"] <= actor.ACTOR["generation_reserve"])
        self.log.append("invocation_completed", row, [])
        print(f"Completed {tag}: {usage['completion_tokens']} output; {row['actual_operations']} actual operations", flush=True)
        return row

    def execute(self, session):
        started = time.monotonic()
        self.snapshot(session, "starting")
        disposition = "request_allowance_exhausted"
        while self.sent < self.task.MAX_REQUESTS:
            if self.stop_requested():
                disposition = "operator_stopped"
                break
            if session.delivery_blocked:
                disposition = "feedback_capacity_denied"
                break
            if session.calls_used >= session.call_limit:
                disposition = "action_allowance_exhausted"
                break
            self.invoke(session)
            if session.submitted:
                disposition = "checked_submission"
                break
            if self.no_operation:
                disposition = "actor_stopped_without_operation"
                break
        if self.stop_requested() and not session.submitted:
            disposition = "operator_stopped"
        self.snapshot(session, "final")
        result = dict(disposition=disposition, sent_requests=self.sent, actual_operations=session.calls_used,
            candidate_id=session.candidate.candidate_id, current_check=session.check_state(), submitted=session.submitted,
            task_loop_seconds=time.monotonic() - started,
            check_opportunities=check_opportunities(session.pairs[session.starting_archive_length:], call_limit=session.call_limit))
        self.log.append("task_loop_completed", result, [])
        return result


def verify_package(module=task):
    manifest = module.read(module.MANIFEST)
    seal = module.read(module.PACKAGE / "SEAL.json")
    module.require(manifest["preparation_seal_sha256"] == sha256_file(module.PACKAGE / "SEAL.json"), "package seal differs")
    module.require(seal["status"] == "qualified_no_model_inference" and seal["completion_requests"] == 0, "unqualified package")
    module.require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "inventory differs")
    for row in seal["files"]:
        module.require(sha256_file(module.PACKAGE / row["path"]) == row["sha256"], "qualified file changed")
    module.verify_sources(manifest["source_sha256"])
    module.require(manifest["source_sha256"] == module.source_identities(), "source inventory changed")
    session, adapter = module.initial_session(), Adapter(module)
    module.require((module.PACKAGE / "starting-candidate.json").read_bytes() == module.candidate_bytes(session.candidate), "starting work differs")
    module.require((module.PACKAGE / "initial-wire-request.json").read_bytes() == completion_request_bytes(adapter.request_for(session.view())), "initial wire differs")
    module.require(manifest["actor"] == module.ACTOR and manifest["maximum_requests"] == module.MAX_REQUESTS and
                   manifest["maximum_operations"] == module.MAX_OPERATIONS, "declared limits differ")
    return manifest


def run_once(args, module=task):
    module.require(args.owner_direction.strip() and args.manifest_sha256 == sha256_file(module.MANIFEST), "execution identity or direction missing")
    manifest = verify_package(module)
    module.require(not module.RUN.exists(), "attempt exists; no retry")
    module.RUN.mkdir()
    store, log = ArtifactStore(module.RUN), RunLog(module.RUN / "records.jsonl", "uncoached-contribution-001", task_module=module)
    log.append("attempt_reserved", dict(owner_direction=args.owner_direction, manifest_sha256=args.manifest_sha256),
        [store.put("EXECUTION_MANIFEST.json", module.MANIFEST.read_bytes()), store.put("SPEC.md", (module.AREA / "SPEC.md").read_bytes())])
    args.server, args.model, _ = module.runtime_paths()
    args.output = module.RUN
    session, adapter = module.initial_session(), Adapter(module)
    error, outcome = None, None
    try:
        with module.base.base.owned_runtime(args, store, log) as url:
            loop = Loop(module.RUN, store, log, url=url, task_module=adapter,
                source_check=lambda: module.verify_sources(manifest["source_sha256"]), initial=manifest["initial"])
            outcome = loop.execute(session)
            module.base.pilot.health(module.RUN)
    except BaseException as problem:
        error = problem
        log.append("attempt_stopped", dict(error_type=type(problem).__name__, error=str(problem)), [])
        for name, value in (("stopped-state.json", module.snapshot(session)),
                            ("stopped-candidate.json", module.candidate_bytes(session.candidate)),
                            ("stopped-preceding-feedback.json", adapter.preceding_feedback)):
            store.put(name, value if isinstance(value, bytes) else canonical_json_bytes(value))
    finally:
        records, files = verify_records(module.RUN / "records.jsonl", module.RUN), module.base.base.file_inventory(module.RUN)
        seal = dict(disposition="stopped_without_retry" if error else outcome["disposition"], actor=module.ACTOR,
            source_sha256=manifest["source_sha256"], files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),
            record_count=len(records), sent_requests=sum(r["record_type"] == "invocation_started" for r in records),
            returned_responses=sum(r["record_type"] == "response_received" for r in records),
            processed_invocations=sum(r["record_type"] == "invocation_completed" for r in records),
            actual_operations=session.calls_used, memory=module.base.base.memory_stats(module.RUN / "memory.csv"),
            runtime=module.base.base.runtime_evidence(module.RUN / "private-runtime/server.stderr.log"),
            port_free=module.base.base.port_free(module.base.base.PORT),
            private_runtime_files_local_only={p.name: sha256_file(p) for p in (module.RUN / "private-runtime").glob("*") if p.is_file()})
        store.put("RESPONSE_SEAL.json", canonical_json_bytes(seal))
    if error:
        raise error
    print("Closed: " + outcome["disposition"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-direction", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    run_once(parser.parse_args())
