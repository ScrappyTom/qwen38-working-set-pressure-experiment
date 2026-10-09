"""Only the corrected checker and runtime ownership may change on restore."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import continuation_task as study
import corrected_checker
import material
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='saved-write-continuation-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.task = study.Task()
        self.session = self.task.initial_session(self.folder)

    def act(self, operation):
        self.session.mark_delivered(self.session.view())
        self.session.begin_request()
        study.process_reply(self.session, dict(discussion='CPU qualification only',
            operation=operation), lambda view: 1, [])
        return self.session.pairs[-1]['result']

    def test_exact_saved_state_and_remaining_opportunity(self):
        self.assertEqual(canonical_json_bytes(study.snapshot(self.session)),
                         (study.OLD/'final-state.json').read_bytes())
        self.assertEqual(study.candidate_bytes(self.session.candidate),
                         (study.OLD/'final-candidate.json').read_bytes())
        self.assertEqual((self.session.requests_used, self.session.calls_used), (9, 12))
        self.assertEqual((self.session.request_limit, self.session.call_limit), (40, 120))
        self.assertEqual(self.session.observations.root, self.folder/'observations')
        self.assertNotEqual(self.session.checkers['public'], study.previous.qualify_cpu.checker())
        self.assertEqual(self.session.check_contracts['public']['checker_sha256'],
                         sha256_bytes(corrected_checker.checker()))
        self.assertEqual((AREA/'SYSTEM.txt').read_bytes(), (study.previous.AREA/'SYSTEM.txt').read_bytes())

    def test_serialized_restore_preserves_inherited_identity(self):
        state = json.loads(canonical_json_bytes(study.snapshot(self.session)))
        candidate = json.loads(study.candidate_bytes(self.session.candidate))
        restored = self.task.restore(state, candidate, self.folder, replay=True)
        self.assertEqual(canonical_json_bytes(restored.view()), canonical_json_bytes(self.session.view()))
        self.assertEqual(restored.pairs[:12], self.session.pairs)
        result = self.act(dict(action='reopen_event', handle='EVT-0012', offset=0))
        self.assertTrue(result['accepted'])
        self.assertIn('InvalidWriteError', canonical_json_bytes(result).decode())
        self.assertEqual(self.session.candidate.candidate_id, study.STARTING_ID)
        self.assertEqual(self.session.pairs[:12], state['pairs'])

    def test_selected_source_authority_and_release(self):
        old = 'class Interpolation:'
        action = dict(action='patch', path=material.LIBRARY, old=old,
            new='# CPU authority fixture\n'+old,
            expected_candidate_id=self.session.candidate.candidate_id,
            expected_file_sha256=self.session.candidate.file_sha256(material.LIBRARY))
        # Restored exact current source is delivered, giving ordinary edit authority.
        self.assertTrue(self.act(action)['accepted'])
        self.session = self.task.initial_session(self.folder/'released')
        self.assertTrue(self.act(dict(action='work_on', sources=[], results=[]))['accepted'])
        self.assertFalse(self.act(action)['accepted'])
        line = self.session.candidate.file_map[material.LIBRARY].decode().splitlines().index(old)+1
        self.assertTrue(self.act(dict(action='read', path=material.LIBRARY,
            start_line=line, end_line=line))['accepted'])
        self.assertTrue(self.act(action)['accepted'])

    def test_failed_current_check_preserves_saved_work_and_full_observation(self):
        result = self.act(dict(action='check', check_id='public',
            expected_candidate_id=self.session.candidate.candidate_id))
        self.assertTrue(result['accepted'])
        self.assertFalse(result['passed'])
        self.assertEqual(self.session.candidate.candidate_id, study.STARTING_ID)
        self.assertFalse(self.session.verification_view()['submission']['eligible'])
        streams = list((self.folder/'observations').glob('*/stdout.bin'))
        self.assertEqual(len(streams), 1)
        self.assertIn('InvalidWriteError', streams[0].read_text())
        state = json.loads(canonical_json_bytes(study.snapshot(self.session)))
        restored = self.task.restore(state, self.session.candidate, self.folder, replay=True)
        self.assertEqual(canonical_json_bytes(restored.view()), canonical_json_bytes(self.session.view()))


if __name__ == '__main__':
    unittest.main()
