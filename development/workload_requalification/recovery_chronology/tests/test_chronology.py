import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import qualification as q
from working_set_exp.jsonutil import canonical_json_bytes

class ChronologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.base,_,_=q.restore('documentation-C52')
    def session(self):
        session=self.base.clone();session.__class__=q.Session
        return session
    def test_fitting_rows_preserve_required_view_and_archive(self):
        original=self.base.clone();original._fits_feedback(lambda view:10000)
        session=self.session();before=canonical_json_bytes(q.previous.snapshot(session))
        self.assertTrue(session._fits_feedback(lambda view:10000+len(view['recent_activity'])*100))
        view=session.view();self.assertEqual(len(view['recent_activity']),6)
        rows=view.pop('recent_activity');expected=original.view();expected.pop('recent_activity')
        self.assertEqual(view,expected)
        self.assertEqual(rows,[session.summary(i) for i in range(71,77)])
        self.assertEqual(session.pairs,self.base.pairs)
        self.assertEqual(session.candidate,self.base.candidate)
        self.assertEqual(session.working_account(),self.base.working_account())
    def test_capacity_selects_optional_suffix_then_restores(self):
        session=self.session()
        self.assertTrue(session._fits_feedback(lambda view:23500+100*len(view['recent_activity'])))
        self.assertEqual(session.recovery_recent_count,3)
        self.assertEqual([r['sequence'] for r in session.view()['recent_activity']],[74,75,76])
        self.assertTrue(session._fits_feedback(lambda view:23000+100*len(view['recent_activity'])))
        self.assertEqual(session.recovery_recent_count,6)
    def test_zero_rows_and_real_minimum_failure(self):
        session=self.session()
        self.assertTrue(session._fits_feedback(lambda view:23808+len(view['recent_activity'])))
        self.assertEqual(session.recovery_recent_count,0)
        self.assertFalse(session._fits_feedback(lambda view:23809))
        self.assertEqual(session.recovery_recent_count,0)
    def test_ordinary_view_unchanged(self):
        old=self.base.clone();old.recovery=False
        new=old.clone();new.__class__=q.Session
        self.assertEqual(new.view(),old.view())
        self.assertTrue(new._fits_feedback(lambda view:10000))
        old._fits_feedback(lambda view:10000)
        self.assertEqual(new.view(),old.view())
    def test_snapshot_restores_count_and_exact_view(self):
        session=self.session();session._fits_feedback(lambda view:23500+100*len(view['recent_activity']))
        saved=q.snapshot(session)
        restored=self.session();restored.recovery_recent_count=saved['recovery_recent_count']
        self.assertEqual(restored.view(),session.view())
        self.assertEqual(restored.clone().view(),session.view())

if __name__=='__main__':unittest.main()
