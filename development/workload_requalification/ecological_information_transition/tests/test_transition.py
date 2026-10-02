"""Decision-boundary qualifications; no inference or native runtime."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import transition_task as task
from working_set_exp.working_session import MAX_ACTION_BYTES

COUNT_OLD = '        rel = path.relative_to(root).as_posix()\n        artifacts.append({"path": rel})\n        if len(artifacts) >= max_files:\n            break\n'
COUNT_NEW = '        if len(artifacts) >= max_files:\n            break\n        rel = path.relative_to(root).as_posix()\n        artifacts.append({"path": rel})\n'

def correction(session):
    return dict(action='patch', path=task.TARGET, old=COUNT_OLD, new=COUNT_NEW,
        expected_candidate_id=session.candidate.candidate_id,
        expected_file_sha256=session.candidate.file_sha256(task.TARGET))

def request(module):
    import run_uncoached_contribution
    return run_uncoached_contribution.Adapter(module).request_for(module.initial_session().view())

class TransitionTests(unittest.TestCase):
    def test_complete_starting_input_isolation(self):
        a, b = task.initial_session(), task.initial_session('released')
        va, vb = a.view(), b.view()
        self.assertEqual({k for k in va if va[k] != vb[k]}, {'working_set', 'visibility'})
        va = copy.deepcopy(va)
        va['working_set']['sources'] = vb['working_set']['sources']
        va['visibility'] = vb['visibility']
        self.assertEqual(va, vb)
        ra, rb = request(task.Task()), request(task.Task('released'))
        self.assertEqual({k:v for k,v in ra.items() if k!='messages'},
                         {k:v for k,v in rb.items() if k!='messages'})
        self.assertEqual(ra['messages'][0], rb['messages'][0])
        self.assertEqual(a.working_account(), b.working_account())
        self.assertEqual(a.pairs, b.pairs)
        self.assertIn('[NEXT]', a.working_account()['text'])
        self.assertNotIn('previously submitted', va['episode_annotation'])
        self.assertEqual((a.requests_used,a.calls_used,a.request_limit,a.call_limit),(16,24,24,72))

    def test_release_restore_reacquire_current_edit_authority(self):
        a, b = task.initial_session(), task.initial_session('released')
        b = task.restore(task.snapshot(b), b.candidate)
        for s in (a,b):
            self.assertEqual(s.delivered_sources, [])
            s.mark_delivered(s.view())
        coverage = copy.deepcopy(b.prerequisite_state())
        accepted = a.execute(correction(a), lambda _: 100)
        rejected = b.execute(correction(b), lambda _: 100)
        self.assertTrue(accepted['accepted'])
        self.assertFalse(rejected['accepted'])
        self.assertIn('visible', rejected['error'])
        self.assertEqual(b.prerequisite_state(), coverage)
        b = task.restore(task.snapshot(b), b.candidate)
        read = b.execute(dict(action='read', path=task.TARGET, start_line=1,end_line=0), lambda _:100)
        self.assertTrue(read['accepted'])
        b.mark_delivered(b.view())
        accepted = b.execute(correction(b), lambda _:100)
        self.assertTrue(accepted['accepted'])
        self.assertEqual(a.candidate, b.candidate)
        self.assertEqual(task.snapshot(task.restore(task.snapshot(b), b.candidate)),task.snapshot(b))

    def test_exact_inherited_and_separate_new_handles(self):
        a, b = task.initial_session(), task.initial_session('released')
        for i in range(1,25):
            for prefix in ('RES','EVT'):
                self.assertEqual(a.payload(f'{prefix}-{i:04d}'), b.payload(f'{prefix}-{i:04d}'))
        a.execute(dict(action='record_account',text='Branch A pending question'),lambda _:100)
        b.execute(dict(action='record_account',text='Branch B pending question'),lambda _:100)
        self.assertNotEqual(a.payload('EVT-0025'), b.payload('EVT-0025'))
        for s in (a,b):
            restored = task.restore(task.snapshot(s),s.candidate)
            self.assertEqual(restored.payload('EVT-0025'),s.payload('EVT-0025'))
        with self.assertRaises(ValueError):
            task.Task('unchanged').restore(task.snapshot(b),b.candidate)

    def test_historical_account_retrieval_does_not_designate_it_current(self):
        s = task.initial_session('released')
        s.execute(dict(action='record_account',text='Current distinct account'),lambda _:100)
        current = s.working_account()
        form = next(row for row in s.action_rule()['oneOf']
                    if row['properties']['action'].get('const')=='reopen_event')
        action = dict(action='reopen_event',handle='EVT-0022',offset=0)
        for key in form['required']:
            if key not in action:
                self.fail('Unexpected required retrieval field: '+key)
        result = s.execute(action,lambda _:100)
        self.assertTrue(result['accepted'])
        self.assertEqual(s.working_account(),current)
        self.assertIn('[NEXT]',result['exact_utf8'])

    def test_successful_acquisition_and_rejected_account_stay_distinct(self):
        s = task.initial_session('released')
        acquired = s.execute(dict(action='read',path=task.TARGET,start_line=1,end_line=0),lambda _:100)
        current = s.working_account()
        rejected = s.execute(dict(action='record_account',text='x'*(MAX_ACTION_BYTES+1)),lambda _:100)
        self.assertTrue(acquired['accepted'])
        self.assertFalse(rejected['accepted'])
        self.assertTrue(s.pairs[-2]['result']['accepted'])
        self.assertFalse(s.pairs[-1]['result']['accepted'])
        self.assertEqual(s.working_account(),current)
        restored = task.restore(task.snapshot(s),s.candidate)
        self.assertEqual(restored.pairs,s.pairs)

    def test_no_later_check_submission_or_repair_is_imported(self):
        for condition in task.CONDITIONS:
            s = task.initial_session(condition)
            self.assertIsNone(s.check_state())
            self.assertFalse(s.submitted)
            self.assertEqual(len(s.pairs),24)
            self.assertIn(COUNT_OLD,s.candidate.file_map[task.TARGET].decode())
            self.assertIn('if idx >= MAX_JSONL_LINES or',s.candidate.file_map[task.SAVED_RUNS].decode())
            self.assertFalse(s.view()['verification']['submission']['eligible'])

    def test_tampered_checkpoint_history_and_coverage_rejected(self):
        s = task.initial_session('released')
        for key in ('pairs','source_prerequisites'):
            state = task.snapshot(s)
            if key=='pairs':
                state['pairs'][0]['response']['action']='submit'
            else:
                state[key]['first_mutation']['request_number']+=1
            with self.assertRaises(ValueError):
                task.restore(state,s.candidate)

    def test_runtime_and_checker_fixed_in_both(self):
        a,b = request(task.Task()),request(task.Task('released'))
        old = task.read(task.OLD/'calls/C17-wire-request.json')
        self.assertEqual(a['grammar'],old['grammar'])
        self.assertEqual(a['chat_template_kwargs'],dict(enable_thinking=True,reasoning_effort='medium'))
        for key in set(old)-{'messages'}:
            self.assertEqual(a[key],old[key],key)
        self.assertEqual(a['max_tokens'],-1)
        self.assertEqual(a['grammar'],b['grammar'])
        self.assertEqual(task.initial_session().checkers,task.initial_session('released').checkers)
        self.assertEqual((task.AREA/'SYSTEM.txt').read_bytes(),(task.original.AREA/'SYSTEM.txt').read_bytes())

if __name__=='__main__':
    unittest.main(verbosity=2)
