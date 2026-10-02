"""Focused CPU custody/phase boundaries; no inference or GPU operations.

Zero-cost input measurement tests state transitions, not native input capacity.
Deliberately malformed report text is an engineering fixture, not actor evidence.
"""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import saved_report_task as task
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict


REPORT = 'reports/incident.json'
STARTING = 'f7939c49b60d57f19b88dde8d31c6deb0ea036b6a3746c5d27b61d5ce0b99fd6'
MALFORMED = '{"builds": []\n'


def shown_saved(view):
    pages = list(view['working_set']['saved_results'])
    latest = view.get('latest_feedback')
    if latest:
        result = latest['result']
        pages.extend(result.get('saved_results', []))
        if result.get('kind') == 'saved_bytes':
            pages.append(result)
    return {page['handle']: page['exact_utf8'].encode() for page in pages
            if page['offset'] == 0 and page['next_offset'] is None and 'exact_utf8' in page}


def shown_captures(view):
    receipts = [load_json_strict(body) for body in shown_saved(view).values()]
    latest = view.get('latest_feedback')
    if latest:
        receipts.append(latest['result'])
    return {receipt['handle']: receipt['content_utf8'].encode() for receipt in receipts
            if receipt.get('accepted') and receipt.get('kind') == 'imported_observation'}


class SavedReportEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='saved-report-entry-test-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.session = task.initial_session(self.folder)
        self.preceding = []

    def setup_phase(self, phase, record=None):
        return task.setup(self.session, phase, lambda view: 0, self.preceding, record=record)

    def reply(self, operation=None, account=None):
        self.session.mark_delivered(self.session.view())
        self.session.begin_request()
        value = {'discussion': 'CPU phase boundary qualification.'}
        if operation is not None:
            value['operation'] = operation
        if account is not None:
            value['account'] = account
        return task.process_reply(self.session, value, lambda view: 0, self.preceding)

    def report_patch(self, text=MALFORMED):
        return {'action': 'patch', 'path': REPORT,
                'old': self.session.candidate.file_map[REPORT].decode(), 'new': text,
                'expected_candidate_id': self.session.candidate.candidate_id,
                'expected_file_sha256': self.session.candidate.file_sha256(REPORT)}

    def check(self, account=None):
        return self.reply({'action': 'check', 'check_id': 'public',
                           'expected_candidate_id': self.session.candidate.candidate_id}, account)

    def test_starting_custody_and_four_setup_results_are_separate_from_actor_work(self):
        original_pairs = load_json_strict((task.ROOT / 'development/delivery_dialogue/proposal-check-001/scripted-pairs.json').read_bytes())
        self.assertEqual(self.session.candidate.candidate_id, STARTING)
        self.assertEqual(canonical_json_bytes(self.session.pairs), canonical_json_bytes(original_pairs))
        self.assertEqual(self.session.starting_archive_length, 3)
        self.assertEqual((self.session.requests_used, self.session.calls_used), (0, 0))
        self.assertEqual(self.session.call_limit, 41)
        for number, pair in enumerate(original_pairs, 1):
            self.assertEqual(self.session.payload(f'RES-{number:04d}'), canonical_json_bytes(pair['result']))
        legacy = original_pairs[2]['result']
        self.assertNotIn('observation', legacy)
        self.assertNotIn('check_definition_sha256', legacy)
        self.assertIn('25/26 contract cases passed', legacy['stdout'])
        self.assertFalse(self.session.check_state()['applies_to_current'])
        self.assertFalse(self.session.check_state()['check_definition_matches'])

        recorded = []
        sequences = self.setup_phase(1, lambda sequence, action, result: recorded.append((sequence, action, result)))
        self.assertEqual(sequences, [4, 5, 6, 7])
        self.assertEqual([x[1]['action'] for x in recorded], ['read', 'read', 'reopen_observation', 'reopen_observation'])
        counters = self.session.phase_counters()
        self.assertEqual((counters['phase_requests_used'], counters['phase_actor_operations_used']), (0, 0))
        self.assertEqual((counters['inherited_operations'], counters['assisted_operations_new'], counters['archived_operations']), (3, 4, 7))
        self.assertEqual(counters['phase_requests_remaining'], 8)
        self.assertEqual(counters['phase_actor_operations_remaining'], 16)
        view = self.session.view()
        self.assertEqual(shown_captures(view), {handle: self.session.imported_record(handle)[1] for handle in ('OBS-0001', 'OBS-0002')})
        sources = {row['path']: row['content'].encode() for row in view['working_set']['sources']}
        self.assertEqual(sources, {name: self.session.candidate.file_map[name] for name in ('README.md', REPORT)})
        self.assertFalse(view['verification']['after_accepted_edit'])
        self.assertNotIn('EXPECTED_REPORT', canonical_json_bytes(view).decode())

    def test_transition_requires_actual_post_edit_execution_not_rejection_or_retrieval(self):
        self.setup_phase(1)
        pre_edit = self.check()['operations'][-1]['result']
        self.assertTrue(pre_edit['accepted'] and pre_edit['executed'])
        self.assertFalse(self.session.transition_ready())
        stale = self.report_patch()
        stale['expected_candidate_id'] = '0' * 64
        rejected = self.reply(stale)['operations'][-1]['result']
        self.assertFalse(rejected['accepted'])
        self.assertEqual(self.session.candidate.candidate_id, STARTING)
        self.assertFalse(self.session.transition_ready())
        self.assertTrue(self.reply(self.report_patch())['operations'][-1]['result']['accepted'])
        self.assertFalse(self.session.transition_ready())
        rejected_check = self.reply({'action': 'check', 'check_id': 'public', 'expected_candidate_id': STARTING})['operations'][-1]['result']
        self.assertFalse(rejected_check['accepted'])
        self.assertFalse(self.session.transition_ready())
        self.assertTrue(self.reply({'action': 'reopen_result', 'handle': 'RES-0003', 'offset': 0})['operations'][-1]['result']['accepted'])
        self.assertFalse(self.session.transition_ready())
        checked = self.check()['operations'][-1]['result']
        self.assertTrue(checked['accepted'] and checked['executed'])
        self.assertFalse(checked['passed'])
        self.assertTrue(self.session.transition_ready())
        self.assertEqual(self.session.phase_counters()['phase_actor_operations_used'], 6)

    def test_restart_preserves_actual_work_check_account_and_expires_unused_opportunity(self):
        self.setup_phase(1)
        nonreport = {name: raw for name, raw in self.session.candidate.file_map.items() if name != REPORT}
        account = 'The report has been saved provisionally; consume its actual check before revising it.'
        self.reply(self.report_patch(), account)
        checked = self.check(account='The saved expectation remains provisional until the result is interpreted.')
        check_result = checked['operations'][-1]['result']
        self.assertFalse(check_result['passed'])
        self.assertIn('JSONDecodeError', canonical_json_bytes(check_result).decode())
        check_handle = f'RES-{len(self.session.pairs):04d}'
        check_bytes = self.session.payload(check_handle)
        saved_candidate = self.session.candidate
        saved_pairs = copy.deepcopy(self.session.pairs)
        saved_account = self.session.working_account()
        before_requests = self.session.requests_used
        self.assertEqual(before_requests, 2)
        self.assertTrue(self.session.delivered_sources)
        first_boundary = []
        def record(sequence, action, result):
            if not first_boundary:
                first_boundary.append((copy.deepcopy(self.session.delivered_sources), copy.deepcopy(self.session.working_account())))
        setup_sequences = self.setup_phase(2, record)
        self.assertEqual(first_boundary, [([], saved_account)])
        self.assertEqual(self.session.candidate, saved_candidate)
        self.assertEqual(self.session.candidate.file_map[REPORT], MALFORMED.encode())
        self.assertEqual(self.session.pairs[:len(saved_pairs)], saved_pairs)
        self.assertEqual(self.session.working_account(), saved_account)
        self.assertEqual(len(setup_sequences), 5)
        self.assertEqual(self.session.requests_used, before_requests)
        counters = self.session.phase_counters()
        self.assertEqual((counters['phase'], counters['phase_requests_used'], counters['phase_actor_operations_used']), (2, 0, 0))
        self.assertEqual(counters['phase_requests_remaining'], 8)
        self.assertEqual(counters['assisted_operations_new'], 9)
        self.assertEqual(counters['actor_operations_used'], 4)
        view = self.session.view()
        self.assertEqual(shown_captures(view), {handle: self.session.imported_record(handle)[1] for handle in ('OBS-0001', 'OBS-0003')})
        self.assertEqual(shown_saved(view)[check_handle], check_bytes)
        self.assertFalse(next(row for row in view['imported_observations']['entries'] if row['handle'] == 'OBS-0002')['shown_complete'])
        self.assertEqual({name: raw for name, raw in self.session.candidate.file_map.items() if name != REPORT}, nonreport)
        for number in range(8):
            self.reply({'action': 'read', 'path': 'README.md', 'start_line': 1, 'end_line': 0}, account=f'Phase-two budget fixture {number}.')
        self.assertEqual(self.session.requests_used, 10)
        self.assertEqual(self.session.phase_counters()['phase_actor_operations_used'], 16)
        self.assertFalse(self.session.phase_budget_available())
        with self.assertRaises(ValueError):
            self.session.begin_request()

    def test_eight_requests_per_phase_reach_exact_forty_four_archive_ceiling(self):
        self.setup_phase(1)
        self.reply(self.report_patch(), account='Budget fixture: pending real check.')
        for number in range(6):
            self.reply({'action': 'read', 'path': 'README.md', 'start_line': 1, 'end_line': 0}, account=f'Phase-one budget fixture {number}.')
        self.check(account='Last phase-one reply requests actual verification.')
        self.assertTrue(self.session.transition_ready())
        self.assertEqual(self.session.phase_counters()['phase_actor_operations_used'], 16)
        self.setup_phase(2)
        for number in range(8):
            self.reply({'action': 'read', 'path': 'README.md', 'start_line': 1, 'end_line': 0}, account=f'Phase-two budget fixture {number}.')
        counters = self.session.phase_counters()
        self.assertEqual((counters['cumulative_requests_used'], counters['actor_operations_used']), (16, 32))
        self.assertEqual((counters['assisted_operations_total'], counters['archived_operations'], counters['backend_new_operations']), (12, 44, 41))
        self.assertEqual(len(self.session.pairs), 44)
        self.assertEqual(self.session.last['sequence'], 44)
        self.assertEqual(self.session.payload('RES-0003'), canonical_json_bytes(self.session.pairs[2]['result']))
        self.assertFalse(self.session.phase_budget_available())

    def test_early_phase_one_submit_records_truthful_rejection_and_ends_without_restart(self):
        self.setup_phase(1)
        result = self.reply({'action': 'submit', 'expected_candidate_id': STARTING})['operations'][-1]['result']
        self.assertFalse(result['accepted'])
        self.assertFalse(self.session.submitted)
        self.assertTrue(self.session.early_phase_one_submit)
        self.assertFalse(self.session.phase_budget_available())
        self.assertFalse(self.session.transition_ready())
        self.assertEqual(self.session.phase_counters()['assisted_operations_new'], 4)
        with self.assertRaises(ValueError):
            self.setup_phase(2)

    def test_complete_reply_budget_guard_does_not_commit_a_partial_account(self):
        self.setup_phase(1)
        self.session.mark_delivered(self.session.view())
        self.session.begin_request()
        counters = self.session.phase_counters()
        # Isolate the public budget-consumer boundary. Real ledger accounting is
        # exercised above; this is not a purported reachable model trajectory.
        narrow = {**counters, 'phase_actor_operations_used': 15, 'phase_actor_operations_remaining': 1}
        before = copy.deepcopy(self.session.pairs)
        candidate = self.session.candidate
        reply = {'discussion': 'Whole reply must fit.', 'account': 'Must not be committed.',
                 'operation': {'action': 'read', 'path': 'README.md', 'start_line': 1, 'end_line': 0}}
        with patch.object(self.session, 'phase_counters', return_value=narrow):
            with self.assertRaises(ValueError):
                task.process_reply(self.session, reply, lambda view: 0, self.preceding)
        self.assertEqual(self.session.pairs, before)
        self.assertEqual(self.session.candidate, candidate)
        self.assertIsNone(self.session.working_account())
        self.assertEqual(self.session.requests_used, 1)

    def test_checkpoint_restores_phase_custody_and_rejects_rebound_capture(self):
        self.setup_phase(1)
        self.reply(self.report_patch(), account='Preserve this unresolved report across the declared restart.')
        self.check()
        self.setup_phase(2)
        state = task.snapshot(self.session)
        restored = task.restore(load_json_strict(canonical_json_bytes(state)), self.session.candidate,
                                replay_folder=self.folder, replay=True)
        self.assertEqual(canonical_json_bytes(task.snapshot(restored)), canonical_json_bytes(state))
        self.assertEqual(canonical_json_bytes(restored.view()), canonical_json_bytes(self.session.view()))
        self.assertEqual(restored.phase_counters(), self.session.phase_counters())
        self.assertEqual(restored.working_account(), self.session.working_account())
        self.assertEqual(restored.payload('RES-0003'), self.session.payload('RES-0003'))
        changed_capture = copy.deepcopy(state)
        changed_capture['imported_capture_state']['inventory'][0]['candidate_id'] = '0' * 64
        changed_history = copy.deepcopy(state)
        changed_history['pairs'][2]['result']['stdout'] += 'Invented diagnostic.'
        impossible_counter = copy.deepcopy(state)
        impossible_counter['saved_report_state']['phase_start_requests'] = state['requests_used'] + 1
        for label, changed in (('capture', changed_capture), ('legacy receipt', changed_history),
                               ('phase counter', impossible_counter)):
            with self.subTest(label=label), self.assertRaises(ValueError):
                task.restore(changed, self.session.candidate, replay_folder=self.folder, replay=True)


if __name__ == '__main__':
    unittest.main()
