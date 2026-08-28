from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from working_set_exp.bank import construct_bank, verify_bank
from working_set_exp.candidate import Candidate, CandidateError
from working_set_exp.fixture import load_fixture, load_truth
from working_set_exp.isolation import run_checker
from working_set_exp.p0 import build_p0
from working_set_exp.request import build_request
from working_set_exp.tools import SessionState, ToolError, ToolExecutor, strict_action


class CoreTests(unittest.TestCase):
    def test_empty_and_one_line_reads_are_exact(self):
        candidate = Candidate.create({"empty.py": b"", "one.py": b"x = 1\n"})
        state = SessionState(candidate)
        executor = ToolExecutor(
            state,
            required_full_reads=(),
            prefork_checker=b"print('ok')\n",
            public_checker=b"print('ok')\n",
            final_target="one.py",
            probe_id=None,
            probe_body=None,
        )
        empty = executor.execute({"action": "read", "path": "empty.py", "start_line": 1, "line_count": 1})
        self.assertTrue(empty["accepted"])
        self.assertEqual(empty["content"], "")
        self.assertTrue(empty["complete"])
        one = executor.execute({"action": "read", "path": "one.py", "start_line": 1, "line_count": 1})
        self.assertEqual(one["content"], "x = 1\n")
        beyond = executor.execute({"action": "read", "path": "one.py", "start_line": 3, "line_count": 1})
        self.assertEqual(beyond["content"], "")

    def test_candidate_rejects_oversized_line(self):
        with self.assertRaises(CandidateError):
            Candidate.create({"bad.py": ("x" * 513).encode("utf-8")})

    def test_p0_is_readable_and_task_independent(self):
        candidate = Candidate.create({"a.py": b"def f(x: int) -> int:\n    return x\n"})
        p0 = build_p0(candidate)
        self.assertEqual(p0["files"][0]["path"], "a.py")
        self.assertEqual(p0["files"][0]["symbols"][0]["name"], "f")
        self.assertTrue(p0["task_independent"])
        self.assertNotIn("relevance", str(p0).lower())

    def test_check_isolation_can_import_candidate(self):
        candidate = Candidate.create({"pkg/value.py": b"VALUE = 7\n"})
        result = run_checker(candidate, b"from pkg.value import VALUE\nassert VALUE == 7\nprint('pass')\n")
        self.assertTrue(result["passed"])

    def test_banks_reproduce_and_graders_discriminate(self):
        with tempfile.TemporaryDirectory(prefix="e2-bank-test-") as raw:
            bank = Path(raw) / "bank"
            construct_bank(bank, measured=True)
            self.assertTrue(verify_bank(bank)["verified"])
            for fixture_id in ("E2-SOURCE", "E2-OBSERVATION"):
                fixture = load_fixture(bank, fixture_id)
                self.assertFalse(run_checker(fixture.initial, fixture.prefork_checker)["passed"])
                truth = load_truth(bank, fixture_id)
                self.assertEqual(truth["fixture_id"], fixture_id)
                model_root = bank / "model_visible" / fixture_id
                visible_bytes = b"\n".join(path.read_bytes() for path in model_root.rglob("*") if path.is_file())
                self.assertNotIn(b"XP9:", visible_bytes)
                self.assertFalse((model_root / "checks").exists())

    def test_observation_body_is_execution_only(self):
        with tempfile.TemporaryDirectory(prefix="e2-leak-test-") as raw:
            bank = Path(raw) / "bank"
            construct_bank(bank, measured=True)
            fixture = load_fixture(bank, "E2-OBSERVATION")
            self.assertIn("wire_prefix=XP9:", fixture.probe_body or "")
            self.assertTrue((bank / "execution_only" / "E2-OBSERVATION" / "PROBE.txt").is_file())
            manifest = (bank / "execution_only" / "E2-OBSERVATION" / "FIXTURE.json").read_bytes()
            self.assertNotIn(b"wire_prefix", manifest)
            model_root = bank / "model_visible" / "E2-OBSERVATION"
            self.assertEqual(
                {path.name for path in model_root.iterdir()},
                {"TASK.txt", "candidate"},
            )
            request = build_request(
                fixture_id=fixture.fixture_id,
                task=fixture.task,
                candidate=fixture.initial,
                stage="prefix",
                visible_history=[],
                prefix_calls_used=0,
                continuation_calls_used=0,
                probe_id=fixture.probe_id,
                observations=[],
                reconstructed=False,
                fork_binding=None,
            )
            self.assertNotIn(b"XP9:", request)

    def test_strict_json_accepts_lexical_freedom_but_not_duplicates_or_prose(self):
        self.assertEqual(strict_action(b'{\n  "action": "begin"\n}'), {"action": "begin"})
        with self.assertRaises(ToolError):
            strict_action(b'{"action":"begin","action":"begin"}')
        with self.assertRaises(ToolError):
            strict_action(b'Here is the action: {"action":"begin"}')

    def test_known_good_candidates_pass_both_graders(self):
        with tempfile.TemporaryDirectory(prefix="e2-grade-test-") as raw:
            bank = Path(raw) / "bank"
            construct_bank(bank, measured=True)
            for fixture_id in ("E2-SOURCE", "E2-OBSERVATION"):
                fixture = load_fixture(bank, fixture_id)
                truth = load_truth(bank, fixture_id)
                known_root = bank / "evaluator_only" / fixture_id / "known_good"
                known = Candidate.create(
                    {
                        path.relative_to(known_root).as_posix(): path.read_bytes()
                        for path in known_root.rglob("*")
                        if path.is_file()
                    }
                )
                self.assertEqual(known.candidate_id, truth["known_good_candidate_id"])
                self.assertTrue(run_checker(known, fixture.public_checker)["passed"])
                hidden = (bank / "evaluator_only" / fixture_id / "hidden.py").read_bytes()
                self.assertTrue(run_checker(known, hidden)["passed"])


if __name__ == "__main__":
    unittest.main()
