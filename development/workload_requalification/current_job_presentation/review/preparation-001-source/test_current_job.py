"""Derived-state, authority and intended-execution boundaries; no model calls."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import overlap_task as entry
import overlap_reference as reference_work
study = entry.study
from working_set_exp.current_job_view import render
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict
from working_set_exp.observations import ObservationStore


class CurrentJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.task = entry.Task()
        cls.entry = cls.task.initial_session()

    def projected(self, state=None):
        view = copy.deepcopy(self.entry.view())
        if state is not None: view['verification']['checks']['public'] = state
        return render(view, title=entry.TITLE, pairs=self.entry.pairs,
            boundary=57, submitted=False)

    def test_same_candidate_changed_checker_preserves_accepted_history(self):
        original = self.entry.view()
        frozen = canonical_json_bytes(original)
        result = self.projected()
        self.assertEqual(result['current_job']['submission'], 'open')
        self.assertEqual(result['prior_work']['latest_accepted_submission']['outcome'], 'accepted')
        self.assertEqual(result['prior_work']['latest_accepted_submission']['action_handle'], 'EVT-0057')
        self.assertEqual(result['verification']['checks']['public']['status'], 'not_executed_for_current_candidate_and_checker')
        self.assertTrue(result['verification']['historical_checks']['public']['passed'])
        self.assertEqual(result['working_account']['text'], original['working_account']['text'])
        self.assertEqual(result['working_account']['authored_in'], 'prior_work')
        self.assertEqual(canonical_json_bytes(original), frozen)

    def test_changed_candidate_and_executed_current_fail_or_pass(self):
        state = copy.deepcopy(self.entry.verification_view()['checks']['public'])
        state.update(candidate_matches=False, check_definition_matches=True, applies_to_current=False)
        self.assertIn('public', self.projected(state)['verification']['historical_checks'])
        for passed in (False, True):
            state.update(passed=passed, candidate_matches=True, applies_to_current=True)
            result = self.projected(state)['verification']['checks']['public']
            self.assertEqual(result['status'], 'passed' if passed else 'failed')
            self.assertEqual(result['evidence_origin'], 'prior_work')
            # A genuinely applicable historical observation is not relabelled
            # as absent merely because the current job is new.
            self.assertEqual(result['passed'], passed)

    def test_invalid_boundary_rejected_and_account_clear_kept(self):
        with self.assertRaises(ValueError):
            render(self.entry.view(), title=entry.TITLE, pairs=self.entry.pairs,
                boundary=58, submitted=False)
        view = self.entry.view(); view['working_account'] = None
        self.assertIsNone(render(view, title=entry.TITLE, pairs=self.entry.pairs,
            boundary=57, submitted=False)['working_account'])

    def test_conditions_restore_equal_state_and_source_authority(self):
        control, treatment = entry.Task(), entry.Task('current_job')
        a, b = control.initial_session(), treatment.initial_session()
        self.assertEqual(study.snapshot(a), study.snapshot(b))
        self.assertEqual(a.reply_schema(), b.reply_schema())
        self.assertEqual(control.restore(study.snapshot(a), a.candidate).view(), a.view())
        self.assertEqual(treatment.restore(study.snapshot(b), b.candidate).view(), b.view())
        self.assertFalse(a.delivered_sources); self.assertFalse(b.delivered_sources)
        for session in (a, b):
            session.mark_delivered(session.view()); session.begin_request()
            result = study.process_reply(session, dict(discussion='CPU guard case.',
                operation=dict(action='submit', expected_candidate_id=session.candidate.candidate_id)), lambda _: 0, [])
            self.assertFalse(result['operations'][-1]['result']['accepted'])

    def test_real_checker_pass_failure_normal_namespace_and_fault_sensitivity(self):
        with tempfile.TemporaryDirectory() as folder:
            store = ObservationStore(Path(folder), timeout=60)
            program = entry.checker(self.entry.candidate)
            before = store.execute(self.entry.candidate, program, 'public', 'CHK-0001')
            self.assertFalse(before['passed'])
            files = dict(self.entry.candidate.file_map)
            files[entry.TEST] = reference_work.tests(files[entry.TEST].decode()).encode()
            files[entry.DOC] = reference_work.documentation(files[entry.DOC].decode()).encode()
            candidate = study.Candidate.create(files, max_file_bytes=study.FILE_LIMIT)
            after = store.execute(candidate, program, 'public', 'CHK-0002')
            rows = {r['case']: r for r in (load_json_strict(line) for line in
                (store.directory('CHK-0002')/'stdout.bin').read_bytes().splitlines()) if 'case' in r}
            self.assertTrue(after['passed'], (store.directory('CHK-0002')/'stdout.bin').read_text())
            ordinary = rows['ordinary_standalone_documentation']
            self.assertEqual(ordinary['namespace'], '__main__')
            self.assertEqual(ordinary['failed'], 0)
            self.assertEqual(ordinary['attempted'], rows['executable_documentation']['attempted'])
            self.assertTrue(rows['new_regressions_detect_resolver_fault']['passed'])
            self.assertFalse(rows['new_regressions_detect_resolver_fault']['fault_execution']['passed'])


if __name__ == '__main__': unittest.main()
