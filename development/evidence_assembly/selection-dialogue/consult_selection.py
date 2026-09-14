"""Bind the existing nonexecuting consultation to actual C04/C05 evidence."""
import argparse
import copy
from pathlib import Path

import bounded_visibility_dialogue as dialogue
import pending_task as source_task
from working_set_exp.jsonutil import sha256_file

AREA = Path(__file__).resolve().parent
source = source_task.Task()
ROOT, SOURCE = source.ROOT, source.RUN
OLD = SOURCE / "calls/C05-wire-request.json"
NATIVE = SOURCE / "admission/I0010-native.txt"
PRECEDING = SOURCE / "calls/C04-assistant-content.txt"
SOURCE_SEAL = "c8d7f16179a81002211b588196a656d7eb2ffb7a96678174e6c4ac8c30908bc4"
task = dialogue.task
task.RUN, task.ACTOR = SOURCE, dict(source.ACTOR)
dialogue.AREA = AREA


def identities():
    paths = [Path(__file__), AREA / "test_selection.py", AREA / "SPEC.md",
             AREA / "SYSTEM.txt", AREA / "QUESTION_1.txt", OLD, NATIVE, PRECEDING,
             SOURCE / "RESPONSE_SEAL.json", SOURCE / "calls/C04-host-result.json"]
    return {**source.source_identities(),
            **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}


def original():
    task.require(sha256_file(SOURCE / "RESPONSE_SEAL.json") == SOURCE_SEAL, "closed attempt differs")
    inventory = {r["path"]: r for r in task.read(SOURCE / "RESPONSE_SEAL.json")["files"]}
    for path in (OLD, NATIVE, PRECEDING, SOURCE / "calls/C04-host-result.json"):
        task.require(sha256_file(path) == inventory[path.relative_to(SOURCE).as_posix()]["sha256"],
                     "archived evidence differs")
    old = task.read(OLD)
    task.require(old["chat_template_kwargs"] == dict(enable_thinking=True, reasoning_effort="medium"),
                 "original effort differs")
    old.pop("response_format")
    old["seed"] = 42
    return old


def request_for(turn, follow=None):
    task.require(turn in (1, 2), "consultation allowance exceeded")
    old = original()
    request = copy.deepcopy(old)
    supplied = ("BEGIN EXACT PRECEDING FINAL REPLY C04\n" + PRECEDING.read_text(encoding="utf-8") +
                "\nEND EXACT PRECEDING FINAL REPLY C04\n\n" +
                "\n\n".join("BEGIN EXACT C05 " + m["role"].upper() + " MESSAGE\n" + m["content"] +
                    "\nEND EXACT C05 " + m["role"].upper() + " MESSAGE" for m in old["messages"]))
    request["messages"] = [dict(role="system", content=(AREA / "SYSTEM.txt").read_text(encoding="utf-8")),
        dict(role="user", content=(AREA / "QUESTION_1.txt").read_text(encoding="utf-8") + "\n\n" + supplied)]
    if turn == 2:
        first = AREA / "turn-01"
        seal = task.base.verify_seal(first)
        task.require(seal["disposition"] == "completed_dialogue_turn" and
                     seal["source_sha256"] == identities(), "first turn/source differs")
        task.require(follow and follow.is_file() and (AREA / "D1_REVIEW.md").is_file(),
                     "review the complete first response before qualifying clarification")
        request["messages"] += [dict(role="assistant", content=(first / "calls/D1-assistant-content.txt").read_text(encoding="utf-8")),
                                dict(role="user", content=follow.read_text(encoding="utf-8"))]
    check = copy.deepcopy(request)
    check["messages"] = check["messages"][:2]
    check["chat_template_kwargs"]["reasoning_effort"] = "xhigh"
    task.base.validate_request(check)
    task.require(request["chat_template_kwargs"]["reasoning_effort"] == "medium", "effort drift")
    return request


def native_for(request):
    first = copy.deepcopy(request)
    first["messages"] = first["messages"][:2]
    native = task.delivery.native_for(first, original(), NATIVE.read_text(encoding="utf-8"))
    task.require(native.startswith(b"<|im_start|>system\n" + first["messages"][0]["content"].strip().encode()),
                 "unexpected reasoning prelude")
    if len(request["messages"]) == 4:
        tail = b"<|im_start|>assistant\n<think>\n"
        task.require(native.endswith(tail), "thinking envelope differs")
        native = native[:-len(tail)] + b"<|im_start|>assistant\n<think>\n\n</think>\n\n" + request["messages"][2]["content"].strip().encode() + b"<|im_end|>\n<|im_start|>user\n" + request["messages"][3]["content"].strip().encode() + b"<|im_end|>\n" + tail
    return native


dialogue.identities, dialogue.request_for, dialogue.native_for = identities, request_for, native_for


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run", "verify"))
    parser.add_argument("--turn", type=int, choices=(1, 2), required=True)
    parser.add_argument("--owner-direction", default="")
    args = parser.parse_args()
    follow = AREA / "FOLLOW_UP.txt" if args.turn == 2 else None
    if args.mode == "prepare":
        dialogue.prepare(args.turn, follow)
    elif args.mode == "run":
        dialogue.run(args.turn, follow, args.owner_direction)
    else:
        import verify_bounded_visibility as verifier
        result = verifier.verify(list(range(1, args.turn + 1)))
        task.save(AREA, f"VERIFICATION-{args.turn:02d}.json", result)
        print(result)
