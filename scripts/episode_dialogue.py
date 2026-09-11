"""Two once-only nonexecuting dialogue turns, reusing the qualified runtime."""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
import time

import prepare_investigation_loop as prep
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file

base, require = prep.base, prep.require
AREA = prep.ROOT / "development/episode_dialogue"
PILOT = prep.AREA / "run-001"
PILOT_SEAL = "cc3cf5d47d3fca38f9458964503ff9366f893e4e7ee4e5dfaf0bb5abeb9b27df"


class DialogueLog(prep.PilotLog):
    def append(self, kind, payload, artifacts):
        if kind == "invocation_completed":
            payload = {**payload, "within_proposed_generation_reserve":
                       payload["usage"]["completion_tokens"] <= prep.ACTOR["generation_reserve"]}
        return super().append(kind, payload, artifacts)


def identities():
    return {**prep.source_identities(), **{
        p.relative_to(prep.ROOT).as_posix(): sha256_file(p)
        for p in (Path(__file__), AREA / "SPEC.md", AREA / "SYSTEM.txt", AREA / "QUESTION_1.txt")}}


def initial_request():
    require(sha256_file(PILOT / "RESPONSE_SEAL.json") == PILOT_SEAL, "pilot seal differs")
    base.verify_seal(PILOT)
    old = load_json_strict((PILOT / "calls/L02-012-endpoint-request.json").read_bytes())
    request = copy.deepcopy(old)
    request.pop("response_format")
    request["model"], request["seed"] = base.ALIAS, 42
    supplied = "\n\n".join(
        "BEGIN HISTORICAL " + m["role"].upper() + " MESSAGE\n" + m["content"] +
        "\nEND HISTORICAL " + m["role"].upper() + " MESSAGE" for m in old["messages"])
    request["messages"] = [
        {"role": "system", "content": (AREA / "SYSTEM.txt").read_text(encoding="utf-8")},
        {"role": "user", "content": (AREA / "QUESTION_1.txt").read_text(encoding="utf-8") + "\n\n" + supplied}]
    base.validate_request(request)
    return request


def request_for(turn, follow_up):
    request = initial_request()
    if turn == 2:
        first = AREA / "turn-01"
        seal = base.verify_seal(first)
        require(seal["disposition"] == "completed_dialogue_turn" and seal["sent_requests"] == 1, "first turn incomplete")
        require(seal["source_sha256"] == identities(), "source changed between dialogue turns")
        require((first / "calls/E1-endpoint-request.json").read_bytes() == canonical_json_bytes(request), "conversation origin differs")
        answer = (first / "calls/E1-assistant-content.txt").read_bytes().decode("utf-8")
        require(follow_up is not None and follow_up.is_file(), "reviewed adaptive follow-up is required")
        text = follow_up.read_text(encoding="utf-8")
        require(bool(answer.strip()) and bool(text.strip()), "empty dialogue content")
        request["messages"] += [{"role": "assistant", "content": answer}, {"role": "user", "content": text}]
    return request


def run_turn(args):
    require(bool(args.owner_direction.strip()), "owner direction is required")
    request = request_for(args.turn, args.follow_up)
    pinned = identities()
    output = AREA / f"turn-{args.turn:02d}"
    require(not output.exists(), "dialogue turn consumed; no retry or replacement")
    output.mkdir(parents=True)
    args.output = output
    store, log = ArtifactStore(output), DialogueLog(output / "records.jsonl", f"episode-dialogue-{args.turn}")
    tag = f"E{args.turn}"
    log.append("turn_prepared", {"owner_direction": args.owner_direction, "maximum_dialogue_calls": 2,
        "turn": args.turn, "pilot_seal_sha256": PILOT_SEAL, "source_sha256": pinned,
        "history": "first final answer retained on turn 2; private thinking omitted"},
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
            log.append("invocation_started", {"id": tag, "prompt_tokens": count, **health}, [])
            print(f"{tag} dispatched: {count} native input tokens; nonexecuting dialogue", flush=True)
            started = time.monotonic()
            try:
                raw = base.post(url, "/v1/chat/completions", canonical_json_bytes(request), base.HTTP_TIMEOUT_SECONDS)
            except base.ResponseFailure as error:
                log.append("response_failed", {"id": tag, "error_type": type(error).__name__, "http_status": error.status},
                           [store.put(f"calls/{tag}-partial-response.bin", error.data)])
                raise
            outcome = base.receive_nonexecuting(store, log, {"id": tag, "stage": "episode_dialogue", "prompt_tokens": count}, raw, time.monotonic()-started)
            require(outcome["physical_tokens_remaining"] >= 0, "physical context accounting differs")
            require(pinned == identities(), "source changed during dispatch")
            log.append("post_response_runtime_check", {"id": tag, **prep.health(output)}, [])
            log.append("next_turn_decision", {"id": tag, "next_request_sent": False,
                "next_step": "seal_then_direct_review_before_adaptive_follow_up" if args.turn == 1 else "seal_then_review_and_source_check_proposal"}, [])
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--turn", type=int, choices=(1, 2), required=True)
    parser.add_argument("--follow-up", type=Path)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--owner-direction", required=True)
    run_turn(parser.parse_args())


if __name__ == "__main__":
    main()
