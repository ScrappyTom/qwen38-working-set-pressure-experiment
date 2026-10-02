"""Focused CPU boundary checks; native admission is separately qualified."""
import copy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import unittest

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import url_task as module
import qualification_route as route
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict


class UrlPortEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = AREA / 'review/cpu-tests' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        cls.folder.mkdir(parents=True, exist_ok=False)
        print('Preserved CPU observation evidence:', cls.folder)

    def test_original_verdict_equivalence_and_useful_report(self):
        folder = self.folder / 'equivalence'
        rows = route.run_equivalence(module, folder)
        (folder / 'equivalence.json').write_bytes(canonical_json_bytes(rows))
        self.assertEqual(len(rows), 32)
        self.assertTrue(all(r['observation']['capture_complete'] for r in rows))
        contract = module.checkers.contracts()
        store = module.ObservationStore(folder / 'wrong_expected_message/preserved')
        failed = module.url_reports.assessment(store, 'CHK-0001', contract['tests'])
        self.assertFalse(failed['normal_control_passed'])
        mutants = [r for r in failed['criteria'] if r['criterion'].startswith('detect.')]
        self.assertEqual(len(mutants), 7)
        self.assertTrue(all(r['met'] is None and r['injected_suite_executed'] for r in mutants))
        self.assertTrue(any('Port out of range 0-65535' in str(r) for r in failed['criteria']))
        overview = module.url_reports.overview(failed)
        self.assertEqual(overview['unassessed_records_total'], 7)
        self.assertEqual(overview['failed_records_total'], len(failed['failed_criteria']))
        store = module.ObservationStore(folder / 'weak_exact_class/preserved')
        weak = module.url_reports.assessment(store, 'CHK-0001', contract['tests'])
        self.assertTrue(weak['normal_control_passed'])
        undetected = next(r for r in weak['criteria'] if r['criterion'] == 'detect.error_class')
        self.assertFalse(undetected['met'])
        self.assertTrue(undetected['test_run_passed'])
        store = module.ObservationStore(folder / 'correct/preserved')
        good = module.url_reports.assessment(store, 'CHK-0001', contract['public'])
        self.assertTrue(good['normal_control_passed'])
        self.assertTrue(all(r['met'] is True for r in good['criteria']))
        raw = (store.directory('CHK-0001') / 'stdout.bin').read_bytes()
        full = load_json_strict(raw)
        self.assertEqual(set(full['fault_sensitivity']), set(module.checkers.FAULTS))
        self.assertTrue(all('runner_output' in v and 'details' in v for v in full['fault_sensitivity'].values()))
        # Unsupported process output remains an observation, never invented
        # ordinary-test or injected-fault conclusions.
        unsupported = module.ObservationStore(self.folder / 'unsupported')
        record = unsupported.execute(module.starting_candidate(),
            b"import sys; print('unrelated process problem'); raise SystemExit(3)\n", 'tests', 'CHK-0001')
        self.assertFalse(record['passed'])
        assessment = module.url_reports.assessment(unsupported, 'CHK-0001')
        self.assertFalse(assessment['assessment_available'])
        self.assertIn('unrelated process problem', str(assessment['execution_diagnostic']))
        self.assertEqual(assessment['criteria'], [])
        limited = module.ObservationStore(self.folder / 'incomplete', stream_limit=64)
        record = limited.execute(module.starting_candidate(), b"print('X' * 20000)\n", 'tests', 'CHK-0001')
        self.assertFalse(record['capture_complete'])
        assessment = module.url_reports.assessment(limited, 'CHK-0001')
        self.assertFalse(assessment['assessment_available'])
        self.assertEqual(assessment['criteria'], [])

    def test_actual_correction_refresh_submission_and_multidigit_restore(self):
        folder = self.folder / 'contribution'
        session = module.initial_session(folder)
        preceding = []
        records = route.qualify_contribution(module, session, lambda view: 0, preceding)
        self.assertTrue(session.submitted)
        self.assertEqual(len(records), 15)
        self.assertTrue(any(r['reply']['operation']['action'] == 'work_on_exact' for r in records))
        snapshot = module.snapshot(session)
        self.assertTrue(any(k >= 10 for k in snapshot['diffs']))
        loaded = load_json_strict(canonical_json_bytes(snapshot))
        original = copy.deepcopy(loaded)
        restored = module.restore(loaded, session.candidate, folder, replay=True)
        self.assertEqual(loaded, original)
        self.assertEqual(restored.view(), session.view())
        direct = copy.deepcopy(snapshot)
        restored_direct = module.restore(direct, session.candidate, folder, replay=True)
        self.assertEqual(restored_direct.view(), session.view())
        for mode in ('alias', 'receipt_mismatch', 'unknown', 'duplicate'):
            state = copy.deepcopy(loaded)
            key = next(iter(state['diffs']))
            if mode == 'alias':
                state['diffs']['0' + key] = state['diffs'].pop(key)
            elif mode == 'receipt_mismatch':
                state['diffs'][key] += '\nforged'
            elif mode == 'unknown':
                state['diffs']['999'] = state['diffs'].pop(key)
            else:
                state['diffs'][int(key)] = state['diffs'][key]
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                module.restore(state, session.candidate, folder, replay=True)

    def test_broad_capacity_recovery_and_selectable_exact_region(self):
        session = module.initial_session(self.folder / 'capacity')
        # Deliberately synthetic CPU capacity: this checks transition semantics,
        # not token feasibility. Native preparation measures the identical route.
        def synthetic_measure(view):
            return 6000 + len(canonical_json_bytes(view)) // 4
        rows = route.qualify_capacity(module, session, synthetic_measure, [])
        self.assertEqual(len(rows), 7)
        self.assertTrue(rows[3]['after_view']['presentation']['selected_bodies_omitted'])
        self.assertFalse(rows[-1]['after_view']['presentation']['selected_bodies_omitted'])
        self.assertEqual(session.candidate.candidate_id, module.STARTING_ID)
        self.assertFalse(session.submitted)
        self.assertFalse(any(pair['result'].get('executed') for pair in session.pairs))
        self.assertEqual(session.requests_used, 7)

    def test_fresh_entry_and_address_without_body_cannot_edit(self):
        session = module.initial_session(self.folder / 'eligibility')
        self.assertEqual(session.candidate.candidate_id, module.STARTING_ID)
        self.assertEqual(session.requests_used, 0)
        self.assertEqual(session.pairs, [])
        self.assertEqual(session.view()['working_set']['sources'], [])
        self.assertIsNone(session.working_account())
        before = session.view()
        session.mark_delivered(before)
        session.begin_request()
        out = module.process_reply(session, dict(discussion='Deliberate exact anchor with no delivered source.',
            operation=dict(action='patch', path=route.TEST, old=route.TEST_ANCHOR,
                new='# unearned edit\n' + route.TEST_ANCHOR,
                expected_candidate_id=session.candidate.candidate_id,
                expected_file_sha256=session.candidate.file_sha256(route.TEST))), lambda view: 0, [])
        self.assertEqual(len(out['operations']), 1)
        self.assertFalse(out['operations'][0]['result']['accepted'])
        self.assertFalse(out['policy_check']['executed'])
        self.assertEqual(session.candidate.candidate_id, module.STARTING_ID)


if __name__ == '__main__':
    unittest.main()
