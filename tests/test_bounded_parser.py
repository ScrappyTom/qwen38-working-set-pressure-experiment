import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bounded_parser as task
import run_bounded_parser as run
from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes
from working_set_exp.working_session import WorkingSession


def fake_render(request,stem):
    native=task.expected_native(request)
    count=len(native)//4+1000
    return canonical_json_bytes(dict(prompt=native.decode())),native,canonical_json_bytes(dict(tokens=[0]*count)),count


class BoundedRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="bounded-host-test-")
        self.addCleanup(self.temp.cleanup)
        self.output=Path(self.temp.name)
        self.session=WorkingSession(Candidate.create({"app.py":b"value = 1\n"}),
            b"from app import value\nassert value == 2\n","Save a checked repair",call_limit=4)
        self.sent=[]

    def loop(self,selector,*,finish="stop",render=fake_render,source_check=lambda:None):
        def post(url,route,raw,timeout):
            self.assertEqual(route,"/v1/chat/completions")
            request=json.loads(raw)
            self.assertNotIn("MOCK_PRIVATE_EXPLANATION",raw.decode())
            self.sent.append(request)
            action=selector(json.loads(request["messages"][1]["content"]),len(self.sent))
            count=fake_render(request,"")[-1]
            return canonical_json_bytes(dict(choices=[dict(finish_reason=finish,message=dict(
                reasoning_content="MOCK_PRIVATE_EXPLANATION",content=canonical_json_bytes(action).decode() if action else ""))],
                usage=dict(prompt_tokens=count,completion_tokens=100,total_tokens=count+100,prompt_tokens_details=dict(cached_tokens=0)),
                timings=dict(cache_n=0)))
        return run.Loop(self.output,ArtifactStore(self.output),run.RunLog(self.output/"records.jsonl","offline-test"),
                        post=post,render=render,health=lambda:{},source_check=source_check)

    def test_whole_loop_large_action_exact_feedback_no_private_thinking(self):
        new="value = 2\n"+"# ordinary complete edit\n"*220
        def select(state,n):
            if n==1:
                return dict(action="read",path="app.py",start_line=1,end_line=0)
            if n==2:
                source=state["latest_feedback"]["result"]["source"]
                return dict(action="patch",path="app.py",old="value = 1\n",new=new,
                            expected_candidate_id=state["candidate_id"],expected_file_sha256=source["file_sha256"])
            self.assertEqual(state["working_set"]["sources"][0]["content"],new)
            return dict(action="check",check_id="public",expected_candidate_id=state["candidate_id"]) if n==3 else dict(action="submit",expected_candidate_id=state["candidate_id"])
        loop=self.loop(select)
        outcome=loop.execute(self.session)
        self.assertEqual(outcome["disposition"],"checked_submission")
        self.assertEqual(len(self.sent),4)
        self.assertGreater(len((self.output/"calls/C02-assistant-content.txt").read_bytes()),5000)
        self.assertEqual(self.session.candidate.file_map["app.py"],new.encode())
        records=verify_records(self.output/"records.jsonl",self.output)
        self.assertEqual(sum(r["record_type"]=="invocation_completed" for r in records),4)
        self.assertEqual((self.output/"diffs/EVT-0002.patch").read_text(),self.session.diffs[2])

    def test_incomplete_response_is_saved_without_execution_or_retry(self):
        loop=self.loop(lambda state,n:None,finish="length")
        before=self.session.candidate
        with self.assertRaisesRegex(ValueError,"incomplete response"):
            loop.invoke(self.session)
        self.assertEqual(len(self.sent),1)
        self.assertEqual(self.session.pairs,[])
        self.assertEqual(self.session.candidate,before)
        self.assertTrue((self.output/"calls/C01-endpoint-response.json").is_file())
        self.assertEqual((self.output/"calls/C01-assistant-reasoning.txt").read_text(),"MOCK_PRIVATE_EXPLANATION")

    def test_native_drift_stops_before_dispatch(self):
        def bad(request,stem):
            template,native,tokens,count=fake_render(request,stem)
            native+=b" extra instruction"
            return canonical_json_bytes(dict(prompt=native.decode())),native,tokens,count
        loop=self.loop(lambda state,n:{},render=bad)
        with self.assertRaisesRegex(ValueError,"native rendering differs"):
            loop.invoke(self.session)
        self.assertEqual(self.sent,[])

    def test_frozen_first_input_gate_precedes_dispatch(self):
        loop=self.loop(lambda state,n:{})
        loop.initial=dict(prompt_tokens=1,request_sha256="0"*64,native_sha256="0"*64)
        with self.assertRaisesRegex(ValueError,"first input differs"):
            loop.invoke(self.session)
        self.assertEqual(self.sent,[])

    def test_starting_work_archive_and_settings_are_explicit(self):
        session=task.initial_session()
        self.assertEqual(session.starting_archive_length,32)
        self.assertEqual(session.calls_used,0)
        self.assertEqual(session.call_limit,24)
        self.assertFalse(session.check_state()["passed"])
        self.assertTrue(session.check_state()["applies_to_current"])
        self.assertIsNone(session.last)
        request=task.request_for(session.view())
        old=task.original_request()
        for key in set(old)-{"messages","response_format"}:
            self.assertEqual(request[key],old[key])
        self.assertEqual(request["chat_template_kwargs"],dict(enable_thinking=True,reasoning_effort="xhigh"))
        self.assertEqual(len(session.view()["recent_activity"]),6)
        for edit in task.read(task.task.AREA/"REFERENCE_EDITS.json")["rows"][3:]:
            self.assertNotIn(edit["new"],request["messages"][1]["content"])


if __name__=="__main__":
    unittest.main()
