"""Reviewed parser documentation with optional host-bound post-edit validation.

The consumed assisted-regression runner remains unchanged. This adapter reuses
its recording/lifecycle pattern with a separately frozen input and reply form.
"""
import argparse
import copy
from pathlib import Path
import time
from types import SimpleNamespace

import bounded_parser as base
from run_bounded_parser import Loop, RunLog
from working_set_exp import working_view
from working_set_exp.contribution_reply import completion_request_bytes, process_reply, reply_schema
from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count
from working_set_exp.working_session import WorkingSession, INPUT_LIMIT, MAX_ACTION_BYTES

AREA = base.AREA / "parser-documentation"
MAX_TURNS = 6
MAX_OPERATIONS = 12
GROUP = [dict(path=p, start_line=a, end_line=b) for p, a, b in (
    ("Lib/configparser.py", 299, 341),
    ("Lib/configparser.py", 594, 622),
    ("Lib/configparser.py", 1005, 1106),
    ("Lib/test/test_configparser.py", 1852, 1864),
    ("Doc/library/configparser.rst", 534, 574),
    ("Doc/library/configparser.rst", 914, 952),
    ("Doc/library/configparser.rst", 1340, 1387))]
SOURCE = base.AREA / "assisted-regression/turn-04"
STARTING_ID = "8b8079f15ab90ea4ed23ad18e68c2c5bb175c686f3ca578fcb812a1657314654"
PRIOR_SEAL = "ea011d177c15c6af45adc784d55f7d299efa2e4f593442ea587892554d8a2349"


def identities():
    extra = [Path(__file__), base.ROOT / "tests/test_contribution_reply.py",
             *(AREA / n for n in ("SPEC.md", "TASK.txt", "SYSTEM.txt", "OPENING.txt")),
             SOURCE / "RESPONSE_SEAL.json", SOURCE / "final-candidate.json", SOURCE / "final-state.json"]
    return {**base.source_identities(),
            **{p.relative_to(base.ROOT).as_posix(): sha256_file(p) for p in extra}}


def initial_session():
    base.require(sha256_file(SOURCE / "RESPONSE_SEAL.json") == PRIOR_SEAL, "saved-work seal differs")
    inventory = {r["path"]: r for r in base.read(SOURCE / "RESPONSE_SEAL.json")["files"]}
    for name in ("final-candidate.json", "final-state.json"):
        base.require(sha256_file(SOURCE / name) == inventory[name]["sha256"], "saved work changed: " + name)
    saved, prior = base.read(SOURCE / "final-candidate.json"), base.read(SOURCE / "final-state.json")
    candidate = Candidate.create({r["path"]: r["content_utf8"].encode() for r in saved["files"]},
                                 max_file_bytes=saved["max_file_bytes"])
    base.require(candidate.candidate_id == saved["candidate_id"] == prior["candidate_id"] == STARTING_ID,
                 "starting candidate differs")
    session = WorkingSession(candidate, base.task.checker(),
        (AREA / "TASK.txt").read_text(encoding="utf-8"), pairs=prior["pairs"], call_limit=MAX_OPERATIONS)
    session.last = copy.deepcopy(prior["last"])
    session.diffs = {int(k): v for k, v in prior["diffs"].items()}
    for span in GROUP:
        session.add_source(session.source(span))
    return session


def restore(folder, stem):
    snapshot = base.read(folder / (stem + "-state.json"))
    saved = base.read(folder / (stem + "-candidate.json"))
    candidate = Candidate.create({r["path"]: r["content_utf8"].encode() for r in saved["files"]},
                                 max_file_bytes=saved["max_file_bytes"])
    base.require(candidate.candidate_id == saved["candidate_id"] == snapshot["candidate_id"], "candidate differs")
    session = WorkingSession(candidate, base.task.checker(), (AREA / "TASK.txt").read_text(encoding="utf-8"))
    for key in ("pairs", "last", "ranges", "saved", "starting_archive_length", "call_limit",
                "submitted", "delivery_blocked", "delivered_sources"):
        setattr(session, key, copy.deepcopy(snapshot[key]))
    session.diffs = {int(k): v for k, v in snapshot["diffs"].items()}
    base.require(canonical_json_bytes(base.snapshot(session)) == canonical_json_bytes(snapshot), "state differs")
    return session


