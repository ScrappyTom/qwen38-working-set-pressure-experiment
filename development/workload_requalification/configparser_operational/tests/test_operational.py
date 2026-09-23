"""CPU adapter boundaries; no runtime, model or checker execution."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

AREA=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(AREA))
import bootstrap  # noqa: F401
import operational_task as task
import run_task
import run_uncoached_contribution as runner
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file
from working_set_exp.observations import ObservationStore


class OperationalTests(unittest.TestCase):
    def setUp(self):
        for target in ('subprocess.Popen','subprocess.run','urllib.request.urlopen'):
            guard=patch(target,side_effect=AssertionError('CPU test forbids execution'))
            guard.start();self.addCleanup(guard.stop)

    def test_original_empty_entry_and_only_protocol_changed(self):
        module=task.Task();session=module.initial_session()
        old=task.previous.Task();previous=old.initial_session()
        self.assertEqual(task.snapshot(session),task.snapshot(previous))
        self.assertEqual(session.candidate,previous.candidate)
        self.assertEqual(session.checkers,previous.checkers)
        self.assertEqual(sha256_bytes(session.task.encode()),task.original.TASK_SHA)
        self.assertEqual(sum(len(x) for _,x in session.candidate.files),337239)
        self.assertEqual(session.candidate.max_file_bytes,1048576)
        self.assertEqual((session.request_limit,session.call_limit),(40,80))
        self.assertEqual(session.edit_checks,{})
        self.assertIsNone(session.working_account())
        self.assertEqual((AREA/'SYSTEM.txt').read_bytes(),(old.AREA/'SYSTEM.txt').read_bytes())
        a=runner.Adapter(old).request_for(previous.view());b=runner.Adapter(module).request_for(session.view())
        self.assertEqual(a['messages'][1],b['messages'][1])
        self.assertEqual({k:v for k,v in a.items() if k not in ('messages','grammar')},
                         {k:v for k,v in b.items() if k not in ('messages','grammar')})
        self.assertNotEqual(a['grammar'],b['grammar'])
        self.assertIn('Discussion alone ends the run',a['messages'][0]['content'])
        self.assertNotIn('Discussion alone ends the run',b['messages'][0]['content'])
        self.assertIn('discussion alone is not an accepted reply',b['messages'][0]['content'])
        self.assertEqual(module.reply_schema(),session.reply_schema())

    def test_saved_grammar_proof_is_exact_and_complete(self):
        bindings=task.decoder_reuse_bindings()
        name=(task.DECODER/'reply.gbnf').relative_to(task.ROOT).as_posix()
        self.assertEqual(bindings[name],sha256_bytes(task.response_constraints()['grammar'].encode()))
        self.assertIn((task.DECODER/'SEAL.json').relative_to(task.ROOT).as_posix(),bindings)
        self.assertEqual(sha256_file(task.DECODER/'SEAL.json'),task.DECODER_SEAL_SHA)

    def test_changed_decoder_proof_cannot_be_reused(self):
        original=task.sha256_file
        with patch.object(task,'sha256_file',side_effect=lambda p:'0'*64 if p==task.DECODER/'SEAL.json' else original(p)):
            with self.assertRaisesRegex(AssertionError,'proof changed'):task.decoder_reuse_bindings()

    def test_discussion_rejects_without_effect_and_historical_contract_stays(self):
        module=task.Task();session=module.initial_session();before=canonical_json_bytes(task.snapshot(session))
        text='{"discussion":"I will read the parser."}'
        with self.assertRaises(ValueError):module.decode_reply(text)
        with self.assertRaises(ValueError):module.process_reply(session,json.loads(text),lambda view:1000,[])
        self.assertEqual(before,canonical_json_bytes(task.snapshot(session)))
        self.assertEqual(task.previous.decode_reply(text),json.loads(text))

    def test_optional_account_source_and_scope_forms(self):
        module=task.Task();session=module.initial_session();cid=session.candidate.candidate_id
        header=dict(discussion='Save.',account='Untested.',operation=dict(action='replace_region',region='SRC-'+'a'*64,expected_candidate_id=cid))
        source='x = "\\n"\n# SOURCE\n'
        self.assertEqual(module.decode_reply(json.dumps(header)+'\nSOURCE\n'+source)['operation']['new'],source)
        self.assertEqual(module.decode_reply('{"discussion":"Clear.","account":""}')['account'],'')
        for value in [dict(discussion='',operation=dict(action='check',check_id='tests',expected_candidate_id=cid)),
                      dict(discussion='',operation=dict(action='check',check_id='public',expected_candidate_id=cid),check_after='public')]:
            with self.assertRaises(ValueError):module.decode_reply(json.dumps(value))

    def test_existing_observation_replay_without_checker_execution(self):
        session=task.Task().initial_session()
        session.observations=ObservationStore(task.CPU_QUALIFIED/'original/adapted/observations',replay=True)
        result=session.execute(dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),lambda view:0)
        self.assertTrue(result['executed']);self.assertFalse(result['passed'])
        view=session.view()
        self.assertEqual(view['latest_feedback']['result']['report'],view['verification']['checks']['public']['assessment'])
        self.assertFalse(view['verification']['submission']['eligible'])

    def test_missing_native_gate_prevents_prepare(self):
        module=task.Task('999')
        with (patch.object(task,'qualification_sources',return_value={}),
              patch.object(task,'native_bindings',side_effect=FileNotFoundError('Pending')),
              patch.object(run_task.execution.RUNTIME,'owned_runtime',side_effect=AssertionError('Must not launch')) as runtime):
            with self.assertRaises(FileNotFoundError):run_task.execution.prepare(module)
            runtime.assert_not_called()
        self.assertFalse(module.PACKAGE.exists())

    def test_template_delegates_only_constraint_change(self):
        request=runner.Adapter(task.Task()).request_for(task.Task().initial_session().view())
        before=copy.deepcopy(request)
        with patch.object(task.previous,'expected_native',return_value=b'template') as delegated:
            self.assertEqual(task.expected_native(request),b'template')
        forwarded=delegated.call_args.args[0]
        self.assertEqual(forwarded['grammar'],task.previous.response_constraints()['grammar'])
        forwarded['grammar']=request['grammar'];self.assertEqual(forwarded,request)
        self.assertEqual(request,before)


if __name__=='__main__':unittest.main()
