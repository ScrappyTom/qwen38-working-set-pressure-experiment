"""Qualify one actual regression/check route offline, never request inference."""
import argparse
import json
from pathlib import Path

import assisted_parser_session as task
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes


def qualify(output):
    task.base.require(not output.exists(), "preserve qualification")
    output.mkdir(parents=True)
    status = "incomplete"
    try:
        session = task.initial_session()
        before = session.candidate
        dialogue = [dict(speaker="reviewer", text=(task.AREA/"OPENING.txt").read_text(encoding="utf-8"))]
        adapter = task.Adapter(dialogue)
        counter = task.Counter(output, adapter)
        initial = counter.row(session.view())
        task.base.save(output, "setup.json", dict(assisted_group=task.GROUP,
            historical_actions=len(session.pairs), group_is_model_selected=False))
        task.base.save(output, "starting-candidate.json", task.base.candidate_bytes(before))
        old = "class InlineCommentStrippingTestCase(unittest.TestCase):\n"
        new = '''class AssistedQualificationTest(unittest.TestCase):
    def test_continuation_diagnostic(self):
        parser = configparser.ConfigParser(allow_no_value=True)
        with self.assertRaises(configparser.ParsingError) as caught:
            parser.read_string("[s]\\nflag\\n  continuation\\n", source="qualification.ini")
        self.assertIsInstance(caught.exception, configparser.MultilineContinuationError)
        self.assertEqual(caught.exception.args, ("qualification.ini", 3, "  continuation\\n"))


''' + old
        operation = dict(action="patch", path="Lib/test/test_configparser.py", old=old, new=new,
            expected_candidate_id=before.candidate_id,
            expected_file_sha256=before.file_sha256("Lib/test/test_configparser.py"))
        rows = []
        for discussion, action in (
            ("OFFLINE QUALIFICATION ONLY: save a diagnostic regression.", operation),
            ("OFFLINE QUALIFICATION ONLY: check the exact saved successor.", None)):
            task.base.require(counter.measure(session.view()) <= task.INPUT_LIMIT, "input cannot be delivered")
            session.mark_delivered(session.view())
            if action is None:
                action = dict(action="check", check_id="public", expected_candidate_id=session.candidate.candidate_id)
            adapter.dialogue.append(dict(speaker="Qwen (scripted, not model output)", text=discussion))
            result = session.execute(action, counter.measure)
            rows.append(dict(action=action, result=result, following=counter.row(session.view())))
            task.base.save(output, f"operation-{len(rows):02d}.json", rows[-1])
            task.base.save(output, f"candidate-{len(rows):02d}.json", task.base.candidate_bytes(session.candidate))
            task.base.require(result["accepted"] and not session.delivery_blocked, "scripted operation failed")
            adapter.dialogue.append(dict(speaker="reviewer (scripted)", text="Use the actual latest feedback for the next decision."))
        checked = json.loads(rows[-1]["result"]["stdout"])
        task.base.require(all(checked[k]["successful"] for k in ("upstream", "contract", "candidate_tests")) and
            checked["regression_detects_original"] and not checked["documentation_directive_present"] and
            not rows[-1]["result"]["passed"], "component verdicts differ")
        task.base.require(any(all(text in r["trace"] for text in
            ("original/Lib/configparser.py", "in _read", "AttributeError: 'NoneType' object has no attribute 'append'"))
            for r in checked["new_tests_on_original"]["details"]),
                          "original parser path was not exercised")
        task.base.require(all(session.candidate.file_map[p] == raw for p, raw in before.files
                              if p != "Lib/test/test_configparser.py"), "unrelated source changed")
        task.base.require(counter.measure(session.view()) <= task.INPUT_LIMIT, "check feedback cannot be delivered")
        session.mark_delivered(session.view())
        task.base.save(output, "route.json", rows)
        task.base.save(output, "final-candidate.json", task.base.candidate_bytes(session.candidate))
        status = "offline_assisted_contribution_qualified"
        task.base.save(output, "QUALIFICATION.json", dict(status=status, completion_requests=0, initial=initial,
            peak_input=max(r["prompt_tokens"] for r in counter.rows), native_inputs=len(counter.rows),
            actual_original_parsing_path_exercised=True, unchanged_library_and_other_files=True,
            broader_check_still_fails_for_documentation=True,
            qualification_only_not_model_work=True))
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
