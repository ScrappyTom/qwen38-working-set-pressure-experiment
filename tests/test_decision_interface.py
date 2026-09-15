"""Host meaning, evidence lifetime and literal transport; no model inference."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from working_set_exp import check_assessment, decision_view
from working_set_exp.accounted_contribution import process_reply
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.decision_session import DecisionSession
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes
from working_set_exp.observations import ObservationStore

ROOT = Path(__file__).resolve().parents[1]
OLD_RUN = ROOT/'development/operable_recovery/run-001'


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ObservationStore(Path(self.temp.name)/'obs')

    def session(self, files=None, code=b'print("observed")', **kwargs):
        return DecisionSession(Candidate.create(files or {'app.py':b'value = 2\n', 'test.py':b'assert 2 == 2\n'}),
            {'tests':code,'public':code}, 'Extend tests while preserving implementation.',
            observations=self.store, edit_checks={'test.py':'tests'}, call_limit=48,request_limit=16,**kwargs)

    def read(self,s,path='app.py',first=1,last=0,measure=lambda v:1000):
        return s.execute(dict(action='read',path=path,start_line=first,end_line=last),measure)

    def region_action(self,s,path='test.py',new='assert 3 == 3\n'):
        self.read(s,path)
        s.mark_delivered(s.view())
        source = next(v for v in s.view()['working_set']['sources'] if v['path']==path)
        return dict(action='replace_region',region=source['region_ref'],expected_candidate_id=s.candidate.candidate_id,new=new)

    def test_actual_failed_check_names_fault_and_does_not_promote_mutation_paths(self):
        store=ObservationStore(OLD_RUN/'observations',replay=True)
        value=check_assessment.assessment(store,'CHK-0020')
        self.assertEqual(value['failed_criteria'],['detect.error_class'])
        rows={r['criterion']:r for r in value['criteria']}
        self.assertFalse(rows['detect.error_class']['fault_detected'])
        self.assertTrue(rows['detect.error_arguments']['fault_detected'])
        self.assertTrue(rows['required_paths']['met'])
        self.assertNotIn('missing_paths',rows['detect.error_arguments'])
        self.assertFalse(rows['detect.error_arguments']['mutation_path_coverage_is_required'])

    def test_check_record_pages_are_complete_and_all_records_reconstruct(self):
        store=ObservationStore(OLD_RUN/'observations',replay=True)
        rows, offset=[],0
        while True:
            page=check_assessment.inspect_check(store,'CHK-0020',offset)
            self.assertTrue(page['records_complete'])
            rows.extend(page['entries'])
            if page['next_offset'] is None:
                break
            offset=page['next_offset']
        self.assertEqual(rows,check_assessment.assessment(store,'CHK-0020')['criteria'])
        self.assertEqual(rows[0]['criterion'],'detect.error_class')
        with self.assertRaises(ValueError):
            check_assessment.inspect_check(store,'CHK-0020',999)

    def test_unstructured_check_is_unassessed_not_invented_criteria(self):
        s=self.session(code=b'print("raw diagnostic")\nraise SystemExit(1)')
        r=s.execute(dict(action='check',check_id='tests',expected_candidate_id=s.candidate.candidate_id),lambda v:1000)
        self.assertTrue(r['executed'])
        self.assertFalse(r['passed'])
        self.assertFalse(r['report']['assessment_available'])
        self.assertEqual(r['report']['failed_criteria'],[])

    def test_contract_is_bound_to_checker_not_guessed_from_fault_name(self):
        with self.assertRaisesRegex(ValueError,'different checker'):
            self.session(check_contracts={'tests':{'checker_sha256':'0'*64}})

    def test_malformed_or_incomplete_assessment_keeps_executed_outcome(self):
        for fields in ({'fault_sensitivity':[]}, {'edited_suite':{'successful':False,'details':[7]}},
                       {'assessment_error':'checker failed to finish its own assessment'}):
            with self.subTest(fields=fields), tempfile.TemporaryDirectory() as folder:
                self.store=ObservationStore(Path(folder)/'obs')
                data=json.dumps(dict(observation_schema='contribution-check-v2',**fields))
                s=self.session(code=('print('+repr(data)+')\nraise SystemExit(1)').encode())
                r=s.execute(dict(action='check',check_id='tests',expected_candidate_id=s.candidate.candidate_id),lambda v:1000)
                self.assertTrue(r['accepted'] and r['executed'])
                self.assertFalse(r['report']['assessment_available'])
                self.assertFalse(s.view()['verification']['checks']['tests']['passed'])
        self.store=ObservationStore(Path(self.temp.name)/'capped',stream_limit=64)
        s=self.session(code=b'print("x"*1000)')
        r=s.execute(dict(action='check',check_id='tests',expected_candidate_id=s.candidate.candidate_id),lambda v:1000)
        self.assertFalse(r['report']['observation_capture_complete'])
        self.assertFalse(r['report']['assessment_available'])

    def test_long_escaped_multiple_diagnostics_are_bounded_and_raw_is_exact(self):
        trace='"\\'*6000+'\nAssertionError: decisive end\n'
        data=json.dumps(dict(observation_schema='contribution-check-v2',edited_suite=dict(
            successful=False,tests=3,failures=3,errors=0,details=[dict(test='test_'+str(i),trace=trace) for i in range(3)])))
        s=self.session(code=('print('+repr(data)+')\nraise SystemExit(1)').encode())
        r=s.execute(dict(action='check',check_id='tests',expected_candidate_id=s.candidate.candidate_id),lambda v:1000)
        page=s.execute(dict(action='inspect_check',observation=r['observation'],offset=0),lambda v:1000)
        entry=page['entries'][0]
        self.assertEqual(entry['criterion'],'edited_suite.execution')
        self.assertEqual(entry['additional_diagnostics'],1)
        self.assertEqual(len(entry['diagnostics']),2)
        for detail in entry['diagnostics']:
            self.assertFalse(detail['diagnostic']['complete'])
            self.assertIn('decisive end',detail['diagnostic']['text'])
            self.assertLessEqual(len(detail['diagnostic']['text'].encode()),2048)
        raw=(self.store.directory(r['observation'])/'stdout.bin').read_bytes()
        self.assertEqual(json.loads(raw)['edited_suite']['details'][2]['trace'],trace)
        self.assertLess(len(canonical_json_bytes(page)),11000)

    def test_source_is_in_one_stable_location_after_read_and_group(self):
        s=self.session()
        for action in (dict(action='read',path='app.py',start_line=1,end_line=0),
                       dict(action='work_on',sources=[dict(path='app.py',start_line=1,end_line=1)],results=[])):
            r=s.execute(action,lambda v:1000)
            self.assertTrue(r['accepted'])
            view=s.view()
            self.assertEqual(view['working_set']['sources'][0]['content'],'value = 2\n')
            self.assertNotIn('source',view['latest_feedback']['result'])
            self.assertNotIn('sources',view['latest_feedback']['result'])
            self.assertTrue(view['visibility']['retained_inventory']['entries'][0]['body_shown_in_full'])
            s.mark_delivered(view)

    def test_recovery_reads_retain_previous_implementation_while_reading_imports(self):
        s=self.session()
        s.enter_recovery('saved capacity obstruction')
        self.read(s,'app.py')
        self.read(s,'test.py')
        view=s.view()
        self.assertEqual({v['path'] for v in view['working_set']['sources']},{'app.py','test.py'})
        self.assertEqual(len(s.recovery_focus),2)
        self.assertEqual(len(s.ranges),2)
        self.assertFalse(view['presentation']['selected_bodies_omitted'])
        self.assertNotIn('selection',view)
        self.assertTrue(s.execute(dict(action='search',path='app.py',query='value',offset=0,limit=1),lambda v:1000)['accepted'])
        self.assertEqual(len(s.view()['working_set']['sources']),2)

    def test_rejected_acquisition_does_not_rotate_retained_recovery_evidence(self):
        s=self.session()
        s.enter_recovery('capacity')
        self.read(s)
        def measure(view):
            return 30000 if len(view['working_set']['sources'])>1 else 1000
        result=self.read(s,'test.py',measure=measure)
        self.assertFalse(result['accepted'])
        self.assertEqual([v['path'] for v in s.view()['working_set']['sources']],['app.py'])
        self.assertEqual(len(s.ranges),1)

    def test_small_account_is_full_and_capacity_reduction_never_changes_storage(self):
        s=self.session()
        s.enter_recovery('capacity')
        text='exact conclusion\n'+'x'*725
        s.execute(dict(action='record_account',text=text),lambda v:5761)
        self.assertEqual(s.view()['working_account']['text'],text)
        def crowded(view):
            return 24000 if 'text' in view['working_account'] else 23000
        self.assertTrue(s._fits_feedback(crowded))
        self.assertFalse(s.view()['working_account']['text_complete'])
        self.assertEqual(s.working_account()['text'],text)
        self.assertTrue(s._fits_feedback(lambda v:5000))
        self.assertEqual(s.view()['working_account']['text'],text)

    def test_check_failure_remains_scoped_and_visible_after_inspection(self):
        s=self.session(code=b'print("failure")\nraise SystemExit(1)')
        r=s.execute(dict(action='check',check_id='tests',expected_candidate_id=s.candidate.candidate_id),lambda v:1000)
        s.execute(dict(action='inspect_check',observation=r['observation'],offset=0),lambda v:1000)
        view=s.view()
        self.assertNotIn('current_check',view)
        self.assertFalse(view['verification']['checks']['tests']['passed'])
        self.assertIsNone(view['verification']['checks']['public'])
        self.assertFalse(view['verification']['submission']['eligible'])
        self.assertEqual(view['verification']['outstanding'][0]['scope'],'tests')

    def test_raw_page_separates_complete_capture_from_partial_display(self):
        s=self.session(code=b"print('x'*9000)")
        r=s.execute(dict(action='check',check_id='tests',expected_candidate_id=s.candidate.candidate_id),lambda v:1000)
        p=s.execute(dict(action='inspect_observation',observation=r['observation'],stream='stdout',offset=0),lambda v:1000)
        self.assertTrue(p['observation_capture_complete'])
        self.assertFalse(p['page_complete'])
        self.assertEqual(p['shown_bytes'],4096)

    def test_literal_body_exact_bytes_and_declared_successor_check(self):
        s=self.session()
        body='text = "\\n and \\u0661"\r\n# é\r\nSOURCE\n'
        action=self.region_action(s,new=body)
        header=dict(discussion='Save literal source.',operation={k:v for k,v in action.items() if k!='new'})
        raw=json.dumps(header)+'\nSOURCE\n'+body
        reply=decision_view.decode_reply(raw)
        self.assertEqual(reply['operation']['new'],body)
        outcome=process_reply(s,reply,lambda v:1000,[])
        self.assertEqual(s.candidate.file_map['test.py'],body.encode())
        self.assertEqual(len(outcome['operations']),2)
        self.assertEqual(outcome['operations'][1]['result']['checked_candidate_id'],s.candidate.candidate_id)

    def test_exact_region_can_replace_repeated_old_text_without_guessing_occurrence(self):
        s=self.session(files={'test.py':b'same = 1\nsame = 1\n'})
        self.read(s,'test.py',2,2)
        s.mark_delivered(s.view())
        source=s.view()['working_set']['sources'][0]
        r=s.execute(dict(action='replace_region',region=source['region_ref'],expected_candidate_id=s.candidate.candidate_id,new='same = 2\n'),lambda v:1000)
        self.assertTrue(r['accepted'])
        self.assertEqual(s.candidate.file_map['test.py'],b'same = 1\nsame = 2\n')

    def test_search_supplies_complete_nested_function_without_source_authority(self):
        s=self.session(files={'test.py':b'class Tests:\n    def test_one(self):\n        assert 1 == 1\n\n    def test_two(self):\n        pass\n'})
        r=s.execute(dict(action='search',path='test.py',query='def test_one',offset=0,limit=4),lambda v:1000)
        region,=[v for v in r['regions'] if v.get('name')=='test_one']
        self.assertEqual((region['start_line'],region['end_line']),(2,3))
        s.mark_delivered(s.view())
        action=dict(action='replace_region',region=region['region_ref'],expected_candidate_id=s.candidate.candidate_id,new='    def test_one(self):\n        assert True\n')
        self.assertFalse(s.execute(action,lambda v:1000)['accepted'])
        s.execute(dict(action='work_on_exact',regions=[region['region_ref']],results=[]),lambda v:1000)
        s.mark_delivered(s.view())
        self.assertTrue(s.execute(action,lambda v:1000)['accepted'])

    def test_region_requires_actual_visibility_and_fresh_candidate(self):
        s=self.session()
        action=self.region_action(s)
        candidate=s.candidate.candidate_id
        s.enter_recovery('source now omitted')
        s.mark_delivered(s.view())
        self.assertFalse(s.execute(action,lambda v:1000)['accepted'])
        self.assertEqual(s.candidate.candidate_id,candidate)
        self.read(s,'test.py')
        s.mark_delivered(s.view())
        self.assertFalse(s.execute({**action,'expected_candidate_id':'0'*64},lambda v:1000)['accepted'])
        self.assertTrue(s.execute(action,lambda v:1000)['accepted'])
        self.assertFalse(s.execute(action,lambda v:1000)['accepted'])

    def test_replacement_refreshes_visible_recovery_source_and_releases_on_selection(self):
        s=self.session()
        s.enter_recovery('capacity')
        action=self.region_action(s,new='a = 1\nb = 2\n')
        self.assertTrue(s.execute(action,lambda v:1000)['accepted'])
        self.assertEqual(s.view()['working_set']['sources'][0]['content'],'a = 1\nb = 2\n')
        s.execute(dict(action='work_on',sources=[],results=[]),lambda v:1000)
        self.assertFalse(s.recovery)
        self.assertEqual(s.recovery_focus,[])
        self.assertEqual(s.view()['working_set']['sources'],[])

    def test_empty_literal_replacement_and_malformed_header(self):
        s=self.session()
        action=self.region_action(s,new='')
        raw=json.dumps(dict(discussion='Delete region.',operation={k:v for k,v in action.items() if k!='new'}))+'\nSOURCE\n'
        self.assertEqual(decision_view.decode_reply(raw)['operation']['new'],'')
        with self.assertRaises(ValueError):
            decision_view.decode_reply('{"discussion":"bad","operation":{"action":"read"}}\nSOURCE\ntext')

    def test_literal_grammar_survives_actual_wire_serializer_and_is_exclusive(self):
        request=dict(messages=[],grammar='root ::= "literal"')
        self.assertEqual(json.loads(completion_request_bytes(request)),request)
        with self.assertRaisesRegex(ValueError,'exclusive'):
            completion_request_bytes({**request,'response_format':{}})

    def test_rejected_literal_edit_does_not_trigger_check_or_change_source(self):
        s=self.session()
        action=self.region_action(s)
        action['expected_candidate_id']='0'*64
        before=s.candidate.candidate_id
        result=process_reply(s,dict(discussion='Guarded edit.',operation=action),lambda v:1000,[])
        self.assertFalse(result['operations'][0]['result']['accepted'])
        self.assertFalse(result['policy_check']['executed'])
        self.assertEqual(s.candidate.candidate_id,before)


if __name__=='__main__':
    unittest.main()
