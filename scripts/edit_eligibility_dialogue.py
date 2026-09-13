"""Bind the existing nonexecuting consultation to the reviewed C07 input."""
import argparse
from pathlib import Path

import bounded_visibility_dialogue as dialogue
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


task = dialogue.task
AREA = task.AREA / "edit-eligibility-dialogue"
EVIDENCE = task.AREA / "contribution-v2"
SOURCE = EVIDENCE / "run-001"
dialogue.AREA = AREA
dialogue.OLD_STEM = SOURCE / "admission/I0056"
dialogue.SOURCE_SEAL = "70bf434163e9365d5eb0f9aac40d22675790747800492a25de18638bd3b0d17f"
task.RUN = SOURCE
original_identities = dialogue.identities


def identities():
    extra = [Path(__file__), EVIDENCE/"DECISION.json", EVIDENCE/"VERIFICATION.json",
             EVIDENCE/"EDIT_ELIGIBILITY_PROBE.json", EVIDENCE/"native-edit-002/RESULT.json",
             SOURCE/"calls/C07-action.json"]
    return {**original_identities(), **{p.relative_to(task.ROOT).as_posix():sha256_file(p) for p in extra}}


dialogue.identities = identities


def requirements():
    decision = task.read(EVIDENCE / "DECISION.json")
    verified = task.read(EVIDENCE / "VERIFICATION.json")
    task.require(decision["all_complete_responses_directly_reviewed"] and
                 verified["actual_actions_replayed"] == 8 and verified["native_inputs_verified"] == 71,
                 "complete the closed contribution review first")
    probe = task.read(EVIDENCE / "EDIT_ELIGIBILITY_PROBE.json")
    qualified = task.read(EVIDENCE / "native-edit-002/RESULT.json")
    task.require(qualified["result"]["accepted"] and qualified["after_input_tokens"] == 23639,
                 "diagnostic edit lacks complete native qualification")
    question = (AREA / "QUESTION_1.txt").read_text(encoding="utf-8")
    for operation in (probe["supplied_action"], task.read(SOURCE/"calls/C07-action.json")):
        task.require(canonical_json_bytes(operation).decode() in question, "operation example differs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run", "verify"))
    parser.add_argument("--turn", type=int, choices=(1, 2), required=True)
    parser.add_argument("--follow-up", type=Path)
    parser.add_argument("--owner-direction", default="")
    args = parser.parse_args()
    requirements()
    if args.mode == "prepare":
        dialogue.prepare(args.turn, args.follow_up)
    elif args.mode == "run":
        dialogue.run(args.turn, args.follow_up, args.owner_direction)
    else:
        import verify_bounded_visibility as verification
        value = verification.verify(list(range(1, args.turn+1)))
        task.save(AREA, f"VERIFICATION-{args.turn:02d}.json", value)
        print(value)
