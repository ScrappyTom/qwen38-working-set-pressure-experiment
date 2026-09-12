"""Offline reference and negative-control qualification of the complete task checks."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import configparser_backport as task
from working_set_exp.candidate import Candidate
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_file

OUTPUT = task.AREA / "reference-qualification-001"


def main():
    if OUTPUT.exists():
        raise FileExistsError("preserve existing qualification")
    OUTPUT.mkdir()
    value, status = None, "incomplete"

    def save(name, obj):
        (OUTPUT / name).write_bytes(canonical_json_bytes(obj))

    try:
        fixture = task.fixture()
        value = new_state("offline-reference", fixture)
        edits = task.read(task.AREA / "REFERENCE_EDITS.json")["rows"]
        rows = []
        for index, edit in enumerate(edits, 1):
            candidate = value.state.candidate
            raw = candidate.file_map[edit["path"]].decode()
            assert raw.count(edit["old"]) == 1
            line = raw[:raw.index(edit["old"])].count("\n") + 1
            result = value.execute(dict(action="read", path=edit["path"], start_line=max(1, line-3)))
            assert result["accepted"] and edit["old"] in result["content"]
            action = dict(action="patch", **edit, expected_candidate_id=candidate.candidate_id,
                          expected_file_sha256=candidate.file_sha256(edit["path"]))
            result = value.execute(action)
            assert result["accepted"] and value.state.candidate.max_file_bytes == task.FILE_LIMIT
            handle = f"RES-{len(value.pairs):04d}"
            saved = value.result_payloads[handle]
            reopened = value.execute(dict(action="reopen_result", handle=handle))
            assert reopened["accepted"] and reopened["exact_result_utf8"].encode() == saved
            rows.append(dict(edit=index, source_line=line, candidate_after=value.state.candidate.candidate_id))
        corrected = value.state.candidate
        variants = [("correct_reference", corrected, True), ("original", fixture.initial, False)]

        def variant(name, path, old, new):
            files = corrected.file_map
            text = files[path].decode()
            assert text.count(old) == 1, name
            files[path] = text.replace(old, new, 1).encode()
            variants.append((name, Candidate.create(files, max_file_bytes=task.FILE_LIMIT), False))

        target = "Lib/configparser.py"
        guard = "                    if cursect[optname] is None:\n                        raise MultilineContinuationError(fpname, lineno, line)\n"
        variant("exception_api_without_behavior", target, guard, "")
        variant("rejects_valid_continuations", target, "                    if cursect[optname] is None:\n", "                    if True:\n")
        variant("wrong_line_number", target,
            "        self.source = source\n        self.lineno = lineno\n        self.line = line\n",
            "        self.source = source\n        self.lineno = lineno + 1\n        self.line = line\n")
        variant("vacuous_added_test", "Lib/test/test_configparser.py", edits[3]["new"],
            "class MultilineContinuationBackportTest(unittest.TestCase):\n    def test_nothing(self):\n        self.assertTrue(True)\n\n\n" + edits[3]["old"])
        files = corrected.file_map
        files["Doc/library/configparser.rst"] = fixture.initial.file_map["Doc/library/configparser.rst"]
        variants.append(("documentation_unchanged", Candidate.create(files, max_file_bytes=task.FILE_LIMIT), False))

        outcomes = []
        for name, candidate, expected in variants:
            host = new_state(name, task.fixture())
            host.state.candidate = candidate
            result = host.execute(dict(action="check", check_id="public", expected_candidate_id=candidate.candidate_id))
            save(name + "-pair.json", host.pairs[-1])
            assert result["accepted"], result
            assert result["passed"] is expected and not result["streams_truncated"], (name, result)
            body = load_json_strict(result["stdout"].encode())
            # Check exact historical access to each actual checker result too.
            raw = host.result_payloads["RES-0001"]
            recovered = host.execute(dict(action="reopen_result", handle="RES-0001"))
            assert recovered["accepted"] and recovered["exact_result_utf8"].encode() == raw
            save(name + "-recovery-pair.json", host.pairs[-1])
            outcomes.append(dict(name=name, passed=result["passed"], candidate_id=candidate.candidate_id,
                upstream=body["upstream"], contract=body["contract"], added_tests=body.get("added_tests"),
                regression_detects_original=body["regression_detects_original"],
                documentation_directive_present=body["documentation_directive_present"],
                diagnostics_omitted_for_byte_limit=body.get("diagnostics_omitted_for_byte_limit", False)))
            print(name, result["passed"], "stdout bytes", result["stdout_size_bytes"], flush=True)
        for name, raw in corrected.files:
            path = OUTPUT / "reference-candidate" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        save("RESULTS.json", dict(status="reference_and_negative_controls_qualified", completion_requests=0,
            original_candidate=fixture.initial.candidate_id, reference_candidate=corrected.candidate_id,
            reference_edits=rows, outcomes=outcomes, actual_source_reads_and_edits=True,
            exact_reference_edit_and_check_recovery=True, doc_semantics_automatically_established=False,
            reference_is_not_actor_work=True, native_input_or_delivery_qualified=False))
        status = "reference_and_negative_controls_qualified"
    except BaseException as error:
        save("FAILED.json", dict(error_type=type(error).__name__, message=str(error)))
        raise
    finally:
        if value is not None:
            save("reference-pairs.json", value.pairs)
        save("SEAL.json", dict(status=status, completion_requests=0,
            source_sha256={p.relative_to(ROOT).as_posix():sha256_file(p) for p in
                (Path(__file__), Path(task.__file__), task.AREA / "PUBLIC_CHECK.py", task.AREA / "TASK.txt",
                 task.AREA / "REFERENCE_EDITS.json", ROOT / "src/working_set_exp/tools.py",
                 ROOT / "src/working_set_exp/candidate.py", ROOT / "src/working_set_exp/isolation.py")},
            files=[dict(path=p.relative_to(OUTPUT).as_posix(), size_bytes=p.stat().st_size, sha256=sha256_file(p))
                   for p in sorted(OUTPUT.rglob("*")) if p.is_file()]))


if __name__ == "__main__":
    main()
