"""Exercise the entire continuation dispatch with mocked inference."""
import argparse,copy
from contextlib import contextmanager
from pathlib import Path
import sys,tempfile,unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import decision_follow_up as run
from test_investigation_loop import mocked_render,model_reply
from working_set_exp.jsonutil import load_json_strict,canonical_json_bytes


class DecisionFollowUpTests(unittest.TestCase):
    def test_full_continuation_dispatch_preserves_answer_followup_and_settings(self):
        request=run.validated_request(run.AREA/"FOLLOW_UP.txt")
        before=canonical_json_bytes(request)
        first=(run.AREA/"turn-01/calls/D1-assistant-content.txt").read_bytes()
        self.assertEqual(request["messages"][2]["content"].encode(),first)
        self.assertEqual(len(request["messages"]),4)
        with tempfile.TemporaryDirectory() as tmp:
            area=Path(tmp);(area/"SPEC.md").write_text("mock scope",encoding="utf-8")
            follow=area/"FOLLOW_UP.txt";follow.write_bytes(request["messages"][3]["content"].encode())
            args=argparse.Namespace(turn=2,follow_up=follow,owner_direction="test-only",model=Path("mock.gguf"),server=Path("mock.exe"))
            sent=[]
            def post(url,route,raw,timeout):
                self.assertEqual(route,"/v1/chat/completions");self.assertEqual(raw,before);sent.append(raw)
                return model_reply(request,{},content="A proposed clarification.")
            @contextmanager
            def runtime(args,store,log):
                yield "mock"
                log.append("runtime_closed",dict(owned_server_shutdown_verified=True,dedicated_port_free=True),[])
            with mock.patch.object(run,"AREA",area),mock.patch.object(run,"identities",return_value={}),mock.patch.object(run,"validated_request",return_value=request),mock.patch.object(run.base,"owned_runtime",side_effect=runtime),mock.patch.object(run.prep,"render_only",side_effect=mocked_render),mock.patch.object(run.prep,"health",return_value={}),mock.patch.object(run.base,"post",side_effect=post),mock.patch.object(run.base,"port_free",return_value=True),mock.patch.object(run.base,"running_process_ids",return_value=()):
                run.run_turn(args)
                self.assertEqual(len(sent),1)
                self.assertEqual(run.base.verify_seal(area/"turn-02")["disposition"],"completed_dialogue_turn")
                with self.assertRaisesRegex(ValueError,"consumed"):run.run_turn(args)
                self.assertEqual(len(sent),1)
            self.assertEqual(canonical_json_bytes(request),before)

    def test_extra_roles_or_changed_settings_are_rejected(self):
        original=run.validated_request(run.AREA/"FOLLOW_UP.txt")
        for mutate in (lambda r:r["messages"].append(dict(role="user",content="extra")),lambda r:r.update(max_tokens=10),lambda r:r.update(response_format={})):
            request=copy.deepcopy(original);mutate(request)
            with mock.patch.object(run.dialogue,"request_for",return_value=request):
                with self.assertRaises(ValueError):run.validated_request(run.AREA/"FOLLOW_UP.txt")


if __name__=="__main__":unittest.main()
