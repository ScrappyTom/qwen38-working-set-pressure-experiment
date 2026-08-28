from __future__ import annotations

import unittest
from pathlib import Path

from working_set_exp.recurrent_pressure import (
    CandidateBoundProbeExecutor,
    hidden_grade,
    load_recurrent_fixture,
    verify_bank,
)
from working_set_exp.tools import SessionState, ToolExecutor, action_schema


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "007_recurrent_bounded_pressure"
PRIMARY = ROOT / "experiments" / "008_recurrent_bounded_pressure_primary"


class RecurrentPressureTests(unittest.TestCase):
    def test_fresh_corrected_primary_bank_and_known_good_candidates(self) -> None:
        result = verify_bank(PRIMARY / "fresh_bank")
        self.assertEqual(result["file_count"], 62)
        for fixture_id in ("E8-SOURCE", "E8-OBSERVATION"):
            fixture = load_recurrent_fixture(PRIMARY / "fresh_bank", fixture_id)
            known_good = fixture.initial
            import json
            truth = json.loads((PRIMARY / "fresh_bank" / "evaluator_only" / fixture_id / "TRUTH.json").read_text())
            for key in ("phase_a_patch", "phase_b_patch", "phase_c_patch"):
                row = truth[key]
                known_good, _ = known_good.patch(
                    path=row["path"], old=row["old"], new=row["new"],
                    expected_candidate_id=known_good.candidate_id,
                    expected_file_sha256=known_good.file_sha256(row["path"]),
                )
            self.assertTrue(hidden_grade(fixture, known_good)["passed"])

    def test_fresh_bank_and_known_good_candidates(self) -> None:
        result = verify_bank(EXPERIMENT / "fresh_bank")
        self.assertEqual(result["file_count"], 62)
        for fixture_id in ("E7-SOURCE", "E7-OBSERVATION"):
            fixture = load_recurrent_fixture(EXPERIMENT / "fresh_bank", fixture_id)
            known_good = fixture.initial
            import json
            truth = json.loads((EXPERIMENT / "fresh_bank" / "evaluator_only" / fixture_id / "TRUTH.json").read_text())
            for key in ("phase_a_patch", "phase_b_patch", "phase_c_patch"):
                row = truth[key]
                known_good, _ = known_good.patch(
                    path=row["path"], old=row["old"], new=row["new"],
                    expected_candidate_id=known_good.candidate_id,
                    expected_file_sha256=known_good.file_sha256(row["path"]),
                )
            self.assertTrue(hidden_grade(fixture, known_good)["passed"])

    def test_recurrent_schema_exposes_existing_boundary_actions(self) -> None:
        schema = action_schema("recurrent", probe_id="session")
        actions = {
            option["properties"]["action"]["const"]
            for option in schema["json_schema"]["schema"]["oneOf"]
        }
        self.assertIn("reopen_observation", actions)
        self.assertIn("fork_ready", actions)
        self.assertIn("probe", actions)
        self.assertNotIn("submit", actions)

    def test_mutation_invalidates_candidate_bound_check(self) -> None:
        fixture = load_recurrent_fixture(EXPERIMENT / "fresh_bank", "E7-SOURCE")
        state = SessionState(fixture.initial, stage="continuation", public_check_passed=True)
        executor = ToolExecutor(
            state, required_full_reads=(), prefork_checker=fixture.phase_a_checker,
            public_checker=fixture.final_checker, final_target=fixture.phase_c_target,
            probe_id=None, probe_body=None,
        )
        result = executor.execute({
            "action": "patch", "path": "delivery/tag.py", "old": "    return code.strip().upper()",
            "new": '    return "quartz-" + code.strip().upper()',
            "expected_candidate_id": state.candidate.candidate_id,
            "expected_file_sha256": state.candidate.file_sha256("delivery/tag.py"),
        })
        self.assertTrue(result["accepted"])
        self.assertFalse(state.public_check_passed)

    def test_probe_version_changes_mechanically_after_mutation(self) -> None:
        fixture = load_recurrent_fixture(EXPERIMENT / "fresh_bank", "E7-OBSERVATION")
        state = SessionState(fixture.initial, stage="recurrent")
        baseline = state.candidate.candidate_id
        executor = CandidateBoundProbeExecutor(
            state, required_full_reads=(), prefork_checker=fixture.phase_a_checker,
            public_checker=fixture.phase_b_checker, final_target=fixture.phase_c_target,
            probe_id=fixture.probe_id, probe_body=fixture.probe_v1, baseline_candidate_id=baseline,
            probe_v1=fixture.probe_v1, probe_v2=fixture.probe_v2,
        )
        first = executor.execute({"action": "probe", "probe_id": "session"})
        self.assertIn("K4::", first["observation"])
        executor.execute({
            "action": "patch", "path": "session/label.py", "old": "    return name.strip().upper()",
            "new": '    return "anything" + name.strip().upper()',
            "expected_candidate_id": state.candidate.candidate_id,
            "expected_file_sha256": state.candidate.file_sha256("session/label.py"),
        })
        second = executor.execute({"action": "probe", "probe_id": "session"})
        self.assertIn("M7::", second["observation"])


if __name__ == "__main__":
    unittest.main()
