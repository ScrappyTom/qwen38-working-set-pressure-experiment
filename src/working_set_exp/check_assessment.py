"""Decision reports derived from preserved observations, never replacement evidence."""
from .jsonutil import load_json_strict
from .observations import text_tail


def supported_shape(full):
    """Reject unsupported structures before assigning meaning to their fields."""
    if not isinstance(full, dict) or full.get('observation_schema') != 'contribution-check-v2':
        return False
    if full.get('assessment_error'):
        return False
    for key in ('existing_work_preserved', 'documentation_preserved'):
        if key in full and type(full[key]) is not bool:
            return False
    for key in ('saved_suite', 'edited_suite', 'observed_paths', 'examples'):
        if key not in full:
            continue
        value = full[key]
        if not isinstance(value, dict) or type(value.get('successful')) is not bool:
            return False
        details = value.get('details', [])
        if not isinstance(details, str) and (not isinstance(details, list) or
                any(not isinstance(d, dict) for d in details)):
            return False
        if any(type(value[k]) is not int or value[k] < 0 for k in
               ('tests', 'examples', 'failures', 'errors', 'skipped') if k in value):
            return False
        if key == 'observed_paths' and (type(value.get('complete')) is not bool or
                not isinstance(value.get('missing_paths', []), list)):
            return False
    faults = full.get('fault_sensitivity', {})
    if not isinstance(faults, dict) or len(faults) > 32:
        return False
    return all(len(name) <= 64 and isinstance(value, dict) and
               type(value.get('tests')) is int and value['tests'] >= 0 and
               type(value.get('successful')) is bool for name, value in faults.items())


def assessment(store, handle, contract=None):
    record = store.read(handle)  # Verify custody before interpreting captured data.
    result = dict(observation=handle, scope=record['check_id'],
                  candidate_id=record['candidate_id'], checker_sha256=record['checker_sha256'],
                  executed=record['executed'], passed=record['passed'],
                  observation_capture_complete=record['capture_complete'],
                  raw_access=dict(action='inspect_observation', observation=handle, stream='stdout', offset=0))
    if contract and contract.get('checker_sha256') != record['checker_sha256']:
        raise ValueError('check interpretation contract belongs to a different checker')
    try:
        full = load_json_strict((store.directory(handle) / 'stdout.bin').read_bytes())
    except (ValueError, UnicodeError):
        full = None
    if not record['capture_complete'] or not supported_shape(full):
        return dict(**result, assessment_available=False, criteria=[], failed_criteria=[],
                    explanation='No complete supported structured assessment is available. Inspect captured streams; no criterion is inferred.',
                    assessment_error=text_tail(str(full['assessment_error']).encode())
                        if isinstance(full, dict) and full.get('assessment_error') else None)
    criteria = []

    def add(name, met, meaning, **detail):
        criteria.append(dict(criterion=name, met=met if type(met) is bool else None,
                             meaning=meaning, **detail))

    for key, meaning in (('existing_work_preserved', 'Preserve existing implementation and tests.'),
                         ('documentation_preserved', 'Preserve existing documentation.')):
        if key in full:
            add(key, full[key], meaning)
    for key in ('saved_suite', 'edited_suite', 'observed_paths', 'examples'):
        value = full.get(key)
        if not isinstance(value, dict):
            continue
        details = value.get('details') or []
        if isinstance(details, str):
            details = [dict(test='documentation examples', trace=details)]
        diagnostics = [dict(test=str(d.get('test', ''))[:300],
                            diagnostic=text_tail(str(d.get('trace', d)).encode(), 2048))
                       for d in details[:2]]
        add(key + '.execution', value.get('successful'), 'Ordinary execution must pass.',
            counts={k:value[k] for k in ('tests','examples','failures','errors','skipped') if k in value},
            diagnostics=diagnostics, additional_diagnostics=max(0,len(details)-2))
        if key == 'observed_paths':
            add('required_paths', value.get('complete'), 'Exercise required paths in the normal, unmodified run.',
                missing_paths=value.get('missing_paths', [])[:16],
                additional_missing_paths=max(0,len(value.get('missing_paths', []))-16))
    faults = full.get('fault_sensitivity', {})
    for name, value in faults.items():
        tested, successful = value.get('tests'), value.get('successful')
        detected = bool(tested and not successful) if type(tested) is int and type(successful) is bool else None
        add('detect.' + name, detected, 'The new tests must fail or error when this fault is injected.',
            injected_change=(contract or {}).get('fault_changes', {}).get(name, 'Checker-defined fault: ' + name),
            test_run_passed=successful, fault_detected=detected,
            observed=('The test run still passed: this fault was not detected.' if detected is False else
                      'The test run failed or errored as expected: this fault was detected.' if detected else
                      'Insufficient structured data to determine detection.'),
            mutation_path_coverage_is_required=False)
    # Put unmet criteria first; optional mutation traces never look like extra obligations.
    criteria.sort(key=lambda row: (row['met'] is not False, row['met'] is not None))
    failed = [c['criterion'] for c in criteria if c['met'] is False]
    return dict(**result, assessment_available=True, criteria=criteria, failed_criteria=failed,
                explanation='Normal execution and normal path coverage must pass. Each injected fault must be detected by a failing or erroring test. Mutation-run path completeness is not a requirement.',
                assessment_error=full.get('assessment_error'))


def overview(value):
    """Keep failed criteria identifiable even in a small standing verification view."""
    return {**{k:v for k,v in value.items() if k != 'criteria'},
            'criteria':[{k:v for k,v in c.items() if k not in ('diagnostics','missing_paths')}
                        for c in value['criteria'] if c['met'] is not True]}


def inspect_check(store, handle, offset, contract=None):
    value = assessment(store, handle, contract)
    rows = value.pop('criteria')
    if type(offset) is not int or not 0 <= offset <= len(rows):
        raise ValueError('assessment offset is outside complete criterion records')
    page = rows[offset:offset+4]
    return dict(accepted=True, kind='check_criteria', **value, entries=page, offset=offset,
                total_records=len(rows), next_offset=offset+len(page) if offset+len(page)<len(rows) else None,
                records_complete=True, all_records_shown=(offset==0 and len(page)==len(rows)))
