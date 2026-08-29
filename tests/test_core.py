from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from working_set_exp.bank import construct_bank, verify_bank
from working_set_exp.acquisition_granularity import construct_bank as construct_acquisition_bank
from working_set_exp.acquisition_granularity import verify_bank as verify_acquisition_bank
from working_set_exp.candidate import Candidate, CandidateError
from working_set_exp.fixture import load_fixture, load_truth
from working_set_exp.isolation import run_checker
from working_set_exp.measured import build_executable_closure, construct_execution_package, verify_execution_package
from working_set_exp.p0 import build_p0
from working_set_exp.request import build_request, observation_directory_v2
from working_set_exp.tools import SessionState, ToolError, ToolExecutor, action_schema, strict_action


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

    def test_complete_read_is_union_of_exact_pages(self):
        candidate = Candidate.create({"paged.py": b"one\ntwo\nthree\n"})
        state = SessionState(candidate)
        executor = ToolExecutor(
            state,
            required_full_reads=("paged.py",),
            prefork_checker=b"print('ok')\n",
            public_checker=b"print('ok')\n",
            final_target="paged.py",
            probe_id=None,
            probe_body=None,
        )
        first = executor.execute({"action": "read", "path": "paged.py", "start_line": 1, "line_count": 2})
        self.assertFalse(first["complete"])
        self.assertNotIn("paged.py", state.complete_reads)
        second = executor.execute({"action": "read", "path": "paged.py", "start_line": 3, "line_count": 2})
        self.assertTrue(second["complete"])
        self.assertIn("paged.py", state.complete_reads)

    def test_maximal_bounded_read_removes_actor_page_size_decision(self):
        lines = [f"ROW_{index:04d} = {'x' * 80!r}\n" for index in range(1, 221)]
        candidate = Candidate.create({"ledger.py": "".join(lines).encode("utf-8")})
        state = SessionState(candidate)
        executor = ToolExecutor(
            state,
            required_full_reads=("ledger.py",),
            prefork_checker=b"print('ok')\n",
            public_checker=b"print('ok')\n",
            final_target="unused.py",
            probe_id=None,
            probe_body=None,
            read_mode="maximal_bounded_page",
        )
        first = executor.execute({"action": "read", "path": "ledger.py", "start_line": 1})
        self.assertTrue(first["accepted"])
        self.assertEqual(first["paging_mode"], "maximal_bounded_page")
        self.assertIsNotNone(first["next_start_line"])
        self.assertLessEqual(len(first["content"].encode("utf-8")), 18_000)
        second = executor.execute(
            {"action": "read", "path": "ledger.py", "start_line": first["next_start_line"]}
        )
        self.assertTrue(second["complete"])
        self.assertIn("ledger.py", state.complete_reads)
        rejected = executor.execute(
            {"action": "read", "path": "ledger.py", "start_line": 1, "line_count": 50}
        )
        self.assertFalse(rejected["accepted"])

    def test_observation_directory_v2_uses_literal_capture_order(self):
        rows = [
            {"handle": "OBS-0007", "sequence": 9, "action": "probe", "target": "alpha", "candidate_id": "a" * 64, "size_bytes": 5, "sha256": "b" * 64},
            {"handle": "OBS-0005", "sequence": 5, "action": "probe", "target": "beta", "candidate_id": "c" * 64, "size_bytes": 6, "sha256": "d" * 64},
        ]
        directory = observation_directory_v2(rows)
        self.assertEqual(directory["ordering"], "capture_ordinal_ascending")
        self.assertEqual([row["capture_ordinal"] for row in directory["entries"]], [1, 2])
        self.assertEqual([row["source_stage_sequence"] for row in directory["entries"]], [9, 5])
        self.assertNotIn("sequence_ascending", str(directory))

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

    def test_acquisition_granularity_bank_is_fresh_and_reproducible(self):
        with tempfile.TemporaryDirectory(prefix="e10-bank-test-") as raw:
            bank = Path(raw) / "bank"
            manifest = construct_acquisition_bank(bank)
            self.assertEqual(len(manifest["cases"]), 2)
            self.assertTrue(verify_acquisition_bank(bank)["verified"])
            for fixture_id in ("E10-PAGE-ALPHA", "E10-PAGE-BETA"):
                fixture = load_fixture(bank, fixture_id)
                self.assertEqual(len(fixture.required_full_reads), 2)
                self.assertNotIn(b"known_good", (bank / "model_visible" / fixture_id / "TASK.txt").read_bytes())

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

    def test_setup_response_schema_is_direct_object(self):
        schema = action_schema("setup", probe_id=None)["json_schema"]["schema"]
        self.assertEqual(schema["type"], "object")
        self.assertNotIn("oneOf", schema)

    def test_maximal_read_schema_omits_line_count(self):
        schema = action_schema("prefix", probe_id=None, read_mode="maximal_bounded_page")
        read = next(
            row for row in schema["json_schema"]["schema"]["oneOf"]
            if row["properties"]["action"].get("const") == "read"
        )
        self.assertEqual(read["required"], ["action", "path", "start_line"])
        self.assertNotIn("line_count", read["properties"])

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

    def test_measured_package_reconstructs_exact_initial_calls(self):
        root = Path(__file__).resolve().parents[1]
        experiment = root / "experiments" / "002_single_boundary_reconstruction"
        with tempfile.TemporaryDirectory(prefix="e2-pkg-test-") as raw:
            package = Path(raw) / "package"
            manifest = construct_execution_package(
                package,
                bank_root=experiment / "fresh_bank",
                schedule_path=experiment / "MEASURED_SCHEDULE.json",
                runtime_profile_path=experiment / "RUNTIME_PROFILE.json",
            )
            self.assertEqual(len(manifest["cells"]), 4)
            self.assertTrue(
                verify_execution_package(
                    package,
                    bank_root=experiment / "fresh_bank",
                    schedule_path=experiment / "MEASURED_SCHEDULE.json",
                    runtime_profile_path=experiment / "RUNTIME_PROFILE.json",
                )["verified"]
            )

    def test_executable_closure_covers_package_and_entrypoint(self):
        root = Path(__file__).resolve().parents[1]
        closure = build_executable_closure(root)
        paths = {row["path"] for row in closure["files"]}
        self.assertIn("src/working_set_exp/measured.py", paths)
        self.assertIn("scripts/run_measured.py", paths)


if __name__ == "__main__":
    unittest.main()
