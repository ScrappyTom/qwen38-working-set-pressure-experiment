"""Exact replay of the closed E18 source continuation, without new execution.

Saved native measurements supply admission. Every actual public reply, receipt,
checkpoint, candidate version and executed observation is checked mechanically.
Interpretation and artifact review remain separate duties.
Adapted from the existing URL continuation auditor (9e38a5f2). Its replay loop
remains; admission, ancestry and observation expectations describe this job.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import traceback
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap  # noqa: F401
import continuation_task as study
from working_set_exp import working_view
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.working_session import MAX_ACTION_BYTES

RUNNER_PATH = study.ROOT / 'scripts/run_uncoached_contribution.py'
INHERITED_REQUESTS, INHERITED_OPERATIONS = 24, 37
MAXIMUM_REQUESTS, MAXIMUM_OPERATIONS = 36, 73
OLD_SEAL_SHA = study.OLD_SEAL
ORIGINAL_ENTRY_ID = study.previous.STARTING_ID
CONTINUATION_ENTRY_ID = study.SAVED_ID


def _runner():
    spec = importlib.util.spec_from_file_location('url_continuation_closed_common_runner', RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _within(root, name):
    path = (root / name).resolve()
    assert path.is_relative_to(root.resolve()), 'artifact address escapes custody root'
    return path


def _inventory(root, seal):
    rows = seal['files']
    assert len({row['path'] for row in rows}) == len(rows)
    assert sha256_bytes(canonical_json_bytes(rows)) == seal['aggregate_sha256']
    for row in rows:
        path = _within(root, row['path'])
        assert path.stat().st_size == row['size_bytes'] and sha256_file(path) == row['sha256'], row['path']
    for name, digest in seal['private_runtime_files_local_only'].items():
        assert sha256_file(_within(root / 'private-runtime', name)) == digest


def _preparation(module, seal):
    run, preparation = module.RUN, module.PACKAGE
    manifest = study.read(module.MANIFEST)
    assert manifest['source_sha256'] == seal['source_sha256'] == module.source_identities()
    module.verify_sources(manifest['source_sha256'])
    assert manifest['actor'] == seal['actor'] == module.ACTOR and manifest['seed'] == module.SEED
    assert (manifest['maximum_requests'], manifest['maximum_operations']) == (36, 73)
    assert manifest['starting_candidate_id'] == CONTINUATION_ENTRY_ID
    assert manifest['starting_archive_operations'] == 37 and manifest['original_starting_archive_length'] == 0
    assert (manifest['inherited_requests'], manifest['inherited_operations']) == (24, 37)
    assert (manifest['maximum_new_requests'], manifest['maximum_new_operations']) == (12, 36)
    assert manifest['selection_assistance'] == 'none; exact saved actor selection'
    assert manifest['inherited_run_seal_sha256'] == OLD_SEAL_SHA
    assert manifest['literal_source_reply'] and manifest['no_live_coaching'] and not manifest['automatic_retry']
    assert manifest['automatic_edit_checks'] == {}
    assert manifest['checker_contracts'] == {'public': {'checker_sha256': module.PUBLIC_SHA}}
    assert module.PUBLIC_SHA == module.previous.PUBLIC_SHA and manifest['task_and_checker_unchanged']
    assert manifest['task_sha256'] == module.previous.TASK_SHA
    if (run / 'EXECUTION_MANIFEST.json').exists():
        assert module.MANIFEST.read_bytes() == (run / 'EXECUTION_MANIFEST.json').read_bytes()
    assert sha256_file(preparation / 'SEAL.json') == manifest['preparation_seal_sha256']
    proof = study.read(preparation / 'SEAL.json')
    assert proof['status'] == 'qualified_no_model_inference' and proof['completion_requests'] == 0
    assert proof['source_sha256'] == manifest['source_sha256']
    _inventory(preparation, proof)
    qualification = study.read(preparation / 'QUALIFICATION.json')
    assert qualification['status'] == 'qualified' and qualification['completion_requests'] == 0
    assert qualification['entry_unchanged_after_qualification'] and qualification['route']['submitted']
    assert qualification['route']['audit']['temporal_contract_met']
    assert qualification['initial'] == manifest['initial']
    assert qualification['native_forms']['status'] == 'passed'
    assert len(qualification['native_forms']['cases']) == 31
    assert all(row['accepted_including_eos'] == row['expected'] for row in qualification['native_forms']['cases'])
    adapter = _runner().Adapter(module)
    adapter.preceding_feedback[:] = module.initial_preceding_feedback()
    session = module.initial_session()
    initial = adapter.request_for(session.view())
    assert completion_request_bytes(initial) == (preparation / 'initial-wire-request.json').read_bytes()
    user = load_json_strict(initial['messages'][-1]['content'])
    view = user['workspace']
    assert view['candidate_id'] == CONTINUATION_ENTRY_ID
    assert view['allowance']['requests_used'] == 24 and view['allowance']['actions_used'] == 37
    assert view['allowance']['request_limit'] == 36 and view['allowance']['requests_remaining'] == 12
    assert view['allowance']['actions_remaining'] == 36
    assert user['preceding_operation_feedback'] == module.initial_preceding_feedback()
    assert view['latest_feedback']['sequence'] == 37
    assert view['latest_feedback']['action_summary']['action'] == 'patch'
    assert not view['verification']['submission']['eligible']
    first = run / 'calls/C25-wire-request.json'
    if first.exists():
        assert first.read_bytes() == (preparation / 'initial-wire-request.json').read_bytes()
        assert sha256_file(first) == manifest['initial']['wire_request_sha256']
    return manifest


def _inherited(module, session, run):
    """Authenticate the partial predecessor without changing its outcome."""
    old = module.OLD
    assert sha256_file(old / 'RESPONSE_SEAL.json') == OLD_SEAL_SHA
    old_seal = study.read(old / 'RESPONSE_SEAL.json')
    _inventory(old, old_seal)
    old_records = verify_records(old / 'records.jsonl', old)
    assert len(old_records) == old_seal['record_count'] == 1443
    assert old_seal['disposition'] == 'request_allowance_exhausted'
    assert (old_seal['sent_requests'], old_seal['actual_operations']) == (24, 37)
    proof_path = old.parent / 'review/VERIFICATION-001.json'
    assert sha256_file(proof_path) == module.OLD_VERIFICATION
    proof = study.read(proof_path)
    assert proof['status'] == 'replayed_exactly' and not proof['submitted']
    assert proof['final_candidate_id'] == CONTINUATION_ENTRY_ID
    assert proof['initial_candidate_id'] == ORIGINAL_ENTRY_ID
    original = study.read(old / 'final-state.json')
    expected = {**original, 'request_limit': 36, 'call_limit': 73}
    assert canonical_json_bytes(module.snapshot(session)) == canonical_json_bytes(expected)
    assert module.candidate_bytes(session.candidate) == (old / 'final-candidate.json').read_bytes()
    assert session.requests_used == 24 and session.calls_used == len(session.pairs) == 37
    assert session.starting_archive_length == 0 and (session.request_limit, session.call_limit) == (36, 73)
    assert not session.submitted and session.check_state() is None
    assert module.initial_preceding_feedback() == study.read(old / 'final-preceding-feedback.json')
    last = session.pairs[-1]
    assert last['response']['action'] == 'patch' and last['response']['path'] == module.previous.POLICY
    assert last['result']['accepted']
    assert not any(row['path'].startswith('observations/') for row in old_seal['files'])
    return original, old_records


def _native_counts(run, records, adapter):
    counts = {}
    for record in records:
        if record['record_type'] != 'native_input_prepared':
            continue
        row, stem = record['payload'], record['payload']['stem']
        request = study.read(_within(run, stem + '-endpoint-request.json'))
        key = sha256_bytes(canonical_json_bytes(request))
        native = _within(run, stem + '-native.txt').read_bytes()
        assert study.read(_within(run, stem + '-template-request.json')) == request
        assert study.read(_within(run, stem + '-tokens-request.json')) == dict(add_special=False, content=native.decode())
        assert native == adapter.expected_native(request)
        assert native == study.read(_within(run, stem + '-template.json'))['prompt'].encode()
        assert row['prompt_tokens'] == len(study.read(_within(run, stem + '-tokens.json'))['tokens'])
        assert row['request_sha256'] == key and row['native_sha256'] == sha256_bytes(native)
        assert row['physical_generation_space'] == adapter.ACTOR['context'] - row['prompt_tokens']
        assert _within(run, stem + '-wire-request.json').read_bytes() == completion_request_bytes(request)
        assert study.read(_within(run, stem + '-count.json')) == {field: row[field] for field in
            ('stem', 'prompt_tokens', 'physical_generation_space', 'request_sha256', 'native_sha256')}
        assert key not in counts or counts[key] == row['prompt_tokens']
        counts[key] = row['prompt_tokens']
    return counts


def _response(module, run, tag, count, stopped):
    """Only a recorded, validated public final can become executable work."""
    response = run / f'calls/{tag}-endpoint-response.json'
    reply_path = run / f'calls/{tag}-reply.json'
    host_path = run / f'calls/{tag}-host-result.json'
    operations = list((run / 'calls').glob(f'{tag}-operation-*.json'))

    def incomplete(reason):
        assert stopped and not reply_path.exists() and not host_path.exists() and not operations
        return None, reason

    if not response.exists():
        return incomplete('transport_response_unavailable')
    try:
        value = study.read(response)
    except (ValueError, TypeError):
        return incomplete('malformed_endpoint_response')
    if not isinstance(value, dict):
        return incomplete('unsupported_endpoint_response_shape')
    choices = value.get('choices')
    if not isinstance(choices, list) or len(choices) != 1:
        return incomplete('unsupported_choice_count')
    choice = choices[0]
    if not isinstance(choice, dict) or not isinstance(choice.get('message'), dict):
        return incomplete('unsupported_message_shape')
    message = choice['message']
    if any(message.get(field) is not None and not isinstance(message[field], str)
           for field in ('content', 'reasoning_content')):
        return incomplete('unsupported_message_text_shape')
    for field, suffix in (('content', 'content'), ('reasoning_content', 'reasoning')):
        extracted = run / f'calls/{tag}-assistant-{suffix}.txt'
        if extracted.exists():
            assert (message.get(field) or '').encode() == extracted.read_bytes()
    content = message.get('content') or ''
    if choice.get('finish_reason') != 'stop' or not content.strip():
        return incomplete('unfinished_or_empty_final')
    if message.get('tool_calls') or message.get('function_call'):
        return incomplete('unsupported_action_channel')
    usage, timings = value.get('usage', {}), value.get('timings', {})
    details = usage.get('prompt_tokens_details', {}) if isinstance(usage, dict) else None
    if not (isinstance(usage, dict) and isinstance(details, dict) and isinstance(timings, dict)
            and all(type(usage.get(k)) is int for k in ('prompt_tokens', 'completion_tokens', 'total_tokens'))
            and usage['prompt_tokens'] == count and usage['completion_tokens'] > 0
            and usage['total_tokens'] == count + usage['completion_tokens'] <= module.ACTOR['context']
            and details.get('cached_tokens') == 0 and timings.get('cache_n') == 0):
        return incomplete('invalid_usage_or_cache_accounting')
    try:
        reply = module.decode_reply(content)
        working_view.validate(reply, module.reply_schema()['json_schema']['schema'])
    except (ValueError, TypeError, KeyError):
        return incomplete('malformed_or_unsupported_public_final')
    if not reply_path.exists():
        return incomplete('public_final_not_selected')
    assert reply == study.read(reply_path)
    for suffix in ('content', 'reasoning'):
        assert (run / f'calls/{tag}-assistant-{suffix}.txt').exists()
    return reply, None


def verify_preparation(version='001'):
    """Replay the scripted information path with saved counts and observations."""
    import qualification_route
    module = study.Task(version)
    folder = module.PACKAGE
    seal = study.read(folder / 'SEAL.json')
    manifest = _preparation(module, seal)
    records = verify_records(folder / 'records.jsonl', folder)
    session = study.initial_session(folder / 'scripted', replay=True)
    _, inherited = _inherited(module, session, folder)
    adapter = _runner().Adapter(module)
    adapter.preceding_feedback[:] = module.initial_preceding_feedback()
    counts = _native_counts(folder, records, adapter)

    def measure(view):
        key = sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
        assert key in counts, 'script replay needs absent native measurement'
        return counts[key]

    def record(row, current):
        stem = folder / ('route/' + row['name'])
        assert row == study.read(stem.with_suffix('.json'))
        assert canonical_json_bytes(module.snapshot(current)) == Path(str(stem) + '-state.json').read_bytes()
        assert module.candidate_bytes(current.candidate) == Path(str(stem) + '-candidate.json').read_bytes()
        restored = module.restore(module.snapshot(current), current.candidate, folder / 'scripted', replay=True)
        assert restored.view() == current.view()

    with patch('working_set_exp.observations.subprocess.Popen',
               side_effect=AssertionError('checker execution prohibited during preparation replay')):
        route = qualification_route.journey(module, session, measure,
            feedback=adapter.preceding_feedback, record=record, request_for=adapter.request_for)
    assert route == study.read(folder / 'QUALIFICATION.json')['route']
    return dict(status='preparation_replayed_exactly', artifacts=len(seal['files']),
        custody_records=len(records), inherited_custody_records=len(inherited), native_inputs=len(counts),
        source_files=len(seal['source_sha256']), temporal_contract_met=route['audit']['temporal_contract_met'],
        researcher_scripted=True, no_new_model_or_checker_or_tokenizer_execution=True,
        preparation_seal_sha256=manifest['preparation_seal_sha256'])


def verify(version='001'):
    module = study.Task(version)
    run = module.RUN
    if not (run / 'RESPONSE_SEAL.json').is_file():
        raise ValueError('Do not replay an open model run')
    seal = study.read(run / 'RESPONSE_SEAL.json')
    _inventory(run, seal)
    manifest = _preparation(module, seal)
    for raw in (run / 'records.jsonl').read_bytes().splitlines():
        for artifact in load_json_strict(raw)['artifacts']:
            _within(run, artifact['path'])
    records = verify_records(run / 'records.jsonl', run)
    assert len(records) == seal['record_count']
    accounting_started = [row['payload'] for row in records
                          if row['record_type'] == 'continuation_accounting_started']
    assert accounting_started == [dict(
        inherited_requests=INHERITED_REQUESTS, inherited_operations=INHERITED_OPERATIONS,
        cumulative_request_limit=MAXIMUM_REQUESTS, cumulative_operation_limit=MAXIMUM_OPERATIONS,
        maximum_new_requests=12, maximum_new_operations=36)]
    replay_module = study.Task(version, replay_folder=run)
    session = replay_module.initial_session()
    assert session.observations.replay is True
    adapter = _runner().Adapter(replay_module)
    adapter.preceding_feedback[:] = module.initial_preceding_feedback()
    counts = _native_counts(run, records, adapter)
    checked_states, checked_candidates, checked_feedback = set(), set(), set()
    expected_operations, starts, processed, terminal = [], [], [], None
    stopped = seal['disposition'] == 'stopped_without_retry'

    def measure(view):
        key = sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
        assert key in counts, 'replay requires an absent actual native admission measurement'
        return counts[key]

    def checkpoint(stem):
        state_path = stem + '-state.json'
        raw = _within(run, state_path).read_bytes()
        assert canonical_json_bytes(module.snapshot(session)) == raw, state_path
        checked_states.add(state_path)
        candidate_path = stem + '-candidate.json'
        assert module.candidate_bytes(session.candidate) == _within(run, candidate_path).read_bytes(), candidate_path
        checked_candidates.add(candidate_path)
        feedback_path = stem + '-preceding-feedback.json'
        assert canonical_json_bytes(adapter.preceding_feedback) == _within(run, feedback_path).read_bytes(), feedback_path
        checked_feedback.add(feedback_path)
        for number, diff in session.diffs.items():
            assert _within(run, f'diffs/EVT-{number:04d}.patch').read_bytes() == diff.encode()
        incoming = load_json_strict(raw)
        original = canonical_json_bytes(incoming)
        restored = module.restore(incoming, session.candidate, run, replay=True)
        assert canonical_json_bytes(incoming) == original, 'restore mutated loaded checkpoint'
        assert canonical_json_bytes(restored.view()) == canonical_json_bytes(session.view())
        assert canonical_json_bytes(module.snapshot(restored)) == raw

    def matches_stop(error):
        failures = [row['payload'] for row in records if row['record_type'] == 'attempt_stopped']
        assert stopped and len(failures) == 1
        assert failures[0] == dict(error_type=type(error).__name__, error=str(error))

    with patch('working_set_exp.observations.subprocess.Popen',
               side_effect=AssertionError('checker execution is prohibited during replay')):
        checkpoint('starting')
        starting, old_records = _inherited(module, session, run)
        assert session.candidate.candidate_id == CONTINUATION_ENTRY_ID
        assert (run / 'starting-candidate.json').read_bytes() == (module.PACKAGE / 'starting-candidate.json').read_bytes()
        for record in records:
            kind, payload = record['record_type'], record['payload']
            if kind == 'wire_input_prepared':
                request = study.read(_within(run, payload['stem'] + '-endpoint-request.json'))
                wire = _within(run, payload['stem'] + '-wire-request.json').read_bytes()
                assert payload['request_sha256'] == sha256_bytes(canonical_json_bytes(request))
                assert payload['wire_request_sha256'] == sha256_bytes(wire)
            elif kind == 'response_extracted':
                response = study.read(run / f"calls/{payload['id']}-endpoint-response.json")
                assert payload['finish_reason'] == response['choices'][0].get('finish_reason')
                assert payload['usage'] == response['usage']
            elif kind == 'reply_processed':
                assert processed and payload['id'] == processed[-1]
                host = study.read(run / f"calls/{payload['id']}-host-result.json")
                following = measure(session.view())
                assert payload['feedback_input_tokens'] == following
                assert payload['feedback_admitted'] == (following <= 23808 and not session.delivery_blocked)
                assert payload['no_next_model_receipt_yet'] is True
            elif kind == 'invocation_completed':
                assert processed and payload['id'] == processed[-1]
                response = study.read(run / f"calls/{payload['id']}-endpoint-response.json")
                host = study.read(run / f"calls/{payload['id']}-host-result.json")
                received = [r['payload'] for r in records if r['record_type'] == 'response_received'
                    and r['payload']['id'] == payload['id']]
                assert len(received) == 1 and payload['elapsed_seconds'] == received[0]['elapsed_seconds']
                assert payload['usage'] == response['usage']
                assert payload['actual_operations'] == len(host['operations'])
                assert payload['within_generation_reserve'] == (
                    response['usage']['completion_tokens'] <= module.ACTOR['generation_reserve'])
            elif kind == 'invocation_started':
                assert terminal is None and not session.submitted and not session.delivery_blocked
                tag = payload['id']
                assert tag == f'C{INHERITED_REQUESTS+len(starts)+1:02d}'
                assert session.requests_used == INHERITED_REQUESTS + len(starts)
                request = adapter.request_for(session.view())
                wire = (run / f'calls/{tag}-wire-request.json').read_bytes()
                assert wire == completion_request_bytes(request)
                assert wire == _within(run, payload['input_stem'] + '-wire-request.json').read_bytes()
                assert sha256_bytes(wire) == payload['wire_request_sha256'] and payload['completion_sent'] is True
                count = measure(session.view())
                assert count == payload['prompt_tokens'] <= 23808
                session.mark_delivered(session.view())
                session.begin_request()
                starts.append(tag)
                reply, terminal = _response(module, run, tag, count, stopped)
                if reply is None:
                    continue
                if 'operation' in reply and len(canonical_json_bytes(reply['operation'])) > MAX_ACTION_BYTES:
                    assert stopped and not (run / f'calls/{tag}-host-result.json').exists()
                    assert not list((run / 'calls').glob(f'{tag}-operation-*.json'))
                    terminal = 'public_operation_exceeds_host_allowance'
                    continue

                def operation(number, value):
                    assert value == study.read(run / f'calls/{tag}-operation-{number:02d}.json')
                    expected_operations.append(dict(id=tag, number=number, origin=value['origin']))
                    checkpoint(f'after/{tag}-O{number:02d}')

                try:
                    result = adapter.process_reply(session, reply, measure, adapter.preceding_feedback, operation)
                except Exception as error:
                    matches_stop(error)
                    assert not (run / f'calls/{tag}-host-result.json').exists()
                    terminal = 'public_reply_processing_stopped'
                    continue
                assert result == study.read(run / f'calls/{tag}-host-result.json')
                measure(session.view())
                processed.append(tag)
            elif kind == 'task_loop_completed':
                assert terminal is None
                checkpoint('final')
                expected = dict(sent_requests=INHERITED_REQUESTS + len(starts), actual_operations=session.calls_used,
                    candidate_id=session.candidate.candidate_id, current_check=session.check_state(), submitted=session.submitted)
                assert all(payload[k] == v for k, v in expected.items())
                assert payload['disposition'] == seal['disposition']
            elif kind == 'check_observation_preserved':
                handle = payload['observation']
                outcome = session.observations.read(handle)
                assert {key: payload[key] for key in outcome} == outcome

        ending = 'final' if (run / 'final-state.json').exists() else 'stopped'
        checkpoint(ending)
        assert checked_states == {p.relative_to(run).as_posix() for p in run.rglob('*-state.json')}
        assert checked_candidates == {p.relative_to(run).as_posix() for p in run.rglob('*-candidate.json')}
        assert checked_feedback == {p.relative_to(run).as_posix() for p in run.rglob('*-preceding-feedback.json')}
        assert expected_operations == [row['payload'] for row in records if row['record_type'] == 'contribution_operation']
        assert len(processed) == seal['processed_invocations'] == sum(r['record_type'] == 'invocation_completed' for r in records)
        assert len(starts) == seal['sent_requests']
        assert session.requests_used == INHERITED_REQUESTS + len(starts) <= MAXIMUM_REQUESTS
        assert seal['cumulative_requests_used'] == session.requests_used
        assert sum(r['record_type'] == 'response_received' for r in records) == seal['returned_responses']
        assert session.calls_used == seal['actual_operations']
        assert len(session.pairs) == session.calls_used and session.starting_archive_length == 0
        assert session.calls_used <= MAXIMUM_OPERATIONS
        assert seal['inherited_requests'] == INHERITED_REQUESTS
        assert seal['inherited_operations'] == INHERITED_OPERATIONS
        assert seal['new_operations'] == session.calls_used - INHERITED_OPERATIONS
        accounting_closed = [row['payload'] for row in records
                             if row['record_type'] == 'continuation_accounting_closed']
        assert accounting_closed == [dict(
            inherited_requests=INHERITED_REQUESTS, inherited_operations=INHERITED_OPERATIONS,
            new_dispatches=len(starts), cumulative_requests=INHERITED_REQUESTS + len(starts),
            displayed_requests_used=session.requests_used,
            new_operations=session.calls_used-INHERITED_OPERATIONS,
            cumulative_operations=session.calls_used,
            task_loop_completed_totals_are_cumulative=True,
            response_seal_dispatch_totals_are_new=True)]
        assert {p.relative_to(run).as_posix() for p in (run / 'calls').glob('*-operation-*.json')} == {
            f"calls/{row['id']}-operation-{row['number']:02d}.json" for row in expected_operations}
        observed = {}
        for pair in session.pairs:
            action, receipt = pair['response'], pair['result']
            if action['action'] != 'check' or not receipt.get('executed') or not receipt.get('observation'):
                continue
            handle = receipt['observation']
            outcome = session.observations.read(handle)
            assert outcome['candidate_id'] == receipt['checked_candidate_id'] == action['expected_candidate_id']
            assert outcome['checker_sha256'] == receipt['check_definition_sha256'] == sha256_bytes(session.checkers[action['check_id']])
            assert outcome['check_id'] == action['check_id']
            assert outcome['accepted'] == receipt['accepted'] is True and outcome['executed'] is True
            for key in ('passed', 'returncode', 'termination', 'capture_complete', 'streams'):
                assert receipt[key] == outcome[key]
            observed[handle] = dict(candidate_id=outcome['candidate_id'], checker_sha256=outcome['checker_sha256'],
                scope=outcome['check_id'], passed=outcome['passed'], termination=outcome['termination'],
                capture_complete=outcome['capture_complete'], streams=outcome['streams'])
        assert set(observed) == {
            r['payload']['observation'] for r in records if r['record_type'] == 'check_observation_preserved'}
        closed = [row['payload'] for row in records if row['record_type'] == 'runtime_closed']
        assert len(closed) == 1 and closed[0]['owned_server_shutdown_verified'] and closed[0]['dedicated_port_free']
        if seal['disposition'] == 'checked_submission':
            assert session.submitted and session.verification_view()['submission']['eligible']
            assert session.check_state()['passed'] and session.check_state()['applies_to_current']

    return dict(status='replayed_exactly', completed_new_replies=len(processed), new_requests=len(starts),
        inherited_requests=INHERITED_REQUESTS, cumulative_requests=session.requests_used,
        inherited_operations=INHERITED_OPERATIONS, new_operations=session.calls_used-INHERITED_OPERATIONS,
        cumulative_operations=session.calls_used, native_inputs=len(counts), custody_records=len(records),
        checked_state_snapshots=len(checked_states), source_files=len(seal['source_sha256']),
        fresh_original_entry=False, entry='saved_work_continuation_with_declared_extra_opportunity',
        original_entry_candidate_id=ORIGINAL_ENTRY_ID, initial_candidate_id=CONTINUATION_ENTRY_ID,
        original_run_seal_sha256=OLD_SEAL_SHA, inherited_custody_records=len(old_records), submitted=session.submitted,
        final_candidate_id=session.candidate.candidate_id, terminal_response=terminal,
        observations=observed, observations_replayed_without_execution=len(observed),
        source_closure_and_preparation_verified=True, every_saved_checkpoint_restored=True,
        no_additional_checker_execution=True, no_additional_model_inference=True, no_additional_tokenization=True,
        owned_runtime_closed=True, response_seal_sha256=sha256_file(run / 'RESPONSE_SEAL.json'),
        records_sha256=sha256_file(run / 'records.jsonl'),
        executed_manifest_sha256=sha256_file(run / 'EXECUTION_MANIFEST.json'),
        preparation_seal_sha256=manifest['preparation_seal_sha256'],
        verification_source_sha256=sha256_file(Path(__file__)), runner_source_sha256=sha256_file(RUNNER_PATH),
        interpretation_and_artifact_review_required=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or Path(__file__).with_name('VERIFICATION-' + args.version + '.json')
    try:
        value = verify(args.version)
    except BaseException as error:
        failure = output.with_name(output.stem + '-FAILED.json')
        payload = canonical_json_bytes(dict(status='verification_failed', type=type(error).__name__,
            message=str(error), traceback=traceback.format_exc(),
            verification_source_sha256=sha256_file(Path(__file__))))
        if failure.exists():
            assert failure.read_bytes() == payload, 'Preserve differing unsuccessful verification attempts separately'
        else:
            failure.parent.mkdir(parents=True, exist_ok=True)
            failure.write_bytes(payload)
        raise
    raw = canonical_json_bytes(value)
    if output.exists():
        assert output.read_bytes() == raw, 'Existing verification differs; preserve it'
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(raw)
    print(json.dumps(value, indent=2))
