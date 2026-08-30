from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from working_set_exp.jsonutil import load_json_strict
from working_set_exp.phase_receipts import _receipt
from working_set_exp.unified_receipts import build_request, construct_bank, load_fixture


class UnifiedReceiptTests(unittest.TestCase):
    def test_unified_sequence_includes_postreset_check_while_split_freezes(self) -> None:
        with TemporaryDirectory() as raw:
            bank = Path(raw) / "bank"
            construct_bank(bank)
            fixture = load_fixture(bank, "E14-CLOSURE-MINT")
            candidate = fixture.initial
            receipts = [
                _receipt({"action": "read", "path": f"x/{n}.py", "start_line": 1},
                         {"accepted": True, "candidate_id": candidate.candidate_id, "path": f"x/{n}.py",
                          "complete": True}, sequence=n, handle=f"RES-{n:04d}")
                for n in range(1, 6)
            ]
            check_action = {"action": "check", "check_id": "public", "expected_candidate_id": candidate.candidate_id}
            check_result = {"accepted": True, "check_id": "public", "checked_candidate_id": candidate.candidate_id,
                            "passed": True}
            receipts.append(_receipt(check_action, check_result, sequence=6, handle="RES-0006"))
            history = [{"response": check_action, "result": check_result}]
            common = dict(fixture=fixture, candidate=candidate, phase_id="B", history=history, observations=[],
                          completed=["A"], reconstructed=True, boundary_binding=None, calls_used=6,
                          stage="continuation", receipt_entries=receipts, externalized_receipt_count=5)
            split = load_json_strict(build_request(condition="T25-SPLIT", **common))
            unified = load_json_strict(build_request(condition="T25-UNIFIED", **common))
            self.assertEqual(split["active_phase_receipt_ledger"]["complete_through_sequence"], 5)
            self.assertEqual(unified["active_phase_receipt_ledger"]["complete_through_sequence"], 6)
            self.assertTrue(unified["active_phase_receipt_ledger"]["entries"][-1]["passed"])
            self.assertEqual(unified["active_phase_receipt_ledger"]["entries"][-1]["checked_candidate_id"], candidate.candidate_id)

    def test_rejected_receipt_does_not_claim_acceptance(self) -> None:
        row = _receipt({"action": "submit", "expected_candidate_id": "0" * 64},
                       {"accepted": False, "error_code": "tool_rejected"}, sequence=3, handle="RES-0003")
        self.assertFalse(row["accepted"])
        self.assertNotIn("submitted_candidate_id", row)

    def test_check_receipt_keeps_exact_candidate_binding(self) -> None:
        candidate_id = "a" * 64
        row = _receipt({"action": "check", "check_id": "public", "expected_candidate_id": candidate_id},
                       {"accepted": True, "checked_candidate_id": candidate_id, "passed": True},
                       sequence=4, handle="RES-0004")
        self.assertEqual(row["checked_candidate_id"], candidate_id)
        self.assertTrue(row["passed"])


if __name__ == "__main__":
    unittest.main()
