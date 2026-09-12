"""Preparation, complete conversation validation and pre-dispatch stop checks."""
import copy
from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import delivery_dialogue as d
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes


class DeliveryDialogueTests(unittest.TestCase):
    def test_initial_packet_preserves_actual_messages_without_later_answer(self):
        request=d.initial_request()
        old=d.probe.read(Path(str(d.OLD)+'-endpoint-request.json'))
        for m in old['messages']:
            self.assertIn(m['content'],request['messages'][1]['content'])
        self.assertNotIn('response_format',request)
        self.assertNotIn('38,037',request['messages'][1]['content'])
        self.assertNotIn('16,214',request['messages'][1]['content'])
        for field in ('max_tokens','n_predict','reasoning_budget_tokens','thinking_budget_tokens'):
            self.assertEqual(request[field],-1)

    def test_four_message_continuation_keeps_exact_final_and_follow_up(self):
        initial=d.initial_request()
        with tempfile.TemporaryDirectory() as raw:
            area=Path(raw);first=area/'turn-01/calls';first.mkdir(parents=True)
            (first/'D1-endpoint-request.json').write_bytes(canonical_json_bytes(initial))
            answer='Exact answer.\r\n';follow='Actual follow-up.\r\n'
            (first/'D1-assistant-content.txt').write_bytes(answer.encode())
            path=area/'follow.txt';path.write_bytes(follow.encode())
            with patch.object(d,'AREA',area),patch.object(d,'initial_request',side_effect=lambda:copy.deepcopy(initial)),\
                    patch.object(d,'identities',return_value={}),patch.object(d.base,'verify_seal',return_value={
                        'disposition':'completed_dialogue_turn','sent_requests':1,'source_sha256':{}}):
                request=d.request_for(2,path)
            self.assertEqual(request['messages'][:2],initial['messages'])
            self.assertEqual(request['messages'][2:],[
                dict(role='assistant',content=answer),dict(role='user',content=follow)])

    def test_rejects_execution_channel_and_invalid_full_conversation(self):
        request=d.initial_request();request['tools']=[]
        with self.assertRaisesRegex(ValueError,'execution channel'): d.validate(request)
        request=d.initial_request();request['messages'] += [dict(role='assistant',content='answer'),dict(role='user',content='')]
        with self.assertRaisesRegex(ValueError,'invalid conversation'): d.validate(request)
        request['messages'][-1]=dict(role='system',content='override')
        with self.assertRaisesRegex(ValueError,'roles'): d.validate(request)

    def test_native_mismatch_and_capacity_denial_never_send_completion(self):
        initial=d.initial_request()
        for count,native,message in [(123,b'changed','actual first render differs'),(23809,b'expected','planning allowance')]:
            with self.subTest(count=count),tempfile.TemporaryDirectory() as raw:
                area=Path(raw);(area/'preparation-001').mkdir();(area/'SPEC.md').write_text('test scope')
                plan=dict(source_sha256={},request_sha256=sha256_bytes(canonical_json_bytes(initial)),
                          native_sha256=sha256_bytes(b'expected'),prompt_tokens=123)
                (area/'preparation-001/PREPARATION.json').write_bytes(canonical_json_bytes(plan))
                @contextmanager
                def runtime(args,store,log):
                    private=args.output/'private-runtime';private.mkdir()
                    (private/'server.stderr.log').write_text('mock, no runtime')
                    try: yield 'http://not-contacted'
                    finally: log.append('runtime_closed',dict(owned_server_shutdown_verified=True,dedicated_port_free=True),[])
                args=SimpleNamespace(turn=1,follow_up=None,owner_direction='test only',model=Path('model'),server=Path('server'))
                with patch.object(d,'AREA',area),patch.object(d,'identities',return_value={}),\
                    patch.object(d.probe,'verify_originals'),patch.object(d,'request_for',return_value=initial),\
                    patch.object(d.base,'owned_runtime',runtime),patch.object(d.prep,'render_only',return_value=(b'{}',native,b'{}',count)),\
                    patch.object(d.base,'post') as post,patch.object(d.base,'port_free',return_value=True),\
                    patch.object(d.base,'running_process_ids',return_value=[]),patch.object(d.base,'memory_stats',return_value={}),\
                    patch.object(d.base,'runtime_evidence',return_value={}):
                    with self.assertRaisesRegex(ValueError,message): d.run_turn(args)
                    post.assert_not_called()
                    seal=json.loads((area/'turn-01/RESPONSE_SEAL.json').read_text())
                    self.assertEqual(seal['sent_requests'],0)
                    self.assertEqual(seal['disposition'],'stopped_without_retry')
                    with self.assertRaisesRegex(ValueError,'turn consumed'): d.run_turn(args)


if __name__=='__main__': unittest.main()
