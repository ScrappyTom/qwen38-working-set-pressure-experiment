import copy
import json
import unittest

import test_accounted_contribution as accounted_tests
from working_set_exp.working_session import CapacityError, INPUT_LIMIT, WorkingSession


class FeedbackHistoryTests(unittest.TestCase):
    def prepared(self):
        fixture = accounted_tests.AccountedContributionTests()
        session = fixture.session()
        for _ in range(3):
            session.execute(dict(action="work_on", sources=[dict(path="test_app.py", start_line=1, end_line=0)],
                                 results=[]), lambda view: 500)
        return fixture, session

    def test_failed_read_delivers_rejection_without_releasing_selected_evidence(self):
        _, session = self.prepared()
        candidate, ranges, sources = session.candidate.candidate_id, copy.deepcopy(session.ranges), session.sources()
        def measure(view):
            if view["latest_feedback"]["result"].get("accepted"):
                return INPUT_LIMIT + 1  # No new page fits.
            return 23000 if len(view["recent_activity"]) <= 2 else INPUT_LIMIT + 1
        result = session.execute(dict(action="read", path="test_app.py", start_line=1, end_line=0), measure)
        self.assertFalse(result["accepted"])
        self.assertIn("work_on", result["error"])
        self.assertEqual(session.ranges, ranges)
        self.assertEqual(session.sources(), sources)
        self.assertEqual(session.candidate.candidate_id, candidate)
        self.assertEqual(session.calls_used, 4)
        self.assertEqual(len(session.view()["recent_activity"]), 2)
        self.assertEqual(json.loads(session.payload("RES-0004")), result)
        self.assertEqual(session.view()["archive"]["action_count"], 4)
        session.mark_delivered(session.view())
        # The model can subsequently replace the group; normal history returns.
        narrowed = session.execute(dict(action="work_on", sources=[], results=[]), lambda view: 500)
        self.assertTrue(narrowed["accepted"])
        self.assertEqual(len(session.view()["recent_activity"]), 5)
        self.assertNotIn("recent_activity_limit", session.last)

    def test_actual_check_feedback_has_priority_over_recent_summaries(self):
        _, session = self.prepared()
        ranges = copy.deepcopy(session.ranges)
        result = session.execute(dict(action="check", check_id="tests", expected_candidate_id=session.candidate.candidate_id),
            lambda view: 23000 if len(view["recent_activity"]) <= 1 else INPUT_LIMIT + 1)
        self.assertTrue(result["accepted"])
        self.assertFalse(result["passed"])
        self.assertEqual(session.last["result"], result)
        self.assertNotIn("output_scope", session.last)
        self.assertTrue(session.scoped_check_state("tests")["applies_to_current"])
        self.assertEqual(session.ranges, ranges)
        self.assertEqual(len(session.view()["recent_activity"]), 1)

    def test_genuine_minimum_capacity_failure_keeps_original_state(self):
        _, session = self.prepared()
        before = copy.deepcopy(session.__dict__)
        with self.assertRaisesRegex(CapacityError, "Rejection cannot be delivered"):
            session.execute(dict(action="read", path="test_app.py", start_line=1, end_line=0), lambda view: INPUT_LIMIT + 1)
        self.assertEqual(session.pairs, before["pairs"])
        self.assertEqual(session.ranges, before["ranges"])
        self.assertEqual(session.last, before["last"])

    def test_historical_default_does_not_silently_change_policy(self):
        _, source = self.prepared()
        session = WorkingSession(source.candidate, source.checker, source.task, pairs=source.pairs)
        with self.assertRaisesRegex(CapacityError, "Rejection cannot be delivered"):
            session.execute(dict(action="read", path="test_app.py", start_line=999, end_line=0),
                lambda view: 23000 if len(view["recent_activity"]) <= 2 else INPUT_LIMIT + 1)
        self.assertEqual(len(session.pairs), 3)


if __name__ == "__main__":
    unittest.main()
