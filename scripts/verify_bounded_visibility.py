"""Verify completed consultation bytes and operational custody without inference."""
import argparse
from pathlib import Path

import bounded_visibility_dialogue as dialogue
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


def verify(turns):
    task = dialogue.task
    rows = []
    for turn in turns:
        folder = dialogue.AREA/f"turn-{turn:02d}"; tag=f"D{turn}"
        seal = task.base.verify_seal(folder)
        task.require(seal["disposition"] == "completed_dialogue_turn" and seal["sent_requests"] == 1, "turn incomplete")
        task.require(seal["source_sha256"] == dialogue.identities() and seal["actor"] == task.ACTOR and seal["seed"] == 42, "source or actor differs")
        expected_files={row["path"] for row in seal["files"]}|{"RESPONSE_SEAL.json"}
        actual_files={p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and "private-runtime" not in p.parts}
        task.require(actual_files == expected_files, "unsealed public files")
        verified_private=[]
        for name,digest in seal["private_runtime_files_local_only"].items():
            p=folder/"private-runtime"/name
            if p.exists():
                task.require(sha256_file(p) == digest, "private artifact differs")
                verified_private.append(name)
        records=verify_records(folder/"records.jsonl",folder)
        def event(kind):
            found=[r["payload"] for r in records if r["record_type"] == kind]
            task.require(len(found) == 1, "expected one "+kind)
            return found[0]
        closed=event("runtime_closed")
        task.require(closed["owned_server_shutdown_verified"] and closed["dedicated_port_free"] and seal["port_free"], "closure incomplete")
        task.require(seal["memory"] == task.base.memory_stats(folder/"memory.csv"), "memory summary differs")
        runtime=dict(full_offload=True,context_matches=True,q4_k_and_v=True,mtp_disabled=True,truncation_observed=False,cuda_failure_observed=False)
        task.require(seal["runtime"] == runtime, "runtime differs")
        for kind in ("invocation_started","post_response_runtime_check"):
            task.require(event(kind)["effective_runtime"] == runtime and event(kind)["memory"]["reference_is_advisory"], "runtime policy differs")
        request=dialogue.request_for(turn, dialogue.AREA/"FOLLOW_UP.txt" if turn==2 else None)
        path=lambda suffix:folder/f"calls/{tag}-{suffix}"
        task.require(path("endpoint-request.json").read_bytes() == canonical_json_bytes(request), "exact messages/settings differ")
        native=path("native.txt").read_bytes()
        task.require(native == dialogue.native_for(request) == task.read(path("template.json"))["prompt"].encode(), "native template differs")
        count=len(task.read(path("tokens.json"))["tokens"])
        plan=task.read(folder/"PLAN.json")
        task.require(count == plan["prompt_tokens"] == event("invocation_prepared")["prompt_tokens"] == event("invocation_started")["prompt_tokens"] <= 23808, "input accounting differs")
        response=task.read(path("endpoint-response.json"))
        task.require(len(response["choices"]) == 1, "response count differs")
        choice=response["choices"][0];message=choice["message"];usage=response["usage"]
        task.require(choice["finish_reason"] == "stop" and message["content"].strip(), "incomplete response")
        for field,suffix in (("reasoning_content","assistant-reasoning.txt"),("content","assistant-content.txt")):
            task.require(message.get(field,"").encode() == path(suffix).read_bytes(), "raw output differs")
        task.require(usage["prompt_tokens"] == count and usage["total_tokens"] == count+usage["completion_tokens"] <= 56576, "usage differs")
        task.require(usage["prompt_tokens_details"]["cached_tokens"] == response["timings"]["cache_n"] == 0, "cache reused")
        task.require(response["timings"]["predicted_n"] == usage["completion_tokens"], "generated counter differs")
        host=task.read(path("host-result.json"))
        task.require(host == dict(executed=False,tool_execution_enabled=False,mode="bounded_visibility_dialogue",finish_reason="stop",
            candidate_mutated=False,nonexecuting_response_not_a_coding_continuation=True), "dialogue executed work")
        done=event("invocation_completed")
        task.require(done["usage"] == usage and done["host_result"] == host and done["elapsed_seconds"] == event("response_received")["elapsed_seconds"], "recorded result differs")
        selected=event("selected_generation_measurement")
        task.require(selected["reserve"] == 32768 and selected["within_selected_reserve"] == (usage["completion_tokens"]<=32768), "reserve attribution differs")
        rows.append(dict(turn=turn,response_seal_sha256=sha256_file(folder/"RESPONSE_SEAL.json"),files=len(seal["files"]),records=len(records),
            source_identities=len(seal["source_sha256"]),input_tokens=count,output_tokens=usage["completion_tokens"],request_seconds=done["elapsed_seconds"],
            thinking_characters=len(message.get("reasoning_content","")),final_characters=len(message["content"]),memory=seal["memory"],
            local_private_files_verified=verified_private,normal_runtime_closure=True))
    return dict(status="completed_dialogue_verified",no_model_requests=True,rows=rows,
        direct_review="Complete thinking, final answer and implications require the separately recorded direct review.")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--turns",type=int,nargs="+",required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();dialogue.task.require(a.turns in ([1],[1,2]),"turn sequence differs")
    value=verify(a.turns)
    dialogue.task.save(a.output.parent,a.output.name,value)
    print(value)
