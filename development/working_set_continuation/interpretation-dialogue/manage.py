"""Bind the existing nonexecuting consultation to actual C13, at medium effort."""
import argparse
import copy
from pathlib import Path

import bounded_visibility_dialogue as dialogue
import interpolation_contribution as source_task
from working_set_exp.jsonutil import sha256_file

AREA = Path(__file__).resolve().parent
ROOT = source_task.ROOT
SOURCE = source_task.RUN
OLD = SOURCE / "calls/C13-wire-request.json"
NATIVE = SOURCE / "admission/I0101-native.txt"
task = dialogue.task
task.RUN = SOURCE
task.ACTOR = dict(source_task.ACTOR)
dialogue.AREA = AREA


def identities():
    paths = [*sorted((ROOT / "src").rglob("*.py")),
             *sorted((ROOT / "scripts").glob("*.py")),
             Path(__file__), AREA / "SPEC.md", AREA / "SYSTEM.txt", AREA / "QUESTION_1.txt",
             SOURCE / "RESPONSE_SEAL.json", OLD, NATIVE,
             SOURCE / "calls/C12-operation-01.json",
             SOURCE / "calls/C13-assistant-reasoning.txt",
             SOURCE / "calls/C13-assistant-content.txt",
             SOURCE / "calls/C13-host-result.json",
             SOURCE / "calls/C14-wire-request.json",
             SOURCE / "after/C12-O01-candidate.json"]
    return {p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}


def original():
    seal = task.read(SOURCE / "RESPONSE_SEAL.json")
    task.require(seal["aggregate_sha256"] ==
                 "5893802b52cf3547e323b38f8629453427b1556e57117bccd656087295c0b555",
                 "closed attempt differs")
    inventory = {r["path"]: r for r in seal["files"]}
    for p in (OLD, NATIVE):
        task.require(sha256_file(p) == inventory[p.relative_to(SOURCE).as_posix()]["sha256"],
                     "archived input differs")
    old = task.read(OLD)
    task.require(old["chat_template_kwargs"] == dict(enable_thinking=True, reasoning_effort="medium"),
                 "original effort differs")
    old.pop("response_format")
    old["seed"] = 42
    return old


def request_for(turn, follow=None):
    task.require(turn in (1, 2), "dialogue allowance exceeded")
    old = original()
    request = copy.deepcopy(old)
    supplied = "\n\n".join("BEGIN EXACT ARCHIVED " + m["role"].upper() + " MESSAGE\n" +
        m["content"] + "\nEND EXACT ARCHIVED " + m["role"].upper() + " MESSAGE" for m in old["messages"])
    request["messages"] = [dict(role="system", content=(AREA / "SYSTEM.txt").read_text(encoding="utf-8")),
        dict(role="user", content=(AREA / "QUESTION_1.txt").read_text(encoding="utf-8") + "\n\n" + supplied)]
    if turn == 2:
        first = AREA / "turn-01"
        seal = task.base.verify_seal(first)
        task.require(seal["disposition"] == "completed_dialogue_turn" and
                     seal["source_sha256"] == identities(), "first turn/source differs")
        task.require(follow and follow.is_file() and (AREA / "D1_REVIEW.md").is_file(),
                     "complete first review and qualify a factual follow-up")
        request["messages"] += [dict(role="assistant", content=(first / "calls/D1-assistant-content.txt").read_text(encoding="utf-8")),
                                dict(role="user", content=follow.read_text(encoding="utf-8"))]
    # Reuse the frozen sampler/channel validator; medium's actual native envelope
    # is separately checked below and by /apply-template before dispatch.
    check = copy.deepcopy(request)
    check["messages"] = check["messages"][:2]
    check["chat_template_kwargs"]["reasoning_effort"] = "xhigh"
    task.base.validate_request(check)
    task.require(request["chat_template_kwargs"]["reasoning_effort"] == "medium", "effort drift")
    return request


def native_for(request):
    old = original()
    first = copy.deepcopy(request)
    first["messages"] = first["messages"][:2]
    native = task.delivery.native_for(first, old, NATIVE.read_text(encoding="utf-8"))
    task.require(native.startswith(b"<|im_start|>system\n" + first["messages"][0]["content"].strip().encode()),
                 "unexpected reasoning-effort prelude")
    if len(request["messages"]) == 4:
        tail = b"<|im_start|>assistant\n<think>\n"
        task.require(native.endswith(tail), "thinking envelope differs")
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
        task.save(AREA, f"VERIFICATION-{args.turn:02d}.json", result)
        print(result)
