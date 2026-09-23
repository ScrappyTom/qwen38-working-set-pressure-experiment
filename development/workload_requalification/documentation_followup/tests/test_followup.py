import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bootstrap
import followup_task as task
from working_set_exp.jsonutil import canonical_json_bytes

class FollowupTests(unittest.TestCase):
    def test_only_declared_task_state_changes(self):
        old=task.restore(amend=False);new=task.Task().initial_session()
        a=task.previous.snapshot(old);b=task.previous.snapshot(new)
        self.assertEqual({k for k in a if a[k]!=b[k]}, {'submitted','request_limit','call_limit'})
        self.assertEqual(task.previous.candidate_bytes(old.candidate),task.previous.candidate_bytes(new.candidate))
        self.assertEqual((new.requests_used,new.calls_used,new.request_limit,new.call_limit),(49,73,57,97))
        self.assertTrue(old.submitted);self.assertFalse(new.submitted)
        self.assertNotEqual(old.task,new.task)
        self.assertEqual(new.view()['task'],(task.AREA/'TASK.txt').read_text())
    def test_review_is_assignment_not_hidden_correction(self):
        s=task.Task().initial_session();v=s.view()
        self.assertIn('reviewer-supplied',s.task)
        self.assertIn(':attr:`!allow_no_value`',s.candidate.file_map['Doc/library/configparser.rst'].decode())
        self.assertTrue(v['verification']['checks']['public']['applies_to_current'])
        self.assertTrue(v['verification']['checks']['public']['passed'])
        self.assertEqual(s.working_account()['text'],task.restore(amend=False).working_account()['text'])
    def test_observations_and_decoder_preserved(self):
        s=task.Task().initial_session()
        for name in ('CHK-0054','CHK-0066','CHK-0072'):
            self.assertEqual((s.observations.directory(name)/'stdout.bin').read_bytes(),(task.OLD/'observations'/name/'stdout.bin').read_bytes())
        self.assertEqual(task.Task().response_constraints(),task.previous.Task().response_constraints())
        self.assertEqual(task.Task().reply_schema(),task.previous.Task().reply_schema())

if __name__=='__main__':unittest.main()
