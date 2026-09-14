import copy
import json
import unittest

import pending_task as task
from manage_pending import reference_reply
import run_uncoached_contribution as runner
from working_set_exp.contribution_reply import process_reply


class PendingContributionTests(unittest.TestCase):
    def test_exact_checkpoint_and_fresh_declared_allowance(self):
        original, _ = task.grouped.checkpoint()
        current = task.Task().initial_session()
        self.assertEqual(current.candidate, original.candidate)
        for key in ("pairs", "ranges", "saved", "last", "diffs"):
            self.assertEqual(getattr(current, key), getattr(original, key))
        self.assertEqual(current.starting_archive_length, 71)
        self.assertEqual(current.calls_used, 0)
        self.assertEqual(current.requests_used, 0)
        self.assertEqual(current.view()["allowance"]["requests_remaining"], 8)
        self.assertEqual(current.call_limit, 12)
        self.assertFalse(current.check_state()["applies_to_current"])
        self.assertTrue(all(row["episode"] == "prior_work" for row in current.view()["recent_activity"]))

    def test_actual_input_offers_recovery_without_supplying_proposal_or_answer(self):
        module = task.Task()
        session = module.initial_session()
        request = runner.Adapter(module).request_for(session.view())
        native = module.expected_native(request).decode()
        self.assertIn("^(RES|EVT)-[0-9]{4,}$", native)
        self.assertIn("EVT-0071", native)
        self.assertNotIn("class InterpolationMissingOptionErrorTestCase", native)
        self.assertNotIn("offline-wrong-option", native)
        self.assertNotIn("No actions have yet run", native)
        self.assertIn("At this attempt's starting checkpoint", native)
        self.assertEqual(json.loads(session.payload("EVT-0071")),
                         task.study.read(task.grouped.SOURCE / "calls/C04-operation-01.json")["action"])
        self.assertEqual(request["seed"], 961212)
        self.assertEqual(request["chat_template_kwargs"], dict(enable_thinking=True, reasoning_effort="medium"))

    def test_complete_and_actual_failed_check_correction_paths(self):
        for scenario in ("complete", "correction"):
            with self.subTest(scenario=scenario):
                module = task.Task(scenario)
                session = module.initial_session()
                original = copy.deepcopy(session.pairs)
                feedback = []
                for number in range(1, 9):
                    session.mark_delivered(session.view())
                    session.begin_request()
                    value = process_reply(session, reference_reply(module, session, number), lambda view: 500, feedback)
                    self.assertTrue(all(o["result"]["accepted"] for o in value["operations"]))
                    if session.submitted:
                        break
                self.assertTrue(session.submitted)
                self.assertEqual(session.pairs[:71], original)
                self.assertLess(session.requests_used, 8)
                results = [p["result"]["passed"] for p in session.pairs[71:] if p["response"]["action"] == "check"]
                self.assertEqual(results, [True] if scenario == "complete" else [False, True])
                self.assertEqual(session.candidate.candidate_id,
                                 "5b7b3b06f55935d950317fedce9add1d481c56e15d29158e2a38ddeda369131d")


if __name__ == "__main__":
    unittest.main()
