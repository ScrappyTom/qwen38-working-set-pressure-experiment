"""Bind the existing nonexecuting dialogue to actual assembled C08."""
import argparse
import copy
from pathlib import Path

import study
import bounded_visibility_dialogue as dialogue
from working_set_exp.jsonutil import sha256_file

AREA = Path(__file__).resolve().parent
ROOT = study.ROOT
SOURCE = study.Task("assembled").RUN
OLD = SOURCE / "calls/C08-wire-request.json"
NATIVE = SOURCE / "admission/I0022-native.txt"
QUALIFICATION = AREA / "qualification-002"
task = dialogue.task
task.RUN = SOURCE
task.ACTOR = dict(study.Task.ACTOR)
dialogue.AREA = AREA


def identities():
    paths = [Path(__file__), AREA / "qualify.py", AREA / "SPEC.md", AREA / "SYSTEM.txt",
             AREA / "QUESTION_1.txt", SOURCE / "RESPONSE_SEAL.json", OLD, NATIVE,
             SOURCE / "calls/C04-operation-01.json", SOURCE / "calls/C05-operation-01.json",
             SOURCE / "calls/C08-assistant-reasoning.txt", SOURCE / "calls/C08-assistant-content.txt",
             QUALIFICATION / "SEAL.json", QUALIFICATION / "after/Q2-wire-request.json",
             QUALIFICATION / "steps/Q2-result.json", AREA / "VERIFICATION-qualification-002.json"]
    return {**study.Task("assembled").source_identities(),
            **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}


def original():
    seal = study.read(SOURCE / "RESPONSE_SEAL.json")
    study.require(seal["aggregate_sha256"] ==
        "06a393015d3830c4885c795fba2786fd3dc18af65e2c411bae52e4885ccd68ae",
        "closed attempt differs")
    inventory = {r["path"]: r for r in seal["files"]}
    for p in (OLD, NATIVE):
        study.require(sha256_file(p) == inventory[p.relative_to(SOURCE).as_posix()]["sha256"],
                      "archived input differs")
    old = study.read(OLD)
    study.require(old["chat_template_kwargs"] == dict(enable_thinking=True, reasoning_effort="medium"),
                  "original effort differs")
    old.pop("response_format")
    old["seed"] = 42
    return old


def request_for(turn, follow=None):
    study.require(turn in (1, 2), "dialogue allowance exceeded")
    qualification = study.read(AREA / "VERIFICATION-qualification-002.json")
    study.require(qualification["status"] == "replayed_exactly" and qualification["new_model_requests"] == 0,
                  "qualify the existing route before consultation")
    old = original()
    request = copy.deepcopy(old)
    supplied = "\n\n".join("BEGIN EXACT ARCHIVED " + m["role"].upper() + " MESSAGE\n" +
        m["content"] + "\nEND EXACT ARCHIVED " + m["role"].upper() + " MESSAGE" for m in old["messages"])
    request["messages"] = [dict(role="system", content=(AREA / "SYSTEM.txt").read_text(encoding="utf-8")),
        dict(role="user", content=(AREA / "QUESTION_1.txt").read_text(encoding="utf-8") + "\n\n" + supplied)]
    if turn == 2:
        first = AREA / "turn-01"
        seal = task.base.verify_seal(first)
        study.require(seal["disposition"] == "completed_dialogue_turn" and
                      seal["source_sha256"] == identities(), "first turn/source differs")
        study.require(follow and follow.is_file() and (AREA / "D1_REVIEW.md").is_file(),
                      "review the complete first response before qualifying a clarification")
        request["messages"] += [dict(role="assistant", content=(first / "calls/D1-assistant-content.txt").read_text(encoding="utf-8")),
                                dict(role="user", content=follow.read_text(encoding="utf-8"))]
    check = copy.deepcopy(request)
    check["messages"] = check["messages"][:2]
    check["chat_template_kwargs"]["reasoning_effort"] = "xhigh"
    task.base.validate_request(check)
    study.require(request["chat_template_kwargs"]["reasoning_effort"] == "medium", "effort drift")
    return request


def native_for(request):
    old = original()
    first = copy.deepcopy(request)
    first["messages"] = first["messages"][:2]
    native = task.delivery.native_for(first, old, NATIVE.read_text(encoding="utf-8"))
    study.require(native.startswith(b"<|im_start|>system\n" + first["messages"][0]["content"].strip().encode()),
                  "unexpected reasoning prelude")
    if len(request["messages"]) == 4:
        tail = b"<|im_start|>assistant\n<think>\n"
        study.require(native.endswith(tail), "thinking envelope differs")
        native = native[:-len(tail)] + b"<|im_start|>assistant\n<think>\n\n</think>\n\n" + request["messages"][2]["content"].strip().encode() + b"<|im_end|>\n<|im_start|>user\n" + request["messages"][3]["content"].strip().encode() + b"<|im_end|>\n" + tail
    return native


dialogue.identities = identities
dialogue.request_for = request_for
dialogue.native_for = native_for


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
        study.save(AREA, f"VERIFICATION-{args.turn:02d}.json", result)
        print(result)
