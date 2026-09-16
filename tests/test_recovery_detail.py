"""Recovery detail follows actual complete-input capacity, not a shared cutoff."""
import copy
import unittest

from working_set_exp.candidate import Candidate
from working_set_exp.recovery_detail_session import RecoveryDetailSession
from test_decision_interface import DecisionTests


class RecoveryDetailTests(unittest.TestCase):
    setUp = DecisionTests.setUp

    def session(self, *, account='Known question.', payload='details'*300):
        s = RecoveryDetailSession(Candidate.create({'app.py':b'x = 1\nx = 1\n'}),
            {'tests':b'print("ok")','public':b'print("ok")'},'Contribute.',
            observations=self.store,edit_checks={},call_limit=48,request_limit=16)
        s.execute(dict(action='record_account',text=account),lambda view:1000)
        s.enter_recovery('fixture')
        s.recovery_focus=[dict(path='app.py',start_line=1,end_line=2)]
        s._record(dict(action='search',path='app.py',query='x',offset=0,limit=1),
                  dict(accepted=True,detail_blob=payload))
        return s

    @staticmethod
    def capacity(view):
        # Deterministic admission boundary test, not a native token measurement.
        if view['working_set']['sources']:
            return 24000
        if len(view['latest_feedback']['result'].get('detail_blob',''))>4000:
            return 24000
        if len((view['working_account'] or {}).get('text',''))>4000:
            return 24000
        return 1000

    def test_bulk_omission_does_not_keep_its_obsolete_control_cuts(self):
        s=self.session()
        old=copy.deepcopy(s.pairs)
        self.assertTrue(s._fits_feedback(self.capacity))
        v=s.view()
        self.assertEqual(v['working_set']['sources'],[])
        self.assertIn('detail_blob',v['latest_feedback']['result'])
        self.assertTrue(v['working_account']['text_complete'])
        self.assertEqual(s.pairs,old)
        clone=s.clone();self.assertEqual(clone.view(),v)
        clone.restored_control_fields=()
        self.assertEqual(s.view(),v)
        s.mark_delivered(v)
        source=s.source(s.recovery_focus[0])
        result=s.execute(dict(action='replace_region',region=source['region_ref'],
            expected_candidate_id=s.candidate.candidate_id,new='x = 2\n'),self.capacity)
        self.assertFalse(result['accepted'])
        self.assertIn('not visible',result['error'])

    def test_large_result_does_not_remove_a_fitting_account(self):
        s=self.session(payload='z'*6000)
        self.assertTrue(s._fits_feedback(self.capacity))
        v=s.view()
        self.assertNotIn('detail_blob',v['latest_feedback']['result'])
        self.assertEqual(v['latest_feedback']['output_scope'],'status_only_full_result_archived')
        self.assertTrue(v['working_account']['text_complete'])
        self.assertEqual(s.restored_control_fields,('account',))

    def test_large_account_does_not_remove_fitting_feedback(self):
        s=self.session(account='a'*6000)
        self.assertTrue(s._fits_feedback(self.capacity))
        v=s.view()
        self.assertIn('detail_blob',v['latest_feedback']['result'])
        self.assertFalse(v['working_account']['text_complete'])
        self.assertIn('exact_text_in',v['working_account'])
        self.assertEqual(s.restored_control_fields,('feedback',))

    def test_independent_limits_and_true_minimum_failure_stay_truthful(self):
        s=self.session(account='a'*6000,payload='z'*6000)
        self.assertTrue(s._fits_feedback(self.capacity))
        self.assertEqual(s.restored_control_fields,())
        self.assertFalse(s._fits_feedback(lambda view:24000))
        self.assertEqual(s.restored_control_fields,())

    def test_small_full_account_can_cost_less_than_truncation_metadata(self):
        s=self.session(account='x')
        def measure(v):
            if v['working_set']['sources'] or not v['working_account'].get('text_complete'):
                return 24000
            return 1000
        self.assertTrue(s._fits_feedback(measure))
        self.assertEqual(s.view()['working_account']['text'],'x')

    def test_restored_check_keeps_actual_execution_and_scoped_assessment(self):
        s=self.session()
        result=s.execute(dict(action='check',check_id='public',
            expected_candidate_id=s.candidate.candidate_id),self.capacity)
        self.assertTrue(result['executed'])
        view=s.view()
        shown=view['latest_feedback']['result']
        self.assertEqual(shown['observation'],result['observation'])
        self.assertTrue(shown['passed'])
        self.assertEqual(shown['report']['scope'],'public')
        self.assertFalse(shown['report']['assessment_available'])
        self.assertTrue(view['verification']['submission']['eligible'])


if __name__=='__main__':
    unittest.main()
