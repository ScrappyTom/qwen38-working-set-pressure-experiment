"""Offline evidence verification for the two-turn development conversation."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import decision_dialogue as dialogue
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_file
from working_set_exp.runtime import tokenizer_count

require, base, prep = dialogue.require, dialogue.base, dialogue.prep
TOKENIZER_SHA = "d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c"


def verify(args):
    require(sha256_file(args.model) == prep.ACTOR["model_sha256"], "model identity differs")
    require(sha256_file(args.tokenizer) == TOKENIZER_SHA, "tokenizer identity differs")
    profile = SimpleNamespace(model_path=args.model, tokenizer_path=args.tokenizer)
    rows = []
    for turn in args.turns:
        folder, tag = dialogue.AREA / f"turn-{turn:02d}", f"D{turn}"
        seal = base.verify_seal(folder)  # Verify custody before accessing output.
        require(seal["disposition"] == "completed_dialogue_turn" and seal["sent_requests"] == 1, "turn incomplete")
        require(seal["actor"] == prep.ACTOR and seal["memory_policy"] == prep.cont.POLICY, "active settings differ")
        require(seal["source_sha256"] == dialogue.identities(), "execution source identities differ")
        public = {p.relative_to(folder).as_posix() for p in folder.rglob("*")
                  if p.is_file() and "private-runtime" not in p.relative_to(folder).parts}
        require(public == {p["path"] for p in seal["files"]} | {"RESPONSE_SEAL.json"}, "unsealed evidence")
        for name, digest in seal["private_runtime_files_local_only"].items():
            require(sha256_file(folder / "private-runtime" / name) == digest, "private evidence differs")
        records = verify_records(folder / "records.jsonl", folder)
        require(len(records) == seal["record_count"], "record count differs")
        require(records[0]["payload"]["owner_direction"] == "Proceed" and records[0]["payload"]["maximum_dialogue_calls"] == 2, "owner direction/scope differs")
        require(records[0]["payload"]["follow_up_sha256"] == (sha256_file(dialogue.AREA / "FOLLOW_UP.txt") if turn == 2 else None), "adaptive follow-up binding differs")

        def record(kind):
            matches = [r["payload"] for r in records if r["record_type"] == kind]
            require(len(matches) == 1, "expected one " + kind)
            return matches[0]

        for kind in ("runtime_closed", "turn_closed"):
            require(record(kind)["owned_server_shutdown_verified"] and record(kind)["dedicated_port_free"], "closure differs")
        runtime = record("runtime_prepared")
        require(runtime["actor"] == prep.ACTOR and runtime["memory_policy"] == prep.cont.POLICY, "runtime metadata differs")
        expected_health = dict(full_offload=True, context_matches=True, q4_k_and_v=True,
                               mtp_disabled=True, truncation_observed=False, cuda_failure_observed=False)
        require(seal["effective_runtime"] == expected_health, "effective runtime differs")
        require(seal["memory"] == base.memory_stats(folder / "memory.csv"), "memory summary differs")
        for kind in ("invocation_started", "post_response_runtime_check"):
            require(record(kind)["effective_runtime"] == expected_health and
                    record(kind)["memory"]["reference_is_advisory"], "invocation health differs")
        launch = load_json_strict((folder / "private-runtime/launch.json").read_bytes())
        require(sha256_file(Path(launch[0])) == prep.ACTOR["server_sha256"], "server identity differs")
        require(launch == base.launch_args(Path(launch[0]), args.model), "launch differs")
        path = lambda suffix: folder / "calls" / f"{tag}-{suffix}"
        raw = path("endpoint-request.json").read_bytes()
        request = load_json_strict(raw)
        require(raw == canonical_json_bytes(dialogue.request_for(turn, dialogue.AREA / "FOLLOW_UP.txt")), "conversation differs")
        require("response_format" not in request and "tools" not in request and "functions" not in request, "execution channel present")
        native = path("rendered-prompt.txt").read_bytes()
        require(load_json_strict(path("template-response.json").read_bytes())["prompt"].encode() == native, "native rendering differs")
        start = 0
        for message in request["messages"]:
            # The pinned template trims message-edge whitespace and prefixes
            # the system with its xhigh instruction. Inner content is exact.
            content = message["content"].strip().encode()
            found = native.find(content, start)
            require(found >= 0, "message absent from native input")
            start = found + len(content)
        n = tokenizer_count(profile, native)
        require(n == len(load_json_strict(path("tokenization.json").read_bytes())["tokens"])
                == record("invocation_prepared")["prompt_tokens"] <= prep.INPUT_CEILING, "input accounting differs")
        require(record("invocation_started")["prompt_tokens"] == n, "dispatch differs")
        response = load_json_strict(path("endpoint-response.json").read_bytes())
        require(len(response["choices"]) == 1 and response["choices"][0]["finish_reason"] == "stop", "response incomplete")
        message, usage, timings = response["choices"][0]["message"], response["usage"], response["timings"]
        for field, suffix in (("reasoning_content", "assistant-reasoning.txt"), ("content", "assistant-content.txt")):
            require(message[field].encode() == path(suffix).read_bytes(), "output field differs")
        require(usage["prompt_tokens"] == timings["prompt_n"] == n and usage["completion_tokens"] == timings["predicted_n"], "usage differs")
        require(usage["prompt_tokens_details"]["cached_tokens"] == timings["cache_n"] == 0, "cache reused")
        require(usage["total_tokens"] == n + usage["completion_tokens"] <= prep.ACTOR["context"], "physical accounting differs")
        host = load_json_strict(path("host-result.json").read_bytes())
        require(host == dict(candidate_mutated=False, executed=False, finish_reason="stop", mode="decision_dialogue",
                            nonexecuting_response_not_a_coding_continuation=True, tool_execution_enabled=False), "host execution differs")
        done = record("invocation_completed")
        require(done["host_result"] == host and done["usage"] == usage, "completion record differs")
        require(record("response_received")["elapsed_seconds"] == done["elapsed_seconds"], "request time differs")
        require(done["within_proposed_generation_reserve"] == (usage["completion_tokens"] <= prep.ACTOR["generation_reserve"]), "reserve metadata differs")
        require(record("next_turn_decision")["next_request_sent"] is False, "unexpected dispatch")
        require(record("next_turn_decision")["next_step"] == ("seal_then_direct_review_before_adaptive_follow_up" if turn == 1 else "seal_then_review_and_source_check_proposal"), "decision differs")
        memory_lines = (folder / "memory.csv").read_text().splitlines()
        stamps = [datetime.strptime(line.split(",")[0], "%Y/%m/%d %H:%M:%S.%f") for line in memory_lines]
        rows.append(dict(id=tag, seal_sha256=sha256_file(folder / "RESPONSE_SEAL.json"),
                         public_files=len(seal["files"]), records=len(records), input_tokens=n,
                         output_tokens=usage["completion_tokens"], request_seconds=done["elapsed_seconds"],
                         reasoning_characters=len(message["reasoning_content"]), final_characters=len(message["content"]),
                         retokenized_reasoning_text_tokens=tokenizer_count(profile,message["reasoning_content"].encode()),
                         retokenized_final_text_tokens=tokenizer_count(profile,message["content"].encode()),
                         physical_tokens_remaining=prep.ACTOR["context"]-usage["total_tokens"],
                         memory=seal["memory"], maximum_sampling_gap_seconds=max((b-a).total_seconds() for a,b in zip(stamps,stamps[1:]))))
    result = dict(verification_source_sha256=sha256_file(Path(__file__)), completion_requests=len(rows),
                  source_identities=len(dialogue.identities()), first_answer_retained_exactly=2 in args.turns, first_thinking_omitted=True,
                  raw_output_fields_exact=True, native_cli_counts_match=True, model_actions_executed=0,
                  pilot_seal_sha256=dialogue.PILOT_SEAL, turns=rows,
                  first_review_sha256=sha256_file(dialogue.AREA / "TURN_1_REVIEW.md") if (dialogue.AREA / "TURN_1_REVIEW.md").exists() else None,
                  follow_up_sha256=sha256_file(dialogue.AREA / "FOLLOW_UP.txt") if 2 in args.turns else None,
                  tokenization_note="Retokenized saved text is not original generated-token segmentation.")
    require(not args.output.exists(), "verification output exists")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(result))
    print(canonical_json_bytes(result).decode())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--turns", type=int, choices=(1,2), nargs="+", default=[1,2])
    verify(parser.parse_args())
