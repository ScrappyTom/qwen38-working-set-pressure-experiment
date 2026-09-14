"""One frozen, monitored bounded-host continuation. No automatic retry."""
import argparse
from pathlib import Path
import time

import bounded_parser as task
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.measurement import check_opportunities
from working_set_exp.working_session import INPUT_LIMIT, MAX_ACTION_BYTES


class RunLog(RecordLog):
    def __init__(self, *args, task_module=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.task = task_module or task

    def append(self, kind, payload, artifacts):
        if kind == "runtime_prepared":
            payload = {**payload, "runtime_helper_actor": payload["actor"], "actor": self.task.ACTOR,
                       "memory_policy": self.task.pilot.cont.POLICY}
        return super().append(kind, payload, artifacts)


def verify_package(task_module=None):
    task = task_module or globals()["task"]
    seal = task.read(task.PACKAGE/"SEAL.json")
    task.require(seal["status"] == "offline_full_path_qualified" and seal["completion_requests"] == 0,
                 "offline qualification incomplete")
    task.require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "preparation seal differs")
    for row in seal["files"]:
        path = task.PACKAGE/row["path"]
        task.require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"], "qualified artifact differs")
    task.verify_sources(seal["source_sha256"])
    session = task.initial_session()
    task.require((task.PACKAGE/"initial-request.json").read_bytes() == canonical_json_bytes(task.request_for(session.view())) and
                 (task.PACKAGE/"starting-candidate.json").read_bytes() == task.candidate_bytes(session.candidate), "starting work differs")
    return task.read(task.PACKAGE/"QUALIFICATION.json")


def plan(task_module=None):
    task = task_module or globals()["task"]
    result = verify_package(task)
    return dict(schema="bounded-parser-execution-v1", actor=task.ACTOR, seed=task.SEED, maximum_requests=task.CALL_LIMIT,
                input_ceiling=INPUT_LIMIT, initial=result["initial"], source_sha256=task.source_identities(),
                preparation_seal_sha256=sha256_file(task.PACKAGE/"SEAL.json"),
                prior_run_seal_sha256=sha256_file(task.OLD/"RESPONSE_SEAL.json"),
                authorization="owner Proceed after bounded-host implementation and contribution recommendation",
                automatic_retry=False, reasoning_in_future_inputs=False, memory_policy=task.pilot.cont.POLICY)


