from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import parser_roundtrip as task
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_session import ContributionSession


def candidate_with(extra):
    candidate, _ = task.starting_work()
    files = dict(candidate.files)
    anchor = "class InlineCommentStrippingTestCase(unittest.TestCase):"
    source = files["Lib/test/test_configparser.py"].decode()
    assert source.count(anchor) == 1
    files["Lib/test/test_configparser.py"] = source.replace(anchor, extra + "\n\n" + anchor).encode()
    return Candidate.create(files, max_file_bytes=candidate.max_file_bytes)


def check(candidate):
    session = ContributionSession(candidate, task.checker(), "Offline qualification")
    result = session.execute(dict(action="check", check_id="public", expected_candidate_id=candidate.candidate_id), lambda v: 500)
    assert result["accepted"]
    return result, json.loads(result["stdout"])


class RoundtripTaskTests(unittest.TestCase):
    def reference(self):
        return (task.AREA/"REFERENCE_TEST.py").read_text(encoding="utf-8")

    def test_baseline_has_no_new_coverage_and_fails_only_new_requirement(self):
        result, report = check(task.starting_work()[0])
        self.assertFalse(result["passed"])
        self.assertTrue(report["existing_work_preserved"])
        self.assertTrue(report["saved_suite"]["successful"])
        self.assertEqual(report["added_tests"], [])

    def test_real_transport_coverage_passes_and_detects_each_restoration_fault(self):
        result, report = check(candidate_with(self.reference()))
        self.assertTrue(result["passed"], report)
        self.assertTrue(report["transports"]["complete"])
        self.assertEqual(report["edited_suite"]["tests"], 357)
        self.assertTrue(all(not r["successful"] for r in report["restoration_faults"].values()))

    def test_only_default_pickle_protocol_is_insufficient(self):
        extra = self.reference().replace("range(pickle.HIGHEST_PROTOCOL + 1)", "(pickle.DEFAULT_PROTOCOL,)")
        result, report = check(candidate_with(extra))
        self.assertFalse(result["passed"])
        self.assertFalse(report["transports"]["complete"])

    def test_restoring_without_asserting_diagnostics_is_insufficient(self):
        extra = self.reference()
        lines = [line for line in extra.splitlines() if not line.lstrip().startswith("self.assertEqual")]
        result, report = check(candidate_with("\n".join(lines) + "\n"))
        self.assertFalse(result["passed"])
        self.assertTrue(report["transports"]["complete"])
        self.assertTrue(all(r["successful"] for r in report["restoration_faults"].values()))

    def test_existing_regression_changes_are_rejected(self):
        candidate = candidate_with(self.reference())
        files = dict(candidate.files)
        files["Lib/test/test_configparser.py"] = files["Lib/test/test_configparser.py"].replace(
            b"    def test_multilinecontinuationerror(self):\n", b"    def test_multilinecontinuationerror(self):\n        return\n")
        result, report = check(Candidate.create(files, max_file_bytes=candidate.max_file_bytes))
        self.assertFalse(result["passed"])
        self.assertFalse(report["existing_work_preserved"])


if __name__ == "__main__":
    unittest.main()
