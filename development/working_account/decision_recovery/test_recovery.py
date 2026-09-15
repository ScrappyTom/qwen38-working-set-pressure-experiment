"""Mechanical boundaries of the prospective presentation; no model inference."""
import copy
import json
import unittest

import recovery_task as study
from working_set_exp.jsonutil import canonical_json_bytes


class RecoveryPresentationTests(unittest.TestCase):
    def test_paired_inputs_differ_only_by_declared_frame(self):
        plain, focused = [study.initial_session(c) for c in ("ordinary", "focused")]
        a = study.runner.Adapter(study.Task("ordinary")).request_for(plain.view())
        b = study.runner.Adapter(study.Task("focused")).request_for(focused.view())
        shown = json.loads(b["messages"][1]["content"])
        self.assertEqual(shown["workspace"].pop("decision_focus"), study.FRAME_PATH.read_text(encoding="utf-8").strip())
        b["messages"][1]["content"] = canonical_json_bytes(shown).decode()
        self.assertEqual(a, b)
        saved = study.read(study.CHECKPOINT)
        self.assertEqual(plain.ranges, saved["ranges"])
        self.assertEqual(plain.pairs, saved["pairs"])
        self.assertEqual(plain.candidate.candidate_id, saved["candidate_id"])
        self.assertEqual((plain.requests_used, plain.calls_used), (0, 0))
        self.assertIsNone(plain.working_account())

    def test_successful_coordinate_search_clears_frame_without_changing_selection(self):
        session = study.initial_session("focused")
        ranges, candidate = copy.deepcopy(session.ranges), session.candidate.candidate_id
        session.mark_delivered(session.view())
        session.begin_request()
        result = session.execute(dict(action="search", path=study.TEST,
            query="def test_attributes_bad_port", offset=0, limit=1), lambda view: 500)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["matches"][0]["line"], 716)
        self.assertNotIn("decision_focus", session.view())
        self.assertEqual(session.ranges, ranges)
        self.assertEqual(session.candidate.candidate_id, candidate)
        self.assertEqual(session.calls_used, 1)

    def test_only_the_declared_actual_rejection_triggers(self):
        session = study.initial_session("focused")
        for change in (dict(accepted=True), dict(error="stale candidate or pre-edit file binding")):
            with self.subTest(change=change):
                altered = study.initial_session("focused")
                altered.last["result"].update(change)
                self.assertNotIn("decision_focus", altered.view())
        other = study.initial_session("focused")
        other.last["action_summary"]["action"] = "patch"
        self.assertNotIn("decision_focus", other.view())
        self.assertIn("decision_focus", session.view())

    def test_delivery_checks_the_actual_frame(self):
        session = study.initial_session("focused")
        tampered = session.view()
        tampered["decision_focus"] = "Invented next action"
        with self.assertRaisesRegex(ValueError, "framing differs"):
            session.mark_delivered(tampered)
        session.mark_delivered(session.view())
        self.assertEqual(session._verified_source_ranges(session.delivered_sources), session.ranges)


if __name__ == "__main__":
    unittest.main()
