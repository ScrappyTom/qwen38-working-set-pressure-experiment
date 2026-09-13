"""One focused response, with at most one reviewed adaptive clarification."""
import argparse
import copy
from pathlib import Path
import time
from types import SimpleNamespace

import bounded_parser as task
from run_bounded_parser import RunLog
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count

AREA = task.AREA / "visibility-dialogue"
OLD_STEM = task.RUN / "admission/I0050"
SOURCE_SEAL = "402cd2e034cec912d09aa1380bff7d222a37a613c269d122505d2bff6ef0f961"


def identities():
    paths = [Path(__file__), task.ROOT/"scripts/run_bounded_parser.py", *sorted((task.ROOT/"src").rglob("*.py")),
        task.ROOT/"scripts/bounded_parser.py", task.ROOT/"scripts/run_interface_follow_on.py",task.ROOT/"tests/test_bounded_visibility.py",
        AREA/"SPEC.md", AREA/"SYSTEM.txt", AREA/"QUESTION_1.txt", task.RUN/"RESPONSE_SEAL.json",
        Path(str(OLD_STEM)+"-endpoint-request.json"), Path(str(OLD_STEM)+"-native.txt")]
    return {p.relative_to(task.ROOT).as_posix():sha256_file(p) for p in paths}


def request_for(turn, follow=None):
    task.require(sha256_file(task.RUN/"RESPONSE_SEAL.json") == SOURCE_SEAL, "source attempt differs")
    old = task.read(Path(str(OLD_STEM)+"-endpoint-request.json"))
    request = copy.deepcopy(old)
    request.pop("response_format")
    request["seed"] = 42
    supplied = "\n\n".join("BEGIN EXACT ARCHIVED "+m["role"].upper()+" MESSAGE\n"+m["content"]+
        "\nEND EXACT ARCHIVED "+m["role"].upper()+" MESSAGE" for m in old["messages"])
    request["messages"] = [dict(role="system",content=(AREA/"SYSTEM.txt").read_text(encoding="utf-8")),
        dict(role="user",content=(AREA/"QUESTION_1.txt").read_text(encoding="utf-8")+"\n\n"+supplied)]
    if turn == 2:
        first = AREA/"turn-01"
        seal = task.base.verify_seal(first)
        task.require(seal["disposition"] == "completed_dialogue_turn" and seal["source_sha256"] == identities(), "first response/source differs")
        task.require(follow and follow.is_file(), "reviewed clarification required")
        request["messages"] += [dict(role="assistant",content=(first/"calls/D1-assistant-content.txt").read_text(encoding="utf-8")),
            dict(role="user",content=follow.read_text(encoding="utf-8"))]
    check = copy.deepcopy(request); check["messages"] = check["messages"][:2]
    task.base.validate_request(check)
    return request


def native_for(request):
    old = task.read(Path(str(OLD_STEM)+"-endpoint-request.json"))
    old.pop("response_format"); old["seed"] = 42
    first = copy.deepcopy(request); first["messages"] = first["messages"][:2]
    native = task.delivery.native_for(first, old, Path(str(OLD_STEM)+"-native.txt").read_text(encoding="utf-8"))
    if len(request["messages"]) == 4:
        tail = b"<|im_start|>assistant\n<think>\n"
        task.require(native.endswith(tail), "thinking envelope differs")
        native = native[:-len(tail)] + b"<|im_start|>assistant\n<think>\n\n</think>\n\n" + request["messages"][2]["content"].strip().encode() + b"<|im_end|>\n<|im_start|>user\n" + request["messages"][3]["content"].strip().encode() + b"<|im_end|>\n" + tail
    return native


def prepare(turn, follow):
    output = AREA/f"preparation-{turn:02d}"
    task.require(not output.exists(), "preserve preparation")
    task.base.verify_seal(task.RUN)
    _, model, tokenizer = task.runtime_paths()
    task.require(sha256_file(tokenizer) == task.delivery.TOKENIZER_SHA and sha256_file(model) == task.ACTOR["model_sha256"], "runtime identity differs")
    request = request_for(turn, follow); native = native_for(request)
    count = tokenizer_count(SimpleNamespace(model_path=model, tokenizer_path=tokenizer), native)
    output.mkdir(parents=True)
    task.save(output, "request.json", request); task.save(output, "native.txt", native)
    status = "qualified" if count <= 23808 else "input_capacity_denied"
    task.save(output, "PLAN.json", dict(status=status, source_sha256=identities(), actor=task.ACTOR,
        seed=42, maximum_dialogue_requests=2, completion_requests=0, prompt_tokens=count,
        physical_generation_space=56576-count, request_sha256=sha256_bytes(canonical_json_bytes(request)),
        native_sha256=sha256_bytes(native), follow_up_sha256=sha256_file(follow) if follow else None))
    task.require(status == "qualified", "consultation input does not fit")
    print(turn, count, "input tokens; zero completions", flush=True)


