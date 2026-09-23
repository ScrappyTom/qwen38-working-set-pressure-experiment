"""Unqualified preparation: distinguish current execution from injected faults.

No active run imports this adapter. Acceptance comes from the pinned checker;
this module only gives its actual observations bounded, recoverable presentation.
"""
import copy

import configparser_reports as common
from diagnostic_reports import fragments
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict

SCHEMA = 'exception-transport-v1'
SUITES = ('saved_suite', 'edited_suite', 'contract', 'transports')
FAULTS = ('changed_source', 'changed_line_number', 'stripped_raw_line', 'lost_errors')
COUNTS = common.COUNTS


def suite_shape(row):
    if not isinstance(row, dict) or type(row.get('successful')) is not bool:
        return False
    if any(type(row.get(k)) is not int or row[k] < 0 for k in COUNTS):
        return False
    details = row.get('details')
    if not isinstance(details, list) or not common.utf8_text(row.get('runner_output')):
        return False
    if any(not isinstance(d, dict) or not common.utf8_text(d.get('test')) or
           not common.utf8_text(d.get('trace')) for d in details):
        return False
    return (len(details) == row['failures'] + row['errors'] and
            not (row['successful'] and (row['failures'] or row['errors'])))


def unique_strings(value):
    return (isinstance(value, list) and all(common.utf8_text(v) for v in value)
            and len(set(value)) == len(value))


def supported_shape(value):
    if not isinstance(value, dict) or value.get('observation_schema') != SCHEMA:
        return False
    if any(type(value.get(k)) is not bool for k in ('passed', 'existing_work_preserved')):
        return False
    if not unique_strings(value.get('added_tests')):
        return False
    if any(not suite_shape(value.get(name)) for name in SUITES):
        return False
    faults = value.get('restoration_faults')
    if not isinstance(faults, dict) or set(faults) != set(FAULTS):
        return False
    if any(not suite_shape(row) for row in faults.values()):
        return False
    transport = value['transports']
    if type(transport.get('complete')) is not bool or not unique_strings(transport.get('required_modes')):
        return False
    observed = transport.get('observed_modes')
    if not isinstance(observed, dict) or set(observed) != {'False', 'True'}:
        return False
    if any(not unique_strings(modes) for modes in observed.values()):
        return False
    complete = all(set(transport['required_modes']) <= set(modes) for modes in observed.values())
    passed = (value['existing_work_preserved'] and bool(value['added_tests']) and
              all(value[n]['successful'] for n in SUITES) and complete and
              all(row['tests'] > 0 and not row['successful'] for row in faults.values()))
    return complete is transport['complete'] and passed is value['passed']


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
        exact_attribute_assertions_require_direct_review=True,
        existing_test_text_preservation_automatically_established=False)
    rows, diagnostics, pages = [], [], []

    def add_diagnostics(name, part, expected_fault=False):
        links = []
        for number, detail in enumerate(part['details']):
            start = len(pages)
            label = common.bounded_text(detail['test'].encode(), 240, 384)
            for field in ('test', 'trace'):
                for fragment in fragments(detail[field]):
                    pages.append(dict(criterion=name, diagnostic_index=number, field=field,
                        test_label=label, injected_fault=expected_fault, **fragment))
            link = dict(action='inspect_check', observation=handle, offset=start)
            links.append(link)
            # Expected injected failures have exact access, but do not displace
            # current-parser failures in the ordinary diagnostic overview.
            if not expected_fault:
                diagnostics.append(dict(common.diagnostic(detail), criterion=name,
                    diagnostic_index=number, inspect=link, record_start=start,
                    record_end_exclusive=len(pages)))
        return links

    if known:
        rows.append(dict(criterion='existing_work_preserved', met=full['existing_work_preserved'],
            meaning='All non-test files match the saved entry; prior test-method ASTs remain unchanged. This is not a byte comparison of all old test text.'))
        rows.append(dict(criterion='added_tests', met=bool(full['added_tests']),
            count=len(full['added_tests']), meaning='At least one newly added test is discovered.'))
        meanings = {
            'saved_suite': 'The saved tests run against the current unchanged library.',
            'edited_suite': 'The current edited tests run against the current unchanged library.',
            'contract': 'Independent continuation behavior runs against the current library.',
            'transports': 'The added tests run with transport observation enabled; this suite must succeed.'}
        for name in SUITES:
            part = full[name]
            links = add_diagnostics(name + '.execution', part)
            row = dict(criterion=name + '.execution', met=part['successful'], meaning=meanings[name],
                counts={k:part[k] for k in COUNTS}, diagnostics_total=len(part['details']))
            if links:
                row['diagnostic_access'] = links[0]
            if not part['successful'] and not part['details']:
                row['runner_diagnostic'] = common.bounded_text(part['runner_output'].encode())
                row['diagnostic_note'] = 'No failure/error trace was emitted; inspect the captured runner output for other unsuccessful outcomes.'
            rows.append(row)
        transport = full['transports']
        rows.append(dict(criterion='transport_modes', met=transport['complete'],
            required_modes=transport['required_modes'], observed_modes=transport['observed_modes'],
            meaning='Parser-raised exceptions with and without final newline must undergo all declared transport modes. Observation of a mode does not prove every required attribute was asserted.'))
        for name in FAULTS:
            part = full['restoration_faults'][name]
            links = add_diagnostics('restoration_fault.' + name, part, True)
            rows.append(dict(criterion='restoration_fault.' + name,
                met=part['tests'] > 0 and not part['successful'],
                meaning='In this isolated injected-fault run the added suite must execute and be unsuccessful. That outcome detects this fault; it is not a current-library failure or an additional repair requirement.',
                injected_fault=name, comparison_failure_is_expected=True,
                counts={k:part[k] for k in COUNTS}, suite_successful=part['successful'],
                diagnostics_total=len(part['details']),
                diagnostic_access=links[0] if links else result['raw_access']))
    if not known or not normal or record['passed'] != full['passed']:
        rows.insert(0, dict(criterion='public_execution', met=bool(normal and record['passed']),
            meaning='Actual execution must complete; a printed report alone does not establish a completed check.',
            termination=record['termination'], returncode=record['returncode'],
            structured_report_recognized=known, stdout=common.bounded_text(stdout), stderr=common.bounded_text(stderr)))
    rows.sort(key=lambda r:r['met'] is not False)
    result.update(criteria=rows, failed_criteria=[r['criterion'] for r in rows if r['met'] is False],
        diagnostic_details=diagnostics, diagnostic_records=pages,
        explanation='Current suites must succeed, required transports must be observed, and added tests must detect each of the four named injected faults. Fault-run test failures are expected detection evidence. Exact assertion coverage and unrelated-text preservation require direct review.')
    return result


