"""Preserve explicit criterion meanings from the declared checker."""
import case_reports


def assessment(store, handle, contract=None):
    result = case_reports.assessment(store, handle, contract)
    for row in result['criteria']:
        if 'observation' in row:
            row['meaning'] = row['observation'].get('meaning', row['meaning'])
    result['explanation'] = ('Declared contribution criteria. A failing baseline regression '
        'establishes sensitivity; it is separate from the current candidate execution. No injected faults.')
    return result


overview = case_reports.overview


def inspect_check(store, handle, offset, contract=None):
    result = case_reports.inspect_check(store, handle, offset, contract)
    for row in result['entries']:
        if 'observation' in row:
            row['meaning'] = row['observation'].get('meaning', row['meaning'])
    return result
