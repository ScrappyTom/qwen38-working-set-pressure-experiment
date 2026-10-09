"""Original-case identity, serialized transitions and truthful scoped feedback."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import receipt_task as study
import receipt_qualification
from working_set_exp.jsonutil import canonical_json_bytes,load_json_strict
from working_set_exp.observations import ObservationStore


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='receipt-entry-cpu-')
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)

    def new(self,case):
        task=study.Task(case=case)
        session=task.initial_session()
        session.observations=ObservationStore(self.folder/study.CASES[case]['folder']/'observations')
        return task,session

    def step(self,task,session,action,account=None):
        session.mark_delivered(session.view())
        session.begin_request()
        reply=dict(discussion='CPU engineering qualification.',operation=action)
        if account is not None: reply['account']=account
        reply=task.decode_reply(canonical_json_bytes(reply).decode())
        return task.process_reply(session,reply,lambda view:0,[])['operations'][-1]['result']

    def test_original_entries_and_no_imported_marker(self):
        for case,config in study.CASES.items():
            with self.subTest(case=case):
                task,session=self.new(case)
                self.assertEqual(session.candidate.candidate_id,config['initial'])
                self.assertEqual(len(session.candidate.files),config['files'])
                self.assertEqual(session.pairs,[])
                self.assertFalse(session.ranges)
                self.assertFalse(session.saved)
                self.assertIsNone(session.working_account())
                self.assertNotIn('M8::',canonical_json_bytes(session.view()).decode())
                self.assertEqual(session.edit_checks,{})
                self.assertEqual((session.request_limit,session.call_limit),(32,96))
                self.assertEqual(session.task,task.task_text())

    def test_complete_routes_and_every_actual_serialized_checkpoint(self):
        for case in study.CASES:
            with self.subTest(case=case):
                task,session=self.new(case)
                snapshots=[]
                def record(row,current):
                    raw=canonical_json_bytes(task.snapshot(current))
                    candidate=load_json_strict(task.candidate_bytes(current.candidate))
                    restored=task.restore(load_json_strict(raw),candidate,session.observations.root.parent,replay=True)
                    self.assertEqual(canonical_json_bytes(task.snapshot(restored)),raw)
                    self.assertEqual(restored.view(),current.view())
                    snapshots.append(raw)
                result=receipt_qualification.journey(task,session,lambda view:0,[],variant='complete',record=record)
                self.assertTrue(result['submitted'])
                self.assertTrue(all(r['complete'] for phase in ('A','B') for r in session.coverage_status(phase)))
                self.assertLessEqual(session.requests_used,32)
                self.assertLessEqual(session.calls_used,96)
                self.assertGreater(len(snapshots),10)
                damaged=load_json_strict(snapshots[-1])
                key=next(iter(damaged['diffs']))
                damaged['diffs'][key]+='altered'
                with self.assertRaisesRegex(ValueError,'diff history'):
                    task.restore(damaged,session.candidate,self.folder,replay=True)

    def test_scope_is_not_name_behavior(self):
        task,session=self.new('E14-STALE-SABLE')
        # Exercise the ordinary scoped capture on its own original program;
        # no phase entry or fabricated prior pass is used for the full journey.
        result=session.observations.execute(session.candidate,task.checker('B'),'public','CHK-0001')
        self.assertTrue(result['passed'])
        contract=session.check_contracts['public']
        full=study.receipt_reports.assessment(session.observations,'CHK-0001',contract)
        summary=study.receipt_reports.overview(full)
        page=study.receipt_reports.inspect_check(session.observations,'CHK-0001',0,contract)
        for value in (full,summary,page):
            self.assertIn('does not test normalized-name',value['explanation'])
            self.assertTrue(value['passed'])
        namespace={}
        exec(session.candidate.file_map['api/name.py'],namespace)
        self.assertNotEqual(namespace['normalize_name'](' Ab '),'sable-ab')
        with self.assertRaises(ValueError):
            study.receipt_reports.assessment(session.observations,'CHK-0001',dict(contract,checker_sha256='0'*64))

    def test_case_and_opportunity_tampering_rejected(self):
        mint,m=self.new('E14-CLOSURE-MINT')
        sable,s=self.new('E14-STALE-SABLE')
        with self.assertRaises(ValueError): sable.candidate_from_snapshot(load_json_strict(mint.candidate_bytes(m.candidate)))
        state=load_json_strict(canonical_json_bytes(mint.snapshot(m)))
        state['request_limit']=64
        with self.assertRaisesRegex(ValueError,'opportunity'):
            mint.restore(state,m.candidate,self.folder,replay=True)

    def test_probe_available_only_for_original_probe_case(self):
        op=dict(discussion='Probe original fixture.',operation=dict(action='probe',probe_id='integrity'))
        mint,m=self.new('E14-CLOSURE-MINT')
        sable,s=self.new('E14-STALE-SABLE')
        self.assertEqual(mint.decode_reply(canonical_json_bytes(op).decode()),op)
        with self.assertRaises(ValueError): sable.decode_reply(canonical_json_bytes(op).decode())
        result=self.step(mint,m,op['operation'])
        self.assertTrue(result['accepted'])
        self.assertIn('marker=M8::',result['observation'])
        self.assertEqual(m.observation('OBS-0001')[1],canonical_json_bytes(result))

    def test_probe_branch_identity_and_serialized_restore(self):
        task,session=self.new('E14-CLOSURE-MINT')
        self.step(task,session,dict(action='probe',probe_id='integrity'))
        branch=session.clone()
        self.step(task,branch,dict(action='read',path='workflow/progress.py',start_line=1,end_line=0))
        self.step(task,branch,dict(action='patch',path='workflow/progress.py',old='return 0',new='return 1',
            expected_candidate_id=branch.candidate.candidate_id,expected_file_sha256=branch.candidate.file_sha256('workflow/progress.py')))
        for current in (session,branch): self.step(task,current,dict(action='probe',probe_id='integrity'))
        self.assertEqual(session.observation('OBS-0001'),branch.observation('OBS-0001'))
        self.assertNotEqual(session.observation('OBS-0002'),branch.observation('OBS-0002'))
        for current in (session,branch):
            restored=task.restore(load_json_strict(canonical_json_bytes(task.snapshot(current))),current.candidate,self.folder,replay=True)
            self.assertEqual(restored.observation_rows(),current.observation_rows())
            self.assertEqual(restored.observation('OBS-0002'),current.observation('OBS-0002'))


if __name__=='__main__': unittest.main()
