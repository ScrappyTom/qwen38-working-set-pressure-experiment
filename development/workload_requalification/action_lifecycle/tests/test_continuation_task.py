"""CPU checkpoint/reply tests. Subprocesses, endpoints and checker execution forbidden."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import bootstrap  # noqa: F401,E402
import continuation_task as task  # noqa: E402
import navigation_task as previous  # noqa: E402
import run_uncoached_contribution as runner  # noqa: E402
from working_set_exp import working_view  # noqa: E402
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file  # noqa: E402


class ContinuationTaskTests(unittest.TestCase):
    def setUp(self):
        for name in ('subprocess.Popen', 'subprocess.run', 'subprocess.call',
                     'subprocess.check_call', 'subprocess.check_output',
                     'urllib.request.urlopen'):
            guard = patch(name, side_effect=AssertionError('CPU qualification must not execute processes/endpoints'))
            guard.start()
            self.addCleanup(guard.stop)
        self.module = task.Task()
        self.session = self.module.initial_session()

    def test_restore_is_exact_and_allowance_is_cumulative(self):
        self.assertEqual(canonical_json_bytes(task.snapshot(self.session)),
                         (task.OLD / 'final-state.json').read_bytes())
        self.assertEqual(task.candidate_bytes(self.session.candidate),
                         (task.OLD / 'final-candidate.json').read_bytes())
        self.assertEqual(self.module.initial_preceding_feedback(), [])
        self.assertEqual((self.session.requests_used, self.session.request_limit), (5, 24))
        self.assertEqual((self.session.calls_used, self.session.call_limit), (5, 72))
        self.assertEqual(self.session.starting_archive_length, 0)
        self.assertEqual(self.session.ranges, [])
        self.assertIsNone(self.session.check_state())
        self.assertFalse(self.session.submitted)

    def test_entry_keeps_original_task_checker_account_and_navigation(self):
        original = previous.Task('receipts').initial_session()
        self.assertEqual(self.session.task, original.task)
        self.assertEqual(self.session.checkers, original.checkers)
        self.assertEqual(self.session.edit_checks, {})
        self.assertEqual(self.session.candidate, original.candidate)
        self.assertEqual(self.session.working_account()['written_during_request'], 3)
        last = self.session.view()['latest_feedback']
        self.assertEqual(last['sequence'], 5)
        self.assertEqual(last['result']['path'], 'src/dispatchledger')
        self.assertEqual(len(last['result']['entries']), 6)
        self.assertEqual(self.session.view()['working_set']['sources'], [])

    def test_task_session_decoder_reference_and_wire_agree(self):
        self.assertEqual(self.module.reply_schema(), self.session.reply_schema())
        forms = self.module.reply_schema()['json_schema']['schema']['oneOf']
        self.assertEqual([list(form['properties']) for form in forms],
                         [['discussion', 'operation'], ['discussion', 'account'],
                          ['discussion', 'account', 'operation']])
        wire = runner.Adapter(self.module).request_for(self.session.view())
        self.assertNotIn('response_format', wire)
        self.assertEqual(wire['grammar'], task.response_constraints()['grammar'])
        self.assertEqual(json.loads(wire['messages'][-1]['content'])['workspace'], self.session.view())
        self.assertEqual(wire['chat_template_kwargs'], dict(enable_thinking=True, reasoning_effort='medium'))
        self.assertIn('discussion alone is not an accepted reply', wire['messages'][0]['content'])
        self.assertNotIn('Discussion alone ends the run', wire['messages'][0]['content'])
        self.assertIn('Discussion alone ends the run', previous.Task('receipts').operating_reference())

    def test_actual_old_discussion_cannot_execute_or_stop_through_new_contract(self):
        old_final = (task.OLD / 'calls/C05-assistant-content.txt').read_text(encoding='utf-8')
        state = canonical_json_bytes(task.snapshot(self.session))
        with self.assertRaises(ValueError):
            self.module.decode_reply(old_final)
        with self.assertRaises(ValueError):
            self.module.process_reply(self.session, json.loads(old_final), lambda view: 1000, [])
        self.assertEqual(canonical_json_bytes(task.snapshot(self.session)), state)
        # Retained historical callers still accept the exact old form.
        self.assertEqual(previous.decode_reply(old_final), json.loads(old_final))

    def test_next_account_and_read_keep_global_provenance_and_real_effect(self):
        inherited = copy.deepcopy(self.session.pairs)
        self.session.mark_delivered(self.session.view())
        self.session.begin_request()
        result = self.module.process_reply(self.session,
            dict(discussion='CPU qualification only.', account='Pending source inspection.',
                 operation=dict(action='read', path='README.md', start_line=1, end_line=0)),
            lambda view: 1000, [])
        self.assertTrue(result['executed'])
        self.assertEqual(len(result['operations']), 2)
        self.assertTrue(all(row['result']['accepted'] for row in result['operations']))
        self.assertEqual(self.session.pairs[:5], inherited)
        self.assertEqual((self.session.requests_used, self.session.calls_used), (6, 7))
        self.assertEqual(self.session.working_account()['written_during_request'], 6)
        self.assertEqual(self.session.working_account()['action_handle'], 'EVT-0006')
        self.assertEqual(self.session.last['sequence'], 7)
        self.assertEqual(self.session.last['result']['source']['path'], 'README.md')
        self.assertEqual(self.session.candidate.candidate_id, inherited[-1]['result']['candidate_id'])

    def test_empty_account_is_a_real_clear_and_operation_is_optional(self):
        self.session.mark_delivered(self.session.view())
        self.session.begin_request()
        result = self.module.process_reply(self.session,
            self.module.decode_reply('{"discussion":"Clear this account.","account":""}'),
            lambda view: 1000, [])
        self.assertTrue(result['executed'])
        self.assertEqual(self.session.calls_used, 6)
        self.assertEqual(len(result['operations']), 1)
        self.assertTrue(result['operations'][0]['result']['cleared'])
        self.assertEqual(self.session.working_account()['text'], '')

    def test_literal_reply_keeps_exact_source_and_rejects_unavailable_check_form(self):
        header = dict(discussion='CPU literal decoding.', operation=dict(action='replace_region',
            region='SRC-' + '1' * 64, expected_candidate_id=self.session.candidate.candidate_id))
        body = 'literal = "quote \\n"\n# SOURCE\n\n'
        reply = self.module.decode_reply(json.dumps(header) + '\nSOURCE\n' + body)
        self.assertEqual(reply['operation']['new'], body)
        with self.assertRaises(ValueError):
            self.module.decode_reply(json.dumps(dict(discussion='Invalid extra field.',
                operation=dict(action='tree', path='.', offset=0, limit=16), check_after='public')))

    def test_template_delegation_changes_only_decoder_grammar(self):
        request = runner.Adapter(self.module).request_for(self.session.view())
        before = copy.deepcopy(request)
        with patch.object(previous, 'expected_native', return_value=b'CPU template sentinel') as delegate:
            self.assertEqual(task.expected_native(request), b'CPU template sentinel')
        self.assertEqual(request, before)
        forwarded = delegate.call_args.args[0]
        self.assertEqual(forwarded['grammar'], previous.response_constraints()['grammar'])
        forwarded['grammar'] = before['grammar']
        self.assertEqual(forwarded, before)
        bad = {**request, 'response_format': {}}
        with self.assertRaises(AssertionError):
            task.expected_native(bad)

    def test_checkpoint_tampering_is_rejected_without_editing_old_evidence(self):
        target = task.OLD / 'final-state.json'
        digest = sha256_file(target)
        original = task.sha256_file
        with patch.object(task, 'sha256_file', side_effect=lambda p: '0' * 64 if p == target else original(p)):
            with self.assertRaises(AssertionError):
                task.checkpoint_bindings()
        self.assertEqual(sha256_file(target), digest)

    def test_paths_and_source_bindings_cover_continuation_and_inherited_evidence(self):
        self.assertEqual(self.module.AREA, AREA)
        self.assertEqual(self.module.PACKAGE, AREA / 'preparation-001')
        self.assertEqual(self.module.RUN, AREA / 'run-001')
        self.assertEqual(self.module.MANIFEST, AREA / 'EXECUTION_MANIFEST-001.json')
        for bad in ('../001', '1', 1, 'abc'):
            with self.assertRaises(ValueError):
                task.Task(bad)
        bindings = self.module.implementation_identities()
        for path in (Path(task.__file__), AREA / 'operational_reply.py', AREA / 'native_forms.py',
                     AREA / 'run_continuation.py', Path(__file__), AREA / 'SYSTEM.txt', AREA / 'SPEC.md',
                     task.OLD / 'RESPONSE_SEAL.json', task.OLD / 'final-state.json',
                     task.OLD / 'calls/C05-assistant-content.txt', task.ORIGINAL_REPLAY):
            self.assertEqual(bindings[path.relative_to(task.ROOT).as_posix()], sha256_file(path))


if __name__ == '__main__':
    unittest.main(verbosity=2)
