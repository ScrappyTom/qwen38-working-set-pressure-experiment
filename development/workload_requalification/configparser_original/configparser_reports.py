"""Bounded, source-checked interpretation of full original-backport observations."""
import copy

from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes
from working_set_exp.observations import text_tail

SUITES = ('upstream', 'contract', 'candidate_tests', 'new_tests_on_original')
COUNTS = ('tests', 'failures', 'errors', 'skipped')
SCHEMA = 'configparser-original-v1'


def utf8_text(value):
    if not isinstance(value, str):
        return False
    try:
        value.encode('utf-8')
    except UnicodeError:
        return False
    return True


def supported_shape(value):
    if not isinstance(value, dict) or value.get('observation_schema') != SCHEMA:
        return False
    flags = ('passed', 'regression_detects_original', 'documentation_directive_present',
             'documentation_semantics_require_direct_review')
    if any(type(value.get(k)) is not bool for k in flags):
        return False
    if value['documentation_semantics_require_direct_review'] is not True:
        return False
    for name in SUITES:
        row = value.get(name)
        if not isinstance(row, dict) or type(row.get('successful')) is not bool:
            return False
        if any(type(row.get(k)) is not int or row[k] < 0 for k in COUNTS):
            return False
        if not utf8_text(row.get('runner_output')) or not isinstance(row.get('details'), list):
            return False
        if any(not isinstance(d, dict) or not utf8_text(d.get('test')) or
               not utf8_text(d.get('trace')) for d in row['details']):
            return False
        if len(row['details']) != row['failures'] + row['errors']:
            return False
        if row['successful'] and (row['failures'] or row['errors']):
            return False
    added = value.get('added_tests')
    if not isinstance(added, list) or any(not utf8_text(v) for v in added) or len(added) != len(set(added)):
        return False
    detected = bool(added) and not value['new_tests_on_original']['successful']
    passed = all(value[k]['successful'] for k in SUITES[:3]) and detected and value['documentation_directive_present']
    return detected is value['regression_detects_original'] and passed is value['passed']


def bounded_text(raw, byte_limit=1536, serialized_limit=2048):
    value = text_tail(raw, byte_limit)
    while len(canonical_json_bytes(value)) > serialized_limit:
        byte_limit //= 2
        value = text_tail(raw, byte_limit)
    return value


def diagnostic(row):
    return dict(test=bounded_text(row['test'].encode('utf-8'), 320, 512),
        diagnostic=bounded_text(row['trace'].encode('utf-8'), 1536, 2048),
        exact_test_sha256=sha256_bytes(row['test'].encode('utf-8')),
        exact_trace_sha256=sha256_bytes(row['trace'].encode('utf-8')))


