"""Qualify the shared description against actual selection and request boundaries."""
import copy
import json
from pathlib import Path
import subprocess
from types import ModuleType
import unittest
from unittest.mock import patch

import parser_roundtrip as task
from run_uncoached_contribution import Adapter
from test_working_action_groups import rejected_proposal, group, SPAN
from test_working_session import session, act, read, edit
from working_set_exp import working_view
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.jsonutil import canonical_json_bytes

ROOT = Path(__file__).resolve().parents[1]
BASE = "3c143bae5ead30024f9e815a8db109c7f3b49035"


def baseline_view():
    raw = subprocess.run(["git", "show", BASE + ":src/working_set_exp/working_view.py"],
                         cwd=ROOT, check=True, capture_output=True).stdout
    module = ModuleType("working_set_exp.baseline_decision_view")
    module.__package__ = "working_set_exp"
    exec(compile(raw, BASE + ":working_view.py", "exec"), module.__dict__)
    return module


class DecisionStateTests(unittest.TestCase):
    def test_both_request_paths_change_only_one_shared_explanation(self):
        old = baseline_view()
        state = session().view()
        original_state = copy.deepcopy(state)
        adapter = Adapter(task)
        for make in (lambda: working_view.request(state, {}), lambda: adapter.request_for(state)):
            with self.subTest(builder=make):
                with patch.object(working_view, "system_prompt", old.system_prompt):
                    before = make()
                after = make()
                text = after["messages"][0]["content"]
                self.assertEqual(text.count(working_view.INPUT_INTERPRETATION), 1)
                after["messages"][0]["content"] = text.replace(working_view.INPUT_INTERPRETATION + "\n\n", "", 1)
                self.assertEqual(after, before)
                self.assertEqual(completion_request_bytes(after), completion_request_bytes(before))
        self.assertEqual(working_view.schema(), old.schema())
        self.assertEqual(state, original_state)

    def test_empty_feedback_only_mixed_and_unrelated_feedback_keep_exact_selection(self):
        s = session({"app.py": b"value = 1\n", "other.py": b"other = 0\n"})
        self.assertEqual(s.view()["working_set"], dict(sources=[], saved_results=[]))
        self.assertIsNone(s.view()["latest_feedback"])
        read(s)
        feedback_only = s.view()
        self.assertEqual(feedback_only["working_set"]["sources"], [])
        self.assertEqual(s.feedback_sources(feedback_only["latest_feedback"]), s.sources())
        read(s, "other.py")
        mixed = s.view()
        self.assertEqual([r["path"] for r in mixed["working_set"]["sources"]], ["app.py"])
        all_visible = mixed["working_set"]["sources"] + s.feedback_sources(mixed["latest_feedback"])
        self.assertEqual(s._verified_source_ranges(all_visible), s.ranges)
        ranges = copy.deepcopy(s.ranges)
        act(s, dict(action="tree", path=".", offset=0, limit=8))
        self.assertEqual(s.ranges, ranges)
        self.assertEqual(s.view()["working_set"]["sources"], s.sources())
        self.assertTrue(edit(s, "value = 1", "value = 2")["accepted"])

    def test_feedback_is_not_a_claim_that_all_returned_objects_are_selected(self):
        s = session()
        read(s)
        historical_last = copy.deepcopy(s.last)
        group(s, [], [])
        # A copied historical receipt can remain visible without a selection.
        # This is a constructed boundary, not a recorded model decision.
        s.last = historical_last
        self.assertEqual(s.ranges, [])
        self.assertEqual(s.view()["working_set"]["sources"], [])
        self.assertEqual(s.feedback_sources(s.view()["latest_feedback"])[0]["content"], "value = 1\n")
        self.assertTrue(working_view.INPUT_INTERPRETATION.startswith("The complete working set"))

    def test_saved_capacity_result_stays_historical_after_later_success(self):
        s = session()
        proposal, event, result_handle = rejected_proposal(s)
        original_error = s.payload(result_handle)
        original_proposal = s.payload(event)
        self.assertTrue(group(s, [SPAN], [event, result_handle])["accepted"])
        feedback = s.view()["latest_feedback"]["result"]["saved_results"]
        self.assertEqual(s.view()["working_set"]["saved_results"], [])
        self.assertEqual({p["handle"] for p in feedback}, {event, result_handle})
        self.assertEqual(json.loads(s.saved[event]["exact_utf8"]), proposal)
        self.assertFalse(json.loads(s.saved[result_handle]["exact_utf8"])["accepted"])
        self.assertTrue(act(s, proposal)["accepted"])
        self.assertEqual(s.payload(result_handle), original_error)
        self.assertEqual(s.payload(event), original_proposal)
        self.assertEqual(s.sources()[0]["content"], "value = 2\n")
        self.assertIsNone(s.check_state())
        self.assertFalse(s.submitted)


if __name__ == "__main__":
    unittest.main()
