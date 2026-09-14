"""One frozen effort comparison over the unchanged uncoached contribution host."""
import argparse
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import parser_roundtrip as task
import run_uncoached_contribution as prior
from working_set_exp.contribution_reply import completion_request_bytes, process_reply
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.working_session import INPUT_LIMIT

AREA = Path(__file__).resolve().parent
PACKAGE = AREA / "preparation-001"
RUN = AREA / "run-001"
MANIFEST = AREA / "EXECUTION_MANIFEST.json"
BASE_RUN = task.RUN
RUNTIME = task.base.base
SCHEDULE = (
    dict(id="A01", seed=961208, effort="xhigh"),
    dict(id="A02", seed=961208, effort="medium"),
    dict(id="A03", seed=961209, effort="medium"),
    dict(id="A04", seed=961209, effort="xhigh"),
)
XHIGH = ("Reasoning effort is set to xhigh. Please think carefully through the task, "
         "validate key assumptions, consider plausible alternatives, and prioritize "
         "correctness, consistency, and clarity in the final answer.")


class Adapter(prior.Adapter):
    def __init__(self, row):
        task.require(row in SCHEDULE, "undeclared effort/seed/attempt")
        super().__init__(task)
        self.row = dict(row)
        self.ACTOR = {**task.ACTOR, "effort": row["effort"]}
        self.SEED = row["seed"]

    def request_for(self, view):
        request = super().request_for(view)
        request["seed"] = self.SEED
        request["chat_template_kwargs"] = dict(enable_thinking=True, reasoning_effort=self.row["effort"])
        return request

    def expected_native(self, request):
        task.require(request["seed"] == self.SEED and request["chat_template_kwargs"] ==
                     dict(enable_thinking=True, reasoning_effort=self.row["effort"]), "effort/seed drift")
        control = copy.deepcopy(request)
        control["seed"] = task.SEED
        control["chat_template_kwargs"] = dict(enable_thinking=True, reasoning_effort="xhigh")
        native = task.expected_native(control)
        head = ("<|im_start|>system\n" + XHIGH + "\n\n").encode()
        task.require(native.startswith(head), "pinned xhigh instruction/envelope differs")
        return native if self.row["effort"] == "xhigh" else b"<|im_start|>system\n" + native[len(head):]


class Log(RecordLog):
    def __init__(self, path, name, row, *, scripted=False):
        super().__init__(path, name)
        self.row, self.scripted = row, scripted

    def append(self, kind, payload, artifacts):
        payload = {**payload, "comparison_condition": self.row}
        if kind == "runtime_prepared":
            payload = {**payload, "runtime_default_actor": payload["actor"],
                       "actor": {**task.ACTOR, "effort": self.row["effort"]},
                       "effort_selected_by_request": True, "memory_policy": task.base.pilot.cont.POLICY}
        if self.scripted:
            payload.update(qualification_only=True, completion_sent=False)
            if kind in ("invocation_started", "response_received", "response_extracted", "invocation_completed"):
                payload["scripted_response_not_model_output"] = True
        return super().append(kind, payload, artifacts)


def sources():
    extra = [AREA / n for n in ("compare.py", "test_compare.py", "SPEC.md")]
    extra += [task.PACKAGE / "SEAL.json", task.PACKAGE / "cases/broad/calls/C03-wire-request.json",
              BASE_RUN / "RESPONSE_SEAL.json"]
    extra += [BASE_RUN / f"calls/C{i:02d}-reply.json" for i in range(1, 5)]
    return {**task.source_identities(), **{p.relative_to(task.ROOT).as_posix(): sha256_file(p) for p in extra}}


def seal(folder, status, bound, **values):
    inventory = RUNTIME.file_inventory(folder)
    private = folder / "private-runtime"
    value = dict(status=status, source_sha256=bound, files=inventory,
                 aggregate_sha256=sha256_bytes(canonical_json_bytes(inventory)), **values,
                 private_runtime_files_local_only={p.name: sha256_file(p) for p in private.glob("*") if p.is_file()})
    task.save(folder, "SEAL.json", value)
    return value


def verify_seal(folder):
    saved = task.read(folder / "SEAL.json")
    task.require(sha256_bytes(canonical_json_bytes(saved["files"])) == saved["aggregate_sha256"], "inventory differs")
    for row in saved["files"]:
        path = folder / row["path"]
        task.require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"], "sealed file changed")
    return saved


