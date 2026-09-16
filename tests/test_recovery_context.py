"""A read does not resolve ambiguity in an unchanged file's rejected edit."""
import unittest
from working_set_exp.candidate import Candidate
from working_set_exp.recovery_context_session import RecoveryContextSession
from test_decision_interface import DecisionTests


class RecoveryContextTests(unittest.TestCase):
    setUp = DecisionTests.setUp

    def session(self):
        s=RecoveryContextSession(Candidate.create({'app.py':b'x = 1\nx = 1\n'}),
            {'public':b'print("ok")'},'Contribute.',observations=self.store,edit_checks={})
        s.enter_recovery('fixture')
        s.execute(dict(action='read',path='app.py',start_line=1,end_line=2),lambda v:1000)
        s.mark_delivered(s.view())
        result=s.execute(dict(action='patch',path='app.py',old='x = 1',new='x = 2',
            expected_candidate_id=s.candidate.candidate_id,
            expected_file_sha256=s.candidate.file_sha256('app.py')),lambda v:1000)
        self.assertFalse(result['accepted'])
        return s

    def test_current_rejection_is_not_duplicated_then_survives_read(self):
        s=self.session()
        self.assertIsNone(s.view()['recent_edit_rejection'])
        s.execute(dict(action='read',path='app.py',start_line=1,end_line=1),lambda v:1000)
        value=s.view()['recent_edit_rejection']
        self.assertEqual(value['kind'],'historical_rejection_no_edit_committed')
        self.assertTrue(value['file_binding_matches_current'])
        self.assertEqual(value['receipt']['result']['match_count'],2)
        self.assertEqual(len(value['receipt']['result']['match_regions']),2)
        self.assertNotIn('old',value['receipt']['action_summary'])
        self.assertEqual(s.clone().view(),s.view())

    def test_file_change_retires_old_diagnostic_without_erasing_archive(self):
        s=self.session()
        s.execute(dict(action='read',path='app.py',start_line=1,end_line=1),lambda v:1000)
        s.mark_delivered(s.view())
        source=s.view()['working_set']['sources'][0]
        result=s.execute(dict(action='replace_region',region=source['region_ref'],
            expected_candidate_id=s.candidate.candidate_id,new='x = 2\nx = 1\n'),lambda v:1000)
        self.assertTrue(result['accepted'])
        self.assertIsNone(s.view()['recent_edit_rejection'])
        self.assertEqual(s.pairs[1]['result']['match_count'],2)


if __name__=='__main__':
    unittest.main()
