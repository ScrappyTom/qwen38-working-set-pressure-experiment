"""Name the actual original scope without changing its preserved observation."""
import case_reports


def scoped(value):
    # Shared small-task reports predate the prefork scope. Only their derived
    # execution label/prose change; raw output, applicability and pass stay exact.
    if value['scope'] != 'prefork':
        return value
    for row in value.get('criteria', value.get('entries', [])):
        if row['criterion'] == 'public_execution':
            row['criterion'] = 'prefork_execution'
            row['meaning'] = row['meaning'].replace('public checker', 'Phase A prefork checker').replace(
                'public check', 'Phase A prefork check')
    value['failed_criteria'] = ['prefork_execution' if name == 'public_execution' else name
                                for name in value['failed_criteria']]
    return value


def assessment(store, handle, contract=None):
    return scoped(case_reports.assessment(store, handle, contract))


overview = case_reports.overview


def inspect_check(store, handle, offset, contract=None):
    return scoped(case_reports.inspect_check(store, handle, offset, contract))