def public_metadata(value):
    return {k:copy.deepcopy(v) for k,v in value.items() if k not in ('diagnostic_details', 'diagnostic_records')}


def overview(value):
    result = public_metadata(value)
    shown = []
    for detail in value['diagnostic_details']:
        if len(canonical_json_bytes([*shown, detail])) > 6144:
            break
        shown.append(detail)
    result.update(diagnostics=copy.deepcopy(shown), diagnostics_total=len(value['diagnostic_details']),
        diagnostics_shown=len(shown), diagnostics_remaining=len(value['diagnostic_details'])-len(shown),
        diagnostic_record_count=len(value['diagnostic_records']),
        diagnostic_paging='inspect_check offsets index exact test/trace field fragments; follow next_offset.')
    if len(shown) < len(value['diagnostic_details']):
        result['next_unshown_diagnostic'] = copy.deepcopy(value['diagnostic_details'][len(shown)]['inspect'])
    return result


def inspect_check(store, handle, offset, contract=None):
    value = assessment(store, handle, contract)
    rows = value['diagnostic_records']
    if type(offset) is not int or not 0 <= offset <= len(rows):
        raise ValueError('diagnostic record offset is outside this observation')
    page = rows[offset:offset+2]
    return dict(accepted=True, kind='check_diagnostic_fields', **public_metadata(value),
        entries=copy.deepcopy(page), offset=offset, total_records=len(rows),
        next_offset=offset+len(page) if offset+len(page)<len(rows) else None,
        all_records_shown=offset == 0 and len(page) == len(rows),
        field_fragment_rule='Each entry contains exact UTF-8 bytes of its named field. complete=true means the whole field is shown; follow byte extents and next_offset for the remainder.')
