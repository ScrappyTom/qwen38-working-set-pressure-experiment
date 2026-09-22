"""Task portability and qualification boundaries; no model or GPU activity."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import case_reports
import repair_task as task
import repair_qualification as gate
import run_uncoached_contribution as runner
from working_set_exp import working_view
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file
from working_set_exp.observations import ObservationStore


class AlteredOutcome:
    """Counterfactual outer execution over unchanged preserved stdout/stderr."""
    def __init__(self,store,**changes):self.store,self.changes=store,changes
    def directory(self,handle):return self.store.directory(handle)
    def read(self,handle):return {**self.store.read(handle),**self.changes}


class ReportingTests(unittest.TestCase):
    def store(self,case,label='reference'):
        return ObservationStore(task.AREA/'checker-qualification-002'/case/label,replay=True)

    def test_actual_original_and_reference_observations(self):
        for case,count in [('artifact_map',1),('shift',24),('receipts',38)]:
            for label in ('original','reference'):
                with self.subTest(case=case,label=label):
                    store=self.store(case,label)
                    before={p.name:p.read_bytes() for p in store.directory('CHK-0001').iterdir() if p.is_file()}
                    result=case_reports.assessment(store,'CHK-0001')
                    self.assertEqual(len(result['criteria']),count)
                    self.assertIs(result['passed'],label=='reference')
                    self.assertEqual(result['termination'],'completed')
                    self.assertEqual(result['observation_capture_complete'],True)
                    self.assertEqual(bool(result['failed_criteria']),label=='original')
                    pages=[];offset=0
                    while True:
                        page=case_reports.inspect_check(store,'CHK-0001',offset)
                        pages.extend(page['entries'])
                        if page['next_offset'] is None:break
                        offset=page['next_offset']
                    self.assertEqual(pages,result['criteria'])
                    overview=case_reports.overview(result)
                    self.assertEqual(overview['failed_records_total'],len(result['failed_criteria']))
                    self.assertEqual(overview['failed_records_shown']+overview['failed_records_remaining'],len(result['failed_criteria']))
                    if case=='receipts':
                        self.assertEqual(overview['input_observations'][0]['observation'],'input sequence')
                        self.assertIn('X,2,beta,sensor,6,active',overview['input_observations'][0]['csv'])
                    self.assertEqual(before,{p.name:p.read_bytes() for p in store.directory('CHK-0001').iterdir() if p.is_file()})

    def test_incomplete_outer_execution_survives_passing_case_summary(self):
        for reason in ('timeout','capture_limit'):
            with self.subTest(reason=reason):
                original=case_reports.assessment(self.store('shift'),'CHK-0001')
                store=AlteredOutcome(self.store('shift'),capture_complete=False,termination=reason,passed=False,returncode=-1)
                result=case_reports.assessment(store,'CHK-0001')
                self.assertEqual(result['criteria'][1:],original['criteria'])
                self.assertEqual(result['criteria'][0]['criterion'],'public_execution')
                self.assertIs(result['criteria'][0]['met'],False)
                self.assertEqual(result['criteria'][0]['termination'],reason)
                view=case_reports.overview(result)
                self.assertEqual(view['failed_criteria'],['public_execution'])
                self.assertEqual(view['criteria'][0],result['criteria'][0])
                self.assertEqual(view['termination'],reason)
                self.assertIs(view['passed'],False)

    def test_complete_outer_failure_is_not_overridden_by_case_passes(self):
        result=case_reports.assessment(AlteredOutcome(self.store('receipts'),passed=False,returncode=1),'CHK-0001')
        self.assertEqual(result['failed_criteria'],['public_execution'])
        self.assertEqual(len(result['criteria']),39)

    def test_incomplete_single_observation_has_one_execution_criterion_and_keeps_stdout(self):
        store=AlteredOutcome(self.store('artifact_map'),capture_complete=False,termination='timeout',passed=False,returncode=-1)
        result=case_reports.assessment(store,'CHK-0001')
        self.assertEqual(result['failed_criteria'],['public_execution'])
        self.assertEqual(len(result['criteria']),1)
        self.assertIn('current_reopen',result['criteria'][0]['stdout']['text'])
        self.assertEqual(result['criteria'][0]['termination'],'timeout')


class TaskTests(unittest.TestCase):
    def test_original_contract_and_clear_session_boundary_without_reference_leak(self):
        for case in task.MODULES:
            with self.subTest(case=case):
                module=task.Task(case);fixture=module.legacy.constructed_fixture()
                session=module.initial_session();view=session.view()
                self.assertEqual(session.task,fixture.task)
                self.assertEqual(session.candidate.candidate_id,fixture.initial.candidate_id)
                self.assertEqual(session.checkers,{'public':fixture.public_checker})
                self.assertEqual(session.edit_checks,{})
                self.assertEqual((session.request_limit,session.call_limit),(24,72))
                self.assertEqual(session.pairs,[]);self.assertEqual(session.ranges,[])
                self.assertIsNone(session.working_account())
                self.assertIn('before this repair session',view['episode_annotation'])
                self.assertIn('recent_activity',view['episode_annotation'])
                self.assertNotIn('active_phase_event_frame',view['episode_annotation'])
                request=runner.Adapter(module).request_for(view)
                self.assertNotIn(module.legacy.GOOD,json.dumps(request))
                text=request['messages'][0]['content']
                self.assertIn('edits do not trigger checks',text)
                self.assertNotIn('automatic check',text)
                self.assertNotIn('declared fault target',text)
                self.assertNotIn('check_after',text)
                self.assertNotIn('Passing examples',text)
                session.mark_delivered(view)

    def test_only_supported_explicit_check_reply_passes_schema(self):
        schema=task.Task('artifact_map').reply_schema()['json_schema']['schema']
        action=dict(action='check',check_id='public',expected_candidate_id='a'*64)
        working_view.validate(dict(discussion='Check saved work.',operation=action),schema)
        for scope in ('tests','examples'):
            with self.assertRaises(ValueError):
                working_view.validate(dict(discussion='Check.',operation={**action,'check_id':scope}),schema)
        patch=dict(action='patch',path='app.py',expected_candidate_id='a'*64,expected_file_sha256='b'*64,old='old',new='new')
        working_view.validate(dict(discussion='Save.',operation=patch),schema)
        with self.assertRaises(ValueError):
            working_view.validate(dict(discussion='Save/check.',operation=patch,check_after='public'),schema)


class PrerequisiteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='small-repair-gate-')
        self.root=Path(self.temp.name);self.folder=self.root/'qualified';self.folder.mkdir()
        (self.root/'implementation.py').write_text('original implementation\n')
        self.sources={'implementation.py':sha256_file(self.root/'implementation.py')}
        self.result=dict(completion_requests=0,cases=[dict(case=case,entry=entry,passed=entry=='reference')
            for case in ('artifact_map','shift','receipts') for entry in ('original','reference')])
        self.seal(status='qualified_no_model_inference')

    def tearDown(self):self.temp.cleanup()

    def seal(self,**updates):
        (self.folder/'RESULTS.json').write_bytes(canonical_json_bytes(self.result))
        files=[dict(path='RESULTS.json',sha256=sha256_file(self.folder/'RESULTS.json'),size_bytes=(self.folder/'RESULTS.json').stat().st_size)]
        value=dict(status='qualified_no_model_inference',completion_requests=0,source_sha256=self.sources,
            files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files)))
        value.update(updates)
        (self.folder/'SEAL.json').write_bytes(canonical_json_bytes(value))

    def test_passed_qualification_binds_seal_and_output(self):
        self.assertEqual(set(gate.verify(self.root,self.folder,self.sources,'checker')),
                         {'qualified/SEAL.json','qualified/RESULTS.json'})

    def test_changed_source_rejected_even_with_intact_outputs(self):
        (self.root/'implementation.py').write_text('changed implementation\n')
        with self.assertRaises(AssertionError):gate.verify(self.root,self.folder,self.sources,'checker')

    def test_changed_evidence_rejected(self):
        (self.folder/'RESULTS.json').write_text('{}')
        with self.assertRaises(AssertionError):gate.verify(self.root,self.folder,self.sources,'checker')

    def test_failed_status_rejected_even_with_matching_files(self):
        self.seal(status='failed_preserved')
        with self.assertRaises(AssertionError):gate.verify(self.root,self.folder,self.sources,'checker')

    def test_wrong_inventory_or_source_closure_rejected(self):
        self.seal(aggregate_sha256='0'*64)
        with self.assertRaises(AssertionError):gate.verify(self.root,self.folder,self.sources,'checker')
        self.seal(source_sha256={})
        with self.assertRaises(AssertionError):gate.verify(self.root,self.folder,self.sources,'checker')

    def test_checker_outcome_disagreement_rejected(self):
        self.result['cases'][0]['passed']=True;self.seal()
        with self.assertRaises(AssertionError):gate.verify(self.root,self.folder,self.sources,'checker')

    def test_native_status_and_case_outcome_checked(self):
        self.result=dict(status='passed',model_inference_calls=0,vocabulary_only=True,
                         cases=[dict(accepted_including_eos=False,expected=False)])
        self.seal();gate.verify(self.root,self.folder,self.sources,'native')
        self.result['cases'][0]['expected']=True;self.seal()
        with self.assertRaises(AssertionError):gate.verify(self.root,self.folder,self.sources,'native')


if __name__=='__main__':unittest.main()
