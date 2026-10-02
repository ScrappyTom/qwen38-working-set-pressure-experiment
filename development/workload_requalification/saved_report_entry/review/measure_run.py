"""Descriptive accounting for a sealed saved-report run; no runtime requests.

Totals establish recorded cost and outcomes, not repetition, evidence adequacy,
causal performance, or the quality of the saved report.
"""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap  # noqa: F401
import saved_report_task as study
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


VERIFIER_PATH = Path(__file__).with_name('verify_run.py')


def _verifier():
    spec = importlib.util.spec_from_file_location('saved_report_metric_custody', VERIFIER_PATH)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def _counts(rows):
    return dict(sorted(Counter(row['response']['action'] for row in rows).items()))


def _valid_usage(value, prompt):
    return (isinstance(value, dict) and all(type(value.get(key)) is int for key in
        ('prompt_tokens', 'completion_tokens', 'total_tokens'))
        and value['prompt_tokens'] == prompt and value['completion_tokens'] >= 0
        and value['total_tokens'] == value['prompt_tokens'] + value['completion_tokens'])


def _tokens(rows):
    valid = [row['usage'] for row in rows if row['usable_usage']]
    return dict(requests_with_usable_usage=len(valid),
        input_tokens=sum(row['prompt_tokens'] for row in valid),
        generated_tokens=sum(row['completion_tokens'] for row in valid),
        input_plus_generated_tokens=sum(row['total_tokens'] for row in valid),
        maximum_input_plus_generation=max((row['total_tokens'] for row in valid), default=None),
        maximum_generated_tokens=max((row['completion_tokens'] for row in valid), default=None),
        requests_without_usable_usage=[row['id'] for row in rows if not row['usable_usage']])


def _seconds(rows):
    known = [row['model_request_seconds'] for row in rows
        if type(row['model_request_seconds']) in (int, float)]
    return dict(known_requests=len(known), seconds=sum(known),
        requests_without_elapsed_time=[row['id'] for row in rows
            if type(row['model_request_seconds']) not in (int, float)])


