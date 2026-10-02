"""Task-local interpretation of full original URL checker observations.

Real candidate failures precede optional mutation detail. Failure of an injected
run means detection only after the ordinary execution and required paths pass.
Original aggregate sensitivity is retained; no per-target requirement is invented.
"""
from __future__ import annotations

import copy

from working_set_exp import coherent_diagnostics as prior
from working_set_exp.jsonutil import load_json_strict
from working_set_exp.observations import text_tail

from checkers import FAULTS


def assessment(store, handle, contract=None):
    value = prior.assessment(store, handle, contract)
    record = store.read(handle)
    value.update(termination=record['termination'], returncode=record['returncode'])
    if not value['assessment_available']:
        value['execution_diagnostic'] = dict(
            meaning='Captured execution output; no supported acceptance criteria are inferred from it.',
            stdout=text_tail((store.directory(handle) / 'stdout.bin').read_bytes(), 3072),
            stderr=text_tail((store.directory(handle) / 'stderr.bin').read_bytes(), 3072))
        return value
    full = load_json_strict((store.directory(handle) / 'stdout.bin').read_bytes())
    normal = all(full.get(key, {}).get('successful') is True
        for key in ('saved_suite', 'edited_suite', 'observed_paths'))
    normal = normal and full.get('observed_paths', {}).get('complete') is True
    faults = full.get('fault_sensitivity', {})
    if value['scope'] in ('tests', 'public') and set(faults) != set(FAULTS):
        raise ValueError('URL fault report does not identify the original seven faults')
    for row in value['criteria']:
        if row['criterion'] == 'required_paths':
            row['meaning'] = ('New tests must access port through both original APIs, text and ASCII bytes, '
                'for the declared ordinary input categories; Unicode decimal text is also required. '
                'This concerns the normal unmodified run only.')
        if not row['criterion'].startswith('detect.'):
            continue
        raw = faults[row['criterion'][7:]]
        detected = bool(raw['tests'] and not raw['successful']) if normal else None
        row.update(met=detected, fault_detected=detected, normal_control_passed=normal,
            test_run_passed=raw['successful'], injected_suite_executed=True,
            injected_suite_tests=raw['tests'], mutation_path_coverage_is_required=False,
            meaning=('With successful ordinary execution and required path coverage, the added tests '
                'must run at least one test and not succeed under this one injected fault. This is the original aggregate '
                'sensitivity rule, not a requirement for every mutation path to be exercised.'),
            observed=('The injected suite executed. Detection assessment is blocked: the real unmodified candidate '
                'or required coverage failed; '
                'a mutation-run failure is not independent detection evidence.' if not normal else
                'Injected run did not succeed as expected: this fault was detected.' if detected else
                'Injected run passed or had no tests: this fault was not detected.'))
    value['criteria'].sort(key=lambda row: (row['met'] is not False, row['met'] is not None))
    value['failed_criteria'] = [row['criterion'] for row in value['criteria'] if row['met'] is False]
    value['unassessed_criteria'] = [row['criterion'] for row in value['criteria'] if row['met'] is None]
    value['normal_control_passed'] = normal if value['scope'] in ('tests', 'public') else None
    value['explanation'] = ('The current candidate must pass ordinary execution, normal required-path coverage '
        'and preservation. Then failures under the original seven injected faults mean detection. '
        'Mutation-run missing paths are not new task requirements. Added examples must execute successfully '
        'under their scope; prose and account truth require separate review. Exact full observations remain recoverable.')
    return value


def overview(value):
    result = prior.overview(value)
    failed = sum(row['met'] is False for row in value['criteria'])
    failed_shown = sum(row['met'] is False for row in result['criteria'])
    unassessed = sum(row['met'] is None for row in value['criteria'])
    unassessed_shown = sum(row['met'] is None for row in result['criteria'])
    result.update(failed_records_total=failed, failed_records_shown=failed_shown,
        failed_records_remaining=failed-failed_shown,
        unassessed_records_total=unassessed, unassessed_records_shown=unassessed_shown,
        unassessed_records_remaining=unassessed-unassessed_shown)
    return result


def inspect_check(store, handle, offset, contract=None):
    value = assessment(store, handle, contract)
    rows = value.pop('criteria')
    if type(offset) is not int or not 0 <= offset <= len(rows):
        raise ValueError('URL criterion offset is outside complete records')
    page = copy.deepcopy(rows[offset:offset+4])
    return dict(accepted=True, kind='check_criteria', **value, entries=page,
        offset=offset, total_records=len(rows),
        next_offset=offset+len(page) if offset+len(page)<len(rows) else None,
        records_complete=True, all_records_shown=offset == 0 and len(page) == len(rows))