class Loop:
    def __init__(self, output, store, log, *, url="offline", post=None, render=None, health=None,
                 source_check=None, initial=None, task_module=None):
        task = task_module or globals()["task"]
        self.task = task
        self.output, self.store, self.log, self.url = output, store, log, url
        self.post = post or task.base.post
        self.render = render or self.native_render
        self.health = health or (lambda: task.pilot.health(output))
        self.source_check = source_check or (lambda: None)
        self.initial = initial
        self.cache, self.counter, self.sent = {}, 0, 0
        self.operator_stop = None

    def stop_requested(self):
        """Drain the current operation; never cancel or invent its response."""
        task = self.task
        path = self.output / "STOP_REQUEST.txt"
        if self.operator_stop is not None:
            return True
        if not path.exists():
            return False
        raw = path.read_bytes()
        task.require(0 < len(raw) <= 4096 and raw.decode("utf-8").strip(), "invalid operator stop reason")
        self.operator_stop = dict(reason=raw.decode("utf-8").strip(),
            policy="finish_current_operation_then_close", requests_sent=self.sent,
            no_model_instruction_added=True)
        self.log.append("operator_stop_observed", self.operator_stop,
                        [self.store.put("operator-stop-request.txt", raw)])
        return True

    def native_render(self, request, stem):
        task = self.task
        def send(url, route, raw, timeout):
            task.require(route in {"/apply-template", "/tokenize"}, "native preparation route differs")
            suffix = "template" if route == "/apply-template" else "tokens"
            self.log.append("native_request_started",dict(route=route,completion_sent=False),
                            [self.store.put(stem+"-"+suffix+"-request.json",raw)])
            try:
                result = task.base.post(url,route,raw,timeout)
            except task.base.ResponseFailure as error:
                self.log.append("native_transport_stopped",dict(route=route,http_status=error.status),
                                [self.store.put(stem+"-"+suffix+"-partial.bin",error.data)])
                raise
            self.log.append("native_response_received",dict(route=route,completion_sent=False),
                            [self.store.put(stem+"-"+suffix+".json",result)])
            return result
        return task.pilot.render_only(self.url,request,post=send)

    def measure(self, view):
        task = self.task
        request = task.request_for(view)
        raw = canonical_json_bytes(request)
        digest = sha256_bytes(raw)
        if digest in self.cache:
            return self.cache[digest]["prompt_tokens"]
        self.source_check()
        self.health()
        self.counter += 1
        stem = f"admission/I{self.counter:04d}"
        self.log.append("input_constructed",dict(stem=stem,completion_sent=False),
                        [self.store.put(stem+"-endpoint-request.json",raw)])
        template,native,tokens,count = self.render(request,stem)
        task.require(raw == canonical_json_bytes(request) and load_json_strict(template)["prompt"].encode() == native and
                     len(load_json_strict(tokens)["tokens"]) == count and count > 0, "native input evidence differs")
        task.require(native == task.expected_native(request), "actual native rendering differs from qualified template envelope")
        row = dict(stem=stem,prompt_tokens=count,physical_generation_space=task.ACTOR["context"]-count,
                   request_sha256=digest,native_sha256=sha256_bytes(native))
        self.log.append("native_input_prepared",{**row,"completion_sent":False},
                        [self.store.put(stem+"-native.txt",native),self.store.put(stem+"-count.json",canonical_json_bytes(row))])
        self.cache[digest] = {**row,"request":request}
        return count

    def snapshot(self, session, stem):
        task = self.task
        artifacts=[self.store.put(stem+"-state.json",canonical_json_bytes(task.snapshot(session))),
                   self.store.put(stem+"-candidate.json",task.candidate_bytes(session.candidate))]
        for number,diff in session.diffs.items():
            name,raw=f"diffs/EVT-{number:04d}.patch",diff.encode()
            existing=self.output/name
            if existing.exists():
                task.require(existing.read_bytes()==raw,"immutable saved diff changed")
                artifacts.append(dict(path=name,size_bytes=len(raw),sha256=sha256_bytes(raw)))
            else:
                artifacts.append(self.store.put(name,raw))
        self.log.append("state_saved",dict(stem=stem,candidate_id=session.candidate.candidate_id),artifacts)

    def invoke(self, session):
        task = self.task
        task.require(not session.submitted and not session.delivery_blocked and self.sent < session.call_limit,
                     "terminal or allowance boundary")
        view = session.view()
        count = self.measure(view)
        task.require(count <= INPUT_LIMIT, "complete next input exceeds admission")
        digest = sha256_bytes(canonical_json_bytes(task.request_for(view)))
        selected = self.cache[digest]
        if self.sent == 0 and self.initial:
            for key in ("prompt_tokens","request_sha256","native_sha256"):
                task.require(selected[key] == self.initial[key], "first input differs from frozen qualification")
        raw = canonical_json_bytes(selected["request"])
        task.require(sha256_bytes(raw) == selected["request_sha256"], "prepared input changed")
        self.source_check()
        if self.stop_requested():
            return None
        session.mark_delivered(view)
        tag = f"C{self.sent+1:02d}"
        self.log.append("invocation_started",dict(id=tag,input_stem=selected["stem"],prompt_tokens=count,
            completion_sent=True,**self.health()),[])
        self.sent += 1
        print(f"Starting {tag}: {count} input; {task.ACTOR['context']-count} generation space",flush=True)
        started = time.monotonic()
        try:
            raw_response = self.post(self.url,"/v1/chat/completions",raw,task.base.HTTP_TIMEOUT_SECONDS)
        except task.base.ResponseFailure as error:
            self.log.append("transport_stopped",dict(id=tag,status=error.status,received_bytes_not_asserted_complete=True),
                            [self.store.put(f"calls/{tag}-partial-response.bin",error.data)])
            raise
        elapsed = time.monotonic()-started
        self.log.append("response_received",dict(id=tag,elapsed_seconds=elapsed),
                        [self.store.put(f"calls/{tag}-endpoint-response.json",raw_response)])
        response = load_json_strict(raw_response)
        task.require(len(response["choices"]) == 1, "response choice count differs")
        choice,usage = response["choices"][0],response["usage"]
        message = choice["message"]
        reasoning,content = message.get("reasoning_content") or "",message.get("content") or ""
        self.log.append("response_extracted",dict(id=tag,finish_reason=choice.get("finish_reason"),usage=usage),
                        [self.store.put(f"calls/{tag}-assistant-reasoning.txt",reasoning.encode()),
                         self.store.put(f"calls/{tag}-assistant-content.txt",content.encode())])
        task.require(choice.get("finish_reason") == "stop" and bool(content), "incomplete response; no action executed")
        task.require(not message.get("tool_calls") and not message.get("function_call"), "unexpected action channel")
        task.require(all(type(usage.get(k)) is int for k in ("prompt_tokens","completion_tokens","total_tokens")) and
                     usage["prompt_tokens"] == count and usage["completion_tokens"] > 0 and
                     usage["total_tokens"] == count+usage["completion_tokens"] <= task.ACTOR["context"], "response token accounting differs")
        task.require(usage.get("prompt_tokens_details",{}).get("cached_tokens") == 0 and response.get("timings",{}).get("cache_n") == 0,
                     "unexpected cache reuse")
        task.require(len(content.encode()) <= MAX_ACTION_BYTES, "complete action exceeds host allowance")
        self.source_check()
        self.log.append("post_response_runtime_check",dict(id=tag,**self.health()),[])
        action = load_json_strict(content.encode())
        task.require(type(action) is dict, "final output is not one action object")
        self.log.append("action_selected",dict(id=tag),[self.store.put(f"calls/{tag}-action.json",canonical_json_bytes(action))])
        processing = time.monotonic()
        result = session.execute(action,self.measure)
        self.log.append("action_executed",dict(id=tag,sequence=len(session.pairs),
            processing_and_admission_seconds=time.monotonic()-processing),
            [self.store.put(f"calls/{tag}-host-result.json",canonical_json_bytes(dict(action=action,result=result,executed=True)))])
        self.snapshot(session,"after/"+tag)
        row = dict(id=tag,usage=usage,elapsed_seconds=elapsed,action=action["action"],accepted=result["accepted"],
                   within_generation_reserve=usage["completion_tokens"] <= task.ACTOR["generation_reserve"],
                   physical_tokens_remaining=task.ACTOR["context"]-usage["total_tokens"])
        self.log.append("invocation_completed",row,[])
        print(f"Completed {tag}: {action['action']}, accepted={result['accepted']}, {usage['completion_tokens']} output, {elapsed:.1f}s",flush=True)
        return row

    def execute(self,session):
        started=time.monotonic()
        self.snapshot(session,"starting")
        disposition="action_allowance_exhausted"
        while self.sent < session.call_limit and not session.submitted:
            if self.stop_requested():
                disposition="operator_stopped"
                break
            if session.delivery_blocked:
                disposition="feedback_capacity_denied"
                break
            self.invoke(session)
        # A stop arriving during the final operation is still recorded, even if
        # that operation also consumed the allowance or achieved submission.
        if self.stop_requested() and not session.submitted:
            disposition="operator_stopped"
        if session.submitted:
            disposition="checked_submission"
        self.snapshot(session,"final")
        result=dict(disposition=disposition,sent_requests=self.sent,candidate_id=session.candidate.candidate_id,
                    current_check=session.check_state(),submitted=session.submitted,task_loop_seconds=time.monotonic()-started,
                    check_opportunities=check_opportunities(session.pairs[session.starting_archive_length:],call_limit=session.call_limit))
        self.log.append("task_loop_completed",result,[])
        return result


