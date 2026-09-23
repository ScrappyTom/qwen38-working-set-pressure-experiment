from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bootstrap
import continuity_task as task


class TransitionTests(unittest.TestCase):
    def test_failed_details_survive_later_search(self):
        session=task.restore('after/C36-O02')
        before=session.view()['verification']['checks']['public']['assessment']
        self.assertEqual(before['diagnostics_shown'],3)
        session.mark_delivered(session.view())
        result=session.execute(dict(action='search',path='Lib/configparser.py',query='MultilineContinuationError',offset=0,limit=5),lambda view:1)
        self.assertTrue(result['accepted'])
        self.assertEqual(before,session.view()['verification']['checks']['public']['assessment'])
        self.assertEqual(session.candidate.candidate_id,before['candidate_id'])

    def test_final_checkpoint_does_not_inherit_reviewers_check(self):
        session=task.Task().initial_session()
        self.assertEqual((session.requests_used,session.calls_used,session.request_limit,session.call_limit),(40,60,56,108))
        check=session.view()['verification']['checks']['public']
        self.assertFalse(check['applies_to_current'])
        self.assertEqual(check['assessment']['observation'],'CHK-0054')
        self.assertEqual(len(session.pairs),60)
        self.assertIn('rstrip',session.working_account()['text'])
        self.assertEqual(len(task.Task().initial_preceding_feedback()),1)

    def test_reference_matches_new_fragment_contract(self):
        reference=task.Task().operating_reference()
        self.assertIn('Returns up to two exact diagnostic field fragments.',reference)
        self.assertNotIn('Returns up to four complete assessment records',reference)
        self.assertNotIn('Use inspect_check for complete criterion records',reference)


if __name__=='__main__':unittest.main()
