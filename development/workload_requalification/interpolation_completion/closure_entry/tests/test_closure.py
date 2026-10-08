"""Exact inherited feedback, finite opportunity and applicability boundaries."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import closure_task as entry
import run_closure
from working_set_exp.candidate import Candidate
from working_set_exp.decision_view import receipt_view
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes


class ClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.task = entry.Task()

    def test_exact_state_and_natural_account(self):
        session = self.task.initial_session()
        before = {**self.task.inherited_state,
                  'diffs': {int(k):v for k,v in self.task.inherited_state['diffs'].items()}}
        after = self.task.snapshot(session)
        changed = {k for k in before if canonical_json_bytes(before[k]) != canonical_json_bytes(after[k])}
        self.assertEqual(changed, {'request_limit', 'call_limit', 'starting_archive_length'})
        self.assertEqual((session.requests_used,session.calls_used,session.request_limit,session.call_limit), (80,187,82,191))
        old = entry.previous.Task().restore(self.task.inherited_state, self.task.inherited_candidate, entry.OLD, replay=True)
        self.assertEqual(session.candidate, old.candidate)
        self.assertEqual(session.checkers, old.checkers)
        self.assertEqual(session.view()['working_account']['text'], old.view()['working_account']['text'])
        restored = self.task.restore(after, session.candidate, entry.OLD, replay=True)
        self.assertEqual(restored.view(), session.view())

    def test_complete_actual_pending_outcomes_in_input(self):
        session = self.task.initial_session()
        request = run_closure.Adapter(self.task).request_for(session.view())
        old = self.task.read(entry.OLD/'calls/C80-wire-request.json')
        self.assertEqual(request['messages'][0], old['messages'][0])
        self.assertEqual({k:v for k,v in request.items() if k!='messages'}, {k:v for k,v in old.items() if k!='messages'})
        frame = json.loads(request['messages'][1]['content'])
        receipts = [*frame['preceding_operation_feedback'],frame['workspace']['latest_feedback']]
        self.assertEqual([r['sequence'] for r in receipts], [185,186,187])
        operations = self.task.read(entry.OLD/'calls/C80-host-result.json')['operations']
        for shown, operation in zip(receipts, operations):
            expected = receipt_view(dict(sequence=shown['sequence'],action_summary=shown['action_summary'],result=operation['result']))
            diff = expected['result'].pop('applied_diff', None)
            self.assertEqual(shown['result'], expected['result'])
            if shown.get('applied_change'):
                self.assertEqual(shown['applied_change']['sha256'],sha256_bytes(diff.encode()))
        self.assertTrue(frame['workspace']['verification']['submission']['eligible'])
        self.assertEqual(frame['workspace']['working_account']['action_handle'],'EVT-0185')

    def test_wrong_guard_rejected_then_unchanged_checked_submit(self):
        session = self.task.initial_session()
        adapter = run_closure.Adapter(self.task)
        before = self.task.candidate_bytes(session.candidate)
        for identifier, accepted in [('0'*64,False),(session.candidate.candidate_id,True)]:
            session.begin_request()
            result = self.task.process_reply(session,dict(discussion='Offline guard qualification.',
                operation=dict(action='submit',expected_candidate_id=identifier)),lambda view:0,adapter.preceding_feedback)
            self.assertEqual(result['operations'][-1]['result']['accepted'],accepted)
            self.assertEqual(session.submitted,accepted)
        self.assertEqual(self.task.candidate_bytes(session.candidate),before)

    def test_changed_candidate_or_checker_cannot_reuse_pass(self):
        for condition in ('candidate','checker'):
            session = self.task.initial_session()
            original = copy.deepcopy(session.pairs)
            if condition == 'candidate':
                files = dict(session.candidate.file_map)
                files[entry.previous.DOC] += b'\n'
                session.candidate = Candidate.create(files,max_file_bytes=session.candidate.max_file_bytes)
                session.versions[session.candidate.candidate_id] = session.candidate
            else:
                session.checkers['public'] += b'\n# Reviewer qualification: different checker definition.\n'
            self.assertFalse(session.check_state()['applies_to_current'])
            result = session.execute(dict(action='submit',expected_candidate_id=session.candidate.candidate_id),lambda view:0)
            self.assertFalse(result['accepted'])
            self.assertFalse(session.submitted)
            self.assertEqual(session.pairs[:187],original)


if __name__ == '__main__':
    unittest.main()
