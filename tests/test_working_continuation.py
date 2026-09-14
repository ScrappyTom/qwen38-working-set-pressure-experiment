import json
import unittest

import interpolation_contribution as task
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_session import ContributionSession

TEST_PATH, DOC_PATH = "Lib/test/test_configparser.py", "Doc/library/configparser.rst"
TEST_ANCHOR = "if __name__ == '__main__':\n    unittest.main()\n"
DOC_ANCHOR = ".. exception:: InterpolationSyntaxError\n"


def reference_files(extra=None, doc=True):
    files = task.starting_work()[0].file_map
    extra = (task.AREA / "REFERENCE_TEST.py").read_text(encoding="utf-8") if extra is None else extra
    files[TEST_PATH] = files[TEST_PATH].decode().replace(TEST_ANCHOR, extra + "\n\n" + TEST_ANCHOR).encode()
    if doc:
        addition = (task.AREA / "REFERENCE_DOC.txt").read_text(encoding="utf-8")
        files[DOC_PATH] = files[DOC_PATH].decode().replace(DOC_ANCHOR, addition + "\n" + DOC_ANCHOR).encode()
    return files


def check(files):
    candidate = Candidate.create(files, max_file_bytes=1_048_576)
    s = ContributionSession(candidate, task.checker(), "Offline acceptance qualification")
    result = s.execute(dict(action="check", check_id="public", expected_candidate_id=candidate.candidate_id), lambda view: 500)
    if not result.get("stdout"):
        raise AssertionError(result)
    return result, json.loads(result["stdout"])


class ContinuationTaskTests(unittest.TestCase):
    def test_saved_work_is_real_and_initial_group_is_preserved(self):
        s = task.initial_session()
        self.assertEqual(s.candidate.candidate_id, task.STARTING_ID)
        self.assertEqual(len(s.pairs), 55)
        self.assertEqual(s.ranges, task.starting_work()[1]["ranges"])
        self.assertFalse(s.check_state()["applies_to_current"])
        self.assertEqual(s.view()["allowance"]["requests_remaining"], 16)

    def test_baseline_missing_new_contribution_fails(self):
        result, report = check(task.starting_work()[0].file_map)
        self.assertFalse(result["passed"])
        self.assertTrue(report["saved_suite"]["successful"])
        self.assertTrue(report["existing_work_preserved"])
        self.assertEqual(report["added_tests"], [])

    def test_complete_reference_passes_and_detects_restoration_faults(self):
        result, report = check(reference_files())
        self.assertTrue(result["passed"], report)
        self.assertTrue(report["observed_paths"]["complete"])
        self.assertEqual(report["edited_suite"]["tests"], 360)
        self.assertTrue(all(not p["successful"] for p in report["restoration_faults"].values()))

    def test_only_default_protocol_is_incomplete(self):
        extra = (task.AREA / "REFERENCE_TEST.py").read_text(encoding="utf-8").replace(
            "range(pickle.HIGHEST_PROTOCOL + 1)", "(pickle.DEFAULT_PROTOCOL,)")
        result, report = check(reference_files(extra))
        self.assertFalse(result["passed"])
        self.assertFalse(report["observed_paths"]["complete"])

    def test_weak_transport_assertions_fail_fault_detection(self):
        extra = (task.AREA / "REFERENCE_TEST.py").read_text(encoding="utf-8")
        first, end = extra.index("                for result in restored:"), extra.index("                self.assertEqual(parser.get")
        extra = extra[:first] + extra[end:]
        result, report = check(reference_files(extra))
        self.assertFalse(result["passed"])
        self.assertTrue(report["observed_paths"]["complete"])
        self.assertTrue(all(p["successful"] for p in report["restoration_faults"].values()))

    def test_missing_doc_and_changed_prior_work_fail(self):
        result, _ = check(reference_files(doc=False))
        self.assertFalse(result["passed"])
        files = reference_files()
        files[TEST_PATH] = files[TEST_PATH].replace(b"    def test_multilinecontinuationerror_copy(self):\n",
            b"    def test_multilinecontinuationerror_copy(self):\n        return\n")
        result, report = check(files)
        self.assertFalse(result["passed"])
        self.assertFalse(report["existing_work_preserved"])
