"""Offline actual-source edit/check/feedback route for the new contribution."""
import argparse
import json
from pathlib import Path

import parser_documentation_session as task
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes


def qualify(output):
    task.base.require(not output.exists(), "preserve qualification")
    output.mkdir(parents=True)
    status = "incomplete"
    try:
        session = task.initial_session()
        before = session.candidate
        adapter = task.Adapter([dict(speaker="reviewer", text=(task.AREA/"OPENING.txt").read_text(encoding="utf-8"))])
        counter = task.Counter(output, adapter)
        initial = counter.row(session.view())
        task.base.save(output, "starting-candidate.json", task.base.candidate_bytes(before))
        task.base.save(output, "starting-state.json", task.base.snapshot(session))
        task.base.save(output, "setup.json", dict(assisted_group=task.GROUP,
            historical_actions=len(session.pairs), group_is_model_selected=False))
        rows = []
        # Scripted prose is qualification-only and never enters the live inputs.
        fragments = [
            ("   serialized without the trailing delimiter.\n",
             "   serialized without the trailing delimiter. When an indented non-comment\n"
             "   line is parsed as a continuation of a valueless option,\n"
             "   :exc:`MultilineContinuationError` is raised. Options with values still\n"
             "   support valid multiline values.\n"),
            (".. exception:: MissingSectionHeaderError\n",
             ".. exception:: MultilineContinuationError\n\n"
             "   A subclass of :exc:`ParsingError`, raised when an indented non-comment\n"
             "   line is parsed as a continuation of an option without a value. Such\n"
             "   options are accepted when *allow_no_value* is true. The exception's\n"
             "   ``source`` identifies the input; ``lineno`` is the one-based line\n"
             "   number, and ``line`` is the exact offending line, including its\n"
             "   newline if present. These three values are its constructor arguments.\n\n\n"
             ".. exception:: MissingSectionHeaderError\n"),
        ]
        for number, (old, new) in enumerate(fragments, 1):
            task.base.require(counter.measure(session.view()) <= task.INPUT_LIMIT, "input cannot be delivered")
            session.mark_delivered(session.view())
            reply = dict(discussion="OFFLINE SCRIPT: save documentation and obtain actual validation.",
                operation=dict(action="patch", path="Doc/library/configparser.rst", old=old, new=new,
                    expected_candidate_id=session.candidate.candidate_id,
                    expected_file_sha256=session.candidate.file_sha256("Doc/library/configparser.rst")),
                check_after="public")
            adapter.dialogue.append(dict(speaker="Qwen (scripted, not model output)", text=reply["discussion"]))
            host = task.process_reply(session, reply, counter.measure, adapter.preceding_feedback)
            following = counter.row(session.view())
            row = dict(reply=reply, host=host, following=following)
            rows.append(row)
            task.base.save(output, f"reply-{number:02d}.json", row)
            task.base.save(output, f"after-{number:02d}-candidate.json", task.base.candidate_bytes(session.candidate))
            task.base.require(len(host["operations"]) == 2 and all(r["result"]["accepted"] for r in host["operations"]),
                              "scripted contribution rejected")
            result = host["operations"][1]["result"]
            checked = json.loads(result["stdout"])
            task.base.require(all(checked[k]["successful"] for k in ("upstream", "contract", "candidate_tests")) and
                checked["regression_detects_original"] and result["passed"] == (number == 2), "actual check differs")
            native_request = adapter.request_for(session.view())
            shown = json.loads(native_request["messages"][1]["content"])
            task.base.require(shown["preceding_operation_feedback"][0]["result"] == host["operations"][0]["result"] and
                shown["workspace"]["latest_feedback"]["result"] == result, "complete receipt missing")
            task.base.require(following["prompt_tokens"] <= task.INPUT_LIMIT and not session.delivery_blocked,
                              "feedback cannot be delivered")
            # Actual next-model receipt is deliberately not claimed for this script.
            adapter.dialogue.append(dict(speaker="reviewer (scripted)", text="Use the actual feedback for the remaining work."))
        task.base.require(all(session.candidate.file_map[p] == raw for p, raw in before.files
                              if p != "Doc/library/configparser.rst"), "saved work changed")
        session.mark_delivered(session.view())
        reply = dict(discussion="OFFLINE SCRIPT: submit the current checked work.", operation=dict(
            action="submit", expected_candidate_id=session.candidate.candidate_id))
        adapter.dialogue.append(dict(speaker="Qwen (scripted, not model output)", text=reply["discussion"]))
        host = task.process_reply(session, reply, counter.measure, adapter.preceding_feedback)
        task.base.require(session.submitted and host["operations"][0]["result"]["accepted"], "submission failed")
        task.base.save(output, "submission.json", dict(reply=reply, host=host, following=counter.row(session.view())))
        task.base.save(output, "final-candidate.json", task.base.candidate_bytes(session.candidate))
        status = "offline_documentation_contribution_qualified"
        task.base.save(output, "QUALIFICATION.json", dict(status=status, completion_requests=0,
            initial=initial, peak_input=max(r["prompt_tokens"] for r in counter.rows),
            native_inputs=len(counter.rows), actual_operations=session.calls_used,
            starting_candidate=before.candidate_id, final_candidate=session.candidate.candidate_id,
            previous_library_test_and_support_unchanged=True, initial_check_failure_preserved=True,
            complete_edit_and_check_receipts_present=True, source_sufficiency_not_established_by_script=True))
        print(status, initial["prompt_tokens"], "initial;", max(r["prompt_tokens"] for r in counter.rows), "peak", flush=True)
    except BaseException as error:
        task.base.save(output, "FAILED.json", dict(error_type=type(error).__name__, error=str(error)))
        raise
    finally:
        files = task.base.base.file_inventory(output)
        task.base.save(output, "SEAL.json", dict(status=status, files=files,
            aggregate_sha256=sha256_bytes(canonical_json_bytes(files)), source_sha256=task.identities(), completion_requests=0))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    qualify(parser.parse_args().output)
