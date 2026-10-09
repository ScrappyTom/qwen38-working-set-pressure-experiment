"""Source authority, current-check applicability and exact restoration."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import unnamed_task as task
import unnamed_material as material
import unnamed_reference as reference
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='unnamed-host-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.task = task.Task()
        self.session = self.task.initial_session(self.folder)

    def act(self, action):
        self.session.mark_delivered(self.session.view())
        self.session.begin_request()
        task.process_reply(self.session, dict(discussion='CPU qualification only', operation=action), lambda _: 1, [])
        return self.session.pairs[-1]['result']

    def test_exact_saved_work_empty_entry_and_no_reference_solution(self):
        for name, raw in material.baseline_files().items():
            self.assertEqual(self.session.candidate.file_map[name], raw)
        view = self.session.view()
        self.assertFalse(view['working_set']['sources'])
        self.assertIsNone(view['working_account'])
        self.assertEqual(self.session.pairs, [])
        self.assertEqual(view['verification']['checks']['public']['status'], 'not_executed')
        self.assertNotIn('class _UnnamedSection', canonical_json_bytes(view).decode())
        self.assertEqual((self.session.request_limit, self.session.call_limit), (40, 120))

    def test_real_baseline_failure_complete_capture_and_restore(self):
        result = self.act(dict(action='check', check_id='public', expected_candidate_id=self.session.candidate.candidate_id))
        self.assertTrue(result['accepted'])
        self.assertFalse(result['passed'])
        observation = next((self.folder/'observations').glob('*/stdout.bin'))
        self.assertGreater(observation.stat().st_size, 8192)
        full = json.loads(observation.read_bytes())
        self.assertEqual(full['upstream']['tests'], 373)
        self.assertTrue(full['upstream']['successful'])
        self.assertIn('allow_unnamed_section', canonical_json_bytes(self.session.view()).decode())
        state = json.loads(canonical_json_bytes(task.snapshot(self.session)))
        restored = self.task.restore(state, self.session.candidate, self.folder, replay=True)
        self.assertEqual(restored.view(), self.session.view())

    def test_source_delivery_stale_guard_and_mixed_digit_edits(self):
        path = material.NEW_TESTS
        before = self.session.candidate
        op = dict(action='patch', path=path, old=material.SKELETON, new=material.SKELETON+'# one\n',
            expected_candidate_id=before.candidate_id, expected_file_sha256=before.file_sha256(path))
        self.assertFalse(self.act(op)['accepted'])
        self.act(dict(action='read', path=path, start_line=1, end_line=0))
        self.assertTrue(self.act(op)['accepted'])
        self.assertFalse(self.act(op)['accepted'])
        for _ in range(6):
            self.act(dict(action='read', path=path, start_line=1, end_line=0))
        self.assertTrue(self.act(dict(action='patch', path=path, old='# one\n', new='# two\n',
            expected_candidate_id=self.session.candidate.candidate_id,
            expected_file_sha256=self.session.candidate.file_sha256(path)))['accepted'])
        state = json.loads(canonical_json_bytes(task.snapshot(self.session)))
        restored = self.task.restore(state, json.loads(task.candidate_bytes(self.session.candidate)), self.folder, replay=True)
        self.assertEqual(canonical_json_bytes(task.snapshot(restored)), canonical_json_bytes(state))
        self.assertEqual(restored.view(), self.session.view())

    def test_current_pass_preservation_failure_and_submission_gate(self):
        self.assertFalse(self.act(dict(action='submit', expected_candidate_id=self.session.candidate.candidate_id))['accepted'])
        files = reference.files()
        self.session.candidate = Candidate.create(files, max_file_bytes=task.FILE_LIMIT)
        self.session.versions[self.session.candidate.candidate_id] = self.session.candidate
        result = self.act(dict(action='check', check_id='public', expected_candidate_id=self.session.candidate.candidate_id))
        self.assertTrue(result['passed'])
        self.assertTrue(self.session.view()['verification']['submission']['eligible'])
        files['Lib/test/test_configparser_write_safety.py'] += b'\n# changed old test\n'
        self.session.candidate = Candidate.create(files, max_file_bytes=task.FILE_LIMIT)
        self.session.versions[self.session.candidate.candidate_id] = self.session.candidate
        self.assertFalse(self.session.view()['verification']['submission']['eligible'])
        result = self.act(dict(action='check', check_id='public', expected_candidate_id=self.session.candidate.candidate_id))
        self.assertFalse(result['passed'])
        self.assertIn('test_preserves_previous_tests', canonical_json_bytes(self.session.view()).decode())


if __name__ == '__main__':
    unittest.main()
