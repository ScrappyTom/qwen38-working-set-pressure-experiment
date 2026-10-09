"""CPU preservation, applicability and real public-reply transition checks."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import probe_task as study
import probe_qualification
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict
from working_set_exp.observations import ObservationStore


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase-probe-cpu-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.task = study.Task()
        self.session = self.task.initial_session()
        self.session.observations = ObservationStore(self.folder / 'observations')
        self.feedback = []

    def step(self, action, *, account=None, session=None, measure=None):
        session = session or self.session
        session.mark_delivered(session.view())
        session.begin_request()
        reply = dict(discussion='CPU contract qualification.', operation=action)
        if account is not None:
            reply['account'] = account
        reply = self.task.decode_reply(canonical_json_bytes(reply).decode())
        result = self.task.process_reply(session, reply, measure or (lambda view: 0), self.feedback)
        return result['operations'][-1]['result']

    def read(self, path, *, session=None):
        return self.step(dict(action='read', path=path, start_line=1, end_line=0), session=session)

    def progress(self, *, session=None):
        session = session or self.session
        self.read('workflow/progress.py', session=session)
        return self.step(dict(action='patch', path='workflow/progress.py', old='return 0', new='return 1',
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256('workflow/progress.py')), session=session)

    def fork(self):
        return self.step(dict(action='fork_ready', expected_candidate_id=self.session.candidate.candidate_id))

    def ready(self):
        for path in self.session.phase_required['A']:
            self.read(path)
        self.progress()
        result = self.step(dict(action='check', check_id='prefork', expected_candidate_id=self.session.candidate.candidate_id))
        self.assertTrue(result['passed'])

    def test_fresh_entry_no_imported_answer(self):
        view = self.session.view()
        self.assertEqual(view['observation_directory']['entries'], [])
        self.assertNotIn('D4::', canonical_json_bytes(view).decode())
        self.assertEqual(self.session.pairs, [])
        self.assertEqual(self.session.candidate.candidate_id, study.STARTING_ID)

    def test_probe_identity_survives_edit_and_current_guard(self):
        produced = self.step(dict(action='probe', probe_id='integrity'))
        old, raw = self.session.observation('OBS-0001')
        self.assertEqual(load_json_strict(raw), produced)
        self.ready()
        self.assertIsNone(self.session.current_probe())
        rejected = self.fork()
        self.assertFalse(rejected['accepted'])
        self.assertIn('current candidate', rejected['error'])
        self.step(dict(action='probe', probe_id='integrity'))
        self.assertEqual(self.session.current_probe()['observed_candidate_id'], self.session.candidate.candidate_id)
        self.assertTrue(self.fork()['accepted'])
        self.assertEqual(self.session.observation(old['handle'])[1], raw)
        self.assertFalse(self.session.observation_page()['entries'][-1]['candidate_matches_current'])

    def test_failed_check_is_observation_rejected_request_is_not(self):
        result = self.step(dict(action='check', check_id='prefork', expected_candidate_id=self.session.candidate.candidate_id))
        self.assertTrue(result['accepted'])
        self.assertFalse(result['passed'])
        self.assertEqual(self.session.observation_rows()[0]['result_handle'], 'RES-0001')
        self.assertFalse(self.fork()['accepted'])
        self.assertEqual(len(self.session.observation_rows()), 1)

    def test_directory_pages_and_exact_recovery(self):
        for _ in range(9):
            self.step(dict(action='probe', probe_id='integrity'))
        page = self.step(dict(action='observation_history', before=0))
        self.assertEqual([r['sequence'] for r in page['entries']], [9, 8, 7, 6, 5, 4])
        older = self.step(dict(action='observation_history', before=page['next_before']))
        self.assertEqual([r['sequence'] for r in older['entries']], [3, 2, 1])
        self.assertIsNone(older['next_before'])
        before = self.session.candidate
        row, raw = self.session.observation('OBS-0002')
        receipt = self.step(dict(action='reopen_observation', handle=row['handle']))
        recovered, = receipt['saved_results']
        self.assertEqual(recovered['exact_utf8'].encode(), raw)
        self.assertEqual(self.session.candidate, before)
        self.assertIsNone(self.session.check_state())
        self.assertEqual(self.session.payload(row['result_handle']), raw)
        self.assertIn(row['result_handle'], self.session.saved)

    def test_fork_releases_designation_not_history(self):
        self.ready()
        self.step(dict(action='probe', probe_id='integrity'), account='Saved progress; current integrity is archived.')
        row = self.session.current_probe()
        raw = self.session.observation(row['handle'])[1]
        self.step(dict(action='reopen_observation', handle=row['handle']))
        account = self.session.working_account()
        self.assertTrue(self.fork()['accepted'])
        self.assertFalse(self.session.saved)
        self.assertFalse(self.session.ranges)
        self.assertFalse(self.session.delivered_sources)
        self.assertEqual(self.session.working_account(), account)
        self.assertEqual(self.session.observation(row['handle'])[1], raw)
        bad = self.step(dict(action='probe', probe_id='integrity'))
        self.assertFalse(bad['accepted'])
        reopened = self.step(dict(action='reopen_observation', handle=row['handle']))
        self.assertEqual(reopened['saved_results'][0]['exact_utf8'].encode(), raw)

    def test_branch_local_aliases_resolve_own_archive(self):
        self.step(dict(action='probe', probe_id='integrity'))
        branch = self.session.clone()
        self.progress(session=branch)
        self.step(dict(action='probe', probe_id='integrity'), session=branch)
        self.step(dict(action='probe', probe_id='integrity'))
        self.assertEqual(self.session.observation('OBS-0001'), branch.observation('OBS-0001'))
        self.assertNotEqual(self.session.observation('OBS-0002')[1], branch.observation('OBS-0002')[1])
        for session in (self.session, branch):
            raw = canonical_json_bytes(self.task.snapshot(session))
            restored = self.task.restore(load_json_strict(raw), session.candidate, self.folder, replay=True)
            self.assertEqual(self.task.snapshot(restored), load_json_strict(raw))
            self.assertEqual(restored.observation_rows(), session.observation_rows())

    def test_full_public_reply_journey_serialized_restore(self):
        seen = []
        def record(row, current):
            raw = canonical_json_bytes(self.task.snapshot(current))
            decoded = load_json_strict(raw)
            restored = self.task.restore(decoded, current.candidate, self.folder, replay=True)
            self.assertEqual(canonical_json_bytes(self.task.snapshot(restored)), raw)
            self.assertEqual(restored.view(), current.view())
            seen.append(row['name'])
        result = probe_qualification.journey(self.task, self.session, lambda view: 0, self.feedback,
            variant='complete', record=record)
        self.assertTrue(result['submitted'])
        self.assertIn('stale-probe-boundary-rejected', seen)
        self.assertIn('recover-current-observation', seen)
        self.assertTrue(any(int(k) < 10 for k in self.task.snapshot(self.session)['diffs']))
        self.assertTrue(any(int(k) >= 10 for k in self.task.snapshot(self.session)['diffs']))

    def test_restored_diff_mutation_rejected(self):
        self.progress()
        state = load_json_strict(canonical_json_bytes(self.task.snapshot(self.session)))
        state['diffs'][next(iter(state['diffs']))] += 'tampered'
        with self.assertRaisesRegex(ValueError, 'diff history differs'):
            self.task.restore(state, self.session.candidate, self.folder, replay=True)

    def test_invalid_reopen_does_not_create_observation(self):
        result = self.step(dict(action='reopen_observation', handle='OBS-0999'))
        self.assertFalse(result['accepted'])
        self.assertEqual(self.session.observation_rows(), [])
        self.assertEqual(self.session.saved, {})

    def test_reopen_rejection_preserves_archive_and_selection(self):
        self.step(dict(action='probe', probe_id='integrity'))
        row, raw = self.session.observation('OBS-0001')
        self.read('codec/label.py')
        def measure(view):
            latest = view.get('latest_feedback') or {}
            result = latest.get('result') or {}
            return 24000 if result.get('kind') == 'task_observation' and view['presentation']['mode'] == 'ordinary' else 1000
        receipt = self.step(dict(action='reopen_observation', handle=row['handle']), measure=measure)
        self.assertFalse(receipt['accepted'])
        self.assertEqual(self.session.observation('OBS-0001')[1], raw)
        self.assertNotIn(row['result_handle'], self.session.saved)
        self.assertTrue(any(r['path'] == 'codec/label.py' for r in self.session.ranges))


if __name__ == '__main__':
    unittest.main()