class Adapter:
    def __init__(self, dialogue, preceding_feedback=()):
        self.dialogue = copy.deepcopy(dialogue)
        self.preceding_feedback = copy.deepcopy(list(preceding_feedback))

    def __getattr__(self, name):
        return getattr(base, name)

    def request_for(self, view):
        request = base.request_for(view)
        reference = working_view.system_prompt().split("\n\n", 1)[1]
        request["messages"] = [dict(role="system", content=(AREA / "SYSTEM.txt").read_text(encoding="utf-8") + "\n\n" + reference),
            dict(role="user", content=canonical_json_bytes(dict(dialogue=self.dialogue, workspace=view,
                preceding_operation_feedback=[r for r in self.preceding_feedback
                    if not view["latest_feedback"] or r["sequence"] != view["latest_feedback"]["sequence"]])).decode())]
        request["response_format"] = reply_schema()
        return request


class Counter:
    def __init__(self, output, adapter):
        self.output, self.adapter, self.cache, self.rows = output, adapter, {}, []
        _, model, tokenizer = base.runtime_paths()
        base.require(sha256_file(model) == base.ACTOR["model_sha256"] and
                     sha256_file(tokenizer) == base.delivery.TOKENIZER_SHA, "runtime identity differs")
        self.profile = SimpleNamespace(model_path=model, tokenizer_path=tokenizer)

    def measure(self, view):
        request = self.adapter.request_for(view)
        raw = canonical_json_bytes(request)
        digest = sha256_bytes(raw)
        if digest not in self.cache:
            wire = completion_request_bytes(request)
            native = base.expected_native(request)
            count = tokenizer_count(self.profile, native)
            stem = f"inputs/I{len(self.rows)+1:04d}"
            row = dict(stem=stem, prompt_tokens=count, request_sha256=digest,
                       wire_request_sha256=sha256_bytes(wire), native_sha256=sha256_bytes(native))
            for suffix, value in (("-request.json", raw), ("-wire-request.json", wire),
                                  ("-native.txt", native), ("-count.json", row)):
                base.save(self.output, stem + suffix, value)
            self.rows.append(row)
            self.cache[digest] = row
        return self.cache[digest]["prompt_tokens"]

    def row(self, view):
        self.measure(view)
        return self.cache[sha256_bytes(canonical_json_bytes(self.adapter.request_for(view)))]


