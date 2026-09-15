"""One focused outside-run interpretation, with at most one reviewed follow-up."""
import argparse
import copy
from pathlib import Path

import task as candidate
import bounded_visibility_dialogue as dialogue
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file

ROOT = candidate.ROOT
AREA = Path(__file__).resolve().parent / "consultation"
SOURCE = candidate.PARENT / "url_continuation/run-001"
OLD = SOURCE / "calls/C02-wire-request.json"
THINKING = SOURCE / "calls/C02-assistant-reasoning.txt"
task = dialogue.task
task.RUN, task.ACTOR = SOURCE, dict(candidate.ACTOR)
dialogue.AREA = AREA


def identities():
    paths = [Path(__file__), AREA / "SPEC.md", AREA / "SYSTEM.txt", AREA / "QUESTION_1.txt",
             OLD, THINKING, SOURCE / "RESPONSE_SEAL.json"]
    return {**candidate.source_identities(),
            **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}


def original():
    seal = task.base.verify_seal(SOURCE)
    inventory = {r["path"]: r for r in seal["files"]}
    for path in (OLD, THINKING):
        task.require(sha256_file(path) == inventory[path.relative_to(SOURCE).as_posix()]["sha256"],
                     "historical bytes differ")
    return task.read(OLD)


def excerpt(old):
    state = task.read(OLD)
    import json
    state = json.loads(state["messages"][1]["content"])["workspace"]
    sources = state["working_set"]["sources"]
    target = next(s for s in sources if s["path"] == candidate.TEST)
    anchor = '    def test_attributes_bad_port(self):\n        """Check handling of invalid ports."""\n'
    task.require(target["content"].count(anchor) == 1, "visible anchor differs")
    packet = {k: copy.deepcopy(state[k]) for k in
              ("task", "candidate_id", "candidate_limits", "allowance", "archive",
               "current_check", "verification", "working_account", "latest_feedback")}
    packet["original_selection_extents"] = [
        {**{k: v for k, v in s.items() if k != "content"},
         "content_omitted_from_this_consultation": True} for s in sources]
    packet["verbatim_fragment_from_the_original_visible_test_source"] = {
        "path": target["path"], "candidate_id": target["candidate_id"],
        "file_sha256": target["file_sha256"], "content": anchor}
    lines = THINKING.read_text(encoding="utf-8").splitlines(keepends=True)
    return ("BEGIN EXACT HISTORICAL SYSTEM MESSAGE\n" + old["messages"][0]["content"] +
            "\nEND EXACT HISTORICAL SYSTEM MESSAGE\n\nBEGIN FOCUSED STATE EXCERPT\n" +
            canonical_json_bytes(packet).decode() + "\nEND FOCUSED STATE EXCERPT\n\n" +
            "BEGIN VERBATIM MODEL INTERPRETATION EXCERPT (NOT HOST FACTS)\n" +
            "".join(lines[642:679]) + "END MODEL INTERPRETATION EXCERPT")


def request_for(turn, follow=None):
    task.require(turn in (1, 2), "consultation allowance exhausted")
    old = original()
    request = copy.deepcopy(old)
    request.pop("response_format")
    request["seed"] = 42
    request["messages"] = [dict(role="system", content=(AREA / "SYSTEM.txt").read_text(encoding="utf-8")),
        dict(role="user", content=(AREA / "QUESTION_1.txt").read_text(encoding="utf-8") + "\n\n" + excerpt(old))]
    if turn == 2:
        first = task.base.verify_seal(AREA / "turn-01")
        task.require(first["disposition"] == "completed_dialogue_turn" and first["source_sha256"] == identities(),
                     "first response/source differs")
        task.require(follow and follow.is_file() and (AREA / "D1_REVIEW.md").is_file(), "review first")
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
    first["response_format"] = original()["response_format"]
    native = candidate.prior.expected_native(first)
    if len(request["messages"]) == 4:
        tail = b"<|im_start|>assistant\n<think>\n"
        task.require(native.endswith(tail), "native thinking suffix differs")
        native = (native[:-len(tail)] + b"<|im_start|>assistant\n<think>\n\n</think>\n\n" +
                  request["messages"][2]["content"].strip().encode() +
                  b"<|im_end|>\n<|im_start|>user\n" + request["messages"][3]["content"].strip().encode() +
                  b"<|im_end|>\n" + tail)
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
        dialogue.run(args.turn, follow, "Proceed with the recommended focused recovery consultation outside active task work.")
    else:
        import verify_bounded_visibility as verifier
        result = verifier.verify(list(range(1, args.turn + 1)))
        task.save(AREA, f"VERIFICATION-{args.turn:02d}.json", result)
        print(result)