def make_loop(folder, row, bound, *, url, runtime_folder=None, scripted=False, post=None, initial=None):
    folder.mkdir()
    adapter = Adapter(row)
    store = ArtifactStore(folder)
    log = Log(folder / "records.jsonl", "effort-" + row["id"], row, scripted=scripted)
    loop = prior.Loop(folder, store, log, url=url, task_module=adapter, post=post, initial=initial,
                      health=lambda: task.base.pilot.health(runtime_folder or folder),
                      source_check=lambda: task.verify_sources(bound))
    return adapter, store, log, loop


def prepare(output=PACKAGE):
    prior.verify_package()  # The completed source host/package is still intact.
    task.require(not output.exists(), "preserve existing preparation; no retry")
    output.mkdir()
    bound = sources()
    store = ArtifactStore(output)
    log = Log(output / "records.jsonl", "effort-preparation", SCHEDULE[0], scripted=True)
    server, model, _ = task.runtime_paths()
    error, cases = None, []
    try:
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=output), store, log) as url:
            (output / "cases").mkdir()
            for row in SCHEDULE:
                session = task.initial_session()
                folder = output / "cases" / row["id"]
                def scripted_post(url, route, wire, timeout):
                    task.require(route == "/v1/chat/completions", "unexpected mocked route")
                    request = json.loads(wire)
                    task.require(wire == completion_request_bytes(adapter.request_for(session.view())), "scripted wire drift")
                    count = loop.cache[sha256_bytes(canonical_json_bytes(request))]["prompt_tokens"]
                    reply = task.read(BASE_RUN / f"calls/C{loop.sent:02d}-reply.json")
                    return canonical_json_bytes(dict(choices=[dict(finish_reason="stop", message=dict(
                        reasoning_content="", content=json.dumps(reply)))],
                        usage=dict(prompt_tokens=count, completion_tokens=1, total_tokens=count + 1,
                                   prompt_tokens_details=dict(cached_tokens=0)), timings=dict(cache_n=0)))
                adapter, _, _, loop = make_loop(folder, row, bound, url=url, runtime_folder=output,
                                                scripted=True, post=scripted_post)
                loop.measure(session.view())
                initial = {k: next(iter(loop.cache.values()))[k] for k in
                           ("prompt_tokens", "request_sha256", "native_sha256", "wire_request_sha256")}
                if row["id"] in ("A01", "A02"):
                    outcome = loop.execute(session)
                    task.require(outcome["submitted"] and outcome["actual_operations"] == 5 and loop.sent == 4,
                                 "scripted contribution failed")
                    # Counterfactual rendering of the actual prior broad-reading state.
                    broad = task.read(task.PACKAGE / "cases/broad/calls/C03-wire-request.json")
                    broad_view = json.loads(broad["messages"][1]["content"])
                    adapter.preceding_feedback[:] = broad_view["preceding_operation_feedback"]
                    broad_count = loop.measure(broad_view["workspace"])
                    task.require(broad_count <= INPUT_LIMIT, "prior broad state no longer fits")
                    replayed = replay(folder, row)
                else:
                    outcome, broad_count, replayed = None, None, None
                cases.append(dict(**row, initial=initial, scripted_outcome=outcome,
                                  broad_state_tokens=broad_count, replay=replayed, native_inputs=len(loop.cache)))
                task.save(folder, "QUALIFICATION.json", cases[-1])
            for pair in ((0, 1), (3, 2)):
                control = task.read(output / "cases" / SCHEDULE[pair[0]]["id"] / "admission/I0001-wire-request.json")
                variant = task.read(output / "cases" / SCHEDULE[pair[1]]["id"] / "admission/I0001-wire-request.json")
                changed = copy.deepcopy(control)
                changed["chat_template_kwargs"]["reasoning_effort"] = "medium"
                task.require(changed == variant, "paired request changed beyond effort")
            task.require(all(not r["payload"].get("completion_sent") for case in cases
                for r in verify_records(output/"cases"/case["id"]/"records.jsonl", output/"cases"/case["id"])),
                "preparation claims a model completion")
    except BaseException as problem:
        error = problem
        task.save(output, "FAILED.json", dict(error_type=type(problem).__name__, error=str(problem)))
    finally:
        task.save(output, "QUALIFICATION.json", dict(cases=cases, completion_requests=0,
            memory=RUNTIME.memory_stats(output/"memory.csv"), port_free=RUNTIME.port_free(RUNTIME.PORT)))
        seal(output, "failed_preserved" if error else "qualified_no_model_inference", bound, completion_requests=0)
    if error:
        raise error
    task.save(AREA, "EXECUTION_MANIFEST.json", dict(status="prepared", schedule=SCHEDULE, source_sha256=bound,
        cases=cases, preparation_seal_sha256=sha256_file(output/"SEAL.json"),
        max_requests_per_attempt=16, max_operations_per_attempt=24, input_limit=INPUT_LIMIT,
        actor=task.ACTOR, baseline_run_seal_sha256=sha256_file(BASE_RUN/"RESPONSE_SEAL.json"),
        owner_direction="Proceed with the recommended bounded comparison of reasoning effort on complete work",
        no_live_coaching=True, automatic_retry=False))
    print("Qualified:", len(cases), "initial requests; zero model inference", flush=True)


