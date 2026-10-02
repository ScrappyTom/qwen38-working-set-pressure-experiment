"""Exact imported-world and contribution boundaries; no model/GPU requests."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import compiler_task as task
import capture_bridge
import qualification_route as route
from working_set_exp import working_view
from working_set_exp.accounted_contribution import process_reply
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict


class CompilerEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='compiler-entry-test-')
        self.addCleanup(self.temp.cleanup)
        self.session = task.initial_session(Path(self.temp.name))

    def act(self, action, measure=lambda view: 0):
        self.session.mark_delivered(self.session.view())
        self.session.begin_request()
        return process_reply(self.session, {'discussion':'CPU engineering boundary check.', 'operation':action},
                             measure, [])['operations'][-1]['result']

    def test_entry_is_exact_original_without_oracle_or_invented_actions(self):
        candidate, checker, assignment, inventory, bodies = task.original_material()
        self.assertEqual(self.session.candidate, candidate)
        self.assertEqual(self.session.checkers, {'public': checker})
        self.assertEqual(self.session.task, assignment)
        self.assertEqual(self.session.pairs, [])
        self.assertEqual(self.session.ranges, [])
        self.assertEqual(self.session.saved, {})
        self.assertIsNone(self.session.working_account())
        self.assertEqual((self.session.requests_used, self.session.calls_used), (0,0))
        self.assertEqual((self.session.request_limit, self.session.call_limit), (40,100))
        value = self.session.view()
        entries = value['imported_observations']['entries']
        self.assertEqual([r['handle'] for r in entries], list(inventory))
        self.assertTrue(all(r['observed_candidate_id'] == task.STARTING_ID for r in entries))
        self.assertFalse(any(r['shown_complete'] or r['latest_acquisition_result'] for r in entries))
        self.assertNotIn('EXPECTED_REPORT', canonical_json_bytes(value).decode())
        self.assertNotIn('-log(r)', canonical_json_bytes(value).decode())
        self.assertEqual([len(raw) for raw in bodies.values()], [9228,9168,9180])
        self.assertEqual(candidate.file_map['reports/incident.json'], b'{"builds": []}\n')

    def test_imported_decoder_only_adds_the_declared_form(self):
        schema = task.Task().reply_schema()['json_schema']['schema']
        good = {'discussion':'Retrieve incident evidence.',
                'operation':{'action':'reopen_observation','handle':'OBS-0001'}}
        working_view.validate(good,schema)
        self.assertEqual(task.Task().decode_reply(canonical_json_bytes(good).decode()),good)
        for changes in ({'offset':0},{'handle':'CHK-0001'},{'handle':'OBS-001'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                working_view.validate({**good,'operation':{**good['operation'],**changes}},schema)
        text = task.Task().operating_reference()
        self.assertIn('without rerunning', text.replace('\n',' '))
        self.assertIn('supply no source-edit authority',text.replace('\n',' '))
        self.assertIn('partial serialized RES page',text.replace('\n',' '))

    def test_acquisition_is_exact_retrieval_and_not_source_or_check_authority(self):
        before = self.session.candidate
        result = self.act({'action':'reopen_observation','handle':'OBS-0001'})
        manifest, raw = self.session.imported_record('OBS-0001')
        self.assertEqual(result['content_utf8'].encode(),raw)
        self.assertEqual(result['observed_candidate_id'],task.STARTING_ID)
        self.assertEqual(result['sha256'],manifest['sha256'])
        self.assertEqual(result['exact_result_handle'],'RES-0001')
        self.assertTrue(result['retrieval_only'])
        self.assertIs(result['source_edit_authority'],False)
        self.assertEqual(self.session.candidate,before)
        self.assertEqual(self.session.ranges,[])
        self.assertIsNone(self.session.check_state())
        self.session.mark_delivered(self.session.view())
        self.assertEqual(self.session.delivered_sources,[])
        rejected = self.act({'action':'patch','path':route.TARGET,'old':route.OLD,'new':route.GOOD,
            'expected_candidate_id':before.candidate_id,
            'expected_file_sha256':before.file_sha256(route.TARGET)})
        self.assertFalse(rejected['accepted'])
        self.assertEqual(self.session.candidate,before)

    def test_unavailable_valid_handle_is_truthful_rejection_and_does_not_rebind(self):
        result = self.act({'action':'reopen_observation','handle':'OBS-9999'})
        self.assertFalse(result['accepted'])
        self.assertIn('unavailable',result['error'])
        self.assertEqual(self.session.candidate.candidate_id,task.STARTING_ID)
        self.assertFalse(any(r['shown_complete'] for r in self.session.view()['imported_observations']['entries']))

    def test_complete_group_preserves_original_bindings_across_source_edit(self):
        acquired=[]
        for handle in ('OBS-0001','OBS-0002','OBS-0003'):
            self.act({'action':'reopen_observation','handle':handle})
            acquired.append(f'RES-{len(self.session.pairs):04d}')
        selected=self.act({'action':'work_on','sources':[{'path':route.TARGET,'start_line':1,'end_line':0}],
                           'results':acquired})
        self.assertTrue(selected['accepted'])
        expected={handle:self.session.imported_record(handle)[1] for handle in ('OBS-0001','OBS-0002','OBS-0003')}
        self.assertEqual(route.delivered_capture_bodies(self.session.view()),expected)
        before=self.session.candidate
        result=self.act({'action':'patch','path':route.TARGET,'old':route.OLD,'new':route.GOOD,
            'expected_candidate_id':before.candidate_id,
            'expected_file_sha256':before.file_sha256(route.TARGET)})
        self.assertTrue(result['accepted'])
        self.assertNotEqual(self.session.candidate.candidate_id,task.STARTING_ID)
        self.assertEqual(route.delivered_capture_bodies(self.session.view()),expected)
        self.assertTrue(all(r['shown_complete'] and r['observed_candidate_id']==task.STARTING_ID
                            for r in self.session.view()['imported_observations']['entries']))
        self.act({'action':'work_on','sources':[],'results':[]})
        self.assertFalse(any(r['shown_complete'] for r in self.session.view()['imported_observations']['entries']))
        self.assertEqual(load_json_strict(self.session.payload('RES-0001'))['content_utf8'].encode(),expected['OBS-0001'])

    def test_partial_serialized_page_is_not_a_complete_capture(self):
        self.act({'action':'reopen_observation','handle':'OBS-0001'})
        full = self.session.payload('RES-0001')
        # Synthetic presentation cost exercises paging control flow only. The
        # runner separately measures real whole-input native costs.
        def measure(view):
            last=view.get('latest_feedback')
            result=last['result'] if last else {}
            return 23000+len(result.get('exact_utf8','').encode())
        result=self.act({'action':'reopen_result','handle':'RES-0001','offset':0},measure)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['exact_utf8'].encode(),full[:result['next_offset']])
        self.assertIsNotNone(result['next_offset'])
        self.assertEqual(route.delivered_capture_bodies(self.session.view()),{})
        self.assertFalse(self.session.view()['imported_observations']['entries'][0]['shown_complete'])
        self.assertEqual(self.session.candidate.candidate_id,task.STARTING_ID)

    def test_bindings_and_checkpoint_cannot_silently_change_imported_world(self):
        candidate,checker,assignment,inventory,bodies=task.original_material()
        corrupted=dict(bodies);corrupted['OBS-0001']=corrupted['OBS-0001'].replace(b'parsed input module',b'parsed other module')
        with self.assertRaises(ValueError):
            capture_bridge.Session(candidate,{'public':checker},assignment,edit_checks={},
                imported_observations=inventory,imported_bodies=corrupted)
        snapshot=capture_bridge.capture_snapshot(self.session)
        self.assertIs(capture_bridge.restore_capture_state(self.session,snapshot),self.session)
        altered=copy.deepcopy(snapshot);altered['inventory'][0]['candidate_id']='a'*64
        with self.assertRaises(ValueError):capture_bridge.restore_capture_state(self.session,altered)
        clone=self.session.clone()
        self.assertEqual(capture_bridge.capture_snapshot(clone),snapshot)

    def test_capture_derived_report_uses_trees_not_selection_labels_or_checker(self):
        _,_,_,_,bodies=task.original_material()
        report=route.derive_report(bodies)
        self.assertEqual(report['builds'][0]['changed_functions'],['_normal_dist_inv_cdf'])
        self.assertEqual(report['builds'][1]['changed_functions'],['_normal_dist_inv_cdf','weibullvariate'])
        self.assertEqual(report['builds'][0]['first_change'],
            {'function':'_normal_dist_inv_cdf','before':'-log(r)','after':'log(r)'})
        altered=dict(bodies)
        record=load_json_strict(altered['OBS-0003']);record['compile_request']['functions']=[]
        altered['OBS-0003']=canonical_json_bytes(record)
        self.assertEqual(route.derive_report(altered),report)
        del altered['OBS-0001']
        with self.assertRaises(ValueError):route.derive_report(altered)

    def test_safe_captured_ast_compatibility_rejects_execution_and_unknown_fields(self):
        for text in ("__import__('os').getcwd()", 'UnknownNode()',
                     'Module(body=[x for x in []], type_ignores=[])',
                     'Module(body=[], type_ignores=[], surprise=1)',
                     'Module(body=[FunctionDef(type_params=[1])], type_ignores=[])'):
            with self.subTest(text=text), self.assertRaises((ValueError,TypeError)):
                route.decode_tree(text)
        _,_,_,_,bodies=task.original_material()
        # Native 3.12 empty type_params are preserved in custody and explicitly
        # qualified as empty compatibility fields in the evaluator parser only.
        text=load_json_strict(bodies['OBS-0001'])['ast_dump']
        self.assertIn('type_params=[]',text)
        self.assertIsNotNone(route.decode_tree(text))

    def test_actual_tools_complete_and_correct_failed_check_without_model_inference(self):
        for correction in (False,True):
            with self.subTest(correction=correction):
                session=task.initial_session(Path(self.temp.name)/str(correction))
                value=route.qualify_contribution(session,lambda view:0,correction=correction)
                self.assertTrue(session.submitted)
                self.assertEqual(value['completion_requests'],0)
                self.assertEqual(value['scripted_requests'],12 if correction else 10)
                checks=[op['result']['passed'] for row in value['snapshots'] for op in row['outcome']['operations']
                        if op['action']['action']=='check']
                self.assertEqual(checks,[False,True] if correction else [True])
                check=next(pair['result'] for pair in reversed(session.pairs) if pair['response']['action']=='check')
                self.assertIn('26/26',session.observations.directory(check['observation']).joinpath('stdout.bin').read_text())


if __name__=='__main__':unittest.main()
