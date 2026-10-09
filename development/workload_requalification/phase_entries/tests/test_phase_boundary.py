"""Actual original files/checkers through the missing phase transition."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import phase_task as study
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict
from working_set_exp.observations import ObservationStore


class PhaseBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='phase_boundary_test_')
        self.addCleanup(self.tmp.cleanup)
        self.task = study.Task()
        self.s = self.task.initial_session()
        self.s.observations = ObservationStore(Path(self.tmp.name) / 'observations')

    def call(self, action, deliver=True):
        if deliver:
            self.s.mark_delivered(self.s.view())
        return self.s.execute(action, lambda view: 1000)

    def read(self, path, first=1, last=0, deliver=True):
        return self.call(dict(action='read', path=path, start_line=first, end_line=last), deliver)

    def patch(self, path, old, new):
        return self.call(dict(action='patch', path=path, old=old, new=new,
            expected_candidate_id=self.s.candidate.candidate_id,
            expected_file_sha256=self.s.candidate.file_sha256(path)))

    def check(self, scope):
        return self.call(dict(action='check', check_id=scope,
                              expected_candidate_id=self.s.candidate.candidate_id))

    def ready(self):
        for path in self.s.phase_required['A']:
            self.assertTrue(self.read(path)['accepted'])
        self.assertTrue(self.read('workflow/progress.py')['accepted'])
        self.assertTrue(self.patch('workflow/progress.py', 'return 0', 'return 1')['accepted'])
        self.assertTrue(self.check('prefork')['passed'])

    def fork(self):
        return self.call(dict(action='fork_ready', expected_candidate_id=self.s.candidate.candidate_id))

    def test_acquired_but_not_delivered_is_not_coverage(self):
        for path in self.s.phase_required['A']:
            self.read(path, deliver=False)
        self.assertTrue(all(not r['complete'] for r in self.s.coverage_status()))
        before = canonical_json_bytes(self.s.ranges)
        reply = self.fork_without_delivery()
        self.assertFalse(reply['accepted'])
        self.assertEqual(reply['missing_paths'], list(self.s.phase_required['A']))
        self.assertEqual(canonical_json_bytes(self.s.ranges), before)
        self.assertEqual(self.s.phase, 'A')

    def fork_without_delivery(self):
        return self.call(dict(action='fork_ready', expected_candidate_id=self.s.candidate.candidate_id), False)

    def test_tail_is_not_full_file_and_disjoint_pages_union(self):
        path = self.s.phase_required['A'][0]
        self.read(path, 20)
        self.s.mark_delivered(self.s.view())
        self.assertFalse(self.s.coverage_status()[0]['complete'])
        self.call(dict(action='work_on', sources=[dict(path=path, start_line=1, end_line=19)], results=[]))
        self.s.mark_delivered(self.s.view())
        self.assertTrue(self.s.coverage_status()[0]['complete'])
        self.assertFalse(self.s.coverage_status()[1]['complete'])

    def test_coverage_survives_unrelated_edit_but_not_required_file_change(self):
        self.ready()
        self.assertTrue(all(r['complete'] for r in self.s.coverage_status()))
        path = self.s.phase_required['A'][0]
        raw = self.s.candidate.file_map[path].decode()
        # Releasing and reading a current region does not alter coverage history.
        self.read(path)
        self.assertTrue(self.patch(path, raw.splitlines()[0], raw.splitlines()[0] + '  # changed')['accepted'])
        self.assertFalse(self.s.coverage_status()[0]['complete'])
        self.assertTrue(self.s.coverage_status()[1]['complete'])
        self.assertFalse(self.s.scoped_check_state('prefork')['applies_to_current'])

    def test_failed_check_wrong_scope_and_premature_submit_do_not_transition(self):
        self.assertFalse(self.check('public')['accepted'])
        self.assertFalse(self.call(dict(action='submit', expected_candidate_id=self.s.candidate.candidate_id))['accepted'])
        for path in self.s.phase_required['A']:
            self.read(path)
        self.assertFalse(self.check('prefork')['passed'])
        self.assertFalse(self.fork()['accepted'])
        self.assertEqual(self.s.phase, 'A')
        self.assertEqual(self.s.candidate.candidate_id, study.STARTING_ID)

    def test_fork_preserves_work_history_account_and_clears_edit_authority(self):
        self.ready()
        self.call(dict(action='record_account', text='Observed progress repair; later policy value not inspected.'))
        old_candidate = self.s.candidate.candidate_id
        old_pairs = canonical_json_bytes(self.s.pairs)
        old_account = self.s.working_account()
        self.assertTrue(self.fork()['accepted'])
        self.assertEqual(self.s.phase, 'B')
        self.assertEqual(self.s.candidate.candidate_id, old_candidate)
        self.assertEqual(canonical_json_bytes(self.s.pairs[:-1]), old_pairs)
        self.assertEqual(self.s.working_account(), old_account)
        self.assertEqual((self.s.ranges, self.s.saved, self.s.delivered_sources), ([], {}, []))
        self.assertFalse(self.patch('workflow/progress.py', 'return 1', 'return 2')['accepted'])
        self.assertFalse(self.fork()['accepted'])
        self.assertFalse(self.check('prefork')['accepted'])
        self.assertIsNone(self.s.scoped_check_state('public'))
        self.assertFalse(self.s.view()['verification']['submission']['eligible'])
        self.read('workflow/progress.py')
        self.assertTrue(self.patch('workflow/progress.py', 'return 1', 'return 2')['accepted'])

    def test_stale_fork_guard_and_check_preserve_phase(self):
        self.ready()
        self.assertFalse(self.call(dict(action='fork_ready', expected_candidate_id=study.STARTING_ID))['accepted'])
        self.read('api/name.py')
        self.assertTrue(self.patch('api/name.py', 'return value.strip().casefold()', 'return value.strip().lower()')['accepted'])
        self.assertFalse(self.fork()['accepted'])
        self.assertEqual(self.s.phase, 'A')

    def test_restore_both_phases_and_complete_original_behavior(self):
        self.ready()
        for transition in (False, True):
            if transition:
                self.assertTrue(self.fork()['accepted'])
            state = load_json_strict(canonical_json_bytes(self.task.snapshot(self.s)))
            restored = self.task.restore(state, load_json_strict(self.task.candidate_bytes(self.s.candidate)),
                                         replay_folder=Path(self.tmp.name), replay=True)
            self.assertEqual(canonical_json_bytes(restored.view()), canonical_json_bytes(self.s.view()))
            self.assertEqual(restored.phase, self.s.phase)
            self.assertEqual(canonical_json_bytes(self.task.snapshot(restored)), canonical_json_bytes(state))
        self.call(dict(action='p0_page', path='policies', offset=0))
        self.read('policies/current.py')
        self.read('api/name.py')
        self.assertTrue(self.patch('api/name.py', 'return value.strip().casefold()',
                                   'return "lumen-" + value.strip().casefold()')['accepted'])
        for path in self.s.phase_required['B']:
            self.read(path)
        self.assertTrue(self.check('public')['passed'])
        self.assertTrue(all(r['complete'] for r in self.s.coverage_status()))
        self.assertTrue(self.call(dict(action='submit', expected_candidate_id=self.s.candidate.candidate_id))['accepted'])
        self.assertTrue(self.s.submitted)
        self.assertEqual(self.s.candidate.candidate_id, self.task.fixture['phase_candidate_ids']['B'])

    def test_restore_rejects_changed_opportunity_and_impossible_coverage(self):
        self.read(self.s.phase_required['A'][0])
        self.s.mark_delivered(self.s.view())
        saved = load_json_strict(canonical_json_bytes(self.task.snapshot(self.s)))
        for field in ('call_limit', 'presented_coverage'):
            altered = copy.deepcopy(saved)
            if field == 'call_limit':
                altered[field] += 1
            else:
                altered[field][0]['ranges'] = [[1, 2000000]]
            with self.assertRaises(ValueError):
                self.task.restore(altered, self.s.candidate)

    def test_clone_rejection_cannot_leak_coverage_and_rule_is_declared(self):
        self.read(self.s.phase_required['A'][0])
        other = self.s.clone()
        other.mark_delivered(other.view())
        self.assertEqual(self.s.presented_coverage, [])
        self.assertTrue(other.presented_coverage)
        operation = dict(action='fork_ready', expected_candidate_id=study.STARTING_ID)
        reply = dict(discussion='Ready for the declared boundary.', operation=operation)
        self.assertEqual(study.decode_reply(canonical_json_bytes(reply).decode()), reply)
        self.assertEqual(self.s.reply_schema(), study.reply_schema())
        self.assertIn('fork_ready', study.response_constraints()['grammar'])
        reference = self.task.operating_reference()
        self.assertIn('fork_ready:', reference)
        self.assertIn('"enum":["prefork","public"]', reference)

    def test_scripted_information_path_and_check_capture_restore(self):
        import qualification_route
        recorded = []
        def record(row, current):
            restored = self.task.restore(self.task.snapshot(current), current.candidate,
                replay_folder=Path(self.tmp.name), replay=True)
            self.assertEqual(restored.view(), current.view())
            self.assertTrue(row['input_support'])
            recorded.append(row)
        result = qualification_route.journey(self.task, self.s, lambda view: 1000, [],
            variant='complete', record=record)
        self.assertTrue(result['submitted'])
        self.assertEqual(self.s.phase, 'B')
        self.assertTrue(any(r['name'] == 'observed-prefork-failure' for r in recorded))
        self.assertTrue(any(r['name'] == 'released-source-not-editable' for r in recorded))

    def test_prefork_report_names_actual_scope_without_rewriting_observation(self):
        failed = self.check('prefork')
        handle = failed['observation']
        raw_before = (self.s.observations.directory(handle) / 'stderr.bin').read_bytes()
        report = self.s.view()['latest_feedback']['result']['report']
        self.assertFalse(report['passed'])
        self.assertEqual(report['scope'], 'prefork')
        self.assertEqual(report['failed_criteria'], ['prefork_execution'])
        self.assertIn('Phase A prefork checker', report['criteria'][0]['meaning'])
        self.assertEqual(report['criteria'][0]['stderr']['text'].encode(), raw_before)
        inspected = self.call(dict(action='inspect_check', observation=handle, offset=0))
        self.assertEqual(inspected['entries'][0]['criterion'], 'prefork_execution')
        self.assertEqual((self.s.observations.directory(handle) / 'stderr.bin').read_bytes(), raw_before)
        self.ready()
        self.fork()
        public = self.check('public')
        self.assertFalse(public['passed'])
        self.assertEqual(self.s.view()['latest_feedback']['result']['report']['failed_criteria'], ['public_execution'])


if __name__ == '__main__':
    unittest.main()
