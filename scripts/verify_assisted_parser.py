"""Verify and replay one closed assisted turn using its actual native counts."""
import argparse

import assisted_parser_session as task
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


def verify(turn):
    folder = task.AREA / f"turn-{turn:02d}"
    tag = f"T{turn:02d}"
    seal = task.base.base.verify_seal(folder)
    assert seal["disposition"] == "completed_assisted_turn" and seal["sent_requests"] == 1
    assert seal["source_sha256"] == task.identities() and seal["actor"] == task.base.ACTOR
    expected = {r["path"] for r in seal["files"]} | {"RESPONSE_SEAL.json"}
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*")
              if p.is_file() and "private-runtime" not in p.parts}
    assert actual == expected
    private = []
    for name, digest in seal["private_runtime_files_local_only"].items():
        path = folder / "private-runtime" / name
        if path.exists():
            assert sha256_file(path) == digest
            private.append(name)
    records = verify_records(folder / "records.jsonl", folder)
    by_digest, by_stem = {}, {}
    for record in records:
        if record["record_type"] != "native_input_prepared":
            continue
        row = record["payload"]
        stem = row["stem"]
        request = task.base.read(folder / (stem + "-endpoint-request.json"))
        native = (folder / (stem + "-native.txt")).read_bytes()
        assert native == task.base.expected_native(request)
        assert native == task.base.read(folder / (stem + "-template.json"))["prompt"].encode()
        assert row["prompt_tokens"] == len(task.base.read(folder / (stem + "-tokens.json"))["tokens"])
        assert sha256_bytes(native) == row["native_sha256"]
        assert sha256_bytes(canonical_json_bytes(request)) == row["request_sha256"]
        by_digest[row["request_sha256"]] = row
        by_stem[stem] = (request, row)
    session = task.restore(folder, "starting")
    dialogue = task.base.read(folder / "starting-dialogue.json")
    if turn == 1:
        assert canonical_json_bytes(task.base.snapshot(session)) == canonical_json_bytes(task.base.snapshot(task.initial_session()))
        assert dialogue == [dict(speaker="reviewer", text=(task.AREA / "OPENING.txt").read_text(encoding="utf-8"))]
    else:
        prior = task.AREA / f"turn-{turn-1:02d}"
        plan = task.base.read(folder / "PLAN.json")
        assert sha256_file(prior / "RESPONSE_SEAL.json") == plan["previous_seal_sha256"]
        assert (prior / "final-state.json").read_bytes() == canonical_json_bytes(task.base.snapshot(session))
        assert (prior / "final-candidate.json").read_bytes() == task.base.candidate_bytes(session.candidate)
        assert dialogue[:-1] == task.base.read(prior / "final-dialogue.json")
        assert dialogue[-1] == dict(speaker="reviewer", text=(folder / "reviewer-message.txt").read_text(encoding="utf-8"))
    adapter = task.Adapter(dialogue)
    def measure(view):
        digest = sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
        assert digest in by_digest, "replayed input was not actually measured"
        return by_digest[digest]["prompt_tokens"]
    def one(kind):
        rows = [r["payload"] for r in records if r["record_type"] == kind]
        assert len(rows) == 1, kind
        return rows[0]
    started = one("invocation_started")
    request, initial = by_stem[started["input_stem"]]
    assert request == adapter.request_for(session.view()) and measure(session.view()) == started["prompt_tokens"] <= task.INPUT_LIMIT
    assert all(initial[k] == task.base.read(folder / "PLAN.json")["initial"][k]
               for k in ("request_sha256", "native_sha256", "prompt_tokens"))
    session.mark_delivered(session.view())
    response = task.base.read(folder / f"calls/{tag}-endpoint-response.json")
    assert len(response["choices"]) == 1
    choice, usage = response["choices"][0], response["usage"]
    assert choice["finish_reason"] == "stop" and choice["message"]["content"].strip()
    for field, suffix in (("reasoning_content", "reasoning"), ("content", "content")):
        assert choice["message"].get(field, "").encode() == (folder / f"calls/{tag}-assistant-{suffix}.txt").read_bytes()
    assert usage["prompt_tokens"] == started["prompt_tokens"]
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"] <= task.base.ACTOR["context"]
    assert usage["prompt_tokens_details"]["cached_tokens"] == response["timings"]["cache_n"] == 0
    assert response["timings"]["predicted_n"] == usage["completion_tokens"]
    reply = task.base.read(folder / f"calls/{tag}-reply.json")
    assert reply == task.base.read(folder / f"calls/{tag}-assistant-content.txt")
    task.working_view.validate(reply, task.reply_schema()["json_schema"]["schema"])
    adapter.dialogue.append(dict(speaker="Qwen", text=reply["discussion"]))
    if "operation" in reply:
        result = session.execute(reply["operation"], measure)
        expected_host = dict(executed=True, action=reply["operation"], result=result)
    else:
        expected_host = dict(executed=False, discussion_only=True)
    assert task.base.read(folder / f"calls/{tag}-host-result.json") == expected_host
    processed = one("reply_processed")
    assert measure(session.view()) == processed["feedback_input_tokens"]
    assert processed["feedback_admitted"] == (measure(session.view()) <= task.INPUT_LIMIT and not session.delivery_blocked)
    assert (folder / "final-state.json").read_bytes() == canonical_json_bytes(task.base.snapshot(session))
    assert (folder / "final-candidate.json").read_bytes() == task.base.candidate_bytes(session.candidate)
    assert task.base.read(folder / "final-dialogue.json") == adapter.dialogue
    closed = one("runtime_closed")
    assert closed["owned_server_shutdown_verified"] and closed["dedicated_port_free"] and seal["port_free"]
    runtime = dict(full_offload=True, context_matches=True, q4_k_and_v=True, mtp_disabled=True,
                   truncation_observed=False, cuda_failure_observed=False)
    assert seal["runtime"] == runtime
    assert seal["memory"] == task.base.base.memory_stats(folder / "memory.csv")
    for kind in ("invocation_started", "post_response_runtime_check"):
        assert one(kind)["effective_runtime"] == runtime and one(kind)["memory"]["reference_is_advisory"]
    completed = one("invocation_completed")
    assert completed["usage"] == usage and completed["elapsed_seconds"] == one("response_received")["elapsed_seconds"]
    return dict(status="verified_closed_assisted_turn", turn=turn, no_model_requests=True,
        response_seal_sha256=sha256_file(folder / "RESPONSE_SEAL.json"), source_identities=len(seal["source_sha256"]),
        sealed_files=len(seal["files"]), records=len(records), native_inputs=len(by_digest),
        operation_replayed=expected_host["executed"], operation=reply.get("operation", {}).get("action"),
        accepted=expected_host.get("result", {}).get("accepted"), input_tokens=usage["prompt_tokens"],
        generated_tokens=usage["completion_tokens"], request_seconds=completed["elapsed_seconds"],
        reasoning_characters=len(choice["message"].get("reasoning_content", "")),
        final_characters=len(choice["message"]["content"]), memory=seal["memory"], private_files_verified=private,
        candidate_id=session.candidate.candidate_id, feedback_admitted=processed["feedback_admitted"],
        direct_review="Requires separate direct review of complete input, thinking, public reply and result.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--turn", type=int, required=True)
    args = parser.parse_args()
    value = verify(args.turn)
    task.base.save(task.AREA, f"VERIFICATION-{args.turn:02d}.json", value)
    print(value)
