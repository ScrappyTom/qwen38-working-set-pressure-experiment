from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from working_set_exp.fixture import load_fixture, load_truth
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import canonical_json_bytes
from working_set_exp.progress import CASE_IDS, construct_bank, progress_pointer, verify_bank
from working_set_exp.request import build_request
from working_set_exp.tools import SessionState, ToolExecutor


class ProgressStudyTests(unittest.TestCase):
    def test_fresh_bank_reproduces_and_known_good_passes(self):
        with tempfile.TemporaryDirectory(prefix="e3-bank-") as raw:
            bank = Path(raw) / "bank"
            construct_bank(bank)
            self.assertTrue(verify_bank(bank)["verified"])
            for fixture_id in CASE_IDS:
                fixture = load_fixture(bank, fixture_id)
                truth = load_truth(bank, fixture_id)
                known = fixture.initial
                for patch in (truth["prefork_patch"], truth["final_patch"]):
                    known, _ = known.patch(
                        path=patch["path"], old=patch["old"], new=patch["new"],
                        expected_candidate_id=known.candidate_id,
                        expected_file_sha256=known.file_sha256(patch["path"]),
                    )
                self.assertEqual(known.candidate_id, truth["known_good_candidate_id"])
                self.assertTrue(run_checker(known, fixture.public_checker)["passed"])
                self.assertTrue(run_checker(known, (bank / "evaluator_only" / fixture_id / "hidden.py").read_bytes())["passed"])

    def test_pointer_is_verbatim_frozen_phase_b_and_only_p_gets_it(self):
        with tempfile.TemporaryDirectory(prefix="e3-pointer-") as raw:
            bank = Path(raw) / "bank"
            construct_bank(bank)
            fixture = load_fixture(bank, CASE_IDS[0])
            pointer = progress_pointer(bank, fixture.fixture_id)
            phase_b = (bank / "model_visible" / fixture.fixture_id / "PHASE_B.txt").read_text(encoding="utf-8")
            self.assertEqual(pointer["active_step_verbatim"], phase_b)
            common = dict(
                fixture_id=fixture.fixture_id, task=fixture.task, candidate=fixture.initial, stage="continuation",
                visible_history=[], prefix_calls_used=12, continuation_calls_used=0, probe_id=None, observations=[],
                reconstructed=True, fork_binding={}, prefix_call_limit=18, continuation_call_limit=8,
            )
            mechanical = build_request(**common)
            pointed = build_request(**common, progress_pointer=pointer)
            self.assertNotIn(b"progress_pointer", mechanical)
            self.assertIn(canonical_json_bytes(pointer), pointed)

    def test_successful_probe_can_be_removed_from_next_action_surface(self):
        with tempfile.TemporaryDirectory(prefix="e3-probe-") as raw:
            bank = Path(raw) / "bank"
            construct_bank(bank)
            fixture = load_fixture(bank, "E3-OBSERVATION")
            state = SessionState(fixture.initial)
            executor = ToolExecutor(
                state, required_full_reads=fixture.required_full_reads, prefork_checker=fixture.prefork_checker,
                public_checker=fixture.public_checker, final_target=fixture.final_target,
                probe_id=fixture.probe_id, probe_body=fixture.probe_body,
            )
            result = executor.execute({"action": "probe", "probe_id": "negotiation"})
            self.assertTrue(result["accepted"])
            request = build_request(
                fixture_id=fixture.fixture_id, task=fixture.task, candidate=fixture.initial, stage="prefix",
                visible_history=[{"response": {"action": "probe", "probe_id": "negotiation"}, "result": result}],
                prefix_calls_used=1, continuation_calls_used=0, probe_id=None, observations=[], reconstructed=False,
                fork_binding=None, prefix_call_limit=18, continuation_call_limit=8,
            )
            self.assertNotIn(b'"probe"', request.split(b'"available_actions"', 1)[1].split(b'"available_check_ids"', 1)[0])


if __name__ == "__main__":
    unittest.main()
