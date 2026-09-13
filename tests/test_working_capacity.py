import json
import unittest
from unittest.mock import patch

from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes
from working_set_exp.working_session import WorkingSession, INPUT_LIMIT, CONTROL_ROOM


def make_session():
    return WorkingSession(Candidate.create({'app.py':b'value = 1\n','note.txt':b'preserve the behavior\n'}),
        b'assert True\n', 'make a checked contribution', call_limit=20)


def execute(session, action, measure=lambda view: 1000):
    session.mark_delivered(session.view())
    return session.execute(action, measure)


class WorkingCapacityTests(unittest.TestCase):
    def test_reserved_room_can_deliver_full_historical_result(self):
        s = make_session()
        execute(s, dict(action='read',path='app.py',start_line=1,end_line=0))
        body = s.payload('RES-0001')
        before = s.sources()
        result = execute(s,dict(action='reopen_result',handle='RES-0001',offset=0),lambda view: INPUT_LIMIT-460)
        self.assertTrue(result['accepted'])
        self.assertIsNone(result['next_offset'])
        self.assertEqual(result['exact_utf8'].encode(),body)
        self.assertEqual(s.sources(),before)

    def test_complete_edit_and_check_can_spend_acquisition_headroom(self):
        s = make_session()
        execute(s,dict(action='read',path='app.py',start_line=1,end_line=0))
        result = execute(s,dict(action='patch',path='app.py',old='value = 1',new='value = 2',
            expected_candidate_id=s.candidate.candidate_id,expected_file_sha256=s.candidate.file_sha256('app.py')),
            lambda view: INPUT_LIMIT)
        self.assertTrue(result['accepted'])
        self.assertEqual(s.sources()[0]['content'],'value = 2\n')
        actual = dict(accepted=True,passed=False,checked_candidate_id=s.candidate.candidate_id,stdout='actual diagnostic')
        with patch.object(WorkingSession,'_ordinary',return_value=actual):
            result = execute(s,dict(action='check',check_id='public',expected_candidate_id=s.candidate.candidate_id),lambda view: INPUT_LIMIT-1)
        self.assertEqual(result,actual)
        self.assertNotIn('output_scope',s.last)
        self.assertEqual(s.last['result']['stdout'],'actual diagnostic')

    def test_source_acquisition_prefers_reserve_but_can_spend_it(self):
        for action in ('read','work_on'):
            with self.subTest(action=action):
                s = make_session()
                span = dict(path='app.py',start_line=1,end_line=0)
                request = dict(action='read',**span) if action=='read' else dict(action='work_on',sources=[span],results=[])
                self.assertTrue(execute(s,request,lambda view:INPUT_LIMIT-1)['accepted'])
                self.assertEqual(s.sources()[0]['content'],'value = 1\n')
        # A broad source with available paging still leaves the preferred room.
        s = WorkingSession(Candidate.create({'app.py':b'x = 1\n'*2000}),b'', 'inspect')
        measure = lambda view: 22000 + len(canonical_json_bytes(view))//6
        result = execute(s,dict(action='read',path='app.py',start_line=1,end_line=0),measure)
        self.assertTrue(result['accepted'])
        self.assertIsNotNone(result['source']['next_start_line'])
        self.assertLessEqual(measure(s.view()), INPUT_LIMIT-CONTROL_ROOM)

    def test_hard_limit_still_rejects_edit_without_mutation(self):
        s = make_session()
        execute(s,dict(action='read',path='app.py',start_line=1,end_line=0))
        before, ranges = s.candidate, list(s.ranges)
        result = execute(s,dict(action='patch',path='app.py',old='value = 1',new='value = 2',
            expected_candidate_id=before.candidate_id,expected_file_sha256=before.file_sha256('app.py')),
            lambda view: INPUT_LIMIT+1 if view['candidate_id'] != before.candidate_id else 1000)
        self.assertFalse(result['accepted'])
        self.assertEqual(s.candidate,before)
        self.assertEqual(s.ranges,ranges)
        self.assertEqual(s.diffs,{})

    def test_file_history_includes_grouped_acquisition(self):
        s = make_session()
        action = dict(action='work_on',sources=[dict(path=p,start_line=1,end_line=0) for p in ('app.py','note.txt')],results=[])
        execute(s,action)
        for name in ('app.py','note.txt'):
            result = execute(s.clone(),dict(action='history',before=0,path=name))
            self.assertEqual([r['sequence'] for r in result['entries']],[1])
            self.assertEqual(result['entries'][0]['source_paths'],['app.py','note.txt'])
        result = execute(s.clone(),dict(action='history',before=0,path='absent.py'))
        self.assertEqual(result['entries'],[])
        self.assertEqual(json.loads(s.payload('EVT-0001')),action)

    def test_candidate_boundary_returns_rejection_without_mutation(self):
        s = make_session()
        execute(s,dict(action='read',path='app.py',start_line=1,end_line=0))
        before, sources = s.candidate, s.sources()
        result = execute(s,dict(action='patch',path='app.py',old='value = 1',new='#'+'x'*512,
            expected_candidate_id=before.candidate_id,expected_file_sha256=before.file_sha256('app.py')))
        self.assertFalse(result['accepted'])
        self.assertIn('source line exceeds byte bound',result['error'])
        self.assertEqual(s.candidate,before)
        self.assertEqual(s.sources(),sources)
        self.assertEqual(s.diffs,{})


if __name__ == '__main__':
    unittest.main()
