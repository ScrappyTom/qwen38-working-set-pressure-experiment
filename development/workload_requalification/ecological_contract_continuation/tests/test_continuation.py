"""Exact job transition and recovery controls; no inference or checker execution."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import continuation_task as task
import run_continuation as controller


class ContinuationTests(unittest.TestCase):
    def test_only_declared_checkpoint_controls_change(self):
        session = task.initial_session()
        controller.declared_entry(session)
        original = task.inherited_state()
        self.assertEqual(task.canonical_json_bytes(task.snapshot(session)),
            task.canonical_json_bytes({**original, 'request_limit': 32, 'submitted': False}))
        self.assertTrue(original['submitted'])
        self.assertEqual(session.pairs[-1]['response']['action'], 'submit')
        self.assertIn('new contract-completion job', session.view()['episode_annotation'])

    def test_same_candidate_different_checker_cannot_submit(self):
        session = task.initial_session()
        check = session.view()['verification']['checks']['public']
        self.assertTrue(check['candidate_matches'])
        self.assertFalse(check['check_definition_matches'])
        self.assertFalse(session.view()['verification']['submission']['eligible'])
        with patch('working_set_exp.observations.subprocess.Popen', side_effect=AssertionError('No checker')):
            result = session.execute(dict(action='submit', expected_candidate_id=task.SAVED_ID), lambda _: 100)
        self.assertFalse(result['accepted'])
        self.assertFalse(session.submitted)
        self.assertEqual(session.candidate.candidate_id, task.SAVED_ID)

    def test_initial_and_rejected_checkpoint_restore(self):
        session = task.initial_session()
        for _ in range(2):
            state = task.snapshot(session)
            restored = task.restore(state, session.candidate, task.OLD, replay=True)
            self.assertEqual(task.snapshot(restored), state)
            self.assertEqual(restored.view(), session.view())
            session.execute(dict(action='submit', expected_candidate_id=task.SAVED_ID), lambda _: 100)

    def test_inherited_history_and_coverage_cannot_be_rewritten(self):
        session = task.initial_session()
        state = task.snapshot(session)
        altered = copy.deepcopy(state)
        altered['pairs'][0]['response']['action'] = 'submit'
        with self.assertRaises(ValueError):
            task.restore(altered, session.candidate, task.OLD, replay=True)
        altered = copy.deepcopy(state)
        altered['source_prerequisites']['first_mutation']['request_number'] += 1
        with self.assertRaises(ValueError):
            task.restore(altered, session.candidate, task.OLD, replay=True)

    def test_old_submission_cannot_reclose_new_job(self):
        session = task.initial_session()
        state = task.snapshot(session)
        state['submitted'] = True
        with self.assertRaises(ValueError):
            task.restore(state, session.candidate, task.OLD, replay=True)
        state = task.snapshot(session)
        state['pairs'].append(copy.deepcopy(state['pairs'][27]))
        with self.assertRaises(ValueError):
            task.restore(state, session.candidate, task.OLD, replay=True)

    def test_transport_and_reasoning_policy_unchanged(self):
        module = task.Task()
        request = controller.Adapter(module).request_for(module.initial_session().view())
        old = task.read(task.OLD / 'calls/C19-wire-request.json')
        for key in set(old) - {'messages'}:
            self.assertEqual(request[key], old[key], key)
        self.assertEqual((task.AREA/'SYSTEM.txt').read_bytes(), (task.previous.AREA/'SYSTEM.txt').read_bytes())
        self.assertEqual(request['grammar'], old['grammar'])
        self.assertEqual(request['chat_template_kwargs']['reasoning_effort'], 'medium')
        self.assertEqual(controller.Adapter(module).preceding_feedback, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
