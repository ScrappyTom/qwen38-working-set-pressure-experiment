"""Actual entry, authority, identity and diagnostics; no model inference."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_saved_dispatch as saved
study = saved.study
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict


class SavedTransitionTests(unittest.TestCase):
    def setUp(self):
        self.module = saved.Task('dynamic','001',study.AREA/'union/run-002')
        self.session = self.module.initial_session()
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def act(self, operation):
        self.session.mark_delivered(self.session.view())
        self.session.begin_request()
        study.process_reply(self.session,dict(discussion='CPU transition qualification.',
                            operation=operation),lambda view:0,[])
        return self.session.pairs[-1]['result']

    def test_actual_entry_keeps_work_and_marks_prior_scope(self):
        old = self.module.inherited_state
        self.assertEqual(self.session.candidate,self.module.inherited_candidate)
        self.assertEqual(self.session.pairs,old['pairs'])
        self.assertEqual(len(self.session.versions),len(old['source_versions']))
        first = study.Task('union','002').restore(old,self.module.inherited_candidate,
                                               study.AREA/'union/run-002',replay=True)
        self.assertEqual(self.session.working_account(),first.working_account())
        view = self.session.view()
        self.assertEqual(view['archive']['prior_work_actions'],23)
        self.assertTrue(all(r['episode']=='prior_work' for r in view['recent_activity']))
        self.assertFalse(view['working_set']['sources'])
        self.assertFalse(self.session.delivered_sources)
        self.assertEqual(view['allowance']['requests_remaining'],24)
        self.assertEqual(view['allowance']['actions_remaining'],72)
        self.assertFalse(view['verification']['checks']['public']['applies_to_current'])
        state = study.snapshot(self.session)
        restored = self.module.restore(state,self.session.candidate,replay=True)
        self.assertEqual(canonical_json_bytes(study.snapshot(restored)),canonical_json_bytes(state))

    def test_released_source_has_no_authority_until_ordinary_delivery(self):
        old = study.Task('union','002').restore(self.module.inherited_state,
            self.module.inherited_candidate,study.AREA/'union/run-002',replay=True)
        target = next(s for s in old.view()['working_set']['sources'] if s['path']=='Lib/functools.py')
        operation = dict(action='replace_region',region=target['region_ref'],
            expected_candidate_id=self.session.candidate.candidate_id,
            new=target['content']+'\n# CPU authority probe.\n')
        original = self.session.candidate.candidate_id
        self.assertFalse(self.act(operation)['accepted'])
        self.assertEqual(self.session.candidate.candidate_id,original)
        self.assertTrue(self.act(dict(action='read',path='Lib/functools.py',
            start_line=target['returned_start_line'],end_line=target['returned_end_line']))['accepted'])
        self.assertTrue(self.act(operation)['accepted'])
        self.assertNotEqual(self.session.candidate.candidate_id,original)
        self.assertEqual(self.session.pairs[:23],self.module.inherited_state['pairs'])

    def test_history_identity_and_account_retrieval_do_not_promote(self):
        account = self.session.working_account()
        result = self.act(dict(action='reopen_event',handle='EVT-0017',offset=0))
        self.assertTrue(result['accepted'])
        self.assertEqual(self.session.working_account(),account)
        self.assertEqual(self.session.pairs[:23],self.module.inherited_state['pairs'])
        self.assertEqual(self.session.pairs[23]['response'],dict(
            action='reopen_event',handle='EVT-0017',offset=0))
        self.assertEqual(self.session.view()['recent_activity'][-1]['sequence'],24)
        self.assertEqual(self.session.view()['recent_activity'][-1]['episode'],'this_contribution')
        # The archived body names the same original account, not a new local act.
        self.assertIn('typing.Union',str(result))

    def test_old_pass_cannot_close_new_job(self):
        result = self.act(dict(action='submit',expected_candidate_id=self.session.candidate.candidate_id))
        self.assertFalse(result['accepted'])
        self.assertFalse(self.session.submitted)

    def test_cumulative_allowance_counts_companion_and_action(self):
        # A smaller CPU-only opportunity fixture tests the same absolute rule.
        self.session.call_limit = self.module.INHERITED_OPERATIONS+1
        before = canonical_json_bytes(study.snapshot(self.session))
        with self.assertRaisesRegex(ValueError,'insufficient operation allowance'):
            study.process_reply(self.session,dict(discussion='CPU allowance probe.',
                account='Must not be committed with an over-budget companion.',
                operation=dict(action='read',path='Lib/functools.py',start_line=1,end_line=1)),
                lambda view:0,[])
        self.assertEqual(canonical_json_bytes(study.snapshot(self.session)),before)
        self.assertTrue(self.act(dict(action='read',path='Lib/functools.py',start_line=1,end_line=1))['accepted'])
        self.assertEqual(self.session.calls_used,24)
        self.assertEqual(self.session.view()['allowance']['actions_remaining'],0)

    def test_new_check_distinguishes_preserved_success_and_dynamic_failure(self):
        store = study.ObservationStore(self.folder/'check',timeout=60)
        result = store.execute(self.session.candidate,
            study.checker('dynamic',self.module.inherited_candidate),'public','CHK-0001')
        self.assertFalse(result['passed'])
        rows = {r['case']:r for r in (load_json_strict(line) for line in
            (store.directory('CHK-0001')/'stdout.bin').read_bytes().splitlines()) if 'case' in r}
        for case in ('preserved_material','original_single_dispatch_suite',
                     'union_feature_contract','authored_union_regressions'):
            self.assertTrue(rows[case]['passed'])
        failed = rows['late_virtual_registration_contract']
        self.assertFalse(failed['passed'])
        self.assertEqual(failed['tests'],7)
        self.assertIn("'default'",'\n'.join(r['trace'] for r in failed['details']))


if __name__ == '__main__': unittest.main()
