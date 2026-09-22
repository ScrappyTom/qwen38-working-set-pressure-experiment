"""CPU-only adapter checks; subprocess/native dispatch is forbidden throughout."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

AREA=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(AREA))
import execution_task as task
import run_configparser as run
import run_uncoached_contribution as runner
from working_set_exp import working_view
from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes,load_json_strict,sha256_bytes,sha256_file
from working_set_exp.observations import ObservationStore


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.no_process=patch('subprocess.Popen',side_effect=AssertionError('No subprocess permitted in CPU test'))
        self.no_process.start()
        self.addCleanup(self.no_process.stop)
        self.no_post=patch.object(task.host.base.base,'post',side_effect=AssertionError('No endpoint permitted in CPU test'))
        self.no_post.start()
        self.addCleanup(self.no_post.stop)

    def test_exact_original_entry_limits_and_empty_understanding(self):
        session=task.Task().initial_session();view=session.view()
        self.assertEqual(session.candidate,task.original.starting_candidate())
        self.assertEqual(sha256_bytes(session.task.encode()),task.original.TASK_SHA)
        self.assertEqual(len(session.candidate.files),10)
        self.assertEqual(sum(len(raw) for _,raw in session.candidate.files),337239)
        self.assertEqual(session.candidate.max_file_bytes,1048576)
        self.assertEqual((session.request_limit,session.call_limit),(40,80))
        self.assertEqual((session.pairs,session.ranges,session.saved),([],[],{}))
        self.assertEqual((session.requests_used,session.starting_archive_length),(0,0))
        self.assertIsNone(session.working_account());self.assertEqual(session.edit_checks,{})
        self.assertFalse(view['verification']['submission']['eligible'])
        self.assertEqual(session.checkers,{'public':task.original.checker()})
        self.assertIs(session.assessment_api,task.original.reports)

    def test_actual_request_has_only_original_task_and_empty_state(self):
        module=task.Task();session=module.initial_session();adapter=runner.Adapter(module)
        request=adapter.request_for(session.view())
        self.assertEqual(len(request['messages']),2)
        self.assertEqual(json.loads(request['messages'][1]['content']),
                         dict(workspace=session.view(),preceding_operation_feedback=[]))
        self.assertEqual(request['seed'],961221)
        self.assertEqual(request['chat_template_kwargs'],dict(enable_thinking=True,reasoning_effort='medium'))
        self.assertEqual(task.ACTOR['budget'],-1)
        self.assertEqual(task.ACTOR['context']-task.ACTOR['generation_reserve'],23808)
        self.assertNotIn('response_format',request)
        self.assertEqual(request['grammar'],task.response_constraints()['grammar'])
        text='\n'.join(m['content'] for m in request['messages'])
        self.assertNotIn('REFERENCE_EDITS',text)
        self.assertNotIn('reference-candidate',text)
        self.assertNotIn('vacuous_added_test',text)
        self.assertEqual(session.view()['working_set']['sources'],[])
        expected=task.expected_native(request)  # Local template expectation only.
        self.assertIsInstance(expected,bytes)
        self.assertTrue(expected.endswith(b'<think>\n'))

    def test_public_only_forms_and_literal_decode_without_combined_check(self):
        module=task.Task();session=module.initial_session();cid=session.candidate.candidate_id
        schema=module.reply_schema()['json_schema']['schema']
        good=dict(discussion='',operation=dict(action='check',check_id='public',expected_candidate_id=cid))
        working_view.validate(good,schema)
        for bad in ({**good,'check_after':'public'},
                    dict(discussion='',operation=dict(action='check',check_id='tests',expected_candidate_id=cid))):
            with self.assertRaises(ValueError):working_view.validate(bad,schema)
        header=dict(discussion='',operation=dict(action='replace_region',region='SRC-'+'a'*64,expected_candidate_id=cid))
        literal=json.dumps(header,separators=(',',':'))+'\nSOURCE\nvalue = "\\n"\n'
        decoded=task.decode_reply(literal)
        self.assertEqual(decoded['operation']['new'],'value = "\\n"\n')
        working_view.validate(decoded,schema)
        reference=module.operating_reference()
        self.assertIn('edits do not trigger checks',reference)
        self.assertNotIn('Each declared fault target',reference)
        self.assertIn('expected failure is successful regression detection',reference)

    def test_new_snapshot_preserves_large_file_policy_and_applied_change(self):
        module=task.Task();session=module.initial_session()
        source=session.execute(dict(action='read',path='Lib/configparser.py',start_line=1,end_line=1),lambda v:0)['source']
        session.mark_delivered(session.view())
        old=source['content'];self.assertTrue(old.startswith('"""'))
        action=dict(action='patch',path=source['path'],old=old,
            new=old.rstrip('\n')+' Qualification-only snapshot probe.\n',
            expected_candidate_id=session.candidate.candidate_id,expected_file_sha256=source['file_sha256'])
        result=session.execute(action,lambda v:0)
        self.assertTrue(result['accepted']);self.assertIn('applied_diff',result)
        self.assertEqual(session.candidate.max_file_bytes,1048576)
        with tempfile.TemporaryDirectory(dir=AREA/'tests') as temp:
            folder=Path(temp);store=ArtifactStore(folder)
            log=runner.RunLog(folder/'records.jsonl','cpu-snapshot-only',task_module=module)
            loop=runner.Loop(folder,store,log,task_module=runner.Adapter(module),health=lambda:{})
            loop.snapshot(session,'cpu')
            saved=load_json_strict((folder/'cpu-candidate.json').read_bytes())
            restored=Candidate.create({r['path']:r['content_utf8'].encode() for r in saved['files']},
                                      max_file_bytes=saved['max_file_bytes'])
            self.assertEqual(restored,session.candidate)
            state=load_json_strict((folder/'cpu-state.json').read_bytes())
            self.assertEqual(state['request_limit'],40)
            self.assertEqual(state['call_limit'],80)
            self.assertIn(task.navigation.SETTING,state['last'])
            self.assertIn(task.navigation.CHANGE_SETTING,state['last'])
            self.assertEqual(state['pairs'][-1]['result']['applied_diff'],result['applied_diff'])

    def test_existing_observation_replay_stays_exact_and_reports_current_failures(self):
        folder=task.CPU_QUALIFIED/'original/adapted/observations'
        paths=sorted(p for p in folder.rglob('*') if p.is_file())
        before={str(p):sha256_file(p) for p in paths}
        session=task.Task().initial_session()
        session.observations=ObservationStore(folder,replay=True)
        result=session.execute(dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),lambda v:0)
        self.assertTrue(result['accepted']);self.assertFalse(result['passed'])
        immediate=session.view()
        assessment=immediate['verification']['checks']['public']['assessment']
        self.assertEqual(immediate['latest_feedback']['result']['report'],assessment)
        self.assertTrue(assessment['failed_criteria'])
        self.assertFalse(immediate['verification']['submission']['eligible'])
        session.execute(dict(action='search',path='Lib/configparser.py',query='ParsingError',offset=0,limit=1),lambda v:0)
        self.assertEqual(session.view()['verification']['checks']['public']['assessment'],assessment)
        self.assertEqual({str(p):sha256_file(p) for p in paths},before)

    def test_cpu_prerequisite_verifies_frozen_source_and_all_outputs(self):
        bindings=task.cpu_bindings()
        self.assertIn((task.CPU_QUALIFIED/'SEAL.json').relative_to(task.ROOT).as_posix(),bindings)
        self.assertEqual(len(bindings),196)

    def test_exact_decoder_qualification_is_reused_without_execution(self):
        bindings=task.decoder_reuse_bindings()
        self.assertEqual(len(bindings),30)
        name=(task.host.AREA/'native-005/reply.gbnf').relative_to(task.ROOT).as_posix()
        self.assertEqual(bindings[name],sha256_bytes(task.response_constraints()['grammar'].encode()))

    def test_seal_guard_rejects_status_source_output_duplicate_and_escape(self):
        for problem in ('status','source','output','duplicate','escape'):
            with self.subTest(problem=problem),tempfile.TemporaryDirectory(dir=AREA/'tests') as temp:
                root=Path(temp);folder=root/'qualified';folder.mkdir()
                source=root/'source.py';source.write_text('x=1\n')
                result=folder/'RESULTS.json';result.write_bytes(canonical_json_bytes(dict(completion_requests=0)))
                rows=[dict(path='RESULTS.json',size_bytes=result.stat().st_size,sha256=sha256_file(result))]
                expected={'source.py':sha256_file(source)}
                seal=dict(status='qualified_cpu_only',completion_requests=0,source_sha256=expected,
                          files=rows,aggregate_sha256=sha256_bytes(canonical_json_bytes(rows)))
                if problem=='status':seal['status']='failed_preserved'
                if problem=='source':source.write_text('x=2\n')
                if problem=='output':result.write_text('{}')
                if problem=='duplicate':
                    seal['files']=rows+rows
                    seal['aggregate_sha256']=sha256_bytes(canonical_json_bytes(seal['files']))
                if problem=='escape':
                    seal['files']=rows+[dict(path='../source.py',size_bytes=source.stat().st_size,sha256=sha256_file(source))]
                    seal['aggregate_sha256']=sha256_bytes(canonical_json_bytes(seal['files']))
                (folder/'SEAL.json').write_bytes(canonical_json_bytes(seal))
                with self.assertRaises(AssertionError):
                    task.verified_package(folder,expected,status='qualified_cpu_only',root=root)

    def test_missing_native_gate_stops_preparation_before_runtime_or_directory(self):
        module=task.Task('999')
        with (patch.object(task,'native_bindings',side_effect=FileNotFoundError('Native qualification pending')),
              patch.object(run.RUNTIME,'owned_runtime',side_effect=AssertionError('Runtime must not start')) as runtime):
            with self.assertRaises(FileNotFoundError):run.prepare(module)
            runtime.assert_not_called()
        self.assertFalse(module.PACKAGE.exists())

    def test_version_path_cannot_escape_finite_attempt_directory(self):
        for version in ('../001','1','0001','a01'):
            with self.assertRaises(ValueError):task.Task(version)


if __name__=='__main__':unittest.main()
