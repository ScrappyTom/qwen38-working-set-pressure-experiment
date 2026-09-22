"""CPU boundary tests with synthetic transport/rendering; no runtime or checkers."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import bootstrap  # noqa: F401
import run_uncoached_contribution as shared_runner

SHARED_LOOP = shared_runner.Loop
import run_continuation as subject
import operational_reply
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes


def require(condition, message):
    if not condition:
        raise AssertionError(message)


class Log:
    def __init__(self):
        self.rows = []

    def append(self, kind, payload, artifacts):
        self.rows.append(dict(kind=kind, payload=copy.deepcopy(payload), artifacts=artifacts))

    def payloads(self, kind):
        return [row['payload'] for row in self.rows if row['kind'] == kind]


class Session:
    def __init__(self):
        self.requests_used, self.calls_used = 5, 5
        self.request_limit, self.call_limit = 24, 72
        self.submitted = self.delivery_blocked = False
        self.candidate = SimpleNamespace(candidate_id='c' * 64)
        self.pairs, self.starting_archive_length = [], 0
        self.delivered = []

    def view(self):
        return dict(requests_used=self.requests_used, calls_used=self.calls_used,
                    candidate_id=self.candidate.candidate_id)

    def begin_request(self):
        require(self.requests_used < self.request_limit, 'request allowance exceeded')
        self.requests_used += 1

    def mark_delivered(self, view):
        self.delivered.append(copy.deepcopy(view))

    def check_state(self):
        return None


class TransportFailure(Exception):
    status, data = 599, b'exact partial transport bytes'


class LoopTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.log, self.session = Log(), Session()
        self.actor = SimpleNamespace(
            MAX_REQUESTS=24, ACTOR=dict(context=56576, generation_reserve=32768),
            base=SimpleNamespace(HTTP_TIMEOUT_SECONDS=1, ResponseFailure=TransportFailure),
            preceding_feedback=[], require=require,
            reply_schema=lambda: operational_reply.reply_schema({'public': 'check'}),
            module=SimpleNamespace(decode_reply=lambda text: operational_reply.decode_reply(text, {'public': 'check'})),
            request_for=lambda view: dict(messages=[dict(role='user', content=canonical_json_bytes(view).decode())],
                                          grammar='synthetic-test-grammar'))
        self.actor.expected_native = lambda request: b'cpu-fixture\n' + canonical_json_bytes(request)

        def render(request, stem):
            native = self.actor.expected_native(request)
            return canonical_json_bytes(dict(prompt=native.decode())), native, canonical_json_bytes(dict(tokens=[1] * 100)), 100

        def post(url, route, raw, timeout):
            require(route == '/v1/chat/completions', 'unexpected synthetic route')
            return canonical_json_bytes(dict(choices=[dict(finish_reason='stop', message=dict(
                reasoning_content='Synthetic boundary fixture.',
                content='{"discussion":"Save the question.","account":"Still unresolved."}'))],
                usage=dict(prompt_tokens=100, completion_tokens=5, total_tokens=105,
                           prompt_tokens_details=dict(cached_tokens=0)), timings=dict(cache_n=0)))

        self.post = Mock(side_effect=post)

        def process(session, reply, measure, feedback, record):
            # A real valid account-only reply has one operation. State mutation is
            # simulated solely to isolate the production runner's boundary logic.
            require(session.calls_used < session.call_limit, 'operation allowance exceeded')
            session.calls_used += 1
            operation = dict(origin='model_authored_account', action=dict(action='record_account', text=reply['account']),
                             result=dict(accepted=True))
            record(1, operation)
            return dict(executed=True, operations=[operation])

        self.actor.process_reply = Mock(side_effect=process)
        self.loop = subject.ContinuationLoop(self.root, ArtifactStore(self.root), self.log,
            task_module=self.actor, render=render, post=self.post, health=lambda: {}, source_check=lambda: None)
        self.loop.snapshot = Mock()
        self.loop.measure(self.session.view())
        entry = next(iter(self.loop.cache.values()))
        self.loop.initial = {key:entry[key] for key in subject.INITIAL_KEYS}

    def test_matching_offset_first_input_dispatches_c06(self):
        self.assertEqual(self.loop.sent, 5)
        result = self.loop.invoke(self.session)
        self.assertEqual(result['id'], 'C06')
        self.assertEqual((self.loop.sent, self.session.requests_used, self.session.calls_used), (6, 6, 6))
        self.assertEqual([p['id'] for p in self.log.payloads('invocation_started')], ['C06'])
        self.assertEqual(self.post.call_count, 1)
        self.assertEqual(self.session.delivered, [dict(requests_used=5, calls_used=5, candidate_id='c' * 64)])

    def test_offset_first_input_mismatch_prevents_dispatch(self):
        self.loop.initial['native_sha256'] = '0' * 64
        with self.assertRaisesRegex(AssertionError, 'continuation first input differs'):
            self.loop.invoke(self.session)
        self.assertFalse(self.post.called)
        self.assertEqual((self.loop.sent, self.session.requests_used, self.session.calls_used), (5, 5, 5))
        self.assertFalse(self.session.delivered)
        self.assertFalse(self.log.payloads('invocation_started'))

    def test_exactly_nineteen_more_requests_keep_cumulative_limit_twentyfour(self):
        outcome = self.loop.execute(self.session)
        self.assertEqual(outcome['disposition'], 'request_allowance_exhausted')
        self.assertEqual(outcome['sent_requests'], 24)
        self.assertEqual(self.post.call_count, 19)
        self.assertEqual([p['id'] for p in self.log.payloads('invocation_started')],
                         [f'C{i:02}' for i in range(6, 25)])
        closed = self.log.payloads('continuation_accounting_closed')[-1]
        self.assertEqual((closed['new_dispatches'], closed['cumulative_requests']), (19, 24))
        self.assertEqual((closed['new_operations'], closed['cumulative_operations']), (19, 24))
        self.assertTrue(closed['task_loop_completed_totals_are_cumulative'])
        self.assertTrue(closed['response_seal_dispatch_totals_are_new'])

    def test_operation_seventytwo_stops_ongoing_loop_before_next_dispatch(self):
        # Exercise the inherited execution loop at a later admissible boundary,
        # after continuation-entry validation has already occurred. No reset of
        # inherited counters or fabricated multi-operation reply is involved.
        self.loop.sent = self.session.requests_used = 20
        self.session.calls_used = 71
        outcome = subject.OrdinaryLoop.execute(self.loop, self.session)
        self.assertEqual(outcome['disposition'], 'action_allowance_exhausted')
        self.assertEqual((self.loop.sent, self.session.calls_used), (21, 72))
        self.assertEqual(self.post.call_count, 1)
        self.assertEqual([p['id'] for p in self.log.payloads('invocation_started')], ['C21'])

    def test_operator_stop_before_dispatch_preserves_consumed_allowance(self):
        (self.root / 'STOP_REQUEST.txt').write_text('Declared operator stop.', encoding='utf-8')
        outcome = self.loop.execute(self.session)
        self.assertEqual(outcome['disposition'], 'operator_stopped')
        self.assertFalse(self.post.called)
        self.assertEqual((self.loop.sent, self.session.requests_used, self.session.calls_used), (5, 5, 5))
        self.assertFalse(self.session.delivered)
        self.assertEqual(self.log.payloads('continuation_accounting_closed')[-1]['new_dispatches'], 0)

    def test_transport_failure_counts_dispatch_and_closes_accounting_without_operation(self):
        self.post.side_effect = TransportFailure()
        with self.assertRaises(TransportFailure):
            self.loop.execute(self.session)
        self.assertEqual((self.loop.sent, self.session.requests_used, self.session.calls_used), (6, 6, 5))
        self.assertEqual(self.post.call_count, 1)
        self.assertFalse(self.actor.process_reply.called)
        closed = self.log.payloads('continuation_accounting_closed')[-1]
        self.assertEqual((closed['new_dispatches'], closed['cumulative_requests'], closed['new_operations']), (1, 6, 0))
        self.assertFalse(self.log.payloads('invocation_completed'))
        self.assertFalse(self.log.payloads('task_loop_completed'))
        self.assertEqual((self.root / 'calls/C06-partial-response.bin').read_bytes(), TransportFailure.data)

    def test_wrong_inherited_accounting_is_rejected_before_loop(self):
        self.session.requests_used = 4
        with self.assertRaisesRegex(AssertionError, 'consumed allowance differs'):
            self.loop.execute(self.session)
        self.assertFalse(self.post.called)

    def test_isolated_runner_does_not_replace_shared_loop(self):
        self.assertIs(shared_runner.Loop, SHARED_LOOP)
        self.assertIsNot(subject.runner, shared_runner)
        self.assertIs(subject.runner.Loop, subject.ContinuationLoop)
        self.assertIsNot(subject.OrdinaryLoop, shared_runner.Loop)


class PreparationGateTests(unittest.TestCase):
    def setUp(self):
        self.root = Path('cpu-only-not-created')
        self.request = dict(messages=[], grammar='fixture')
        self.accounting = dict(inherited_requests=5, inherited_operations=5,
                              maximum_new_requests=19, maximum_new_operations=67)
        self.manifest = dict(**self.accounting, request_numbering='cumulative C06 through C24',
                             no_live_coaching=True, automatic_retry=False, initial={'frozen': 'input'})
        self.qualification = dict(**self.accounting, completion_requests=0, checks_executed=1,
                                  checker_starts_without_outcomes=[], initial=copy.deepcopy(self.manifest['initial']))
        self.native = dict(status='passed', completion_requests=0, model_inference_calls=0,
                           checker_executions=0, wire_sha256=sha256_bytes(completion_request_bytes(self.request)),
                           grammar_sha256=sha256_bytes(self.request['grammar'].encode()),
                           cases=[dict(expected=True, accepted_including_eos=True),
                                  dict(expected=False, accepted_including_eos=False)])
        self.module = SimpleNamespace(PACKAGE=self.root, require=require,
                                      initial_session=lambda: SimpleNamespace(view=lambda: {}))
        self.module.read = lambda path: {'QUALIFICATION.json': self.qualification, 'RESULTS.json': self.native}[path.name]
        for target, value in [('verify_package', lambda module: copy.deepcopy(self.manifest)),
                              ('Adapter', lambda module: SimpleNamespace(request_for=lambda view: self.request))]:
            context = patch.object(subject.runner, target, value)
            context.start(); self.addCleanup(context.stop)

    def test_valid_gate_binds_remaining_allowance_and_actual_wire(self):
        self.assertEqual(subject.verify_preparation(self.module), self.manifest)

    def test_manifest_cannot_reset_inherited_or_remaining_allowance(self):
        for key, bad in [('inherited_requests', 0), ('inherited_operations', 0),
                         ('maximum_new_requests', 24), ('maximum_new_operations', 72),
                         ('request_numbering', 'restart C01')]:
            with self.subTest(key=key), patch.dict(self.manifest, {key:bad}):
                with self.assertRaisesRegex(AssertionError, 'manifest accounting differs'):
                    subject.verify_preparation(self.module)

    def test_qualification_accounting_and_first_input_must_match(self):
        for key, bad in [('inherited_requests', 0), ('inherited_operations', 0),
                         ('maximum_new_requests', 24), ('maximum_new_operations', 72),
                         ('initial', {'different': 'input'}), ('checks_executed', 0),
                         ('checker_starts_without_outcomes', ['CHK-0009'])]:
            with self.subTest(key=key), patch.dict(self.qualification, {key:bad}):
                with self.assertRaisesRegex(AssertionError, 'route qualification'):
                    subject.verify_preparation(self.module)

    def test_wrong_native_wire_grammar_or_unfinished_negative_case_rejected(self):
        for key, bad in [('wire_sha256', '0' * 64), ('grammar_sha256', '0' * 64),
                         ('model_inference_calls', 1), ('cases', []),
                         ('cases', [dict(expected=False, accepted_including_eos=True)])]:
            with self.subTest(key=key), patch.dict(self.native, {key:bad}):
                with self.assertRaisesRegex(AssertionError, 'native operational contract'):
                    subject.verify_preparation(self.module)


if __name__ == '__main__':
    unittest.main()