def verify_package():
    prior.verify_package()
    manifest = task.read(MANIFEST)
    task.require(manifest["schedule"] == list(SCHEDULE) and manifest["source_sha256"] == sources(), "comparison drift")
    task.verify_sources(manifest["source_sha256"])
    task.require(manifest["preparation_seal_sha256"] == sha256_file(PACKAGE/"SEAL.json"), "preparation seal drift")
    task.require(verify_seal(PACKAGE)["status"] == "qualified_no_model_inference", "preparation did not qualify")
    task.require(manifest["max_requests_per_attempt"] == 16 and manifest["max_operations_per_attempt"] == 24 and
                 manifest["input_limit"] == INPUT_LIMIT and manifest["actor"] == task.ACTOR, "allowance/actor drift")
    return manifest


def run_attempt(folder, row, manifest):
    folder.mkdir()
    adapter, session = Adapter(row), task.initial_session()
    store, log = ArtifactStore(folder), Log(folder/"records.jsonl", "effort-"+row["id"], row)
    log.append("attempt_reserved", dict(condition=row, manifest_sha256=sha256_file(MANIFEST)),
               [store.put("EXECUTION_MANIFEST.json", MANIFEST.read_bytes())])
    server, model, _ = task.runtime_paths()
    error, outcome, loop = None, None, None
    try:
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            initial = next(c["initial"] for c in manifest["cases"] if c["id"] == row["id"])
            loop = prior.Loop(folder, store, log, url=url, task_module=adapter, initial=initial,
                source_check=lambda: task.verify_sources(manifest["source_sha256"]))
            outcome = loop.execute(session)
    except BaseException as problem:
        error = problem
        log.append("attempt_stopped", dict(error_type=type(problem).__name__, error=str(problem)), [])
        task.save(folder, "stopped-state.json", task.snapshot(session))
        task.save(folder, "stopped-candidate.json", task.candidate_bytes(session.candidate))
        task.save(folder, "stopped-preceding-feedback.json", adapter.preceding_feedback)
    records = verify_records(folder/"records.jsonl", folder)
    natural_stop = error is not None and str(error) in ("incomplete response; no operation executed",
        "complete next input exceeds admission", "insufficient action allowance for the complete requested contribution")
    disposition = ("model_or_allowance_boundary" if natural_stop else "apparatus_stopped") if error else outcome["disposition"]
    result = dict(condition=row, disposition=disposition, outcome=outcome,
        sent_requests=sum(r["record_type"] == "invocation_started" for r in records),
        returned_responses=sum(r["record_type"] == "response_received" for r in records),
        actual_operations=session.calls_used, record_count=len(records),
        error=None if error is None else dict(type=type(error).__name__, message=str(error)),
        memory=RUNTIME.memory_stats(folder/"memory.csv"), runtime=RUNTIME.runtime_evidence(folder/"private-runtime/server.stderr.log"),
        port_free=RUNTIME.port_free(RUNTIME.PORT))
    seal(folder, disposition, manifest["source_sha256"], **result)
    task.require(result["port_free"], "runtime port not released")
    if error and not natural_stop:
        raise error
    return result


def execute():
    manifest = verify_package()
    task.require(not RUN.exists(), "comparison exists; no retry or implicit continuation")
    RUN.mkdir()
    task.save(RUN, "EXECUTION_MANIFEST.json", MANIFEST.read_bytes())
    results, error = [], None
    try:
        for row in SCHEDULE:
            print("Starting attempt", row, flush=True)
            result = run_attempt(RUN/row["id"], row, manifest)
            results.append(result)
            print("Closed attempt", row["id"], result["disposition"], flush=True)
            if result["disposition"] == "operator_stopped" or (RUN/row["id"]/"STOP_REQUEST.txt").exists():
                break
    except BaseException as problem:
        error = problem
    task.save(RUN, "RESULTS.json", dict(attempts=results,
        error=None if error is None else dict(type=type(error).__name__, message=str(error))))
    seal(RUN, "stopped" if error or len(results) < 4 else "schedule_completed", manifest["source_sha256"])
    if error:
        raise error


