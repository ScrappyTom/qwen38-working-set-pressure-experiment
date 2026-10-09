"""Expose each original check's actual scope, retaining the exact observation."""
import phase_reports


def scoped(value, contract):
    if contract and 'scope_description' in contract:
        value['explanation'] = contract['scope_description']
        for row in value.get('criteria', value.get('entries', [])):
            if row['criterion'] in ('public_execution', 'prefork_execution'):
                row['meaning'] = contract['scope_description']
    return value


def assessment(store, handle, contract=None):
    return scoped(phase_reports.assessment(store, handle, contract), contract)


overview = phase_reports.overview


def inspect_check(store, handle, offset, contract=None):
    return scoped(phase_reports.inspect_check(store, handle, offset, contract), contract)
