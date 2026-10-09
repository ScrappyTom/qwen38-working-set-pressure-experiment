"""Qualify ordered transitions, observation applicability and actual restoration."""
from pathlib import Path
import importlib.util
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import recurrent_task as study
import recurrent_qualification
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes
from working_set_exp.observations import ObservationStore


class RecurrentTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='recurrent-entry-cpu-')
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.task = study.Task()
        self.session = self.task.initial_session()
        self.session.observations = ObservationStore(self.folder / 'observations')

    def step(self, session, action):
        session.mark_delivered(session.view())
        session.begin_request()
        reply = self.task.decode_reply(canonical_json_bytes(dict(discussion='CPU qualification.', operation=action)).decode())
        return self.task.process_reply(session, reply, lambda view: 0, [])['operations'][-1]['result']

    def test_fresh_original_entry_and_guard_failures(self):
        s = self.session
        self.assertEqual(s.phase, 'A')
        self.assertEqual((s.request_limit, s.call_limit), (64, 192))
        self.assertEqual(s.candidate.candidate_id, self.task.STARTING_ID)
        self.assertEqual(len(s.candidate.files), 160)
        self.assertFalse(s.pairs or s.ranges or s.saved or s.presented_coverage)
        self.assertIsNone(s.working_account())
        for action in (dict(action='fork_ready', expected_candidate_id=s.candidate.candidate_id),
                       dict(action='check', check_id='public', expected_candidate_id=s.candidate.candidate_id),
                       dict(action='submit', expected_candidate_id=s.candidate.candidate_id)):
            result = self.step(s, action)
            self.assertFalse(result['accepted'])
            self.assertEqual(s.phase, 'A')
            self.assertEqual(s.candidate.candidate_id, self.task.STARTING_ID)
        state = load_json_strict(canonical_json_bytes(self.task.snapshot(s)))
        state['request_limit'] = 65
        with self.assertRaisesRegex(ValueError, 'opportunity'):
            self.task.restore(state, s.candidate, self.folder, replay=True)

    def test_full_route_actual_serialized_states_and_release_authority(self):
        boundaries, seen = {}, []
        def record(row, current):
            raw = canonical_json_bytes(self.task.snapshot(current))
            candidate = load_json_strict(self.task.candidate_bytes(current.candidate))
            state = load_json_strict(raw)
            restored = self.task.restore(state, candidate, self.folder, replay=True)
            self.assertEqual(canonical_json_bytes(self.task.snapshot(restored)), raw)
            self.assertEqual(restored.view(), current.view())
            self.assertEqual(restored.checkers, current.checkers)
            seen.append(row['name'])
            if row['name'] in ('A-to-B', 'B-to-C', 'C-to-D'):
                boundaries[row['name']] = (state, candidate)
        result = recurrent_qualification.journey(self.task, self.session, lambda view: 0, [],
            variant='complete', record=record)
        self.assertTrue(result['submitted'])
        self.assertLessEqual(self.session.requests_used, 64)
        self.assertEqual(len(boundaries), 3)
        self.assertGreater(len(seen), 25)
        self.assertTrue(all(r['complete'] for p in self.session.order for r in self.session.coverage_status(p)))
        verifier_path = study.AREA / 'review/verify_run.py'
        spec = importlib.util.spec_from_file_location('recurrent_cpu_verifier', verifier_path)
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        for pair in self.session.pairs:
            if pair['response']['action'] == 'check' and pair['result'].get('executed'):
                self.assertEqual(sha256_bytes(verifier.checker_bytes_at(self.session, pair)),
                                 pair['result']['check_definition_sha256'])
        for boundary, (state, candidate) in boundaries.items():
            restored = self.task.restore(state, candidate, self.folder, replay=True)
            old_phase = boundary[0]
            scope = 'prefork' if old_phase == 'A' else 'public'
            observation = next(p['result']['observation'] for p in reversed(restored.pairs)
                               if p['response']['action'] == 'check' and p['result'].get('passed'))
            self.assertEqual(restored._contract(observation)['checker_sha256'], sha256_bytes(self.task.checker(old_phase)))
            self.assertFalse(restored.delivered_sources)
            self.assertFalse(restored.view()['verification']['submission']['eligible'])
            if scope == 'public':
                check = restored.scoped_check_state(scope)
                self.assertTrue(check['candidate_matches'])
                self.assertFalse(check['check_definition_matches'])
                self.assertFalse(check['applies_to_current'])
        state, candidate = boundaries['C-to-D']
        restored = self.task.restore(state, candidate, self.folder, replay=True)
        path = 'policies/current.py'
        action = dict(action='patch', path=path, old='zenith-', new='review-only-',
            expected_candidate_id=restored.candidate.candidate_id,
            expected_file_sha256=restored.candidate.file_sha256(path))
        self.assertFalse(self.step(restored, action)['accepted'])
        self.assertTrue(self.step(restored, dict(action='read', path=path, start_line=1, end_line=0))['accepted'])
        self.assertTrue(self.step(restored, action)['accepted'])
        self.assertIn(b'review-only-', restored.candidate.file_map[path])
        # Isolated guard probe; this branch is not the completed scripted artifact.
        self.assertNotEqual(restored.candidate.candidate_id, self.session.candidate.candidate_id)
        bad = load_json_strict(canonical_json_bytes(state))
        boundary = next(p for p in bad['pairs'] if p['response']['action'] == 'fork_ready' and p['result']['accepted'])
        boundary['result']['next_phase'] = 'D'
        with self.assertRaisesRegex(ValueError, 'boundary order'):
            self.task.restore(bad, candidate, self.folder, replay=True)
        bad = load_json_strict(canonical_json_bytes(state))
        bad['diffs'][next(iter(bad['diffs']))] += 'changed'
        with self.assertRaisesRegex(ValueError, 'diff history'):
            self.task.restore(bad, candidate, self.folder, replay=True)


if __name__ == '__main__':
    unittest.main()
