import copy
import json
import unittest

import test_accounted_contribution as fixtures
from working_set_exp.accounted_contribution import process_reply
from working_set_exp.working_session import CapacityError, INPUT_LIMIT


class AccountGroupTests(unittest.TestCase):
    def prepared(self):
        fixture = fixtures.AccountedContributionTests()
        session = fixture.session()
        fixture.source(session, "app.py")
        fixture.run_reply(session, dict(discussion="Initial", account="Previous question."))
        session.mark_delivered(session.view())
        session.begin_request()
        return fixture, session

    def reply(self, text="Revised understanding; actual check still needed.", path="test_app.py"):
        return dict(discussion="Replace support while preserving the question.", account=text,
            operation=dict(action="work_on", sources=[dict(path=path, start_line=1, end_line=0)], results=[]))

    def test_joint_admission_uses_final_selection_and_both_actual_receipts(self):
        _, session = self.prepared()
        original, old_ranges = session.candidate.candidate_id, copy.deepcopy(session.ranges)
        feedback, snapshots = [], []
        def measure(view):
            self.assertEqual(len(feedback), 1)
            self.assertEqual(feedback[0]["action_summary"]["action"], "record_account")
            self.assertEqual(view["latest_feedback"]["action_summary"]["action"], "work_on")
            self.assertEqual(view["working_set"]["sources"], [])  # selected text is in feedback
            return 500
        host = process_reply(session, self.reply(), measure, feedback,
            lambda number, operation: snapshots.append(copy.deepcopy(session.__dict__)))
        self.assertEqual([op["result"]["accepted"] for op in host["operations"]], [True, True])
        self.assertEqual(snapshots[0]["ranges"], old_ranges)
        self.assertEqual(session.ranges[0]["path"], "test_app.py")
        self.assertEqual(session.working_account()["input_candidate_id"], original)
        self.assertEqual(session.working_account()["written_during_request"], 2)
        self.assertEqual(session.calls_used, 3)
        self.assertEqual(len(feedback), 1)
        self.assertEqual(json.loads(session.payload("EVT-0002"))["text"], self.reply()["account"])
        self.assertEqual(session.delivered_sources, snapshots[0]["delivered_sources"])
        # Construction does not claim the newly selected source was delivered.
        self.assertFalse(any(s["path"] == "test_app.py" for s in session.delivered_sources))
        session.mark_delivered(session.view())
        self.assertTrue(any(s["path"] == "test_app.py" for s in session.delivered_sources))

    def test_invalid_replacement_preserves_previous_account_and_selection(self):
        _, session = self.prepared()
        before = copy.deepcopy(session.__dict__)
        feedback = []
        host = process_reply(session, self.reply(path="missing.py"), lambda view: 500, feedback)
        self.assertEqual(len(host["operations"]), 1)
        self.assertFalse(host["operations"][0]["result"]["accepted"])
        self.assertEqual(host["associated_operation_skipped"], "account_group_not_admitted")
        self.assertEqual(session.working_account()["text"], "Previous question.")
        self.assertEqual(session.ranges, before["ranges"])
        self.assertEqual(session.candidate.candidate_id, before["candidate"].candidate_id)
        self.assertEqual(feedback, [])

    def test_account_too_large_after_replacement_rejects_without_partial_commit(self):
        _, session = self.prepared()
        before = copy.deepcopy(session.ranges)
        def measure(view):
            return INPUT_LIMIT + 1 if view["working_account"]["text"].startswith("LARGE") else 500
        host = process_reply(session, self.reply(text="LARGE proposed account"), measure, [])
        self.assertFalse(host["operations"][0]["result"]["accepted"])
        self.assertEqual(session.working_account()["text"], "Previous question.")
        self.assertEqual(session.ranges, before)

    def test_genuine_rejection_delivery_failure_has_no_state_commit(self):
        _, session = self.prepared()
        before = copy.deepcopy(session.__dict__)
        feedback = []
        with self.assertRaisesRegex(CapacityError, "Rejection cannot be delivered"):
            process_reply(session, self.reply(), lambda view: INPUT_LIMIT + 1, feedback)
        self.assertEqual(session.pairs, before["pairs"])
        self.assertEqual(session.ranges, before["ranges"])
        self.assertEqual(session.last, before["last"])
        self.assertEqual(feedback, [])

    def test_clear_and_grow_account_across_group_changes(self):
        fixture, session = self.prepared()
        for text in ("", "A growing account with a specific unresolved question and existing source support."):
            host = fixture.run_reply(session, self.reply(text=text))
            self.assertEqual([op["result"]["accepted"] for op in host["operations"]], [True, True])
            self.assertEqual(session.working_account()["text"], text)
        self.assertEqual(json.loads(session.payload("EVT-0001"))["text"], "Previous question.")


if __name__ == "__main__":
    unittest.main()
