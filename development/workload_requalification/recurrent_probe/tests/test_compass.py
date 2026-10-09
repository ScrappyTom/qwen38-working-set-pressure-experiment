"""Real original checks, source authority and exact recurrent observation recovery."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import compass_task as study
import compass_qualification
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict
from working_set_exp.observations import ObservationStore


class CompassTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='compass-cpu-')
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.task = study.Task()
        self.session = self.task.initial_session()
        self.session.observations = ObservationStore(self.folder / 'observations')

    def step(self, action, *, session=None, measure=None):
        s = session or self.session
        s.mark_delivered(s.view()); s.begin_request()
        reply = self.task.decode_reply(canonical_json_bytes(dict(discussion='CPU qualification.', operation=action)).decode())
        return self.task.process_reply(s, reply, measure or (lambda view: 0), [])['operations'][-1]['result']

    def test_exact_fresh_entry_and_forms(self):
        s = self.session
        self.assertEqual(len(s.candidate.files),160)
        self.assertEqual((s.request_limit,s.call_limit),(64,192))
        self.assertFalse(s.pairs or s.ranges or s.saved or s.presented_coverage)
        self.assertIsNone(s.working_account())
        text = canonical_json_bytes(s.view()).decode()
        for marker in ('A3::','B6::','C9::'):
            self.assertNotIn(marker,text)
        self.assertEqual(s.view()['schema_version'],'decision-facts-v1')
        with self.assertRaises(ValueError):
            self.task.decode_reply('{"discussion":"wrong id","operation":{"action":"probe","probe_id":"integrity"}}')
        self.assertFalse(self.step(dict(action='fork_ready',expected_candidate_id=s.candidate.candidate_id))['accepted'])
        self.assertFalse(s.observation_rows())

    def test_inventory_paging_recovery_and_branch_local_identity(self):
        s = self.session
        for _ in range(9):
            self.assertTrue(self.step(dict(action='probe',probe_id='compatibility'))['executed'])
        page = self.step(dict(action='observation_history',before=0))
        self.assertEqual([r['sequence'] for r in page['entries']],[9,8,7,6,5,4])
        older = self.step(dict(action='observation_history',before=page['next_before']))
        self.assertEqual([r['sequence'] for r in older['entries']],[3,2,1])
        row, raw = s.observation('OBS-0002')
        for _ in range(2):
            result = self.step(dict(action='reopen_observation',handle=row['handle']))
            self.assertEqual(result['saved_results'][0]['exact_utf8'].encode(),raw)
            self.assertTrue(result['retrieval_only'])
        self.assertEqual(len(s.observation_rows()),9)
        branch = s.clone()
        self.step(dict(action='read',path='workflow/progress.py',start_line=1,end_line=0),session=branch)
        self.step(dict(action='patch',path='workflow/progress.py',old='return 0',new='return 1',
            expected_candidate_id=branch.candidate.candidate_id,
            expected_file_sha256=branch.candidate.file_sha256('workflow/progress.py')),session=branch)
        self.step(dict(action='probe',probe_id='compatibility'),session=branch)
        self.step(dict(action='probe',probe_id='compatibility'))
        self.assertEqual(s.observation('OBS-0001'),branch.observation('OBS-0001'))
        self.assertNotEqual(s.observation('OBS-0010')[1],branch.observation('OBS-0010')[1])
        for value in (s,branch):
            state = load_json_strict(canonical_json_bytes(self.task.snapshot(value)))
            restored = self.task.restore(state,value.candidate,self.folder,replay=True)
            self.assertEqual(restored.view(),value.view())
            self.assertEqual(restored.observation_rows(),value.observation_rows())

    def test_failed_check_and_rejected_request_are_distinct(self):
        s = self.session
        result = self.step(dict(action='check',check_id='prefork',expected_candidate_id=s.candidate.candidate_id))
        self.assertTrue(result['executed']); self.assertFalse(result['passed'])
        self.assertEqual(len(s.observation_rows()),1)
        self.assertFalse(self.step(dict(action='reopen_observation',handle='OBS-0999'))['accepted'])
        self.assertEqual(len(s.observation_rows()),1)
        self.assertFalse(s.saved)

    def test_rejected_recovery_preserves_exact_archive(self):
        s = self.session
        self.step(dict(action='probe',probe_id='compatibility'))
        row, raw = s.observation('OBS-0001')
        self.step(dict(action='read',path='codec/label.py',start_line=1,end_line=0))
        def measure(view):
            result = (view.get('latest_feedback') or {}).get('result',{})
            return 24000 if result.get('kind') == 'task_observation' and view['presentation']['mode'] == 'ordinary' else 1000
        result = self.step(dict(action='reopen_observation',handle=row['handle']),measure=measure)
        self.assertFalse(result['accepted'])
        self.assertEqual(s.observation(row['handle'])[1],raw)
        self.assertNotIn(row['result_handle'],s.saved)
        self.assertTrue(any(r['path'] == 'codec/label.py' for r in s.ranges))

    def test_complete_information_path_and_actual_serialized_restoration(self):
        boundaries, seen = {}, []
        def record(row,current):
            raw = canonical_json_bytes(self.task.snapshot(current))
            state = load_json_strict(raw)
            candidate = load_json_strict(self.task.candidate_bytes(current.candidate))
            restored = self.task.restore(state,candidate,self.folder,replay=True)
            self.assertEqual(canonical_json_bytes(self.task.snapshot(restored)),raw)
            self.assertEqual(restored.view(),current.view())
            self.assertEqual(restored.observation_rows(),current.observation_rows())
            for entry in current.observation_rows():
                self.assertEqual(restored.observation(entry['handle']),current.observation(entry['handle']))
            seen.append(row['name'])
            if row['name'] in ('A-to-B','B-to-C','C-to-D'):
                boundaries[row['name']] = (state,candidate)
        result = compass_qualification.journey(self.task,self.session,lambda view:0,[],variant='complete',record=record)
        self.assertTrue(result['submitted'])
        self.assertEqual([r['phase'] for r in result['recovered']],['B','C','D'])
        self.assertLessEqual(result['requests'],64)
        self.assertIn('A-stale-probe-rejected',seen)
        self.assertTrue(all(r['complete'] for p in self.session.order for r in self.session.coverage_status(p)))
        for name,(state,candidate) in boundaries.items():
            restored = self.task.restore(state,candidate,self.folder,replay=True)
            self.assertIsNone(restored.current_probe())
            self.assertFalse(restored.delivered_sources)
            # A valid preceding candidate observation remains discoverable,
            # but is not the next phase's newly produced observation.
            self.assertTrue(any(r['action']=='probe' and r['candidate_matches_current']
                for r in restored.observation_page()['entries']))
            old = [p for p in restored.pairs if p['response']['action']=='check' and p['result'].get('passed')][-1]
            self.assertEqual(restored._contract(old['result']['observation'])['checker_sha256'],
                old['result']['check_definition_sha256'])
        state,candidate = boundaries['A-to-B']
        state['diffs'][next(iter(state['diffs']))] += 'tampered'
        with self.assertRaisesRegex(ValueError,'diff history'):
            self.task.restore(state,candidate,self.folder,replay=True)


if __name__ == '__main__':
    unittest.main()
