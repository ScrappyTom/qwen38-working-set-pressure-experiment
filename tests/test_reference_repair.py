"""Displayed addresses must remain usable without granting unseen edit authority."""
import unittest

from working_set_exp.candidate import Candidate
from working_set_exp.reference_session import ReferenceSession
from test_decision_interface import DecisionTests


class ReferenceTests(unittest.TestCase):
    setUp = DecisionTests.setUp
    read = DecisionTests.read

    def session(self):
        return ReferenceSession(Candidate.create({'app.py':b'a = 1\nb = 2\nc = 3\nd = 4\n',
                                                   'other.py':b'x = 1\ny = 2\n'}),
            {'tests':b'print("observed")','public':b'print("observed")'},
            'Contribute.', observations=self.store, edit_checks={}, call_limit=48, request_limit=16)

    def crowded(self):
        s = self.session()
        s.enter_recovery('fixture')
        for path, first, last in [('app.py',1,2),('app.py',3,3),('other.py',1,1),('other.py',2,2)]:
            self.assertTrue(self.read(s,path,first,last)['accepted'])
        s.mark_delivered(s.view())
        self.assertTrue(s.execute(dict(action='patch',path='app.py',old='b = 2',new='b = 20\ne = 5',
            expected_candidate_id=s.candidate.candidate_id,expected_file_sha256=s.candidate.file_sha256('app.py')),
            lambda v:1000)['accepted'])
        return s

    def test_changed_and_unchanged_merged_references_round_trip(self):
        s = self.crowded()
        sources = s.view()['working_set']['sources']
        self.assertEqual(len(sources),2)
        for source in sources:
            span = s.resolve_region(source['region_ref'])
            self.assertEqual(s.source(span),source)
        s.mark_delivered(s.view())
        source = next(v for v in sources if v['path']=='app.py')
        result = s.execute(dict(action='replace_region',region=source['region_ref'],
            expected_candidate_id=s.candidate.candidate_id,new=source['content'].replace('20','21')),lambda v:1000)
        self.assertTrue(result['accepted'],result)
        # Every successor address, not just the edited one, remains operable.
        for source in s.view()['working_set']['sources']:
            self.assertEqual(s.source(s.resolve_region(source['region_ref'])),source)

    def test_resolution_does_not_grant_undelivered_refreshed_source_authority(self):
        s = self.crowded()
        source = next(v for v in s.view()['working_set']['sources'] if v['path']=='app.py')
        s.resolve_region(source['region_ref'])
        before = s.candidate.candidate_id
        result = s.execute(dict(action='replace_region',region=source['region_ref'],
            expected_candidate_id=before,new=source['content'].replace('20','21')),lambda v:1000)
        self.assertFalse(result['accepted'])
        self.assertIn('not visible',result['error'])
        self.assertEqual(s.candidate.candidate_id,before)

    def test_returned_reference_selects_exact_region_and_keeps_guards(self):
        s = self.crowded()
        source = next(v for v in s.view()['working_set']['sources'] if v['path']=='other.py')
        result = s.execute(dict(action='work_on_exact',regions=[source['region_ref']],results=[]),lambda v:1000)
        self.assertTrue(result['accepted'],result)
        self.assertFalse(s.recovery)
        s.mark_delivered(s.view())
        action = dict(action='replace_region',region=source['region_ref'],
                      expected_candidate_id=s.candidate.candidate_id,new='x = 3\ny = 2\n')
        self.assertFalse(s.execute({**action,'expected_candidate_id':'0'*64},lambda v:1000)['accepted'])
        self.assertTrue(s.execute(action,lambda v:1000)['accepted'])
        with self.assertRaisesRegex(ValueError,'stale'):
            s.resolve_region(source['region_ref'])
        with self.assertRaisesRegex(ValueError,'not been provided'):
            s.resolve_region('SRC-'+'0'*64)

    def test_clamped_extent_uses_actual_rendered_address(self):
        s = self.session();s.enter_recovery('fixture')
        s.recovery_focus=[dict(path='app.py',start_line=1,end_line=999)]
        source,=s.view()['working_set']['sources']
        self.assertEqual(s.resolve_region(source['region_ref'])['end_line'],4)


if __name__ == '__main__':
    unittest.main()
