"""Task/capture/authority integration; native fit is qualified separately."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import write_task as study
import material
import reference_work
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes
from working_set_exp.observations import ObservationStore


class CodingTaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='write-task-tests-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.task = study.Task()
        self.session = self.task.initial_session(self.folder)

    def act(self, operation):
        self.session.mark_delivered(self.session.view())
        self.session.begin_request()
        reply = dict(discussion='CPU transition qualification, not a model response', operation=operation)
        # No claim of native token fit in this CPU test.
        study.process_reply(self.session, reply, lambda value: 1, [])
        return self.session.pairs[-1]['result']

    def test_saved_baseline_and_new_job_have_no_donor_selection(self):
        view = self.session.view()
        self.assertEqual(self.session.candidate.file_map[material.LIBRARY], material.baseline_files()[material.LIBRARY])
        self.assertEqual(self.session.candidate.file_map[material.NEW_TESTS], material.SKELETON.encode())
        self.assertFalse(view['working_set']['sources'])
        self.assertFalse(view['working_set']['saved_results'])
        self.assertIsNone(view['working_account'])
        self.assertEqual(view['current_job']['submission'], 'open')
        self.assertEqual(view['verification']['checks']['public']['status'], 'not_executed')
        self.assertNotIn('_validate_key_contents', canonical_json_bytes(view).decode())
        self.assertNotIn('WriteSafetyTests', canonical_json_bytes(view).decode())
        self.assertEqual((self.session.request_limit, self.session.call_limit), (40, 120))

    def test_failure_diagnostic_and_full_capture_are_available(self):
        result = self.act(dict(action='check', check_id='public',
            expected_candidate_id=self.session.candidate.candidate_id))
        self.assertTrue(result['accepted'])
        self.assertFalse(result['passed'])
        visible = canonical_json_bytes(self.session.view()).decode()
        self.assertIn('InvalidWriteError', visible)
        files = list((self.folder/'observations').glob('*/stdout.bin'))
        self.assertEqual(len(files), 1)
        self.assertGreater(files[0].stat().st_size, 8192)
        observation = json.loads(files[0].read_bytes())
        self.assertEqual(observation['upstream']['tests'], 362)
        self.assertTrue(observation['upstream']['successful'])
        self.assertTrue(any('InvalidWriteError' in row['trace'] for row in observation['contract']['details']))
        assessment = self.session.view()['verification']['checks']['public']['assessment']
        self.assertIn('Add executable public write()', canonical_json_bytes(assessment).decode())
        restored = self.task.restore(study.snapshot(self.session), self.session.candidate,
                                     replay_folder=self.folder, replay=True)
        self.assertEqual(canonical_json_bytes(study.snapshot(restored)),
                         canonical_json_bytes(study.snapshot(self.session)))

    def test_source_authority_requires_actual_delivery(self):
        old = '        for key, value in section_items:\n'
        action = dict(action='patch', path=material.LIBRARY, old=old, new=old+'            pass\n',
            expected_candidate_id=self.session.candidate.candidate_id,
            expected_file_sha256=self.session.candidate.file_sha256(material.LIBRARY))
        rejected = self.act(action)
        self.assertFalse(rejected['accepted'])
        lines = self.session.candidate.file_map[material.LIBRARY].decode().splitlines()
        line = lines.index(old.rstrip('\n'))+1
        self.act(dict(action='read', path=material.LIBRARY, start_line=line, end_line=line))
        accepted = self.act(action)
        self.assertTrue(accepted['accepted'])

    def test_current_pass_and_saved_test_preservation(self):
        files = reference_work.files()
        self.session.candidate = Candidate.create(files, max_file_bytes=study.FILE_LIMIT)
        self.session.versions[self.session.candidate.candidate_id] = self.session.candidate
        result = self.act(dict(action='check', check_id='public',
            expected_candidate_id=self.session.candidate.candidate_id))
        self.assertTrue(result['passed'])
        self.assertTrue(self.session.view()['verification']['submission']['eligible'])
        files['Lib/test/test_configparser.py'] += b'\n# altered preserved tests\n'
        self.session.candidate = Candidate.create(files, max_file_bytes=study.FILE_LIMIT)
        self.session.versions[self.session.candidate.candidate_id] = self.session.candidate
        self.assertFalse(self.session.view()['verification']['submission']['eligible'])
        result = self.act(dict(action='check', check_id='public',
            expected_candidate_id=self.session.candidate.candidate_id))
        self.assertFalse(result['passed'])
        self.assertIn('test_preserves_saved_tests', canonical_json_bytes(self.session.view()).decode())

    def test_serialized_restore_preserves_mixed_digit_edit_history(self):
        self.act(dict(action='read', path=material.NEW_TESTS, start_line=1, end_line=0))
        original = self.session.candidate.file_map[material.NEW_TESTS].decode()
        def append_marker(marker):
            old = self.session.candidate.file_map[material.NEW_TESTS].decode()
            result = self.act(dict(action='patch', path=material.NEW_TESTS,
                old=old, new=old+marker,
                expected_candidate_id=self.session.candidate.candidate_id,
                expected_file_sha256=self.session.candidate.file_sha256(material.NEW_TESTS)))
            self.assertTrue(result['accepted'])
        append_marker('\n# first saved edit\n')
        for _ in range(7):
            self.act(dict(action='read', path=material.NEW_TESTS, start_line=1, end_line=0))
        append_marker('# second saved edit\n')
        self.assertEqual(set(self.session.diffs), {2, 10})
        raw = canonical_json_bytes(study.snapshot(self.session))
        state = json.loads(raw)
        candidate = json.loads(study.candidate_bytes(self.session.candidate))
        restored = self.task.restore(state, candidate, self.folder, replay=True)
        self.assertEqual(canonical_json_bytes(study.snapshot(restored)), raw)
        self.assertEqual(canonical_json_bytes(restored.view()), canonical_json_bytes(self.session.view()))
        self.assertEqual(restored.candidate.file_map[material.NEW_TESTS].decode(),
                         original+'\n# first saved edit\n# second saved edit\n')


if __name__ == '__main__':
    unittest.main()
