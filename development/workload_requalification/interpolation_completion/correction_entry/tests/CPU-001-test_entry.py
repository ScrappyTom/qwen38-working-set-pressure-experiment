"""Successor boundaries, pending delivery and both edit forms across restoration."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import correction_task as task
import run_correction
from working_set_exp.jsonutil import canonical_json_bytes


class EntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.task = task.Task()

    def test_exact_saved_entry_with_only_declared_changes(self):
        session = self.task.initial_session()
        before = self.task.inherited_state
        after = self.task.snapshot(session)
        changed = {key for key in before if canonical_json_bytes(before[key]) != canonical_json_bytes(after[key])}
        self.assertEqual(changed, {'call_limit', 'request_limit', 'starting_archive_length'})
        self.assertEqual((session.requests_used, session.calls_used, session.request_limit, session.call_limit), (64, 152, 80, 200))
        self.assertEqual(session.candidate, self.task.inherited_candidate)
        self.assertEqual(session.checkers, task.qualified_task.Task().initial_session().checkers)
        self.assertEqual(session.view()['working_account']['text'],
                         task.qualified_task.Task().restore(before, self.task.inherited_candidate, task.OLD, replay=True).view()['working_account']['text'])
        self.assertIn('UnboundLocalError', str(session.view()['verification']))

    def test_final_read_and_pending_receipt_are_supplied(self):
        session = self.task.initial_session()
        adapter = run_correction.Adapter(self.task)
        self.assertEqual(adapter.preceding_feedback, task.original.read(task.OLD/'final-preceding-feedback.json'))
        request = adapter.request_for(session.view())
        import json
        sent = json.loads(request['messages'][1]['content'])
        source, = sent['workspace']['working_set']['sources']
        self.assertEqual((source['returned_start_line'], source['returned_end_line']), (2200, 2360))
        self.assertEqual(source['content'], session.last['result']['source']['content'])
        self.assertEqual(sent['preceding_operation_feedback'][0]['sequence'], 151)
        self.assertEqual(session.delivered_sources, [])

    def test_checkpoint_both_edit_forms_and_tamper_rejection(self):
        for kind in ('patch', 'replace_region'):
            session = self.task.initial_session()
            source, = session.view()['working_set']['sources']
            session.mark_delivered(session.view())
            if kind == 'patch':
                action = dict(action=kind, path=task.TEST, old='class InterpolationMissingOptionErrorTransportTestCase',
                    new='class RevisedInterpolationMissingOptionErrorTransportTestCase',
                    expected_candidate_id=session.candidate.candidate_id, expected_file_sha256=source['file_sha256'])
            else:
                action = dict(action=kind, region=source['region_ref'], expected_candidate_id=session.candidate.candidate_id,
                    new=source['content'].replace('class InterpolationMissingOptionErrorTransportTestCase',
                                                   'class RevisedInterpolationMissingOptionErrorTransportTestCase'))
            self.assertTrue(session.execute(action, lambda view: 0)['accepted'])
            state = self.task.snapshot(session)
            restored = self.task.restore(state, session.candidate, task.OLD, replay=True)
            self.assertEqual(restored.view(), session.view())
            changed = copy.deepcopy(state); changed['diffs'][153] += '\ninvalid'
            with self.assertRaises(ValueError):
                self.task.restore(changed, session.candidate, task.OLD, replay=True)


if __name__ == '__main__':
    unittest.main()
