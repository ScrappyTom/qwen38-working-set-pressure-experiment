"""Existing exact-observation projection, with this check's truthful scope."""
import case_reports

def assessment(store, handle, contract=None):
    value = case_reports.assessment(store, handle, contract)
    value['explanation'] = ('Declared E20 verifier public check: original assertions followed by '
        'native path, timeout and preservation contract checks. No injected faults. '
        'Actual process completion governs; earlier pass text is not an overall pass.')
    for row in value['criteria']:
        if row['criterion'] == 'public_execution':
            row['meaning'] = 'Overall execution of the declared public check; inspect the exact assertion diagnostic.'
    return value

overview = case_reports.overview

def inspect_check(store, handle, offset, contract=None):
    value = assessment(store, handle, contract)
    rows = value.pop('criteria')
    if type(offset) is not int or not 0 <= offset <= len(rows):
        raise ValueError('assessment offset is outside complete records')
    page = rows[offset:offset+4]
    return dict(accepted=True, kind='check_criteria', **value, entries=page,
        offset=offset, total_records=len(rows),
        next_offset=offset+len(page) if offset+len(page)<len(rows) else None,
        records_complete=True, all_records_shown=offset==0 and len(page)==len(rows))