def assessment(store, handle, contract=None):
    record = store.read(handle)
    if contract and contract['checker_sha256'] != record['checker_sha256']:
        raise ValueError('check interpretation belongs to another checker')
    stdout = (store.directory(handle) / 'stdout.bin').read_bytes()
    stderr = (store.directory(handle) / 'stderr.bin').read_bytes()
    try:
        full = load_json_strict(stdout)
    except (ValueError, UnicodeError):
        full = None
    known = supported_shape(full)
    normal = record['capture_complete'] and record['termination'] == 'completed'
    result = dict(observation=handle, scope=record['check_id'], candidate_id=record['candidate_id'],
        checker_sha256=record['checker_sha256'], executed=record['executed'], passed=record['passed'],
        termination=record['termination'], returncode=record['returncode'],
        observation_capture_complete=record['capture_complete'], assessment_available=known,
        reported_passed=full['passed'] if known else None,
        report_execution_consistent=(record['passed'] == full['passed']) if known and normal else None,
        raw_access=dict(action='inspect_observation', observation=handle, stream='stdout', offset=0),
        stderr_access=dict(action='inspect_observation', observation=handle, stream='stderr', offset=0),
        documentation_accuracy_automatically_established=False,
        existing_test_text_preservation_automatically_established=False)
    rows = []
    if known:
        meanings = {'upstream': 'Frozen upstream tests run on the current parser.',
                    'contract': 'Independent requested backport behavior runs on the current parser.',
                    'candidate_tests': 'The current edited test module runs on the current parser.'}
        for name in SUITES[:3]:
            part = full[name]
            row = dict(criterion=name + '.execution', met=part['successful'], meaning=meanings[name],
                counts={k:part[k] for k in COUNTS}, diagnostics=[diagnostic(d) for d in part['details'][:2]],
                diagnostics_total=len(part['details']), diagnostics_shown=min(2, len(part['details'])),
                diagnostics_remaining=max(0, len(part['details'])-2),
                diagnostic_access=dict(result['raw_access']))
            if not part['successful'] and not part['details']:
                row.update(runner_diagnostic=bounded_text(part['runner_output'].encode('utf-8')),
                    runner_output_sha256=sha256_bytes(part['runner_output'].encode('utf-8')),
                    diagnostic_note='No structured failure/error trace was emitted. This exact runner-output excerpt may identify another unsuccessful outcome, such as an unexpected success; full output remains in the observation.')
            rows.append(row)
        original = full['new_tests_on_original']
        rows.append(dict(criterion='regression_detects_original', met=full['regression_detects_original'],
            meaning='At least one current added test must fail or error against the original parser. This expected comparison failure is detection, not a current-library failure.',
            original_parser_comparison={k:original[k] for k in (*COUNTS, 'successful')},
            comparison_failure_is_expected=True,
            current_suites_successful=all(full[k]['successful'] for k in SUITES[:3]),
            added_test_count=len(full['added_tests']),
            added_tests=[bounded_text(v.encode('utf-8'), 320, 512) for v in full['added_tests'][:4]],
            added_tests_shown=min(4, len(full['added_tests'])), added_tests_remaining=max(0, len(full['added_tests'])-4),
            detail_access=dict(result['raw_access'])))
        rows.append(dict(criterion='documentation_directive_present', met=full['documentation_directive_present'],
            meaning='The exception declaration is present; this is not a check of documentation accuracy.'))
    if not known or not normal or record['passed'] != full['passed']:
        rows.insert(0, dict(criterion='public_execution', met=bool(normal and record['passed']),
            meaning=('Actual checker execution and captured output; no structured acceptance criteria inferred.' if not known else
                     'Actual execution must complete normally. A printed report alone does not establish completed verification.'),
            termination=record['termination'], returncode=record['returncode'],
            structured_report_recognized=known,
            stdout=bounded_text(stdout), stderr=bounded_text(stderr)))
    rows.sort(key=lambda r:r['met'] is not False)
    result.update(criteria=rows, failed_criteria=[r['criterion'] for r in rows if r['met'] is False],
        explanation=('Current suites must pass, added tests must detect the original parser, and the exception declaration must exist. '
                     'Expected old-parser comparison failures are separate from current failures. tests counts executed methods; '
                     'failure/error counts may include multiple subtest outcomes and are not added-method counts. Exact observations remain accessible. '
                     'Accurate prose and preservation of existing tests require direct review.'))
    return result


def overview(value):
    result = copy.deepcopy(value)
    rows = [r for r in result['criteria'] if r['met'] is not True]
    # Ordinary suite failures precede optional detail about the old-parser run.
    result.update(criteria=rows[:3], failed_records_total=len(rows),
                  failed_records_shown=min(3, len(rows)), failed_records_remaining=max(0, len(rows)-3))
    for row in result['criteria']:
        if 'diagnostics' in row:
            row['diagnostics'] = row['diagnostics'][:1]
            row['diagnostics_shown'] = len(row['diagnostics'])
            row['diagnostics_remaining'] = row['diagnostics_total'] - row['diagnostics_shown']
    return result


def inspect_check(store, handle, offset, contract=None):
    value = assessment(store, handle, contract)
    rows = value.pop('criteria')
    if type(offset) is not int or not 0 <= offset <= len(rows):
        raise ValueError('assessment offset is outside complete records')
    page = rows[offset:offset+4]
    return dict(accepted=True, kind='check_criteria', **value, entries=page, offset=offset,
        total_records=len(rows), next_offset=offset+len(page) if offset+len(page)<len(rows) else None,
        records_complete=True, all_records_shown=offset == 0 and len(page) == len(rows))
