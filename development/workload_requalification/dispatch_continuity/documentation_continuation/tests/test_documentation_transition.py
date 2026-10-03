"""Earned namespace, scope, saved-entry and opportunity boundaries; no inference."""
import ast
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_documentation as entry
import reference_documentation
study = entry.study
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict
from run_saved_dispatch import Task as PreviousTask


class DocumentationTransitionTests(unittest.TestCase):
    def setUp(self):
        self.module = entry.Task()
        self.session = self.module.initial_session()
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def act(self, operation, account=None):
        self.session.mark_delivered(self.session.view())
        self.session.begin_request()
        reply = dict(discussion='CPU boundary qualification.', operation=operation)
        if account is not None: reply['account'] = account
        study.process_reply(self.session, reply, lambda view: 0, [])
        return self.session.pairs[-1]['result']

    def test_actual_entry_keeps_history_account_and_absolute_opportunity(self):
        old = self.module.inherited_state
        self.assertEqual(self.session.candidate, self.module.inherited_candidate)
        self.assertEqual(self.session.pairs, old['pairs'])
        self.assertEqual(len(self.session.versions), 11)
        previous = PreviousTask('dynamic', '001', study.AREA / 'union/run-002').restore(
            old, self.module.inherited_candidate, self.module.inherited, replay=True)
        self.assertEqual(self.session.working_account(), previous.working_account())
        view = self.session.view()
        self.assertEqual(view['archive']['prior_work_actions'], 51)
        self.assertTrue(all(r['episode'] == 'prior_work' for r in view['recent_activity']))
        self.assertFalse(view['working_set']['sources'])
        self.assertFalse(self.session.delivered_sources)
        self.assertEqual((view['allowance']['requests_remaining'],
                          view['allowance']['actions_remaining']), (12, 36))
        self.assertEqual((self.module.MAX_REQUESTS, self.module.MAX_OPERATIONS), (44, 87))
        self.assertFalse(view['verification']['checks']['public']['applies_to_current'])
        state = study.snapshot(self.session)
        restored = self.module.restore(state, self.session.candidate, replay=True)
        self.assertEqual(canonical_json_bytes(study.snapshot(restored)), canonical_json_bytes(state))

    def test_release_requires_ordinary_current_source_and_preserves_identity(self):
        old_source = next(s for s in self.module.inherited_state['delivered_sources']
                          if s['path'] == entry.DOC)
        operation = dict(action='replace_region', region=old_source['region_ref'],
            expected_candidate_id=self.session.candidate.candidate_id,
            new=self.session.candidate.file_map[entry.DOC].decode())
        self.assertFalse(self.act(operation)['accepted'])
        self.assertTrue(self.act(dict(action='read', path=entry.DOC, start_line=1, end_line=0))['accepted'])
        source, = [s for s in self.session.view()['working_set']['sources'] if s['path'] == entry.DOC]
        operation['region'] = source['region_ref']
        operation['new'] = reference_documentation.correction(source['content'])
        self.assertTrue(self.act(operation)['accepted'])
        self.assertEqual(self.session.pairs[:51], self.module.inherited_state['pairs'])
        for path, raw in self.module.inherited_candidate.file_map.items():
            if path != entry.DOC: self.assertEqual(self.session.candidate.file_map[path], raw)

    def test_new_check_preserves_real_namespace_failure_and_protected_scope(self):
        program = entry.checker(self.module.inherited_candidate)
        config = ast.literal_eval(program.split(b'\n', 1)[0].removeprefix(b'CONFIG = ').decode())
        self.assertEqual(set(config['unchanged']), set(self.session.candidate.file_map) - {entry.DOC})
        store = study.ObservationStore(self.folder / 'check', timeout=60)
        result = store.execute(self.session.candidate, program, 'public', 'CHK-0001')
        self.assertFalse(result['passed'])
        rows = {r['case']: r for r in (load_json_strict(line) for line in
            (store.directory('CHK-0001') / 'stdout.bin').read_bytes().splitlines()) if 'case' in r}
        self.assertTrue(all(row['passed'] for name, row in rows.items() if name != 'executable_documentation'))
        row = rows['executable_documentation']
        self.assertEqual((row['namespace'], row['failed'], row['attempted']), ('__main__', 1, 14))
        self.assertIn("<class '__main__.Payload'>", row['runner_output'])
        self.assertIn("<class 'Payload'>", row['runner_output'])

    def test_old_pass_cannot_submit_and_historical_account_is_not_promoted(self):
        account = self.session.working_account()
        self.assertFalse(self.act(dict(action='submit',
            expected_candidate_id=self.session.candidate.candidate_id))['accepted'])
        self.assertTrue(self.act(dict(action='reopen_event', handle='EVT-0050', offset=0))['accepted'])
        self.assertEqual(self.session.working_account(), account)
        self.assertEqual(self.session.pairs[:51], self.module.inherited_state['pairs'])

    def test_cumulative_limit_rejects_over_budget_companion_atomically(self):
        self.session.call_limit = 52
        before = canonical_json_bytes(study.snapshot(self.session))
        with self.assertRaisesRegex(ValueError, 'insufficient operation allowance'):
            study.process_reply(self.session, dict(discussion='CPU opportunity qualification.',
                account='Must not commit this over-budget request.',
                operation=dict(action='read', path=entry.DOC, start_line=1, end_line=1)),
                lambda view: 0, [])
        self.assertEqual(canonical_json_bytes(study.snapshot(self.session)), before)


if __name__ == '__main__': unittest.main()