def run(turn, follow, owner_direction):
    task.require(owner_direction.strip(), "record continuing owner direction")
    plan = task.read(AREA/f"preparation-{turn:02d}/PLAN.json")
    task.require(plan["status"] == "qualified" and plan["source_sha256"] == identities(), "prepared source differs")
    request = request_for(turn, follow); raw_request = canonical_json_bytes(request)
    task.require(sha256_bytes(raw_request) == plan["request_sha256"], "request differs")
    output = AREA/f"turn-{turn:02d}"; task.require(not output.exists(), "turn consumed; no retry")
    output.mkdir(); server, model, _ = task.runtime_paths()
    args = SimpleNamespace(output=output, server=server, model=model)
    store, log = ArtifactStore(output), RunLog(output/"records.jsonl", f"bounded-visibility-{turn}")
    tag = f"D{turn}"; failed = None; disposition = "completed_dialogue_turn"
    log.append("turn_prepared",dict(owner_direction=owner_direction, source_sha256=identities(), maximum_dialogue_requests=2,
        follow_up_sha256=plan["follow_up_sha256"]),[store.put("SPEC.md",(AREA/"SPEC.md").read_bytes()),
        store.put("PLAN.json",canonical_json_bytes(plan)),store.put(f"calls/{tag}-endpoint-request.json",raw_request)])
    try:
        with task.base.owned_runtime(args,store,log) as url:
            template,native,tokens,count = task.pilot.render_only(url,request)
            log.append("invocation_prepared",dict(id=tag,prompt_tokens=count,completion_sent=False),
                [store.put(f"calls/{tag}-template.json",template),store.put(f"calls/{tag}-native.txt",native),
                 store.put(f"calls/{tag}-tokens.json",tokens)])
            task.require(native == native_for(request) and sha256_bytes(native) == plan["native_sha256"] and count == plan["prompt_tokens"] <= 23808,
                "actual native input differs")
            task.require(plan["source_sha256"] == identities(), "source changed before dispatch")
            log.append("invocation_started",dict(id=tag,prompt_tokens=count,**task.pilot.health(output)),[])
            print(tag, "dispatched", count, "input tokens", flush=True)
            started = time.monotonic()
            try:
                raw = task.base.post(url,"/v1/chat/completions",raw_request,task.base.HTTP_TIMEOUT_SECONDS)
            except task.base.ResponseFailure as error:
                log.append("response_failed",dict(id=tag,http_status=error.status),[store.put(f"calls/{tag}-partial-response.bin",error.data)])
                raise
            outcome = task.base.receive_nonexecuting(store,log,dict(id=tag,stage="bounded_visibility_dialogue",prompt_tokens=count),raw,time.monotonic()-started)
            usage = outcome["usage"]
            task.require(usage["total_tokens"] == usage["prompt_tokens"]+usage["completion_tokens"] <= 56576, "usage differs")
            log.append("selected_generation_measurement",dict(id=tag,reserve=32768,within_selected_reserve=usage["completion_tokens"] <= 32768,
                helper_reserve=task.base.ACTOR["generation_reserve"],helper_flag_not_selected_policy=True),[])
            task.require(plan["source_sha256"] == identities(), "source changed during response")
            log.append("post_response_runtime_check",dict(id=tag,**task.pilot.health(output)),[])
    except BaseException as error:
        failed=error;disposition="stopped_without_retry"
        log.append("turn_stopped",dict(error_type=type(error).__name__,error=str(error)),[])
    finally:
        records=verify_records(output/"records.jsonl",output); files=task.base.file_inventory(output)
        task.save(output,"RESPONSE_SEAL.json",dict(disposition=disposition,actor=task.ACTOR,seed=42,
            source_sha256=plan["source_sha256"],files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),
            record_count=len(records),sent_requests=sum(r["record_type"]=="invocation_started" for r in records),
            memory=task.base.memory_stats(output/"memory.csv"),runtime=task.base.runtime_evidence(output/"private-runtime/server.stderr.log"),
            port_free=task.base.port_free(task.base.PORT),
            private_runtime_files_local_only={p.name:sha256_file(p) for p in (output/"private-runtime").glob("*") if p.is_file()}))
    if failed: raise failed
    print(tag, "closed and sealed; review before further work", flush=True)


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("prepare","run")); p.add_argument("--turn",type=int,choices=(1,2),required=True)
    p.add_argument("--follow-up",type=Path); p.add_argument("--owner-direction",default="")
    a=p.parse_args()
    prepare(a.turn,a.follow_up) if a.mode=="prepare" else run(a.turn,a.follow_up,a.owner_direction)
