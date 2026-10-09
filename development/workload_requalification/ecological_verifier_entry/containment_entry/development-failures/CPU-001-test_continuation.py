"""Continuation identity, applicability and real observation boundaries; CPU only."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import continuation_task as m
from qualify_checker import reference_source
from working_set_exp.jsonutil import canonical_json_bytes


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='containment-entry-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.s = m.initial_session()
        # The same copied observations and preservation callback used by the run.
        from manage import legacy
        log = legacy.QualificationLog(self.folder/'records.jsonl', 'cpu-continuation', task_module=m.Task())
        m.attach_observations(self.s, self.folder, log)
        self.preceding = []

    def act(self, action):
        self.s.mark_delivered(self.s.view())
        self.s.begin_request()
        return m.process_reply(self.s, dict(discussion='CPU qualification specimen.', operation=action),
            lambda view: 0, self.preceding)['operations'][-1]['result']

    def test_exact_entry_and_historical_applicability(self):
        old = m.inherited_state()
        self.assertEqual(m.snapshot(self.s), {**old, 'call_limit':65, 'request_limit':32, 'submitted':False})
        self.assertFalse(self.s.check_state()['applies_to_current'])
        self.assertTrue(self.s.check_state()['passed'])
        original = m.previous.restore(old, self.s.candidate, m.OLD, True)
        for i in range(1,30):
            for kind in ('EVT','RES'):
                self.assertEqual(self.s.payload(f'{kind}-{i:04d}'), original.payload(f'{kind}-{i:04d}'))
        restored = m.restore(m.snapshot(self.s), self.s.candidate, self.folder, True)
        self.assertEqual(restored.view(), self.s.view())
        self.assertFalse(self.act(dict(action='submit',expected_candidate_id=m.SAVED_ID))['accepted'])

    def test_tampered_history_provenance_and_designation_rejected(self):
        for field in ('history','provenance','submitted','limit'):
            state=copy.deepcopy(m.snapshot(self.s))
            if field=='history': state['pairs'][0]['result']['accepted']=False
            if field=='provenance': state['original_observation_state']['rows'][0]['candidate_id']=m.SAVED_ID
            if field=='submitted': state['submitted']=True
            if field=='limit': state['call_limit']=66
            with self.subTest(field=field), self.assertRaises(ValueError):
                m.restore(state,self.s.candidate,self.folder,True)

    def test_real_failure_correction_pass_and_restoration(self):
        result=self.act(dict(action='check',check_id='public',expected_candidate_id=m.SAVED_ID))
        self.assertFalse(result['passed'])
        self.assertIn('./C:/outside.py', canonical_json_bytes(self.s.view()).decode())
        self.assertIn('unsafe path component survived normalization',canonical_json_bytes(self.s.view()).decode())
        source=self.s.candidate.file_map[m.TARGET].decode()
        result=self.act(dict(action='patch',path=m.TARGET,expected_candidate_id=m.SAVED_ID,
            expected_file_sha256=self.s.candidate.file_sha256(m.TARGET),old=source,new=reference_source(source)))
        self.assertTrue(result['accepted'],result)
        check=self.act(dict(action='check',check_id='public',expected_candidate_id=self.s.candidate.candidate_id))
        self.assertTrue(check['passed'],check)
        self.assertTrue(self.act(dict(action='submit',expected_candidate_id=self.s.candidate.candidate_id))['accepted'])
        restored=m.restore(m.snapshot(self.s),self.s.candidate,self.folder,True)
        self.assertEqual(restored.view(),self.s.view())
        self.assertTrue(restored.submitted)
        self.assertEqual(restored.pairs[:29],m.inherited_state()['pairs'])


if __name__=='__main__': unittest.main(verbosity=2)
