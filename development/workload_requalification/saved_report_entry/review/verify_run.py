"""Replay a closed, phase-aware saved-report attempt without executing checks.

Admission uses only the saved native measurements. Historical setup, actual
assisted acquisitions, public replies, and executed observations retain their
different origins. Mechanical replay does not assess semantic understanding.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap  # noqa: F401
import saved_report_task as study
import run_saved_report as execution
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.working_session import MAX_ACTION_BYTES


CAPTURE_AUDIT_PATH = study.compiler.AREA / 'review/verify_run.py'


def _within(root, name):
    path = (root / name).resolve()
    assert path.is_relative_to(root.resolve()), 'artifact address escapes its custody root'
    return path


def _inventory(root, seal, private_field):
    rows = seal['files']
    assert len({row['path'] for row in rows}) == len(rows)
    assert sha256_bytes(canonical_json_bytes(rows)) == seal['aggregate_sha256']
    for row in rows:
        path = _within(root, row['path'])
        assert path.stat().st_size == row['size_bytes'] and sha256_file(path) == row['sha256'], row['path']
    for name, digest in seal[private_field].items():
        assert sha256_file(_within(root / 'private-runtime', name)) == digest


def _preparation(module, seal):
    run, preparation = module.RUN, module.PACKAGE
    manifest = study.read(run / 'EXECUTION_MANIFEST.json')
    assert manifest['source_sha256'] == seal['source_sha256']
    assert manifest['source_sha256'] == module.source_identities()
    module.verify_sources(manifest['source_sha256'])
    assert manifest['actor'] == seal['actor'] == module.ACTOR
    assert manifest['seed'] == module.SEED
    assert (manifest['maximum_requests'], manifest['maximum_operations'],
            manifest['phase_request_limit'], manifest['phase_actor_operation_limit'],
            manifest['maximum_archival_operations'], manifest['supplied_operations']) == (
        16, 41, 8, 16, 44, 12)
    assert manifest['no_live_coaching'] is True and manifest['automatic_retry'] is False
    assert sha256_file(preparation / 'SEAL.json') == manifest['preparation_seal_sha256']
    proof = study.read(preparation / 'SEAL.json')
    assert proof['status'] == 'qualified_no_model_inference' and proof['completion_requests'] == 0
    assert proof['source_sha256'] == manifest['source_sha256']
    _inventory(preparation, proof, 'private_runtime_files_local_only')
    if (run / 'calls/C01-wire-request.json').exists():
        first = (run / 'calls/C01-wire-request.json').read_bytes()
        assert first == (preparation / 'initial-wire-request.json').read_bytes()
        assert sha256_bytes(first) == manifest['initial']['wire_request_sha256']
    return manifest


def _capture_auditor():
    spec = importlib.util.spec_from_file_location('saved_report_capture_auditor', CAPTURE_AUDIT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _native_counts(run, records, adapter):
    """Verify saved actual renderings and vocabulary counts; never tokenize again."""
    counts = {}
    for record in records:
        if record['record_type'] != 'native_input_prepared':
            continue
        row, stem = record['payload'], record['payload']['stem']
        request = study.read(run / (stem + '-endpoint-request.json'))
        key = sha256_bytes(canonical_json_bytes(request))
        native = (run / (stem + '-native.txt')).read_bytes()
        assert study.read(run / (stem + '-template-request.json')) == request
        assert study.read(run / (stem + '-tokens-request.json')) == dict(
            add_special=False, content=native.decode())
        assert native == adapter.expected_native(request)
        assert native == study.read(run / (stem + '-template.json'))['prompt'].encode()
        assert row['prompt_tokens'] == len(study.read(run / (stem + '-tokens.json'))['tokens'])
        assert row['request_sha256'] == key and row['native_sha256'] == sha256_bytes(native)
        assert row['physical_generation_space'] == adapter.ACTOR['context'] - row['prompt_tokens']
        assert (run / (stem + '-wire-request.json')).read_bytes() == completion_request_bytes(request)
        assert study.read(run / (stem + '-count.json')) == {
            field: row[field] for field in ('stem', 'prompt_tokens', 'physical_generation_space',
                                            'request_sha256', 'native_sha256')}
        assert key not in counts or counts[key] == row['prompt_tokens']
        counts[key] = row['prompt_tokens']
    return counts


def _response(run, tag, count, stopped):
    """Return only a recorded public reply; incomplete private text stays inert."""
    response = run / f'calls/{tag}-endpoint-response.json'
    reply = run / f'calls/{tag}-reply.json'
    host = run / f'calls/{tag}-host-result.json'
    operations = list((run / 'calls').glob(f'{tag}-operation-*.json'))

    def incomplete(reason):
        assert stopped and not reply.exists() and not host.exists() and not operations
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
    message = choice.get('message', {})
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
    usage = value.get('usage', {})
    details = usage.get('prompt_tokens_details', {}) if isinstance(usage, dict) else None
    timings = value.get('timings', {})
    valid_usage = (isinstance(usage, dict) and isinstance(details, dict) and isinstance(timings, dict)
        and all(type(usage.get(key)) is int for key in
        ('prompt_tokens', 'completion_tokens', 'total_tokens'))
        and usage['prompt_tokens'] == count and usage['completion_tokens'] > 0
        and usage['total_tokens'] == count + usage['completion_tokens'] <= study.ACTOR['context']
        and details.get('cached_tokens') == 0 and timings.get('cache_n') == 0)
    if not valid_usage:
        return incomplete('invalid_usage_or_cache_accounting')
    try:
        decoded = study.decode_reply(content)
    except (ValueError, TypeError, KeyError):
        return incomplete('malformed_or_unsupported_public_final')
    if not reply.exists():
        return incomplete('public_final_not_selected')
    assert decoded == study.read(reply)
    for suffix in ('content', 'reasoning'):
        assert (run / f'calls/{tag}-assistant-{suffix}.txt').exists()
    return decoded, None


def verify(version='001'):
    module = study.Task(version)
    run = module.RUN
    if not (run / 'RESPONSE_SEAL.json').is_file():
        raise ValueError('Do not replay an open model run')
    seal = study.read(run / 'RESPONSE_SEAL.json')
    _inventory(run, seal, 'private_runtime_files_local_only')
    manifest = _preparation(module, seal)
    for raw in (run / 'records.jsonl').read_bytes().splitlines():
        for artifact in load_json_strict(raw)['artifacts']:
            _within(run, artifact['path'])
    records = verify_records(run / 'records.jsonl', run)
    assert len(records) == seal['record_count']
    replay_module = study.Task(version, replay_folder=run)
    session = replay_module.initial_session()
    assert session.observations.replay is True
    adapter = execution.runner.Adapter(replay_module)
    counts = _native_counts(run, records, adapter)
    for record in records:
        if record['record_type'] == 'wire_input_prepared':
            row = record['payload']
            request = study.read(run / (row['stem'] + '-endpoint-request.json'))
            wire = (run / (row['stem'] + '-wire-request.json')).read_bytes()
            assert row['request_sha256'] == sha256_bytes(canonical_json_bytes(request))
            assert row['wire_request_sha256'] == sha256_bytes(wire)
        elif record['record_type'] == 'response_extracted':
            row = record['payload']
            response = study.read(run / f"calls/{row['id']}-endpoint-response.json")
            choice = response['choices'][0]
            assert row['finish_reason'] == choice.get('finish_reason') and row['usage'] == response['usage']
            for field, suffix in (('content', 'content'), ('reasoning_content', 'reasoning')):
                assert (choice['message'].get(field) or '').encode() == (
                    run / f"calls/{row['id']}-assistant-{suffix}.txt").read_bytes()

    def measure(view):
        key = sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
        assert key in counts, 'replay requires a missing actual native admission measurement'
        return counts[key]

    checked_states, checked_candidates, checked_feedback = set(), set(), set()

    def state_only(stem):
        name = stem + '-state.json'
        assert canonical_json_bytes(module.snapshot(session)) == (run / name).read_bytes(), name
        checked_states.add(name)

    def snapshot(stem):
        state_only(stem)
        name = stem + '-candidate.json'
        assert module.candidate_bytes(session.candidate) == (run / name).read_bytes(), name
        checked_candidates.add(name)
        name = stem + '-preceding-feedback.json'
        assert canonical_json_bytes(adapter.preceding_feedback) == (run / name).read_bytes(), name
        checked_feedback.add(name)
        for number, diff in session.diffs.items():
            assert (run / f'diffs/EVT-{number:04d}.patch').read_bytes() == diff.encode()

    snapshot('starting')
    starting = study.read(run / 'starting-state.json')
    inherited = study.starting_material()[1]
    assert starting['pairs'] == inherited and starting['starting_archive_length'] == 3
    assert starting['candidate_id'] == study.STARTING_ID
    assert starting['ranges'] == [] and starting['saved'] == {} and starting['requests_used'] == 0
    assert (run / 'starting-candidate.json').read_bytes() == (module.PACKAGE / 'starting-candidate.json').read_bytes()
    for sequence, pair in enumerate(inherited, 1):
        assert session.payload(f'RES-{sequence:04d}') == canonical_json_bytes(pair['result'])
    assert 'observation' not in inherited[2]['result'] and 'check_definition_sha256' not in inherited[2]['result']
    inventory, bodies = study.compiler.original_material()[3:]
    assert (run / 'imported-captures/inventory.json').read_bytes() == canonical_json_bytes(inventory)
    for handle, raw in bodies.items():
        assert (run / f'imported-captures/{handle}.json').read_bytes() == raw
    auditor = _capture_auditor()
    ending = 'final' if (run / 'final-state.json').exists() else 'stopped'
    final_state = study.read(run / (ending + '-state.json'))
    stopped = seal['disposition'] == 'stopped_without_retry'
    starts, processed, setup_phases, presentations, terminal = [], [], [], [], None
    setup_started, setup_completions = [], {}
    expected_setup, expected_operations = [], []
    restarted = False

    def matches_stop(error):
        failures = [row['payload'] for row in records if row['record_type'] == 'attempt_stopped']
        assert stopped and len(failures) == 1
        assert failures[0] == dict(type=type(error).__name__, message=str(error))

    # Replay is additionally guarded against any accidental subprocess path.
    with patch('working_set_exp.observations.subprocess.Popen',
               side_effect=AssertionError('checker execution is prohibited during replay')):
        for record in records:
            kind, payload = record['record_type'], record['payload']
            if kind == 'assisted_phase_setup_started':
                assert terminal is None
                phase = payload['phase']
                assert phase == len(setup_started)+1 and phase in (1, 2)
                assert payload['completion_sent'] is False
                if phase == 2:
                    assert restarted and session.transition_ready()
                state_only(f'setup/P{phase}-before')
                setup_started.append(phase)

                def acquisition(sequence, action, result):
                    expected_setup.append(dict(phase=phase, sequence=sequence,
                        model_action=False, completion_sent=False))
                    saved = study.read(run / f'setup/P{phase}-O{sequence:03d}.json')
                    assert saved == dict(action=action, result=result)
                    snapshot(f'setup/P{phase}-O{sequence:03d}')

                try:
                    sequences = module.setup(session, phase, measure, adapter.preceding_feedback, acquisition)
                except ValueError as error:
                    matches_stop(error)
                    assert not (run / f'setup/P{phase}-state.json').exists()
                    assert not any(row['record_type'] == 'assisted_phase_setup_completed'
                        and row['payload']['phase'] == phase for row in records)
                    terminal = 'assisted_setup_stopped'
                    continue
                snapshot(f'setup/P{phase}')
                setup_phases.append(phase)
                setup_completions[phase] = dict(phase=phase, sequences=sequences,
                    phase_counters=session.phase_counters(), completion_sent=False)
            elif kind == 'assisted_phase_setup_completed':
                assert payload == setup_completions[payload['phase']]
            elif kind == 'declared_working_context_restart':
                assert not restarted and session.transition_ready()
                snapshot('transition/P1')
                assert payload['candidate_id'] == session.candidate.candidate_id
                assert payload['phase_counters'] == session.phase_counters()
                assert payload['preceding_check_sequence'] == len(session.pairs)
                assert payload['semantic_assessment_used'] is False and payload['assisted'] is True
                assert payload['prior_thinking_reintroduced'] is False
                restarted = True
            elif kind == 'invocation_started':
                assert terminal is None and session.phase_budget_available()
                tag = payload['id']
                assert tag == f'C{len(starts)+1:02d}'
                request = adapter.request_for(session.view())
                wire = (run / f'calls/{tag}-wire-request.json').read_bytes()
                assert wire == completion_request_bytes(request)
                assert wire == (run / (payload['input_stem'] + '-wire-request.json')).read_bytes()
                assert sha256_bytes(wire) == payload['wire_request_sha256']
                assert payload['completion_sent'] is True
                count = measure(session.view())
                assert count == payload['prompt_tokens'] <= 23808
                envelope = load_json_strict(request['messages'][-1]['content'])
                shown = auditor._sent_capture_bytes(envelope, final_state['pairs'], inventory, bodies)
                entries = envelope['workspace']['imported_observations']['entries']
                assert session._shown_acquisitions(envelope['workspace']) == {
                    row['handle'] for row in entries if row['shown_complete']}
                presentations.append(dict(id=tag, phase=session.phase,
                    candidate_id=session.candidate.candidate_id, prompt_tokens=count,
                    phase_counters=session.phase_counters(), actual_capture_bytes_shown=shown))
                session.mark_delivered(session.view())
                session.begin_request()
                starts.append(tag)
                reply, terminal = _response(run, tag, count, stopped)
                if reply is None:
                    continue
                if 'operation' in reply and len(canonical_json_bytes(reply['operation'])) > MAX_ACTION_BYTES:
                    assert stopped and not (run / f'calls/{tag}-host-result.json').exists()
                    assert not list((run / 'calls').glob(f'{tag}-operation-*.json'))
                    terminal = 'public_operation_exceeds_host_allowance'
                    continue

                def operation(number, value):
                    saved = study.read(run / f'calls/{tag}-operation-{number:02d}.json')
                    assert value == saved
                    expected_operations.append(dict(id=tag, number=number, origin=value['origin']))
                    snapshot(f'after/{tag}-O{number:02d}')

                try:
                    result = adapter.process_reply(session, reply, measure, adapter.preceding_feedback, operation)
                except ValueError as error:
                    matches_stop(error)
                    assert not (run / f'calls/{tag}-host-result.json').exists()
                    terminal = 'public_reply_processing_stopped'
                    continue
                assert result == study.read(run / f'calls/{tag}-host-result.json')
                measure(session.view())
                processed.append(tag)
            elif kind == 'task_loop_completed':
                assert terminal is None
                snapshot('final')
                for key, value in dict(sent_requests=len(starts), actual_operations=session.calls_used,
                    archival_operations=len(session.pairs), phase_counters=session.phase_counters(),
                    candidate_id=session.candidate.candidate_id, current_check=session.check_state(),
                    submitted=session.submitted).items():
                    assert payload[key] == value
                assert payload['disposition'] == seal['disposition']

    snapshot(ending)
    assert checked_states == {p.relative_to(run).as_posix() for p in run.rglob('*-state.json')}
    assert checked_candidates == {p.relative_to(run).as_posix() for p in run.rglob('*-candidate.json')}
    assert checked_feedback == {p.relative_to(run).as_posix() for p in run.rglob('*-preceding-feedback.json')}
    assert expected_setup == [row['payload'] for row in records if row['record_type'] == 'assisted_acquisition']
    assert expected_operations == [row['payload'] for row in records if row['record_type'] == 'contribution_operation']
    assert len(processed) == sum(row['record_type'] == 'invocation_completed' for row in records)
    assert len(starts) == seal['sent_requests'] == session.requests_used
    assert len(processed) == seal['processed_invocations']
    assert sum(row['record_type'] == 'response_received' for row in records) == seal['returned_responses']
    assert session.calls_used == seal['actual_operations']
    assert len(session.pairs) == seal['archival_operations']
    assert session.phase_counters() == seal['phase_counters']
    assert final_state['imported_capture_state'] == starting['imported_capture_state']
    restored = module.restore(final_state, session.candidate, run, replay=True)
    assert canonical_json_bytes(restored.view()) == canonical_json_bytes(session.view())
    observed = {}
    for pair in session.pairs[3:]:
        action, receipt = pair['response'], pair['result']
        if action['action'] == 'check' and receipt.get('executed') and receipt.get('observation'):
            handle = receipt['observation']
            outcome = session.observations.read(handle)
            assert outcome['candidate_id'] == receipt['checked_candidate_id'] == action['expected_candidate_id']
            assert outcome['checker_sha256'] == receipt['check_definition_sha256']
            assert outcome['check_id'] == action['check_id']
            assert outcome['accepted'] == receipt['accepted'] is True
            assert outcome['executed'] == receipt['executed'] is True
            for key in ('passed', 'returncode', 'termination', 'capture_complete', 'streams'):
                if key in receipt:
                    assert receipt[key] == outcome[key]
            observed[handle] = dict(candidate_id=outcome['candidate_id'], checker_sha256=outcome['checker_sha256'],
                passed=outcome['passed'], termination=outcome['termination'], capture_complete=outcome['capture_complete'],
                captured_stream_bytes=sum(meta['captured_bytes'] for meta in outcome['streams'].values()))
    closed = [row['payload'] for row in records if row['record_type'] == 'runtime_closed']
    assert len(closed) == 1 and closed[0]['owned_server_shutdown_verified'] and closed[0]['dedicated_port_free']
    if seal['disposition'] == 'checked_submission':
        assert session.phase == 2 and session.submitted
        assert session.check_state()['passed'] and session.check_state()['applies_to_current']
    if seal['disposition'] == 'phase_one_early_submission_attempt':
        assert session.phase == 1 and session.early_phase_one_submit and not session.submitted
    return dict(status='replayed_exactly', completed_replies=len(processed), requests_used=len(starts),
        actual_operations=session.calls_used, archival_operations=len(session.pairs),
        inherited_operations=3, assisted_operations_new=len(session.setup_sequences),
        actor_operations=session.actor_operations_used(), phase_counters=session.phase_counters(),
        setup_phases=setup_phases, setup_phases_started=setup_started,
        declared_restart_replayed=restarted, terminal_response=terminal,
        native_inputs=len(counts), custody_records=len(records), checked_state_snapshots=len(checked_states),
        source_files=len(seal['source_sha256']), source_closure_and_preparation_verified=True,
        submitted=session.submitted, observations=observed, observations_replayed_without_execution=len(observed),
        capture_presentations=presentations, actual_capture_bytes_and_historical_bindings_verified=True,
        no_additional_checker_execution=True, no_additional_model_inference=True, no_additional_tokenization=True,
        owned_runtime_closed=True, executed_manifest_sha256=sha256_file(run / 'EXECUTION_MANIFEST.json'),
        preparation_seal_sha256=manifest['preparation_seal_sha256'],
        verification_source_sha256=sha256_file(Path(__file__)), capture_audit_source_sha256=sha256_file(CAPTURE_AUDIT_PATH),
        interpretation_review_required=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    value = verify(args.version)
    output = args.output or Path(__file__).with_name('VERIFICATION-' + args.version + '.json')
    raw = canonical_json_bytes(value)
    if output.exists():
        assert output.read_bytes() == raw, 'Existing verification differs; preserve it'
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(raw)
    print(json.dumps(value, indent=2))
