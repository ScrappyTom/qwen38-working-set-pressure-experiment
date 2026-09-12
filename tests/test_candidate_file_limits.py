"""Explicit per-candidate admission policy and exact successor boundaries."""
import unittest
import json
from pathlib import Path
import sys

from working_set_exp.candidate import Candidate, CandidateError, MAX_FILE_BYTES, MAX_TOTAL_BYTES

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_investigation_loop as preparation


def source(size):
    marker = b"# marker\n"
    block = b"#" + b"x" * 126 + b"\n"
    count, remainder = divmod(size - len(marker), len(block))
    return marker + block * count + block[:remainder]


class CandidateFileLimitsTests(unittest.TestCase):
    def test_default_and_content_identity_remain_independent_of_explicit_policy(self):
        files = {"small.py": b"value = 1\n"}
        default = Candidate.create(files)
        selected = Candidate.create(files, max_file_bytes=1_048_576)
        self.assertEqual(default.max_file_bytes, MAX_FILE_BYTES)
        self.assertEqual(default.candidate_id, selected.candidate_id)
        self.assertEqual(default.files, selected.files)
        with self.assertRaises(CandidateError):
            Candidate.create({"large.py": source(MAX_FILE_BYTES + 1)})

    def test_successors_and_explicit_reconstruction_keep_the_selected_limit(self):
        candidate = Candidate.create({"large.py": source(26_000)}, max_file_bytes=32_768)
        successor, diff = candidate.patch(path="large.py", old="# marker\n", new="# repaired\n",
            expected_candidate_id=candidate.candidate_id,
            expected_file_sha256=candidate.file_sha256("large.py"))
        self.assertEqual(successor.max_file_bytes, 32_768)
        self.assertNotEqual(successor.candidate_id, candidate.candidate_id)
        self.assertIn("+# repaired", diff)
        extended = successor.with_files([*successor.files, ("note.py", b"# note\n")])
        self.assertEqual(extended.max_file_bytes, 32_768)
        restored = Candidate.create(extended.file_map, max_file_bytes=extended.max_file_bytes)
        self.assertEqual(restored, extended)
        with self.assertRaises(CandidateError):
            Candidate.create(extended.file_map)
        with self.assertRaisesRegex(CandidateError, "stale candidate"):
            successor.patch(path="large.py", old="# repaired\n", new="# next\n",
                expected_candidate_id=candidate.candidate_id,
                expected_file_sha256=candidate.file_sha256("large.py"))

    def test_exact_mebibyte_boundary_and_growth_rejection_preserve_predecessor(self):
        limit = 1_048_576
        body = source(limit)
        self.assertEqual(len(body), limit)
        candidate = Candidate.create({"large.py": body}, max_file_bytes=limit)
        original_id = candidate.candidate_id
        with self.assertRaisesRegex(CandidateError, "file exceeds"):
            Candidate.create({"large.py": body + b"x"}, max_file_bytes=limit)
        with self.assertRaisesRegex(CandidateError, "file exceeds"):
            candidate.patch(path="large.py", old="# marker\n", new="# marker plus\n",
                expected_candidate_id=original_id,
                expected_file_sha256=candidate.file_sha256("large.py"))
        self.assertEqual(candidate.candidate_id, original_id)
        self.assertEqual(candidate.file_map["large.py"], body)

    def test_invalid_policy_values_fail_before_admission(self):
        for value in (True, False, 0, -1, 1.5, "32768", MAX_TOTAL_BYTES + 1):
            with self.subTest(value=value), self.assertRaises(CandidateError):
                Candidate.create({"small.py": b""}, max_file_bytes=value)

    def test_visible_requirements_follow_the_actual_candidate_policy(self):
        request = json.loads((ROOT / "development/saved_work_continuation/preparation-001/initial-request.json").read_bytes())
        grammar = request["response_format"]
        default = preparation.tool_reference(grammar)
        historical = request["messages"][0]["content"]
        self.assertEqual(default, historical[historical.index("Visible tool reference"):])
        small = Candidate.create({"small.py": b"pass\n"})
        self.assertEqual(preparation.tool_reference(grammar, candidate=small), default)
        selected = Candidate.create({"large.py": source(26_000)}, max_file_bytes=1_048_576)
        visible = preparation.tool_reference(grammar, candidate=selected)
        self.assertEqual(visible, default.replace("at most 24,000 bytes\nper file",
                                               "at most 1,048,576 bytes\nper file", 1))


if __name__ == "__main__":
    unittest.main()
