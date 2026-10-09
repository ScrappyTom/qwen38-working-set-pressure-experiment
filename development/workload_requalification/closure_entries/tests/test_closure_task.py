"""Original closure work, historical authority and check applicability."""
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import closure_task as module
import qualification_route
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='original-closure-cpu-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def new(self, case):
        task = module.Task(case, replay_folder=self.folder / case)
        session = task.initial_session()
        # New CPU checks execute into the temporary observation store, not replay.
        session.observations = module.ObservationStore(self.folder / case / 'observations')
        return task, session, []

    def act(self, task, session, feedback, operation):
        session.mark_delivered(session.view())
        session.begin_request()
        result = task.process_reply(session, dict(discussion='CPU engineering qualification.', operation=operation), lambda view: 0, feedback)
        return result['operations'][-1]['result']

    def test_exact_setup_not_counted_as_current_work_or_edit_authority(self):
        for case in module.CASES:
            with self.subTest(case=case):
                task, session, _ = self.new(case)
                self.assertEqual(session.pairs, task.inherited_pairs())
                self.assertEqual((session.starting_archive_length, session.calls_used, session.requests_used), (5, 0, 0))
                self.assertEqual((session.request_limit, session.call_limit), (8, 24))
                view = session.view()
                self.assertEqual(view['task'], task.exact('TASK.txt').decode())
                self.assertEqual(view['active_user_authored_step'], task.exact('ACTIVE_STEP.txt').decode())
                self.assertEqual(len(view['recent_activity']), 5)
                self.assertTrue(all(r['episode'] == 'prior_work' for r in view['recent_activity']))
                for row in view['recent_activity'][-2:]:
                    self.assertEqual(row['returned_range'], dict(start_line=1, end_line=182))
                    self.assertTrue(row['historical_acquisition']['whole_file_returned'])
                    self.assertTrue(row['historical_acquisition']['does_not_establish_current_visibility'])
                self.assertFalse(view['verification']['submission']['eligible'])
                self.assertFalse(session.ranges or session.saved or session.delivered_sources)
                self.assertIsNone(session.working_account())

    def test_all_original_captures_recover_exactly_without_check_authority(self):
        for case in module.CASES:
            with self.subTest(case=case):
                task, session, feedback = self.new(case)
                rows, _, bodies = task.imports()
                for row in rows:
                    result = self.act(task, session, feedback, dict(action='reopen_observation', handle=row['handle']))
                    self.assertTrue(result['accepted'])
                    self.assertEqual(result['content_utf8'].encode(), bodies[row['handle']])
                    self.assertEqual(result['observed_candidate_id'], row['candidate_id'])
                    self.assertTrue(result['retrieval_only'])
                self.assertFalse(session.view()['verification']['submission']['eligible'])
                snapshot = task.snapshot(session)
                restored = task.restore(load_json_strict(canonical_json_bytes(snapshot)), session.candidate,
                    self.folder / case, replay=True)
                self.assertEqual(restored.view(), session.view())
                self.assertEqual(restored.pairs[:5], task.inherited_pairs())
                for i in range(1, 6):
                    self.assertEqual(restored.payload(f'RES-{i:04d}'), canonical_json_bytes(task.inherited_pairs()[i-1]['result']))
                    self.assertEqual(restored.payload(f'EVT-{i:04d}'), canonical_json_bytes(task.inherited_pairs()[i-1]['response']))

    def test_historical_check_does_not_authorize_submission(self):
        task, session, feedback = self.new('E14-STALE-SABLE')
        old = session.view()['verification']['checks']['public']
        self.assertTrue(old['passed'])
        self.assertFalse(old['candidate_matches'] or old['applies_to_current'])
        result = self.act(task, session, feedback, dict(action='submit', expected_candidate_id=session.candidate.candidate_id))
        self.assertFalse(result['accepted'])
        self.assertFalse(session.submitted)

    def test_historical_source_read_is_not_current_edit_authority(self):
        for case, path in [('E14-CLOSURE-MINT', 'codec/label.py'), ('E14-STALE-SABLE', 'api/name.py')]:
            with self.subTest(case=case):
                task, session, feedback = self.new(case)
                current = session.candidate
                old = current.file_map[path].decode()
                operation = dict(action='patch', path=path, old=old, new=old+'# qualified exact source\n',
                    expected_candidate_id=current.candidate_id, expected_file_sha256=current.file_sha256(path))
                self.assertFalse(self.act(task, session, feedback, operation)['accepted'])
                self.assertEqual(session.candidate, current)
                self.assertTrue(self.act(task, session, feedback, dict(action='read', path=path, start_line=1, end_line=0))['accepted'])
                self.assertTrue(self.act(task, session, feedback, operation)['accepted'])
                restored = task.restore(task.snapshot(session), session.candidate, self.folder / case, replay=True)
                self.assertEqual(restored.pairs[:5], task.inherited_pairs())

    def test_current_pass_consumed_before_submit_preserves_all_work(self):
        for case in module.CASES:
            with self.subTest(case=case):
                task, session, feedback = self.new(case)
                original = session.candidate
                result = self.act(task, session, feedback, dict(action='check', check_id='public', expected_candidate_id=original.candidate_id))
                self.assertTrue(result['accepted'] and result['passed'])
                status = session.view()['verification']['checks']['public']
                self.assertTrue(status['candidate_matches'] and status['check_definition_matches'] and status['applies_to_current'])
                self.assertTrue(self.act(task, session, feedback, dict(action='submit', expected_candidate_id=original.candidate_id))['accepted'])
                self.assertTrue(session.submitted)
                self.assertEqual(session.candidate, original)
                self.assertEqual(session.pairs[:5], task.inherited_pairs())

    def test_real_check_failure_keeps_saved_work_and_prevents_submission(self):
        for case, path, text in [('E14-CLOSURE-MINT', 'codec/label.py', 'def codec_label(value):\n    return value\n'),
                                 ('E14-STALE-SABLE', 'invariants/stable.py', 'def invariant_ok():\n    return False\n')]:
            with self.subTest(case=case):
                task, session, feedback = self.new(case)
                original = session.candidate
                self.act(task, session, feedback, dict(action='read', path=path, start_line=1, end_line=0))
                self.assertTrue(self.act(task, session, feedback, dict(action='patch', path=path,
                    old=original.file_map[path].decode(), new=text, expected_candidate_id=original.candidate_id,
                    expected_file_sha256=original.file_sha256(path)))['accepted'])
                saved = session.candidate
                failed = self.act(task, session, feedback, dict(action='check', check_id='public', expected_candidate_id=saved.candidate_id))
                self.assertTrue(failed['accepted'])
                self.assertFalse(failed['passed'])
                self.assertIn('AssertionError', canonical_json_bytes(failed).decode())
                self.assertFalse(self.act(task, session, feedback, dict(action='submit', expected_candidate_id=saved.candidate_id))['accepted'])
                self.assertEqual(session.candidate, saved)

    def test_branch_restore_and_prefix_tampering_rejected(self):
        mint, session, _ = self.new('E14-CLOSURE-MINT')
        sable, _, _ = self.new('E14-STALE-SABLE')
        state = mint.snapshot(session)
        with self.assertRaises(ValueError):
            sable.restore(state, session.candidate)
        modified = copy.deepcopy(state)
        modified['pairs'][0]['result']['accepted'] = False
        with self.assertRaises(ValueError):
            mint.restore(modified, session.candidate)
        modified = copy.deepcopy(state)
        modified['imported_capture_state']['inventory'][0]['candidate_id'] = '0'*64
        with self.assertRaises(ValueError):
            mint.restore(modified, session.candidate)

    def test_legacy_extent_projection_does_not_promote_a_tail_to_whole_file(self):
        task, session, _ = self.new('E14-CLOSURE-MINT')
        # Summary counterexample only: never admitted as an original checkpoint.
        session.pairs[3]['result']['returned_start_line'] = 20
        row = session.summary(4)
        self.assertTrue(row['historical_acquisition']['reached_file_end'])
        self.assertFalse(row['historical_acquisition']['whole_file_returned'])
        self.assertFalse(session.delivered_sources)

    def test_scripted_closure_and_negative_paths_restore_exactly(self):
        for case in module.CASES:
            for variant in ('closure', 'historical', 'failed-check'):
                with self.subTest(case=case, variant=variant):
                    task, session, feedback = self.new(case)
                    def recorded(row, current):
                        restored = task.restore(task.snapshot(current), current.candidate, self.folder / case, replay=True)
                        self.assertEqual(restored.view(), current.view())
                        self.assertTrue(row['input_support'])
                    result = qualification_route.journey(task, session, lambda view: 0, feedback,
                        variant=variant, record=recorded)
                    self.assertEqual(result['submitted'], variant != 'historical')

    def test_imported_custody_is_compared_to_original_bytes_not_only_its_inventory(self):
        path = module.AREA / 'review/verify_run.py'
        spec = importlib.util.spec_from_file_location('closure_custody_verifier', path)
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        task, session, _ = self.new('E14-CLOSURE-MINT')
        records = []
        class Log:
            path = self.folder / 'records.jsonl'
            def append(self, kind, payload, artifacts):
                records.append(dict(record_type=kind, payload=payload, artifacts=artifacts))
        task.attach_observations(session, self.folder, Log())
        self.assertEqual(verifier._imported_custody(task, self.folder, records, ['']), 3)
        body = self.folder / 'imported-captures/OBS-0001.json'
        body.write_bytes(task.imports()[2]['OBS-0002'])
        with self.assertRaises(AssertionError):
            verifier._imported_custody(task, self.folder, records, [''])


if __name__ == '__main__':
    unittest.main()
