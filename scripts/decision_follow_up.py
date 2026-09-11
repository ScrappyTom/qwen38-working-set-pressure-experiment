"""Execute the unexposed continuation with four-message validation.

The consumed first-turn runner remains byte-identical. This adapter reuses its
request builder, runtime and custody helpers and pins the additional source.
"""
from __future__ import annotations
import argparse
import copy
from pathlib import Path
import time

import decision_dialogue as dialogue
from working_set_exp.custody import ArtifactStore,verify_records
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file

base,prep,require=dialogue.base,dialogue.prep,dialogue.require
AREA,PILOT_SEAL,DialogueLog=dialogue.AREA,dialogue.PILOT_SEAL,dialogue.DialogueLog


def identities():
    return {**dialogue.identities(),**{p.relative_to(prep.ROOT).as_posix():sha256_file(p)
            for p in (Path(__file__),prep.ROOT/"tests/test_decision_follow_up.py")}}


def validated_request(follow_up):
    request=dialogue.request_for(2,follow_up)
    require([m["role"] for m in request["messages"]]==["system","user","assistant","user"], "continuation roles differ")
    require(all(set(m)=={"role","content"} and isinstance(m["content"],str) and m["content"].strip() for m in request["messages"]), "continuation message shape differs")
    require(not any(key in request for key in ("response_format","tools","functions")), "execution channel in dialogue")
    # The qualified helper deliberately validates a fresh pair. Apply its
    # sampler/budget checks to the unchanged first pair, without discarding
    # either continuation message from the actual request.
    first_pair=copy.deepcopy(request)
    first_pair["messages"]=first_pair["messages"][:2]
    base.validate_request(first_pair)
    return request


def run_turn(args):
    require(bool(args.owner_direction.strip()), "owner direction is required")
    require(args.turn == 2, "only the unexposed second turn is supported")
    request = validated_request(args.follow_up)
    pinned = identities()
    require(not any(key in request for key in ("response_format", "tools", "functions")), "execution channel in dialogue")
    output = AREA / f"turn-{args.turn:02d}"
    require(not output.exists(), "dialogue turn consumed; no retry or replacement")
    output.mkdir(parents=True)
    args.output = output
    store, log = ArtifactStore(output), DialogueLog(output / "records.jsonl", f"decision-dialogue-{args.turn}")
    tag = f"D{args.turn}"
    log.append("turn_prepared", {"owner_direction": args.owner_direction, "maximum_dialogue_calls": 2,
        "turn": args.turn, "pilot_seal_sha256": PILOT_SEAL, "source_sha256": pinned,
        "history": "first consultation final retained; its thinking omitted; archived task response may be quoted on turn 2",
        "follow_up_sha256": sha256_file(args.follow_up) if args.turn == 2 else None},
        [store.put("SPEC.md", (AREA / "SPEC.md").read_bytes()),
         store.put(f"calls/{tag}-endpoint-request.json", canonical_json_bytes(request))])
    failure, disposition = None, "completed_dialogue_turn"
    try:
        with base.owned_runtime(args, store, log) as url:
            template, native, tokenized, count = prep.render_only(url, request)
            log.append("invocation_prepared", {"id": tag, "prompt_tokens": count,
                "input_ceiling": prep.INPUT_CEILING, "completion_sent": False},
                [store.put(f"calls/{tag}-template-response.json", template),
                 store.put(f"calls/{tag}-rendered-prompt.txt", native),
                 store.put(f"calls/{tag}-tokenization.json", tokenized)])
            require(count <= prep.INPUT_CEILING, "native input exceeds reserve-based capacity; no dispatch")
            health = prep.health(output)
            require(pinned == identities(), "source changed before dispatch")
            require(canonical_json_bytes(validated_request(args.follow_up)) == canonical_json_bytes(request), "conversation changed before dispatch")
            log.append("invocation_started", {"id": tag, "prompt_tokens": count, **health}, [])
            print(f"{tag} dispatched: {count} native input tokens; nonexecuting dialogue", flush=True)
            started = time.monotonic()
            try:
                raw = base.post(url, "/v1/chat/completions", canonical_json_bytes(request), base.HTTP_TIMEOUT_SECONDS)
            except base.ResponseFailure as error:
                log.append("response_failed", {"id": tag, "error_type": type(error).__name__, "http_status": error.status},
                           [store.put(f"calls/{tag}-partial-response.bin", error.data)])
                raise
            outcome = base.receive_nonexecuting(store, log, {"id": tag, "stage": "decision_dialogue", "prompt_tokens": count}, raw, time.monotonic()-started)
            require(outcome["physical_tokens_remaining"] >= 0, "physical context accounting differs")
            require(pinned == identities(), "source changed during dispatch")
            require(canonical_json_bytes(validated_request(args.follow_up)) == canonical_json_bytes(request), "conversation changed during dispatch")
            log.append("post_response_runtime_check", {"id": tag, **prep.health(output)}, [])
            log.append("next_turn_decision", {"id": tag, "next_request_sent": False,
                "next_step": "seal_then_direct_review_before_adaptive_follow_up" if args.turn == 1 else "seal_then_review_and_source_check_proposal"}, [])
        closed = verify_records(output / "records.jsonl", output)[-1]
        require(closed["record_type"] == "runtime_closed" and closed["payload"]["owned_server_shutdown_verified"]
                and closed["payload"]["dedicated_port_free"], "dialogue runtime lifecycle incomplete")
    except BaseException as error:
        failure, disposition = error, "stopped_without_retry"
        detail = str(error)
        for path in (args.model, args.server, output):
            detail = detail.replace(str(path), "<local path>")
        log.append("turn_stopped", {"error_type": type(error).__name__, "error": detail}, [])
    finally:
        log.append("turn_closed", {"disposition": disposition, "dedicated_port_free": base.port_free(base.PORT),
            "owned_server_shutdown_verified": not base.running_process_ids(args.server.name)}, [])
        records = verify_records(output / "records.jsonl", output)
        files = base.file_inventory(output)
        base.write_json(output / "RESPONSE_SEAL.json", {"disposition": disposition, "actor": prep.ACTOR,
            "memory_policy": prep.cont.POLICY, "source_sha256": pinned,
            "sent_requests": sum(r["record_type"] == "invocation_started" for r in records),
            "record_count": len(records), "files": files, "aggregate_sha256": sha256_bytes(canonical_json_bytes(files)),
            "memory": base.memory_stats(output / "memory.csv"),
            "effective_runtime": base.runtime_evidence(output / "private-runtime/server.stderr.log"),
            "private_runtime_files_local_only": {p.name: sha256_file(p) for p in (output / "private-runtime").glob("*") if p.is_file()}})
    if failure:
        raise failure
    print(f"{tag} closed and sealed; response awaits direct review", flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--follow-up",type=Path,required=True)
    parser.add_argument("--model",type=Path,required=True)
    parser.add_argument("--server",type=Path,required=True)
    parser.add_argument("--owner-direction",required=True)
    parser.set_defaults(turn=2)
    run_turn(parser.parse_args())


if __name__=="__main__":main()
