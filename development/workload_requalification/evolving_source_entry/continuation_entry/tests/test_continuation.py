"""Continuation ancestry, exact current authority and the completed temporal path."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import continuation_task as task
import qualification_route as route
import run_continuation as controller
from working_set_exp.jsonutil import canonical_json_bytes


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.session = task.initial_session(Path(self.temp.name))
        self.measure = lambda view: 6000 + len(canonical_json_bytes(view)) // 3

    def test_exact_entry_changes_only_finite_opportunity(self):
        s = self.session
        controller.declared_entry(s)
        old = task.inherited_state()
        self.assertEqual(canonical_json_bytes(task.snapshot(s)), canonical_json_bytes({**old,
            'request_limit': 36, 'call_limit': 73}))
        self.assertEqual(s.view()['allowance']['requests_remaining'], 12)
        self.assertEqual(s.view()['allowance']['actions_remaining'], 36)
        self.assertEqual(s.task, task.previous.task_text())
        self.assertIn('preceding job ended at its24-request allowance', s.view()['episode_annotation'])
        self.assertFalse(s.view()['verification']['submission']['eligible'])
        self.assertEqual(s.payload('EVT-0037'), canonical_json_bytes(old['pairs'][36]['response']))
        self.assertEqual(s.payload('RES-0024'), canonical_json_bytes(old['pairs'][23]['result']))

    def test_parent_delivery_does_not_invent_changed_policy_reacquisition(self):
        trace = route.parent_trace(task, self.session.versions)
        result = trace.result()
        self.assertTrue(result['all_ledgers_delivered'])
        self.assertEqual((result['first_primary'], result['first_policy']), (36, 37))
        self.assertFalse(result['requested_current_policy_delivered_before_secondary'])
        self.assertFalse(result['temporal_contract_met'])
        self.assertEqual(self.session.view()['latest_feedback']['sequence'], 37)

    def test_source_supported_completion_preserves_parent_work_and_history(self):
        s = self.session
        archive, before = canonical_json_bytes(s.pairs), s.candidate
        result = route.journey(task, s, self.measure)
        self.assertTrue(result['audit']['temporal_contract_met'])
        self.assertEqual((result['new_requests'], result['new_operations']), (4, 4))
        self.assertEqual(canonical_json_bytes(s.pairs[:37]), archive)
        self.assertEqual(s.candidate.file_map['api/primary.py'], before.file_map['api/primary.py'])
        self.assertEqual(s.candidate.file_map['policy/current.py'], before.file_map['policy/current.py'])
        restored = task.restore(task.snapshot(s), s.candidate, Path(self.temp.name), replay=True)
        self.assertEqual(restored.view(), s.view())

    def test_restore_rejects_changed_parent_record_and_opportunity(self):
        for key in ('pairs', 'request_limit', 'requests_used'):
            with self.subTest(key=key):
                state = copy.deepcopy(task.snapshot(self.session))
                if key == 'pairs':
                    state['pairs'][0]['result']['accepted'] = False
                elif key == 'request_limit':
                    state[key] = 99
                else:
                    state[key] = 0
                with self.assertRaises(ValueError):
                    task.restore(state, self.session.candidate, Path(self.temp.name), replay=True)

    def test_unseen_secondary_is_not_authorized_by_task_or_old_account(self):
        s = self.session
        s.mark_delivered(s.view())
        before = s.candidate
        r = s.execute(dict(action='patch', path='api/secondary.py', old='value.strip().upper()',
            new='"quartz-" + value.strip().upper()', expected_candidate_id=before.candidate_id,
            expected_file_sha256=before.file_sha256('api/secondary.py')), self.measure)
        self.assertFalse(r['accepted'])
        self.assertEqual(s.candidate, before)
        self.assertIsNone(s.check_state())


if __name__ == '__main__':
    unittest.main()