def receive(loop, session, tag, selected):
    """Preserve the response; execute only its declared contribution operations."""
    adapter = loop.task
    raw_request = completion_request_bytes(selected["request"])
    base.require(sha256_bytes(canonical_json_bytes(load_json_strict(raw_request))) == selected["request_sha256"],
                 "prepared input changed")
    base.require(sha256_bytes(raw_request) == selected["wire_request_sha256"], "prepared wire request changed")
    loop.source_check()
    session.mark_delivered(session.view())
    loop.log.append("invocation_started", dict(id=tag, input_stem=selected["stem"],
        prompt_tokens=selected["prompt_tokens"], wire_request_sha256=sha256_bytes(raw_request), **loop.health()),
        [loop.store.put(f"calls/{tag}-wire-request.json", raw_request)])
    print(f"Starting {tag}: {selected['prompt_tokens']} input tokens", flush=True)
    started = time.monotonic()
    try:
        raw = loop.post(loop.url, "/v1/chat/completions", raw_request, base.base.HTTP_TIMEOUT_SECONDS)
    except base.base.ResponseFailure as error:
        loop.log.append("transport_stopped", dict(id=tag, status=error.status),
                        [loop.store.put(f"calls/{tag}-partial-response.bin", error.data)])
        raise
    elapsed = time.monotonic() - started
    loop.log.append("response_received", dict(id=tag, elapsed_seconds=elapsed),
                    [loop.store.put(f"calls/{tag}-endpoint-response.json", raw)])
    response = load_json_strict(raw)
    base.require(len(response["choices"]) == 1, "choice count differs")
    choice, usage = response["choices"][0], response["usage"]
    message = choice["message"]
    thinking, content = message.get("reasoning_content") or "", message.get("content") or ""
    loop.log.append("response_extracted", dict(id=tag, finish_reason=choice["finish_reason"], usage=usage),
        [loop.store.put(f"calls/{tag}-assistant-reasoning.txt", thinking.encode()),
         loop.store.put(f"calls/{tag}-assistant-content.txt", content.encode())])
    base.require(choice["finish_reason"] == "stop" and content.strip(), "incomplete reply; no operation executed")
    base.require(not message.get("tool_calls") and not message.get("function_call"), "unexpected output channel")
    base.require(all(type(usage.get(k)) is int for k in ("prompt_tokens", "completion_tokens", "total_tokens")) and
        usage["prompt_tokens"] == selected["prompt_tokens"] and usage["completion_tokens"] > 0 and
        usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"] <= base.ACTOR["context"], "usage differs")
    base.require(usage.get("prompt_tokens_details", {}).get("cached_tokens") == 0 and
                 response.get("timings", {}).get("cache_n") == 0, "cache reuse")
    loop.source_check()
    loop.log.append("post_response_runtime_check", dict(id=tag, **loop.health()), [])
    reply = load_json_strict(content.encode())
    working_view.validate(reply, reply_schema()["json_schema"]["schema"])
    adapter.dialogue.append(dict(speaker="Qwen", text=reply["discussion"]))
    loop.log.append("reply_selected", dict(id=tag), [loop.store.put(f"calls/{tag}-reply.json", canonical_json_bytes(reply))])
    started = time.monotonic()
    if "operation" in reply:
        base.require(len(canonical_json_bytes(reply["operation"])) <= MAX_ACTION_BYTES, "complete operation too large")
    def record_operation(number, operation):
        loop.log.append("contribution_operation", dict(id=tag, number=number, origin=operation["origin"]),
            [loop.store.put(f"calls/{tag}-operation-{number:02d}.json", canonical_json_bytes(operation))])
        loop.snapshot(session, f"after/{tag}-O{number:02d}")
    host = process_reply(session, reply, loop.measure, adapter.preceding_feedback, record_operation)
    count = loop.measure(session.view())
    loop.log.append("reply_processed", dict(id=tag, processing_seconds=time.monotonic()-started,
        feedback_input_tokens=count, feedback_admitted=count <= INPUT_LIMIT and not session.delivery_blocked,
        no_next_model_receipt_yet=True), [loop.store.put(f"calls/{tag}-host-result.json", canonical_json_bytes(host))])
    row = dict(id=tag, usage=usage, elapsed_seconds=elapsed, executed=host["executed"],
        actual_operations=len(host["operations"]),
        within_selected_generation_reserve=usage["completion_tokens"] <= base.ACTOR["generation_reserve"])
    loop.log.append("invocation_completed", row, [])
    print(f"Completed {tag}: {usage['completion_tokens']} output tokens; operation executed={host['executed']}", flush=True)
    return row


def prepare(turn, message, review):
    base.require(1 <= turn <= MAX_TURNS and not (AREA / "DECISION.json").exists(), "session closed or allowance consumed")
    output = AREA / f"preparation-{turn:02d}"
    base.require(not output.exists(), "preparation exists; preserve it")
    if turn == 1:
        base.require(message == AREA / "OPENING.txt", "initial message differs")
        session, dialogue, preceding_feedback = initial_session(), [], []
    else:
        previous = AREA / f"turn-{turn-1:02d}"
        seal = base.base.verify_seal(previous)
        base.require(seal["disposition"] == "completed_assisted_turn" and seal["source_sha256"] == identities(), "previous turn/source differs")
        base.require(review and review.is_file() and review.read_text(encoding="utf-8").strip(), "direct review required before follow-up")
        session, dialogue = restore(previous, "final"), base.read(previous / "final-dialogue.json")
        preceding_feedback = base.read(previous / "final-preceding-feedback.json")
        base.require(not session.delivery_blocked and not session.submitted, "previous workspace is terminal")
    dialogue.append(dict(speaker="reviewer", text=message.read_text(encoding="utf-8")))
    output.mkdir(parents=True)
    adapter, counter = Adapter(dialogue, preceding_feedback), None
    try:
        counter = Counter(output, adapter)
        initial = counter.row(session.view())
        base.save(output, "starting-state.json", base.snapshot(session))
        base.save(output, "starting-candidate.json", base.candidate_bytes(session.candidate))
        base.save(output, "dialogue.json", dialogue)
        base.save(output, "preceding-feedback.json", adapter.preceding_feedback)
        base.save(output, "reviewer-message.txt", message.read_bytes())
        if review:
            base.save(output, "preceding-review.md", review.read_bytes())
        base.save(output, "PLAN.json", dict(turn=turn, maximum_replies=MAX_TURNS, maximum_operations=MAX_OPERATIONS,
            source_sha256=identities(), initial=initial, actor=base.ACTOR,
            status="qualified" if initial["prompt_tokens"] <= INPUT_LIMIT else "input_capacity_denied",
            completion_requests=0, previous_seal_sha256=sha256_file(previous / "RESPONSE_SEAL.json") if turn > 1 else None))
        base.require(initial["prompt_tokens"] <= INPUT_LIMIT, "input capacity denied")
    except BaseException as error:
        base.save(output, "FAILED.json", dict(error_type=type(error).__name__, error=str(error)))
        raise
    finally:
        files = base.base.file_inventory(output)
        base.save(output, "SEAL.json", dict(files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files))))
    print(f"Prepared T{turn:02d}: {initial['prompt_tokens']} input tokens; zero completions", flush=True)


