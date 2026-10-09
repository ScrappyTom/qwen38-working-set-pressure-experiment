"""Original probe custody, current-source authority and actual task transitions."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bootstrap
import observation_task as module
import qualification_route
from temporal_audit import Trace
from working_set_exp.jsonutil import canonical_json_bytes,load_json_strict,sha256_bytes


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='e18-observation-cpu-')
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.session=module.initial_session(self.folder)
        self.feedback=[]

    def act(self,operation):
        self.session.mark_delivered(self.session.view());self.session.begin_request()
        outcome=module.process_reply(self.session,dict(discussion='CPU engineering check.',operation=operation),lambda view:0,self.feedback)
        return outcome['operations'][-1]['result']

    def test_original_entry_preserves_two_probes_without_marker_exposure(self):
        s=self.session;rows,transport,bodies=module.imports()
        self.assertEqual(s.candidate.candidate_id,module.STARTING_ID)
        self.assertEqual((len(s.candidate.files),sum(len(x) for _,x in s.candidate.files)),(130,1103867))
        self.assertEqual((s.requests_used,s.calls_used,s.request_limit,s.call_limit),(0,0,32,96))
        self.assertFalse(s.ranges or s.saved or s.pairs or s.delivered_sources)
        self.assertIsNone(s.working_account());self.assertIsNone(s.check_state())
        self.assertEqual(s.task,(module.MODEL_VISIBLE/'TASK.txt').read_text())
        self.assertEqual([r['action'] for r in rows],['probe','probe'])
        self.assertEqual([len(bodies[r['handle']]) for r in rows],[151,152])
        rendered=canonical_json_bytes(s.view()).decode()
        for row in rows:
            self.assertEqual(transport[row['handle']],{**row,'action':'capture'})
            self.assertEqual(sha256_bytes(bodies[row['handle']]),row['sha256'])
            self.assertNotIn(load_json_strict(bodies[row['handle']])['observation'],rendered)
        self.assertFalse(any(r['shown_complete'] for r in s.view()['imported_observations']['entries']))

    def test_historical_probe_never_grants_check_or_source_authority(self):
        old=self.session.candidate
        result=self.act(dict(action='reopen_observation',handle='OBS-0001'))
        self.assertTrue(result['accepted']);self.assertTrue(result['retrieval_only'])
        self.assertFalse(result['source_edit_authority']);self.assertIsNone(self.session.check_state())
        self.assertNotEqual(result['observed_candidate_id'],old.candidate_id)
        result=self.act(dict(action='patch',path=module.TARGET,old=old.file_map[module.TARGET].decode(),
            new='def codec_label(value):\n    return value\n',expected_candidate_id=old.candidate_id,
            expected_file_sha256=old.file_sha256(module.TARGET)))
        self.assertFalse(result['accepted']);self.assertEqual(self.session.candidate,old)

    def test_release_changes_visibility_not_custody_and_recovery_is_exact(self):
        receipt=self.act(dict(action='reopen_observation',handle='OBS-0002'))
        handle=receipt['exact_result_handle'];raw=self.session.payload(handle)
        self.act(dict(action='work_on',sources=[dict(path=module.SECONDARY,start_line=1,end_line=0)],results=[]))
        self.assertFalse(any(r['shown_complete'] for r in self.session.view()['imported_observations']['entries']))
        result=self.act(dict(action='reopen_result',handle=handle,offset=0))
        self.assertTrue(result['accepted']);self.assertEqual(self.session.payload(handle),raw)
        self.assertEqual(load_json_strict(raw),receipt)
        self.assertTrue(any(r['handle']=='OBS-0002' and r['shown_complete'] for r in self.session.view()['imported_observations']['entries']))
        self.assertEqual(qualification_route.source(self.session.view(),module.SECONDARY)['content'].encode(),module.starting_files()[module.SECONDARY])
        self.assertIsNone(self.session.check_state())

    def test_restore_preserves_versions_and_rejects_rebound_provenance(self):
        self.act(dict(action='reopen_observation',handle='OBS-0002'))
        self.act(dict(action='read',path=module.TARGET,start_line=1,end_line=0))
        c=self.session.candidate;old=c.file_map[module.TARGET].decode()
        self.assertTrue(self.act(dict(action='patch',path=module.TARGET,old=old,new=old+'# CPU fixture\n',
            expected_candidate_id=c.candidate_id,expected_file_sha256=c.file_sha256(module.TARGET)))['accepted'])
        state=module.snapshot(self.session)
        restored=module.restore(load_json_strict(canonical_json_bytes(state)),self.session.candidate,self.folder,replay=True)
        self.assertEqual(restored.view(),self.session.view())
        self.assertEqual(restored.payload('RES-0001'),self.session.payload('RES-0001'))
        for key in ('original_observation_state','imported_capture_state'):
            broken=copy.deepcopy(state)
            rows=broken[key]['rows' if key.startswith('original') else 'inventory']
            rows[1]['candidate_id']='0'*64
            with self.assertRaises(ValueError):module.restore(broken,self.session.candidate,self.folder,replay=True)
        row=next(r for r in restored.view()['imported_observations']['entries'] if r['handle']=='OBS-0002')
        self.assertEqual(row['observed_candidate_id'],module.STARTING_ID)
        self.assertNotEqual(row['observed_candidate_id'],restored.candidate.candidate_id)

    def test_unknown_capture_keeps_selection_account_and_candidate(self):
        self.act(dict(action='reopen_observation',handle='OBS-0002'))
        before=(self.session.candidate,copy.deepcopy(self.session.saved),self.session.working_account())
        result=self.act(dict(action='reopen_observation',handle='OBS-9999'))
        self.assertFalse(result['accepted'])
        self.assertEqual((self.session.candidate,self.session.saved,self.session.working_account()),before)

    def test_scripted_source_supported_journey_closes_after_exact_recovery(self):
        rows=[]
        result=qualification_route.journey(module,self.session,lambda view:0,record=lambda row,current:rows.append(copy.deepcopy(row)))
        self.assertTrue(result['submitted']);self.assertTrue(result['audit']['temporal_contract_met'])
        self.assertEqual(result['requests'],12)
        self.assertEqual(result['operations'],12)
        original=module.starting_files()
        self.assertEqual(sum(self.session.candidate.file_map[p]==raw for p,raw in original.items()),128)
        self.assertTrue(self.session.check_state()['passed'])
        # Audit negative: a truthful-looking flag/account cannot replace bytes.
        counterfactual=Trace(module)
        for row in rows:
            view=copy.deepcopy(row['before_view'])
            if row['name']=='footer':
                view['working_set']['saved_results']=[]
                view['latest_feedback']['result']={'accepted':True,'kind':'status_only'}
                view['working_account']={'author':'model','text':'The exact marker is established.'}
                self.assertTrue(any(r['shown_complete'] for r in view['imported_observations']['entries']))
            counterfactual.observe(row['name'],view,row['outcome']['operations'],self.session.versions,self.session.pairs,row['preceding_before'])
        self.assertFalse(counterfactual.result()['exact_marker_available_at_footer'])
        self.assertFalse(counterfactual.result()['temporal_contract_met'])


if __name__=='__main__':unittest.main()
