"""Task composition and real checker boundaries; no model inference."""
import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ecological_task as m
from qualification_route import repair
from working_set_exp.jsonutil import canonical_json_bytes,load_json_strict

class EntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='verifier-entry-cpu-')
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        self.s=m.initial_session(self.folder)
        self.preceding=[]

    def deliver(self):
        self.s.mark_delivered(self.s.view());self.s.begin_request()

    def act(self, action, deliver=True):
        if deliver:self.deliver()
        else:self.s.begin_request()
        return m.process_reply(self.s,dict(discussion='CPU specimen.',operation=action),
            lambda view:0,self.preceding)['operations'][-1]['result']

    def select(self,path,first=1,last=0,results=None):
        return self.act(dict(action='work_on',sources=[dict(path=path,start_line=first,end_line=last)],results=results or []))

    def patch(self,kind='patch'):
        c=self.s.candidate
        if kind=='patch':return dict(action=kind,path=m.TARGET,old=c.file_map[m.TARGET].decode().splitlines(keepends=True)[0],new='# CPU boundary\n',expected_candidate_id=c.candidate_id,expected_file_sha256=c.file_sha256(m.TARGET))
        region=self.s.region(m.TARGET,c.file_sha256(m.TARGET),1,1)['region_ref']
        return dict(action=kind,region=region,new='# CPU boundary\n',expected_candidate_id=c.candidate_id)

    def test_fresh_original_bindings_and_distinct_check(self):
        self.assertEqual(self.s.candidate.candidate_id,m.STARTING_ID)
        self.assertEqual(sum(map(len,self.s.candidate.file_map.values())),128545)
        self.assertEqual(self.s.view()['task'],m.task_text())
        self.assertEqual(tuple(m.fixture()['required_inspection_paths']),m.REQUIRED_INSPECTION_PATHS)
        self.assertEqual(len(m.REQUIRED_INSPECTION_PATHS),10)
        self.assertNotEqual(m.PUBLIC_SHA,m.ORIGINAL_PUBLIC_SHA)
        self.assertTrue(m.public_checker().startswith(m.exact(m.EXECUTION_ONLY/'public.py',m.ORIGINAL_PUBLIC_SHA)))
        self.assertIsNone(self.s.check_state())
        self.assertFalse(self.s.pairs or self.s.ranges or self.s.saved or self.s.delivered_sources)
        self.assertEqual(self.s.prerequisite_state(),m.coverage_state())
        self.assertEqual((self.s.request_limit,self.s.call_limit),(32,96))

    def test_observation_retention_dedup_release_and_restore(self):
        r=self.act(dict(action='reopen_observation',handle='OBS-0002'))
        self.assertEqual(r['content_utf8'].encode(),m.imports()[2]['OBS-0002'])
        self.act(dict(action='read',path=m.REQUIRED_INSPECTION_PATHS[2],start_line=1,end_line=0))
        self.assertEqual(len(self.s.saved),1)
        self.act(dict(action='reopen_observation',handle='OBS-0002'))
        self.assertEqual(len(self.s.saved),1)
        self.assertIsNone(self.s.check_state())
        self.select(m.REQUIRED_INSPECTION_PATHS[2])
        self.assertEqual(len(self.s.saved),0)
        state=load_json_strict(canonical_json_bytes(m.snapshot(self.s)))
        restored=m.restore(state,self.s.candidate,self.folder,replay=True)
        self.assertEqual(canonical_json_bytes(m.snapshot(restored)),canonical_json_bytes(state))
        bad=copy.deepcopy(state);bad['original_observation_state']['rows'][0]['candidate_id']=m.STARTING_ID
        with self.assertRaises(ValueError):m.restore(bad,self.s.candidate,self.folder,replay=True)
        self.assertFalse(self.act(dict(action='reopen_observation',handle='OBS-9999'))['accepted'])

    def test_coverage_is_actual_continuous_delivery_not_acquisition(self):
        path=m.REQUIRED_INSPECTION_PATHS[2]
        self.select(path,1,10)
        self.assertFalse(self.s.coverage_state()['coverage'])
        self.deliver()
        self.assertEqual(self.s.coverage_state()['coverage'][path]['intervals'],[[1,10]])
        self.act(dict(action='read',path=path,start_line=11,end_line=20))
        self.deliver()
        self.assertEqual(self.s.coverage_state()['coverage'][path]['intervals'],[[1,20]])
        self.select(path,30,39);self.deliver()
        self.assertEqual(m.policy.missing_extents(self.s)[path],[[21,29]])
        self.assertFalse(self.act(self.patch())['accepted'])
        self.assertFalse(self.act(self.patch('replace_region'))['accepted'])
        state=m.snapshot(self.s);bad=copy.deepcopy(state)
        bad['source_prerequisites']['coverage'][path]['intervals']=[[1,39]]
        with self.assertRaises(ValueError):m.restore(bad,self.s.candidate,self.folder,replay=True)

    def test_complete_coverage_survives_release_but_does_not_grant_edit_authority(self):
        for path in m.REQUIRED_INSPECTION_PATHS:self.select(path)
        self.deliver()
        self.assertFalse(m.policy.missing_extents(self.s))
        self.assertFalse(self.act(self.patch())['accepted'])
        self.select(m.TARGET)
        result=self.act(self.patch('replace_region'))
        self.assertTrue(result['accepted'],result)
        self.assertIsNotNone(self.s.coverage_state()['first_mutation'])
        state=load_json_strict(canonical_json_bytes(m.snapshot(self.s)))
        restored=m.restore(state,self.s.candidate,self.folder,replay=True)
        self.assertEqual(canonical_json_bytes(m.snapshot(restored)),canonical_json_bytes(state))

    def test_full_checker_rejects_old_two_line_solution_then_accepts_contract_solution(self):
        files=m.starting_files()
        for path,raw in files.items():
            p=self.folder/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        checker=self.folder/'qualification_check.py';checker.write_bytes(m.public_checker())
        target=self.folder/m.TARGET
        outcomes=[]
        for stage in (0,2,3):
            target.write_bytes(repair(files[m.TARGET],stage))
            done=subprocess.run([sys.executable,'-B','-X','utf8',str(checker)],cwd=self.folder,capture_output=True,text=True,timeout=30,
                env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
            outcomes.append((done.returncode,done.stdout,done.stderr))
        self.assertNotEqual(outcomes[0][0],0)
        self.assertIn('public passed',outcomes[1][1])
        self.assertNotEqual(outcomes[1][0],0)
        self.assertIn('unsafe path accepted',outcomes[1][2])
        self.assertEqual(outcomes[2][0],0,outcomes[2][2])
        self.assertIn('expanded verifier contract passed',outcomes[2][1])

if __name__=='__main__':unittest.main()
