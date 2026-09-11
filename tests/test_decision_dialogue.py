"""Check the new conversation boundary without model inference."""
import argparse
from contextlib import contextmanager
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import decision_dialogue as d
from test_investigation_loop import mocked_render,model_reply
from working_set_exp.jsonutil import canonical_json_bytes,load_json_strict


class DecisionDialogueTests(unittest.TestCase):
    def setUp(self):
        self.req=d.initial_request()
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.area=Path(self.temp.name)
        (self.area/"SPEC.md").write_text("mock scope",encoding="utf-8")

    def test_original_messages_exact_without_original_answer_or_action_channel(self):
        old=load_json_strict((d.PILOT/"calls/S01-009-endpoint-request.json").read_bytes())
        for message in old["messages"]:
            self.assertIn(message["content"],self.req["messages"][1]["content"])
        original=(d.PILOT/"calls/S01-009-assistant-content.txt").read_text()
        self.assertNotIn(original,self.req["messages"][1]["content"])
        self.assertFalse(any(k in self.req for k in ("response_format","tools","functions")))
        self.assertEqual(self.req["seed"],42)
        self.assertTrue(all(self.req[k]==-1 for k in ("max_tokens","n_predict","reasoning_budget_tokens","thinking_budget_tokens")))

    def test_adaptive_turn_retains_exact_answer_not_private_thinking_and_rejects_drift(self):
        first=self.area/"turn-01/calls";first.mkdir(parents=True)
        (first/"D1-endpoint-request.json").write_bytes(canonical_json_bytes(self.req))
        answer="The original answer.\nWith its original second line."
        (first/"D1-assistant-content.txt").write_bytes(answer.encode())
        (first/"D1-assistant-reasoning.txt").write_text("PRIVATE_NEVER_CARRY",encoding="utf-8")
        follow=self.area/"FOLLOW_UP.txt";follow.write_text("An adaptive clarification.",encoding="utf-8")
        with mock.patch.object(d,"AREA",self.area),mock.patch.object(d,"initial_request",return_value=self.req),mock.patch.object(d,"identities",return_value={}),mock.patch.object(d.base,"verify_seal",return_value=dict(disposition="completed_dialogue_turn",sent_requests=1,source_sha256={})):
            request=d.request_for(2,follow)
            self.assertEqual(request["messages"][2],dict(role="assistant",content=answer))
            self.assertEqual(request["messages"][3]["content"],follow.read_text())
            self.assertNotIn("PRIVATE_NEVER_CARRY",canonical_json_bytes(request).decode())
            (first/"D1-endpoint-request.json").write_text("{}",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"origin differs"):d.request_for(2,follow)

    def run_mocked(self,render,post):
        args=argparse.Namespace(turn=1,follow_up=None,owner_direction="test-only",model=Path("mock.gguf"),server=Path("mock.exe"))
        @contextmanager
        def runtime(args,store,log):
            yield "mock"
            log.append("runtime_closed",dict(owned_server_shutdown_verified=True,dedicated_port_free=True),[])
        with mock.patch.object(d,"AREA",self.area),mock.patch.object(d,"request_for",return_value=self.req),mock.patch.object(d,"identities",return_value={}),mock.patch.object(d.base,"owned_runtime",side_effect=runtime),mock.patch.object(d.prep,"render_only",side_effect=render),mock.patch.object(d.prep,"health",return_value={}),mock.patch.object(d.base,"post",side_effect=post),mock.patch.object(d.base,"port_free",return_value=True),mock.patch.object(d.base,"running_process_ids",return_value=()):
            d.run_turn(args)

    def test_oversized_input_is_preserved_without_dispatch_or_replacement(self):
        def render(url,request):
            rows=mocked_render(url,request)
            return (*rows[:3],d.prep.INPUT_CEILING+1)
        post=mock.Mock(side_effect=AssertionError("no completion allowed"))
        with self.assertRaisesRegex(ValueError,"capacity"):self.run_mocked(render,post)
        post.assert_not_called()
        seal=load_json_strict((self.area/"turn-01/RESPONSE_SEAL.json").read_bytes())
        self.assertEqual(seal["disposition"],"stopped_without_retry")
        self.assertEqual(seal["sent_requests"],0)
        self.assertTrue((self.area/"turn-01/calls/D1-rendered-prompt.txt").exists())
        with self.assertRaisesRegex(ValueError,"consumed"):self.run_mocked(render,post)

    def test_incomplete_prose_is_saved_without_tool_execution(self):
        raw=model_reply(self.req,{},finish="length",content="incomplete explanatory answer")
        with self.assertRaisesRegex(ValueError,"incomplete final response"):
            self.run_mocked(mocked_render,lambda *a:raw)
        folder=self.area/"turn-01/calls"
        self.assertEqual((folder/"D1-endpoint-response.json").read_bytes(),raw)
        host=load_json_strict((folder/"D1-host-result.json").read_bytes())
        self.assertFalse(host["executed"] or host["candidate_mutated"] or host["tool_execution_enabled"])
        self.assertEqual(d.base.verify_seal(self.area/"turn-01")["disposition"],"stopped_without_retry")


if __name__=="__main__":unittest.main()