def run_turn(turn, owner_direction):
    base.require(owner_direction.strip() and 1 <= turn <= MAX_TURNS and not (AREA / "DECISION.json").exists(), "closed or missing owner direction")
    package, output = AREA / f"preparation-{turn:02d}", AREA / f"turn-{turn:02d}"
    plan = base.read(package / "PLAN.json")
    seal = base.read(package / "SEAL.json")
    base.require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "preparation inventory differs")
    for row in seal["files"]:
        base.require(sha256_file(package / row["path"]) == row["sha256"], "prepared artifact differs")
    base.require(plan["status"] == "qualified" and plan["source_sha256"] == identities(), "prepared source differs")
    base.require(not output.exists(), "turn consumed; no retry")
    session, adapter = restore(package, "starting"), Adapter(base.read(package / "dialogue.json"),
                                                           base.read(package / "preceding-feedback.json"))
    output.mkdir()
    store, log = ArtifactStore(output), RunLog(output / "records.jsonl", f"parser-documentation-{turn}")
    log.append("turn_prepared", dict(owner_direction=owner_direction, turn=turn, maximum_replies=MAX_TURNS),
        [store.put("PLAN.json", (package / "PLAN.json").read_bytes()), store.put("SPEC.md", (AREA / "SPEC.md").read_bytes()),
         store.put("starting-dialogue.json", canonical_json_bytes(adapter.dialogue)),
         store.put("starting-preceding-feedback.json", canonical_json_bytes(adapter.preceding_feedback)),
         store.put("reviewer-message.txt", (package / "reviewer-message.txt").read_bytes())])
    server, model, _ = base.runtime_paths()
    args = SimpleNamespace(output=output, server=server, model=model)
    error, disposition = None, "completed_assisted_turn"
    try:
        with base.base.owned_runtime(args, store, log) as url:
            loop = Loop(output, store, log, url=url, task_module=adapter,
                source_check=lambda: base.verify_sources(plan["source_sha256"]))
            loop.snapshot(session, "starting")
            initial = loop.measure(session.view())
            selected = loop.cache[sha256_bytes(canonical_json_bytes(adapter.request_for(session.view())))]
            base.require(initial <= INPUT_LIMIT and all(selected[k] == plan["initial"][k] for k in
                ("prompt_tokens", "request_sha256", "native_sha256")), "actual input differs from preparation")
            selected["wire_request_sha256"] = plan["initial"]["wire_request_sha256"]
            receive(loop, session, f"T{turn:02d}", selected)
            loop.snapshot(session, "final")
            store.put("final-dialogue.json", canonical_json_bytes(adapter.dialogue))
            store.put("final-preceding-feedback.json", canonical_json_bytes(adapter.preceding_feedback))
    except BaseException as problem:
        error, disposition = problem, "stopped_without_retry"
        log.append("turn_stopped", dict(error_type=type(problem).__name__, error=str(problem)), [])
        for name, value in (("final-state.json", base.snapshot(session)),
                            ("final-candidate.json", base.candidate_bytes(session.candidate)),
                            ("final-dialogue.json", adapter.dialogue),
                            ("final-preceding-feedback.json", adapter.preceding_feedback)):
            if not (output / name).exists():
                store.put(name, value if isinstance(value, bytes) else canonical_json_bytes(value))
    finally:
        records, files = verify_records(output / "records.jsonl", output), base.base.file_inventory(output)
        base.save(output, "RESPONSE_SEAL.json", dict(disposition=disposition, turn=turn, actor=base.ACTOR,
            source_sha256=plan["source_sha256"], files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),
            record_count=len(records), sent_requests=sum(r["record_type"] == "invocation_started" for r in records),
            memory=base.base.memory_stats(output / "memory.csv"),
            runtime=base.base.runtime_evidence(output / "private-runtime/server.stderr.log"),
            port_free=base.base.port_free(base.base.PORT),
            private_runtime_files_local_only={p.name: sha256_file(p) for p in (output / "private-runtime").glob("*") if p.is_file()}))
    if error:
        raise error
    print(f"T{turn:02d} closed and sealed; direct review before another reply", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--turn", type=int, required=True)
    parser.add_argument("--message", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--owner-direction", default="")
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.turn, args.message or AREA / "OPENING.txt", args.review)
    else:
        run_turn(args.turn, args.owner_direction)
