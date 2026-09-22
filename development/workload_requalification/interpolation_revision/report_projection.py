"""Complete, grouped path facts from the unchanged captured interpolation check."""
import copy

import reporting as previous
from working_set_exp.jsonutil import load_json_strict

LOOKUPS = {
    'BasicInterpolation': 'For copy, deepcopy and pickle only: use the exception raised by a real BasicInterpolation missing-reference lookup.',
    'ExtendedInterpolation': 'For copy, deepcopy and pickle only: use the exception raised by a real ExtendedInterpolation cross-section missing-reference lookup.',
}


def assessment(store, handle, contract=None):
    value = previous.assessment(store, handle, contract)
    if not value['assessment_available']:
        return value
    full = load_json_strict((store.directory(handle) / 'stdout.bin').read_bytes())
    if 'observed_paths' not in full:
        return value
    missing = full['observed_paths']['missing_paths']
    for row in value['criteria']:
        if row['criterion'] != 'required_paths':
            continue
        groups = []
        for policy, meaning in LOOKUPS.items():
            operations = [r['operation'] for r in missing if r['policy'] == policy]
            if operations:
                groups.append(dict(policy=policy, transport_source=meaning,
                    missing_operations=operations, missing_operation_count=len(operations)))
        assert sum(g['missing_operation_count'] for g in groups) == len(missing), 'Unknown policy: review projection'
        assert len({(r['policy'], r['operation']) for r in missing}) == len(missing), 'Duplicate observed path'
        for key in tuple(row):
            if key == 'missing_paths' or key.startswith('missing_paths_') or key == 'additional_missing_paths':
                row.pop(key)
        row.update(missing_groups=groups, all_missing_groups_shown=True,
            missing_operation_total=len(missing),
            operation_meanings={
                'copy/deepcopy/pickle:N': 'Transport the real lookup exception; N is the actual pickle protocol number.',
                'raw_bypass': 'Retrieve the unresolved value with raw=True without interpolation.',
                'resolved': 'Retrieve the interpolated value after supplying the missing setting.'})
    return value


overview = previous.overview


def inspect_check(store, handle, offset, contract=None):
    value = assessment(store, handle, contract)
    rows = value.pop('criteria')
    if type(offset) is not int or not 0 <= offset <= len(rows):
        raise ValueError('assessment offset is outside complete criterion records')
    page = copy.deepcopy(rows[offset:offset + 4])
    return dict(accepted=True, kind='check_criteria', **value, entries=page, offset=offset,
        total_records=len(rows), next_offset=offset + len(page) if offset + len(page) < len(rows) else None,
        records_complete=True, all_records_shown=offset == 0 and len(page) == len(rows))
