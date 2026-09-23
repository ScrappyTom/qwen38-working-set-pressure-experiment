import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bootstrap
import closure_task as study
import run_closure as runner
from working_set_exp.jsonutil import canonical_json_bytes

class Closure(unittest.TestCase):
    def test_exact_checkpoint_and_only_allowance_change(self):
        original=study.restore(extend=False);current=study.restore()
        a=study.snapshot(original);b=study.snapshot(current)
        self.assertEqual({k:v for k,v in a.items() if k not in ('request_limit','call_limit')},{k:v for k,v in b.items() if k not in ('request_limit','call_limit')})
        self.assertEqual((current.requests_used,current.calls_used,current.request_limit,current.call_limit),(24,34,26,38))
        self.assertEqual(study.candidate_bytes(current.candidate),study.candidate_bytes(original.candidate))
        self.assertTrue(current.check_state()['passed']);self.assertTrue(current.check_state()['applies_to_current'])
        self.assertEqual(len(current.pairs),73);self.assertEqual(current.starting_archive_length,39)
    def test_actual_pass_is_delivered_without_task_or_setting_changes(self):
        task=study.Task();s=task.initial_session();adapter=runner.runner.Adapter(task);request=adapter.request_for(s.view())
        old=study.read(study.OLD/'calls/C24-wire-request.json')
        self.assertEqual(request['messages'][0],old['messages'][0])
        self.assertEqual({k:v for k,v in request.items() if k!='messages'},{k:v for k,v in old.items() if k!='messages'})
        user=json.loads(request['messages'][-1]['content']);receipts=[*user['preceding_operation_feedback'],user['workspace']['latest_feedback']]
        operations=study.read(study.OLD/'calls/C24-host-result.json')['operations']
        for op in operations:self.assertTrue(any(r['result']==op['result'] for r in receipts))
        self.assertEqual(user['workspace']['task'],s.task)
        self.assertTrue(user['workspace']['verification']['submission']['eligible'])
    def test_stale_submission_rejected_and_actual_pass_remains(self):
        s=study.restore();before=study.candidate_bytes(s.candidate);a=runner.runner.Adapter(study.Task())
        result=study.process_reply(s,dict(discussion='offline stale guard qualification',operation=dict(action='submit',expected_candidate_id='0'*64)),lambda view:1000,a.preceding_feedback)
        self.assertFalse(result['operations'][-1]['result']['accepted']);self.assertFalse(s.submitted)
        self.assertEqual(before,study.candidate_bytes(s.candidate));self.assertTrue(s.check_state()['applies_to_current'])
        result=study.process_reply(s,dict(discussion='offline actual binding',operation=dict(action='submit',expected_candidate_id=s.candidate.candidate_id)),lambda view:1000,a.preceding_feedback)
        self.assertTrue(result['operations'][-1]['result']['accepted']);self.assertTrue(s.submitted)

if __name__=='__main__':unittest.main()
