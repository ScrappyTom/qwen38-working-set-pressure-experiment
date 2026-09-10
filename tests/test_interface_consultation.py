import copy
import unittest
from pathlib import Path

from working_set_exp.interface_consultation import consultation_schedule, development_states, endpoint_request, patch
from working_set_exp.jsonutil import load_json_strict


ROOT = Path(__file__).resolve().parents[1]


class InterfaceConsultationTests(unittest.TestCase):
    def setUp(self):
        self.states = development_states(ROOT)

    def test_saved_crowded_request_changes_only_the_reasoning_allowance(self):
        value = self.states[0]
        before = load_json_strict((ROOT / value.provenance["path"]).read_bytes())
        after = load_json_strict(value.request)
        before["resource_state"]["reasoning_budget_tokens"] = -1
        self.assertEqual(before, after)
        self.assertEqual(len(value.state.complete_reads), 11)

    def test_recovering_a_passing_old_check_does_not_validate_the_new_candidate(self):
        value = self.states[1]
        candidate_id = value.state.candidate.candidate_id
        self.assertFalse(value.state.public_check_passed)
        result = value.execute({"action": "reopen_result", "handle": "RES-0002"})
        self.assertTrue(result["accepted"])
        self.assertEqual(value.state.candidate.candidate_id, candidate_id)
        self.assertFalse(value.state.public_check_passed)
        result = value.execute({"action": "check", "check_id": "public", "expected_candidate_id": candidate_id})
        self.assertTrue(result["passed"])
        self.assertTrue(value.state.public_check_passed)

    def test_edit_checks_the_existing_file_version(self):
        value = self.states[2]
        valid = patch(value, "return 1", "return 2")
        stale = copy.deepcopy(valid)
        stale["expected_file_sha256"] = "0" * 64
        self.assertFalse(value.execute(stale)["accepted"])
        self.assertTrue(value.execute(valid)["accepted"])

    def test_recovering_historical_patch_does_not_replay_it_or_complete_a_read(self):
        value = self.states[3]
        self.assertTrue(value.pairs[1]["result"]["complete"])
        self.assertNotIn("service.py", value.state.complete_reads)
        candidate_id = value.state.candidate.candidate_id
        result = value.execute({"action": "reopen_event", "handle": "EVT-0001"})
        self.assertTrue(result["accepted"])
        self.assertIn("copper-orbit", str(result))
        self.assertEqual(value.state.candidate.candidate_id, candidate_id)
        self.assertNotIn("service.py", value.state.complete_reads)

    def test_consultation_has_sixteen_independent_uncapped_requests_with_actions_first(self):
        schedule = consultation_schedule()
        self.assertEqual(len(schedule), 16)
        self.assertEqual([row["mode"] for row in schedule], ["action"] * 8 + ["diagnostic"] * 8)
        values = {value.name: value for value in self.states}
        for row in schedule:
            request = endpoint_request(values[row["state"]], seed=row["seed"], mode=row["mode"])
            self.assertEqual([message["role"] for message in request["messages"]], ["system", "user"])
            self.assertEqual(request["max_tokens"], -1)
            self.assertEqual(request["reasoning_budget_tokens"], -1)
            self.assertEqual(request["chat_template_kwargs"]["reasoning_effort"], "xhigh")
            self.assertEqual("response_format" in request, row["mode"] == "action")


if __name__ == "__main__":
    unittest.main()
