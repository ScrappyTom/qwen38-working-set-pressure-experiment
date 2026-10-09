"""Original closure work, historical authority and check applicability."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import closure_task as module
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
        result = self.act(task, session, feedback, dict(action='submit', candidate_id=session.candidate.candidate_id))
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
                result = self.act(task, session, feedback, dict(action='check', check_id='public', candidate_id=original.candidate_id))
                self.assertTrue(result['accepted'] and result['passed'])
                status = session.view()['verification']['checks']['public']
                self.assertTrue(status['candidate_matches'] and status['check_definition_matches'] and status['applies_to_current'])
                self.assertTrue(self.act(task, session, feedback, dict(action='submit', candidate_id=original.candidate_id))['accepted'])
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
                failed = self.act(task, session, feedback, dict(action='check', check_id='public', candidate_id=saved.candidate_id))
                self.assertTrue(failed['accepted'])
                self.assertFalse(failed['passed'])
                self.assertIn('AssertionError', canonical_json_bytes(failed).decode())
                self.assertFalse(self.act(task, session, feedback, dict(action='submit', candidate_id=saved.candidate_id))['accepted'])
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


if __name__ == '__main__':
    unittest.main()