def run_once(args, task_module=None):
    task = task_module or globals()["task"]
    task.require(bool(args.owner_direction.strip()),"record owner direction")
    manifest=task.read(task.MANIFEST)
    task.require(args.manifest_sha256 == sha256_file(task.MANIFEST) and manifest == plan(task), "execution package differs")
    task.require(not task.RUN.exists(), "attempt exists; no retry or resume")
    server,model,_=task.runtime_paths()
    args.server,args.model,args.output=server,model,task.RUN
    task.RUN.mkdir()
    store,log=ArtifactStore(task.RUN),RunLog(task.RUN/"records.jsonl","bounded-parser-001")
    log.append("attempt_reserved",dict(owner_direction=args.owner_direction,manifest_sha256=args.manifest_sha256),
               [store.put("EXECUTION_MANIFEST.json",task.MANIFEST.read_bytes()),store.put("SPEC.md",(task.AREA/"SPEC.md").read_bytes())])
    error,outcome=None,None
    try:
        with task.base.owned_runtime(args,store,log) as url:
            loop=Loop(task.RUN,store,log,url=url,source_check=lambda:task.verify_sources(manifest["source_sha256"]),initial=manifest["initial"],task_module=task)
            outcome=loop.execute(task.initial_session())
            task.pilot.health(task.RUN)
    except BaseException as problem:
        error=problem
        log.append("attempt_stopped",dict(error_type=type(problem).__name__,error=str(problem)),[])
    finally:
        records=verify_records(task.RUN/"records.jsonl",task.RUN)
        files=task.base.file_inventory(task.RUN)
        seal=dict(disposition="stopped_without_retry" if error else outcome["disposition"],actor=task.ACTOR,
            source_sha256=manifest["source_sha256"],manifest_sha256=args.manifest_sha256,
            files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),record_count=len(records),
            sent_requests=sum(r["record_type"]=="invocation_started" for r in records),
            completed_responses=sum(r["record_type"]=="invocation_completed" for r in records),
            memory=task.base.memory_stats(task.RUN/"memory.csv"),
            runtime=task.base.runtime_evidence(task.RUN/"private-runtime/server.stderr.log"),
            port_free=task.base.port_free(task.base.PORT),
            private_runtime_files_local_only={p.name:sha256_file(p) for p in (task.RUN/"private-runtime").glob("*") if p.is_file()})
        store.put("RESPONSE_SEAL.json",canonical_json_bytes(seal))
    if error:
        raise error
    print("Attempt closed and sealed: "+outcome["disposition"],flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("freeze","run"),required=True)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--owner-direction",default="")
    args=parser.parse_args()
    if args.mode=="freeze":
        task.save(task.AREA,task.MANIFEST.name,plan())
        print(sha256_file(task.MANIFEST))
    else:
        run_once(args)
