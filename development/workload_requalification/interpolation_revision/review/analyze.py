"""Closed-run exact replay and measurements; no model or checker execution."""
import argparse
import inspect
import json
from pathlib import Path

import interpolation_continuation as study
from manage import load_helper
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


def save_once(path, name, value):
    target = path/name
    if target.exists():
        assert target.read_bytes() == canonical_json_bytes(value), 'Existing derived output differs: '+name
    else:
        study.save(path, name, value)


def main(version):
    area, run = study.AREA, study.AREA/f'run-{version}'
    assert (run/'RESPONSE_SEAL.json').exists(), 'Do not assess before normal recorded closure'
    replay = load_helper('interpolation_continuation_replay',
                        'development/decision_interface/reference_repair/verify_reference.py')
    replay.study = study
    result = replay.verify(run)
    starting = study.read(run/'starting-state.json')
    ending = study.read(run/('final-state.json' if (run/'final-state.json').exists() else 'stopped-state.json'))
    inherited = starting['continuation_accounting']
    assert inherited == study.ACCOUNTING == ending['continuation_accounting']
    assert starting['starting_archive_length'] == ending['starting_archive_length'] == 55
    assert len(starting['pairs']) == 89
    new_operations = len(ending['pairs'])-len(starting['pairs'])
    assert result['actual_operations'] == inherited['previous_contribution_operations'] + new_operations
    assert result['requests_used'] <= inherited['remaining_requests_allocated_here'] == 10
    result['new_continuation_operations'] = new_operations
    result['inherited_contribution_operations'] = inherited['previous_contribution_operations']
    result['inherited_prior_work_operations'] = starting['starting_archive_length']
    result['local_continuation_requests'] = result['requests_used']
    result['total_contribution_dispatches'] = inherited['previous_requests_dispatched'] + result['requests_used']
    result['inherited_unreturned_request'] = inherited['previous_request_without_saved_response']
    save_once(area/'review','VERIFICATION.json',result)

    metrics = load_helper('interpolation_continuation_metrics',
                         'development/decision_interface/reference_repair/review/assess_run.py')
    source = inspect.getsource(metrics.main)
    assert source.count("target='Lib/test/test_urlparse.py'") == 1
    source = source.replace("target='Lib/test/test_urlparse.py'", "target='Lib/test/test_configparser.py'")
    namespace = dict(metrics.__dict__,AREA=area,RUN=run)
    exec(compile(source,__file__+':target_adaptation','exec'),namespace)
    namespace['main']()
    assessment = study.read(area/'review/ASSESSMENT.json')
    assert assessment['totals']['operations'] == new_operations
    previous_cost = study.read(study.previous.AREA/'review/INTERRUPTION_AUDIT.json')
    cumulative = dict(
        prior_completed_request_seconds=previous_cost['completed_request_seconds'],
        prior_completed_generated_tokens=previous_cost['completed_generated_tokens'],
        prior_completed_prompt_tokens=previous_cost['completed_prompt_tokens'],
        new_request_seconds=assessment['totals']['request_seconds'],
        new_generated_tokens=assessment['totals']['generated_tokens'],
        new_prompt_tokens=assessment['totals']['input_tokens'],
        known_completed_request_seconds=previous_cost['completed_request_seconds']+assessment['totals']['request_seconds'],
        known_generated_tokens=previous_cost['completed_generated_tokens']+assessment['totals']['generated_tokens'],
        complete_attempt_cost_known=False,
        excluded_unknown_cost=inherited['previous_request_without_saved_response'],
        accounting=inherited)
    save_once(area/'review','CUMULATIVE_COST.json',cumulative)
    save_once(area/'review','ANALYSIS_PROVENANCE.json',dict(run=run.name,
        analysis_source_sha256=sha256_file(Path(__file__)),
        replay_source_sha256=sha256_file(study.ROOT/'development/decision_interface/reference_repair/verify_reference.py'),
        metrics_source_sha256=sha256_file(study.ROOT/'development/decision_interface/reference_repair/review/assess_run.py'),
        metrics_adaptation='Only target test filename changes from test_urlparse.py to test_configparser.py.',
        replay_adaptation='Task module substitution; verify and separately label inherited and new counters.',
        model_requests=0,checker_executions=0))
    print(json.dumps(result,indent=2),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--version',default='002')
    main(parser.parse_args().version)
