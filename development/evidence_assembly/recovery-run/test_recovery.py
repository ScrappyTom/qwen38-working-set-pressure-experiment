import copy
import json
import unittest

import recovery_task as task
from manage_recovery import reference_reply, TEST, DOC, BAD
import run_uncoached_contribution as runner
from working_set_exp import working_view
from working_set_exp.contribution_reply import process_reply


class RecoveryPreparationTests(unittest.TestCase):
    def test_exact_C05_checkpoint_with_new_episode_and_delivery_accounting(self):
        candidate, state, old_view, records = task.checkpoint()
        current = task.Task().initial_session()
        self.assertEqual(current.candidate, candidate)
        for key in ("pairs", "ranges", "saved", "last"):
            self.assertEqual(getattr(current, key), state[key])
        self.assertEqual(current.starting_archive_length, 75)
        self.assertEqual((current.calls_used, current.requests_used), (0, 0))
        self.assertEqual(current.delivered_sources, [])
        self.assertEqual(current.view()["allowance"]["actions_remaining"], 12)
        self.assertEqual(current.view()["allowance"]["requests_remaining"], 8)
        self.assertTrue(all(row["episode"] == "prior_work" for row in current.view()["recent_activity"]))
        self.assertEqual(old_view["allowance"]["requests_remaining"], 4)
        self.assertEqual(records, 187)
        self.assertFalse(current.check_state()["applies_to_current"])

    def test_initial_input_is_only_declared_checkpoint_and_shared_reference(self):
        module = task.Task()
        current = module.initial_session()
        request = runner.Adapter(module).request_for(current.view())
        native = module.expected_native(request).decode()
        value = json.loads(request["messages"][1]["content"])
        self.assertEqual(value["workspace"], current.view())
        self.assertEqual(value["preceding_operation_feedback"], [])
        self.assertEqual(native.count(working_view.INPUT_INTERPRETATION), 1)
        self.assertEqual(value["workspace"]["working_set"], dict(sources=[], saved_results=[]))
        sources = current.feedback_sources(current.last)
        self.assertEqual([(r["path"],r["returned_start_line"],r["returned_end_line"]) for r in sources],
                         [(TEST,2180,2212),(DOC,400,440)])
        self.assertNotIn("Lib/configparser.py", {r["path"] for r in sources})
        self.assertIn(task.PROPOSAL, native)
        self.assertNotIn("class InterpolationMissingOptionErrorTestCase", native)
        self.assertNotIn(BAD, native)
        self.assertNotIn("7,555", native)
        self.assertNotIn("supplied, separately verified", native)
        self.assertEqual(request["seed"], 961213)
        self.assertEqual(request["chat_template_kwargs"], dict(enable_thinking=True, reasoning_effort="medium"))
        for name in ("SYSTEM.txt", "TASK.txt"):
            self.assertEqual((task.AREA/name).read_bytes(), (task.AREA.parent/"pending-contribution"/name).read_bytes())

    def test_complete_and_failed_check_routes_preserve_work_through_reselection(self):
        final_candidates = []
        for scenario in ("complete", "correction"):
            with self.subTest(scenario=scenario):
                module = task.Task(scenario)
                session = module.initial_session()
                history, initial = copy.deepcopy(session.pairs), session.candidate
                feedback, saved_tests = [], None
                for number in range(1, 9):
                    session.mark_delivered(session.view())
                    session.begin_request()
                    result = process_reply(session, reference_reply(module, session, number), lambda view: 500, feedback)
                    self.assertTrue(all(o["result"]["accepted"] for o in result["operations"]))
                    if number == 2:
                        saved_tests = session.candidate.file_map[TEST]
                    if number in (3, 4):
                        self.assertEqual(session.candidate.file_map[TEST], saved_tests)
                        self.assertTrue(all(r["path"] == DOC for r in session.ranges))
                        self.assertEqual(session.saved, {})
                    if session.submitted:
                        break
                self.assertTrue(session.submitted)
                self.assertEqual(session.pairs[:75], history)
                checks = [r["result"]["passed"] for r in session.pairs[75:] if r["response"]["action"] == "check"]
                self.assertEqual(checks, [True] if scenario == "complete" else [False, True])
                self.assertEqual((session.requests_used, session.calls_used), (5, 6) if scenario == "complete" else (7, 9))
                self.assertEqual(sorted(p for p in initial.file_map if initial.file_map[p] != session.candidate.file_map[p]), sorted([TEST,DOC]))
                final_candidates.append(session.candidate.candidate_id)
        self.assertEqual(final_candidates[0], final_candidates[1])


if __name__ == "__main__":
    unittest.main()
