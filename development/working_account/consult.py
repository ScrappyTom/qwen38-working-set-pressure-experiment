"""Separate, nonexecuting design interpretation of actual saved work."""
import argparse
import copy
from pathlib import Path

import task as candidate
import bounded_visibility_dialogue as dialogue
from working_set_exp.jsonutil import sha256_file

ROOT, AREA = candidate.ROOT, candidate.PARENT / "consultation"
SOURCE = ROOT / "development/evidence_assembly/recovery-run/run-001"
OLD = SOURCE / "calls/C08-wire-request.json"
PRECEDING = SOURCE / "calls/C04-assistant-content.txt"
task = dialogue.task
task.RUN, task.ACTOR = SOURCE, dict(candidate.ACTOR)
dialogue.AREA = AREA


def identities():
    paths = [Path(__file__), AREA / "SPEC.md", AREA / "SYSTEM.txt", AREA / "QUESTION_1.txt",
             OLD, PRECEDING, SOURCE / "RESPONSE_SEAL.json"]
    return {**candidate.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}


def original():
    seal = task.base.verify_seal(SOURCE)
    inventory = {r["path"]: r for r in seal["files"]}
    for p in (OLD, PRECEDING):
        task.require(sha256_file(p) == inventory[p.relative_to(SOURCE).as_posix()]["sha256"], "historical bytes differ")
    return task.read(OLD)


def request_for(turn, follow=None):
    task.require(turn in (1, 2), "consultation allowance exhausted")
    old = original()
    request = copy.deepcopy(old)
    request.pop("response_format")
    request["seed"] = 42
    supplied = ("BEGIN EXACT C04 FINAL REPLY\n" + PRECEDING.read_text(encoding="utf-8") +
        "\nEND EXACT C04 FINAL REPLY\n\n" + "\n\n".join(
        "BEGIN EXACT HISTORICAL C08 " + m["role"].upper() + " MESSAGE\n" + m["content"] +
        "\nEND EXACT HISTORICAL C08 " + m["role"].upper() + " MESSAGE" for m in old["messages"]))
    contract = candidate.policy.operating_reference(dict(tests="Tests and their preservation, excluding unfinished documentation.",
        examples="Execute added examples.", public="Tests, examples and preservation; public only authorizes submission."))
    request["messages"] = [dict(role="system", content=(AREA / "SYSTEM.txt").read_text(encoding="utf-8")),
        dict(role="user", content=(AREA / "QUESTION_1.txt").read_text(encoding="utf-8") + "\n\n" + supplied +
             "\n\nBEGIN PROSPECTIVE CONTRACT, NOT PRESENT IN THE HISTORICAL RUN\n" + contract +
             "\nEND PROSPECTIVE CONTRACT")]
    if turn == 2:
        first = task.base.verify_seal(AREA / "turn-01")
        task.require(first["disposition"] == "completed_dialogue_turn" and first["source_sha256"] == identities(), "review source differs")
        task.require(follow and follow.is_file() and (AREA / "D1_REVIEW.md").is_file(), "review first before clarification")
        request["messages"] += [dict(role="assistant", content=(AREA / "turn-01/calls/D1-assistant-content.txt").read_text(encoding="utf-8")),
                                dict(role="user", content=follow.read_text(encoding="utf-8"))]
    check = copy.deepcopy(request)
    check["messages"] = check["messages"][:2]
    check["chat_template_kwargs"]["reasoning_effort"] = "xhigh"
    task.base.validate_request(check)
    task.require(request["chat_template_kwargs"] == dict(enable_thinking=True, reasoning_effort="medium"), "effort differs")
    return request


def native_for(request):
    first = copy.deepcopy(request)
    first["messages"] = first["messages"][:2]
    first["seed"] = candidate.prior.SEED
    native = candidate.prior.expected_native(first)
    if len(request["messages"]) == 4:
        tail = b"<|im_start|>assistant\n<think>\n"
        task.require(native.endswith(tail), "native thinking suffix differs")
        native = native[:-len(tail)] + b"<|im_start|>assistant\n<think>\n\n</think>\n\n" + request["messages"][2]["content"].strip().encode() + b"<|im_end|>\n<|im_start|>user\n" + request["messages"][3]["content"].strip().encode() + b"<|im_end|>\n" + tail
    return native


dialogue.identities, dialogue.request_for, dialogue.native_for = identities, request_for, native_for

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run", "verify"))
    parser.add_argument("--turn", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    follow = AREA / "FOLLOW_UP.txt" if args.turn == 2 else None
    if args.mode == "prepare":
        dialogue.prepare(args.turn, follow)
    elif args.mode == "run":
        dialogue.run(args.turn, follow, "Proceed with the reviewed working-account and verification recommendation, outside active task work.")
    else:
        import verify_bounded_visibility as verifier
        value = verifier.verify(list(range(1, args.turn + 1)))
        task.save(AREA, f"VERIFICATION-{args.turn:02d}.json", value)
        print(value)
