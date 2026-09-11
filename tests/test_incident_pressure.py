from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_incident_pressure as prep
from working_set_exp.event_frame_v3 import resident_pair_v3
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict


class IncidentPressureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = [prep.constructed_fixture(world) for world in prep.WORLDS]

    def test_counterfactual_evidence_changes_correct_repair(self):
        first, second = self.fixtures
        self.assertEqual(first.initial, second.initial)
        self.assertEqual(first.task, second.task)
        self.assertNotEqual(first.observation_bodies, second.observation_bodies)
        matrix = prep.counterfactual_checks(self.fixtures)
        self.assertEqual(sum(row["result"]["passed"] for row in matrix), 2)
        for row in matrix:
            self.assertEqual(row["result"]["passed"], row["world"] == row["repair"])
            self.assertFalse(row["result"]["streams_truncated"])

    def test_each_route_checks_the_actual_successor_and_finishes(self):
        for fixture in self.fixtures:
            for kind in ("check_shortcut", "observation_shortcut", "source_investigation"):
                value, snapshots, opportunities = prep.qualification_path(fixture, kind)
                self.assertTrue(value.state.submitted)
                self.assertLess(len(snapshots), prep.CALL_LIMIT)
                self.assertTrue(snapshots[-2]["result"]["passed"])
                self.assertEqual(snapshots[-1]["action"]["expected_candidate_id"], value.state.candidate.candidate_id)
                self.assertEqual(snapshots[-2]["action"]["expected_candidate_id"], value.state.candidate.candidate_id)
                self.assertTrue(opportunities)

    def test_forced_recovery_keeps_exact_records_and_execution_state(self):
        value, _, _ = prep.qualification_path(self.fixtures[0], "source_investigation")
        external, recovered = prep.recovery_probe(value)
        self.assertTrue(value.state.submitted)
        self.assertEqual({r["action"] for r in recovered}, {"reopen_result", "reopen_event", "reopen_observation"})
        self.assertTrue(all(r["returned_bytes"] <= 22_000 for r in recovered))
        state = load_json_strict(external["messages"][1]["content"].encode())
        self.assertEqual(state["candidate_id"], value.state.candidate.candidate_id)
        events = state["active_phase_event_frame"]["events"]
        self.assertEqual(len(events), len(value.pairs)-1)
        self.assertFalse(any(e["action"]["action"] == "submit" for e in events))
        self.assertEqual(events[-1]["action"]["action"], "check")
        self.assertTrue(events[-1]["result"]["passed"])
        self.assertEqual(events[-1]["result"]["checked_candidate_id"], state["candidate_id"])

    def test_access_feedback_preserves_canonical_source_without_new_original(self):
        value = new_state("access", self.fixtures[0])
        value.execute(dict(action="read", path=prep.TARGET, start_line=1))
        saved = dict(value.result_payloads)
        result = value.execute(dict(action="reopen_result", handle="RES-0001"))
        self.assertEqual(result["exact_result_utf8"].encode(), saved["RES-0001"])
        self.assertEqual(value.result_payloads, saved)
        reference = prep.pilot.tool_reference(prep.pilot.grammar_for(value))
        request = prep.request_for(value, reference, externalized=1)
        state = load_json_strict(request["messages"][1]["content"].encode())
        last = state["active_phase_event_frame"]["events"][-1]
        self.assertEqual(last["result_body"]["canonical_source"]["handle"], "RES-0001")
        self.assertEqual(resident_pair_v3(last), value.pairs[-1])

    def test_externalization_changes_only_declared_event_payload_view(self):
        value = new_state("pair", self.fixtures[0])
        value.execute(dict(action="reopen_observation", handle="OBS-0001"))
        value.execute(dict(action="read", path=prep.TARGET, start_line=1))
        reference = prep.pilot.tool_reference(prep.pilot.grammar_for(value))
        before = copy.deepcopy(value.pairs)
        resident = prep.request_for(value, reference)
        external = prep.request_for(value, reference, externalized=1)
        left = load_json_strict(resident["messages"][1]["content"].encode())
        right = load_json_strict(external["messages"][1]["content"].encode())
        for state in (left, right):
            state.pop("active_phase_event_frame")
            state.pop("event_frame_verification")
        self.assertEqual(left, right)
        self.assertEqual(resident["messages"][0], external["messages"][0])
        self.assertEqual(resident["response_format"], external["response_format"])
        self.assertEqual(before, value.pairs)
        self.assertIn(reference, resident["messages"][0]["content"])
        self.assertEqual(prep.request_for(value, reference), resident)

    def test_admission_keeps_oldest_prefix_and_stops_when_signals_do_not_fit(self):
        value = new_state("admission", self.fixtures[0])
        for handle in ("OBS-0001", "OBS-0002"):
            value.execute(dict(action="reopen_observation", handle=handle))
        reference = prep.pilot.tool_reference(prep.pilot.grammar_for(value))
        seen = []

        def count(request):
            state = load_json_strict(request["messages"][1]["content"].encode())
            removed = state["active_phase_event_frame"]["externalized_payload_through_sequence"]
            seen.append(removed)
            return 17_000 - removed * 1_000

        result = prep.choose_externalization(value, reference, count)
        self.assertEqual((result["externalized"], result["prompt_tokens"]), (1, 16_000))
        self.assertEqual(seen, [0, 1])
        self.assertIsNone(prep.choose_externalization(value, reference, lambda _: 16_001, previous=1))
        self.assertEqual(prep.ACTOR["context"] - prep.RESIDENT_CEILING, 32_768)
        self.assertLess(prep.WORKING_SET, prep.RESIDENT_CEILING)


if __name__ == "__main__":
    unittest.main()
