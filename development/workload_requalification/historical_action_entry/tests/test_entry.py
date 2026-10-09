"""Information and guard boundaries for the exact imported historical action."""
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import historical_task as task
import qualification_route as route
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict
from working_set_exp.measurement import check_opportunities
from working_set_exp.candidate import Candidate
from working_set_exp.isolation import run_checker


def act(session, operation):
    session.mark_delivered(session.view())
    return task.process_reply(session, dict(discussion='CPU boundary qualification.', operation=operation),
        lambda view: 1000, [])['operations'][0]['result']


def recover_and_read(session):
    assert act(session, dict(action='reopen_event', handle='EVT-0001', offset=0))['accepted']
    assert act(session, dict(action='read', path='report.py', start_line=1, end_line=0))['accepted']


class EntryTests(unittest.TestCase):
    def test_original_entry_and_no_initial_leak(self):
        from run_uncoached_contribution import Adapter
        session = task.initial_session()
        pair = task.inherited_pair()
        marker = pair['response']['old'].split('=', 1)[1].strip()
        request = Adapter(task.Task()).request_for(session.view())
        assert marker not in canonical_json_bytes(request).decode()
        assert marker not in b''.join(session.candidate.file_map.values()).decode()
        assert session.calls_used == 0 and session.starting_archive_length == 1
        assert session.view()['recent_activity'][0]['action_handle'] == 'EVT-0001'
        assert session.view()['allowance']['requests_remaining'] == task.MAX_REQUESTS == 8
        assert session.view()['allowance']['actions_remaining'] == task.MAX_OPERATIONS == 24
        assert request['chat_template_kwargs']['reasoning_effort'] == 'medium'
        assert session.payload('EVT-0001') == canonical_json_bytes(pair['response'])
        assert session.payload('RES-0001') == canonical_json_bytes(pair['result'])

    def test_recovery_is_exact_not_execution_or_edit_authority(self):
        session = task.initial_session()
        before = session.candidate.candidate_id
        result = act(session, dict(action='reopen_event', handle='EVT-0001', offset=0))
        assert result['accepted'] and route.shown_action(session.view()) == task.inherited_pair()['response']
        assert session.candidate.candidate_id == before and session.check_state() is None
        # Deliberately use evaluator-known current source without delivering it.
        text = task.starting_files()['report.py'].decode()
        patch = dict(action='patch', path='report.py', old=text, new=text.replace('missing', 'new'),
            expected_candidate_id=before, expected_file_sha256=session.candidate.file_sha256('report.py'))
        assert not act(session, patch)['accepted']
        assert session.candidate.candidate_id == before and not session.delivered_sources
        assert session.pairs[0] == task.inherited_pair()

    def test_restore_release_and_ordinary_reacquisition(self):
        session = task.initial_session()
        recover_and_read(session)
        proposal = route.replacement(session.view())
        assert act(session, dict(action='work_on', sources=[], results=[]))['accepted']
        restored = task.restore(task.snapshot(session), session.candidate, replay=True)
        assert not act(restored, proposal)['accepted']
        assert act(restored, dict(action='read', path='report.py', start_line=1, end_line=0))['accepted']
        assert act(restored, proposal)['accepted']
        assert restored.candidate.file_map['archive/source.dat'] == task.starting_files()['archive/source.dat']
        assert restored.payload('EVT-0001') == session.payload('EVT-0001')
        state = load_json_strict(canonical_json_bytes(task.snapshot(restored)))
        same = task.restore(state, restored.candidate, replay=True)
        assert canonical_json_bytes(task.snapshot(same)) == canonical_json_bytes(state)
        bad = copy.deepcopy(state)
        bad['pairs'][0]['response']['old'] = 'changed'
        with self.assertRaises(ValueError):
            task.restore(bad, restored.candidate, replay=True)

    def test_branch_local_new_records(self):
        first, second = task.initial_session(), task.initial_session()
        assert act(first, dict(action='reopen_event', handle='EVT-0001', offset=0))['accepted']
        assert act(second, dict(action='read', path='report.py', start_line=1, end_line=0))['accepted']
        assert first.payload('EVT-0001') == second.payload('EVT-0001')
        assert first.payload('EVT-0002') != second.payload('EVT-0002')
        for session in (first, second):
            restored = task.restore(task.snapshot(session), session.candidate, replay=True)
            assert restored.payload('EVT-0002') == session.payload('EVT-0002')
        assert first.pairs[0] == second.pairs[0] == task.inherited_pair()

    def test_checker_ordinary_path_and_current_successor(self):
        with tempfile.TemporaryDirectory() as folder:
            session = task.initial_session(Path(folder))
            recover_and_read(session)
            proposal = route.replacement(session.view())
            failed = act(session, dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id))
            assert failed['executed'] and not failed['passed']
            assert act(session, proposal)['accepted']
            assert not session.verification_view()['submission']['eligible']
            assert not act(session, dict(action='submit', expected_candidate_id=session.candidate.candidate_id))['accepted']
            passed = act(session, dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id))
            assert passed['executed'] and passed['passed']
            assert act(session, dict(action='submit', expected_candidate_id=session.candidate.candidate_id))['accepted']
            opportunities = check_opportunities(session.pairs[session.starting_archive_length:], call_limit=24)
            assert opportunities[0]['first_check'] and not opportunities[1]['first_check']
            for candidate, expected in ((task.starting_candidate(), False), (session.candidate, True)):
                assert run_checker(candidate, task.public_checker())['passed'] is expected
                plain = Path(folder) / candidate.candidate_id
                plain.mkdir()
                for name, raw in candidate.files:
                    out = plain / name
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(raw)
                (plain / 'checker.py').write_bytes(task.public_checker())
                execution = subprocess.run([sys.executable, '-B', 'checker.py'], cwd=plain, capture_output=True)
                assert (execution.returncode == 0) is expected
            assert session.pairs[0] == task.inherited_pair()


if __name__ == '__main__':
    unittest.main(verbosity=2)
