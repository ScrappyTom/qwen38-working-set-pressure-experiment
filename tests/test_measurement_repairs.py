from __future__ import annotations

import copy
import unittest

from working_set_exp.candidate import Candidate
from working_set_exp.ecological_pilot_v2 import inspection_status
from working_set_exp.measurement import check_opportunities, check_opportunity
from working_set_exp.tools import SessionState, ToolExecutor


class InspectionTests(unittest.TestCase):
    def setUp(self):
        self.candidate = Candidate.create({"paged.txt": b"alpha\nbeta\ngamma\ndelta\n", "empty.txt": b""})
        self.state = SessionState(self.candidate, stage="continuation")
        self.executor = ToolExecutor(
            self.state, required_full_reads=(), prefork_checker=b"", public_checker=b"",
            final_target="unused", probe_id=None, probe_body=None,
        )
        self.pairs = []

    def read(self, start, count, path="paged.txt"):
        action = {"action": "read", "path": path, "start_line": start, "line_count": count}
        result = self.executor.execute(action)
        self.assertTrue(result["accepted"])
        self.pairs.append({"response": action, "result": result})
        return result

    def status(self, path="paged.txt"):
        return inspection_status(self.pairs, (path,), initial_candidate=self.candidate)

    def test_missing_middle_is_not_complete_despite_eof(self):
        self.read(1, 1)
        self.assertTrue(self.read(4, 1)["complete"])
        self.assertFalse(self.status()["all_completed_before_first_mutation"])
        self.assertNotIn("paged.txt", self.state.complete_reads)

    def test_adjacent_pages_complete_the_source(self):
        self.read(1, 2)
        self.read(3, 2)
        self.assertTrue(self.status()["all_completed_before_first_mutation"])

    def test_overlapping_out_of_order_pages_complete_the_source(self):
        self.read(3, 2)
        self.read(2, 2)
        self.read(1, 2)
        self.assertTrue(self.status()["all_completed_before_first_mutation"])

    def test_real_empty_file_requires_a_read_at_line_one(self):
        self.read(2, 1, "empty.txt")
        self.assertFalse(self.status("empty.txt")["all_completed_before_first_mutation"])
        self.read(1, 1, "empty.txt")
        self.assertTrue(self.status("empty.txt")["all_completed_before_first_mutation"])

    def test_empty_read_beyond_eof_does_not_erase_missing_coverage(self):
        self.read(1, 1)
        self.assertTrue(self.read(99, 1)["complete"])
        self.assertFalse(self.status()["all_completed_before_first_mutation"])

    def test_full_read_remains_complete_after_an_empty_beyond_eof_read(self):
        self.read(1, 4)
        self.read(99, 1)
        self.assertTrue(self.status()["all_completed_before_first_mutation"])

    def test_wrong_version_or_bytes_cannot_complete_coverage(self):
        self.read(1, 2)
        self.read(3, 2)
        original = copy.deepcopy(self.pairs)
        for field, value in (("candidate_id", "0" * 64), ("file_sha256", "0" * 64), ("content", "invented\n")):
            with self.subTest(field=field):
                self.pairs = copy.deepcopy(original)
                self.pairs[1]["result"][field] = value
                status = self.status()
                self.assertFalse(status["all_completed_before_first_mutation"])
                self.assertEqual(status["invalid_read_sequences"], [2])

    def test_only_reads_before_first_accepted_mutation_count(self):
        self.read(1, 2)
        # A rejected edit does not end the inspection window.
        self.pairs.append({"response": {"action": "patch"}, "result": {"accepted": False}})
        self.read(3, 1)
        self.pairs.append({"response": {"action": "patch"}, "result": {"accepted": True}})
        self.read(4, 1)
        status = self.status()
        self.assertEqual(status["first_mutation_sequence"], 4)
        self.assertFalse(status["all_completed_before_first_mutation"])

    def test_retrieval_of_old_result_is_not_a_new_source_read(self):
        result = self.read(1, 4)
        self.pairs = [{"response": {"action": "reopen_result", "handle": "RES-0001"}, "result": result}]
        self.assertFalse(self.status()["all_completed_before_first_mutation"])


class CorrectionOpportunityTests(unittest.TestCase):
    def test_first_check_with_three_calls_has_no_full_correction_cycle(self):
        value = check_opportunity(calls_used=21, call_limit=24, result={"accepted": True, "passed": True})
        self.assertEqual(value["calls_remaining_before"], 3)
        self.assertEqual(value["calls_remaining_after"], 2)
        self.assertFalse(value["check_patch_recheck_submit_fits_before"])
        self.assertIsNone(value["patch_recheck_submit_fits_after_failure"])

    def test_failed_check_records_actual_remaining_correction_allowance(self):
        for before, expected in ((4, True), (3, False), (1, False)):
            with self.subTest(before=before):
                value = check_opportunity(calls_used=24-before, call_limit=24, result={"accepted": True, "passed": False})
                self.assertEqual(value["calls_remaining_after"], before - 1)
                self.assertEqual(value["patch_recheck_submit_fits_after_failure"], expected)

    def test_rejected_check_consumes_allowance_without_claiming_a_failed_test(self):
        value = check_opportunity(calls_used=20, call_limit=24, result={"accepted": False})
        self.assertEqual(value["calls_remaining_after"], 3)
        self.assertIsNone(value["patch_recheck_submit_fits_after_failure"])

    def test_complete_history_counts_reads_rejections_and_later_checks(self):
        pairs = [
            {"response": {"action": "read"}, "result": {"accepted": True}},
            {"response": {"action": "check"}, "result": {"accepted": True, "passed": False}},
            {"response": {"action": "patch"}, "result": {"accepted": False}},
            {"response": {"action": "check"}, "result": {"accepted": True, "passed": True}},
        ]
        before = copy.deepcopy(pairs)
        values = check_opportunities(pairs, call_limit=5)
        self.assertEqual([row["calls_remaining_before"] for row in values], [4, 2])
        self.assertEqual([row["first_check"] for row in values], [True, False])
        self.assertEqual(pairs, before)

    def test_impossible_attempt_allowance_is_not_silently_clamped(self):
        with self.assertRaises(ValueError):
            check_opportunity(calls_used=24, call_limit=24, result={"accepted": True, "passed": False})


if __name__ == "__main__":
    unittest.main()