def measure(version='001'):
    module = study.Task(version)
    run = module.RUN
    if not (run / 'RESPONSE_SEAL.json').is_file():
        raise ValueError('Do not measure or publish an open model run')
    seal = study.read(run / 'RESPONSE_SEAL.json')
    custody = _verifier()
    custody._inventory(run, seal, 'private_runtime_files_local_only')
    manifest = custody._preparation(module, seal)
    records = verify_records(run / 'records.jsonl', run)
    assert len(records) == seal['record_count']
    ending = 'final' if (run / 'final-state.json').exists() else 'stopped'
    state = study.read(run / (ending + '-state.json'))
    pairs = state['pairs']
    assert state['starting_archive_length'] == study.INHERITED_OPERATIONS == 3
    assert pairs[:3] == study.starting_material()[1]
    assisted = set(state['saved_report_state']['setup_sequences'])
    setup_pairs = [row for sequence, row in enumerate(pairs, 1) if sequence in assisted]
    actor_pairs = [row for sequence, row in enumerate(pairs, 1) if sequence > 3 and sequence not in assisted]
    setup_records = [row['payload'] for row in records if row['record_type'] == 'assisted_acquisition']
    assert {row['sequence'] for row in setup_records} == assisted
    assert len(setup_records) == len(assisted)
    assert len(pairs)-3 == seal['actual_operations']
    assert len(pairs) == seal['archival_operations']

    starts = [row['payload'] for row in records if row['record_type'] == 'invocation_started']
    received = {row['payload']['id']: row['payload'] for row in records
                if row['record_type'] == 'response_received'}
    completed = {row['payload']['id']: row['payload'] for row in records
                 if row['record_type'] == 'invocation_completed'}
    operation_records = [row['payload'] for row in records if row['record_type'] == 'contribution_operation']
    actor_by_tag = {row['id']: [] for row in starts}
    origins = Counter()
    actual_actor_records = []
    for row in operation_records:
        saved = study.read(run / f"calls/{row['id']}-operation-{row['number']:02d}.json")
        assert saved['origin'] == row['origin']
        actor_by_tag[row['id']].append(saved)
        origins[saved['origin']] += 1
        actual_actor_records.append(dict(response=saved['action'], result=saved['result']))
    assert actual_actor_records == actor_pairs
    assert len(starts) == seal['sent_requests'] == state['requests_used']
    assert len(received) == seal['returned_responses']
    assert len(completed) == seal['processed_invocations']

    calls, settings = [], []
    for index, started in enumerate(starts, 1):
        tag = started['id']
        assert tag == f'C{index:02d}'
        request = study.read(run / f'calls/{tag}-wire-request.json')
        assert sha256_file(run / f'calls/{tag}-wire-request.json') == started['wire_request_sha256']
        workspace = load_json_strict(request['messages'][-1]['content'])['workspace']
        counter = workspace['saved_report_phase']
        phase = counter['phase']
        assert phase in (1, 2) and counter['phase_requests_limit'] == 8
        assert 0 <= counter['phase_requests_used'] < 8
        assert counter['cumulative_requests_used'] == index-1
        response_path = run / f'calls/{tag}-endpoint-response.json'
        response = None
        if response_path.exists():
            try:
                response = study.read(response_path)
            except (ValueError, TypeError):
                pass
        usage = response.get('usage') if isinstance(response, dict) else None
        usable = _valid_usage(usage, started['prompt_tokens'])
        finished = tag in completed
        if finished:
            assert usable and completed[tag]['usage'] == usage
            assert completed[tag]['actual_operations'] == len(actor_by_tag[tag])
            assert completed[tag]['elapsed_seconds'] == received[tag]['elapsed_seconds']
        choices = response.get('choices') if isinstance(response, dict) else None
        finish_reason = choices[0].get('finish_reason') if (
            isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict)) else None
        call = dict(id=tag, phase=phase, phase_request_number=counter['phase_requests_used']+1,
            prompt_tokens_sent=started['prompt_tokens'], returned=tag in received,
            completed_invocation=finished, finish_reason=finish_reason,
            usage=usage, usable_usage=usable, model_request_seconds=received.get(tag, {}).get('elapsed_seconds'),
            endpoint_timings=response.get('timings') if isinstance(response, dict) else None,
            recorded_operations=len(actor_by_tag[tag]),
            accounts=sum(row['action']['action'] == 'record_account' for row in actor_by_tag[tag]),
            other_actor_operations=sum(row['action']['action'] != 'record_account' for row in actor_by_tag[tag]),
            within_prospective_generation_reserve=(usage['completion_tokens'] <= module.ACTOR['generation_reserve']
                if usable else None))
        calls.append(call)
        settings.append({key: request.get(key) for key in
            ('model', 'seed', 'chat_template_kwargs', 'temperature', 'top_k', 'top_p', 'min_p',
             'max_tokens', 'n_predict', 'thinking_budget_tokens', 'reasoning_budget_tokens',
             'cache_prompt', 'frequency_penalty', 'presence_penalty', 'repeat_penalty', 'stream')})
        assert request['seed'] == module.SEED
        assert request['chat_template_kwargs'] == dict(enable_thinking=True, reasoning_effort=module.ACTOR['effort'])
    assert not settings or all(row == settings[0] for row in settings)

    phase_rows = []
    for phase in (1, 2):
        rows = [row for row in calls if row['phase'] == phase]
        setup = [row for row in setup_records if row['phase'] == phase]
        if not rows and not setup:
            continue
        assert [row['phase_request_number'] for row in rows] == list(range(1, len(rows)+1))
        operations = sum(row['recorded_operations'] for row in rows)
        assert len(rows) <= 8 and operations <= 16
        phase_rows.append(dict(phase=phase, sent_requests=len(rows), returned_responses=sum(row['returned'] for row in rows),
            completed_invocations=sum(row['completed_invocation'] for row in rows),
            request_limit=8, actor_operation_limit=16, actor_operations=operations,
            account_operations=sum(row['accounts'] for row in rows),
            other_actor_operations=sum(row['other_actor_operations'] for row in rows),
            assisted_operations=len(setup), request_opportunity_unused=8-len(rows),
            actor_operation_opportunity_unused=16-operations, reported_tokens=_tokens(rows),
            recorded_model_time=_seconds(rows)))

    transition = [row['payload'] for row in records if row['record_type'] == 'declared_working_context_restart']
    assert len(transition) <= 1
    if transition:
        assert state['saved_report_state']['phase'] == 2
        assert transition[0]['preceding_check_sequence'] == state['saved_report_state']['phase_start_archive_length']
        sequence = transition[0]['preceding_check_sequence']
        boundary = pairs[sequence-1]
        assert boundary['response']['action'] == 'check' and boundary['response']['check_id'] == 'public'
        assert boundary['result'].get('accepted') is True and boundary['result'].get('executed') is True
    loop = [row['payload'] for row in records if row['record_type'] == 'task_loop_completed']
    assert len(loop) <= 1
    closed = [row['payload'] for row in records if row['record_type'] == 'runtime_closed']
    assert len(closed) == 1
    assert closed[0]['owned_server_shutdown_verified'] and closed[0]['dedicated_port_free']
    rejected, failed_checks, accepted_checks = [], [], []
    for sequence, pair in enumerate(pairs, 1):
        if sequence <= 3:
            continue
        origin = 'assisted_setup' if sequence in assisted else 'actor'
        row = dict(sequence=sequence, origin=origin, action=pair['response']['action'],
            accepted=pair['result'].get('accepted'), executed=pair['result'].get('executed'),
            observation=pair['result'].get('observation'))
        if pair['result'].get('accepted') is False:
            rejected.append({**row, 'error': pair['result'].get('error')})
        if pair['response']['action'] == 'check' and pair['result'].get('executed') is True:
            accepted_checks.append({**row, 'passed': pair['result'].get('passed'),
                'checked_candidate_id': pair['result'].get('checked_candidate_id'),
                'check_definition_sha256': pair['result'].get('check_definition_sha256')})
            if pair['result'].get('passed') is False:
                failed_checks.append(accepted_checks[-1])
    native_rows = [row['payload'] for row in records if row['record_type'] == 'native_input_prepared']
    accounting = seal['phase_counters']
    assert accounting['actor_operations_used'] == len(actor_pairs)
    assert accounting['assisted_operations_new'] == len(setup_pairs)
    assert accounting['archived_operations'] == len(pairs)
    return dict(status='measured_closed_record', classification='assisted two-phase saved-work continuation; no live coaching',
        disposition=seal['disposition'], seed=module.SEED, actor=module.ACTOR,
        effective_request_settings=settings[0] if settings else None,
        sent_requests=len(starts), returned_responses=len(received), completed_invocations=len(completed),
        sent_without_response=[row['id'] for row in calls if not row['returned']],
        returned_without_completed_invocation=[row['id'] for row in calls if row['returned'] and not row['completed_invocation']],
        sent_input_tokens=sum(row['prompt_tokens_sent'] for row in calls),
        completed_token_totals=_tokens([row for row in calls if row['completed_invocation']]),
        returned_token_totals=_tokens([row for row in calls if row['returned']]),
        completed_model_request_time=_seconds([row for row in calls if row['completed_invocation']]),
        returned_model_request_time=_seconds([row for row in calls if row['returned']]),
        task_loop_seconds=loop[0]['task_loop_seconds'] if loop else None,
        task_loop_time_unavailable_reason=None if loop else 'The stopped attempt recorded no task_loop_completed duration.',
        peak_sent_input_tokens=max((row['prompt_tokens_sent'] for row in calls), default=None),
        peak_native_admission_tokens=max((row['prompt_tokens'] for row in native_rows), default=None),
        native_admission_trials=len(native_rows),
        native_peak_includes_unsent_capacity_trials=True,
        output_exceeding_prospective_reserve=[row['id'] for row in calls
            if row['within_prospective_generation_reserve'] is False],
        inherited_operations=3, inherited_action_counts=_counts(pairs[:3]),
        assisted_new_operations=len(setup_pairs), assisted_new_action_counts=_counts(setup_pairs),
        total_assisted_operations=3+len(setup_pairs), actor_operations=len(actor_pairs),
        actor_action_counts=_counts(actor_pairs), actor_operation_origins=dict(sorted(origins.items())),
        backend_new_operations=len(pairs)-3, maximum_backend_new_operations=41,
        archival_operations=len(pairs), maximum_archival_operations=44,
        final_phase_counters=accounting, phases=phase_rows,
        declared_restart=transition[0] if transition else None,
        unused_phase_one_opportunity_expired=bool(transition), rejected_operations=rejected,
        executed_checks=accepted_checks, failed_executed_checks=failed_checks,
        gpu_sampled_memory=seal['memory'], runtime_evidence=seal['runtime'],
        runtime_closed=closed[0], dedicated_port_free_at_seal=seal['port_free'],
        calls=calls, response_seal_sha256=sha256_file(run / 'RESPONSE_SEAL.json'),
        executed_manifest_sha256=sha256_file(run / 'EXECUTION_MANIFEST.json'),
        preparation_seal_sha256=manifest['preparation_seal_sha256'],
        metrics_source_sha256=sha256_file(Path(__file__)), custody_helper_sha256=sha256_file(VERIFIER_PATH),
        no_additional_model_inference=True, no_additional_checker_execution=True, no_additional_native_requests=True,
        interpretation_limit='Totals do not establish semantic adequacy, duplicate work, learning from failures, causal benefit, or artifact correctness.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    value = measure(args.version)
    output = args.output or Path(__file__).with_name('METRICS-' + args.version + '.json')
    raw = canonical_json_bytes(value)
    if output.exists():
        assert output.read_bytes() == raw, 'Existing metrics differ; preserve them'
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(raw)
    print(json.dumps(value, indent=2))