def replay(folder, row):
    """Exact native reconstruction and actual operation/checker replay, no inference."""
    records = verify_records(folder/"records.jsonl", folder)
    adapter, session = Adapter(row), task.initial_session()
    indexed = {}
    for record in records:
        if record["record_type"] != "native_input_prepared":
            continue
        value, stem = record["payload"], record["payload"]["stem"]
        request = task.read(folder/(stem+"-endpoint-request.json"))
        native = (folder/(stem+"-native.txt")).read_bytes()
        task.require(native == adapter.expected_native(request) == task.read(folder/(stem+"-template.json"))["prompt"].encode(),
                     "native reconstruction differs")
        task.require(value["prompt_tokens"] == len(task.read(folder/(stem+"-tokens.json"))["tokens"]), "native token count differs")
        task.require((folder/(stem+"-wire-request.json")).read_bytes() == completion_request_bytes(request), "wire differs")
        indexed[sha256_bytes(canonical_json_bytes(request))] = value["prompt_tokens"]
    def measure(view):
        return indexed[sha256_bytes(canonical_json_bytes(adapter.request_for(view)))]
    task.require(task.snapshot(session) == task.read(folder/"starting-state.json"), "initial state differs")
    completed = 0
    for record in records:
        if record["record_type"] != "invocation_started":
            continue
        tag = record["payload"]["id"]
        request = adapter.request_for(session.view())
        task.require((folder/f"calls/{tag}-wire-request.json").read_bytes() == completion_request_bytes(request), "sent input differs")
        task.require(measure(session.view()) == record["payload"]["prompt_tokens"], "sent token count differs")
        session.mark_delivered(session.view())
        response_path = folder/f"calls/{tag}-endpoint-response.json"
        if not response_path.exists():
            break
        response = task.read(response_path)
        choice = response["choices"][0]
        for field, suffix in (("content", "content"), ("reasoning_content", "reasoning")):
            task.require((choice["message"].get(field) or "").encode() == (folder/f"calls/{tag}-assistant-{suffix}.txt").read_bytes(),
                         "extracted response differs")
        if choice["finish_reason"] != "stop":
            break
        reply = task.read(folder/f"calls/{tag}-reply.json")
        task.require(reply == json.loads(choice["message"]["content"]), "selected reply differs")
        def intermediate(number, operation):
            task.require(operation == task.read(folder/f"calls/{tag}-operation-{number:02d}.json"), "actual operation differs")
            task.require(task.snapshot(session) == task.read(folder/f"after/{tag}-O{number:02d}-state.json"), "intermediate state differs")
            task.require(task.candidate_bytes(session.candidate) == (folder/f"after/{tag}-O{number:02d}-candidate.json").read_bytes(),
                         "intermediate work differs")
        try:
            actual = process_reply(session, reply, measure, adapter.preceding_feedback, intermediate)
        except ValueError as error:
            expected = "insufficient action allowance for the complete requested contribution"
            task.require(str(error) == expected and not (folder/f"calls/{tag}-host-result.json").exists()
                         and any(r["record_type"] == "attempt_stopped" and r["payload"]["error"] == expected for r in records),
                         "unmatched replay rejection")
            break
        task.require(actual == task.read(folder/f"calls/{tag}-host-result.json"), "host result differs")
        completed += 1
    final = "final" if (folder/"final-state.json").exists() else "stopped"
    task.require(task.snapshot(session) == task.read(folder/(final+"-state.json")), "final state differs")
    task.require(task.candidate_bytes(session.candidate) == (folder/(final+"-candidate.json")).read_bytes(), "final work differs")
    task.require(adapter.preceding_feedback == task.read(folder/(final+"-preceding-feedback.json")), "paired feedback differs")
    return dict(status="replayed_exactly", model_requests=0, replies=completed,
                operations=session.calls_used, native_inputs=len(indexed), submitted=session.submitted,
                candidate_id=session.candidate.candidate_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "execute", "verify"))
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode == "execute":
        execute()
    else:
        verify_seal(RUN)
        for row in SCHEDULE:
            folder = RUN/row["id"]
            if folder.exists():
                verify_seal(folder)
                print(row["id"], json.dumps(replay(folder, row)))
