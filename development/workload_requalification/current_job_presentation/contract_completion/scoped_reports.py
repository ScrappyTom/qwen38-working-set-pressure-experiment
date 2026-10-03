"""Truthful derived fault scope; exact historical observations stay unchanged."""
import dispatch_reports as prior


def assessment(store, handle, contract=None):
    value = prior.assessment(store, handle, contract)
    rows = value['criteria']
    has_faults = any('fault_execution' in r.get('observation', {})
                    or 'site_observations' in r.get('observation', {}) for r in rows)
    if has_faults:
        value['explanation'] = ('This execution includes current-candidate checks, historical-baseline sensitivity, '
            'and separate intentional-fault sensitivity. Expected mutant failures satisfy sensitivity criteria; '
            'they are not failures of the real candidate. Authored coverage and prose require their own assessment.')
        value['intentional_faults_present'] = True
    return value


overview = prior.overview


def inspect_check(store, handle, offset, contract=None):
    value = assessment(store, handle, contract)
    rows = value.pop('criteria')
    if type(offset) is not int or not 0 <= offset <= len(rows):
        raise ValueError('assessment offset is outside complete records')
    page = rows[offset:offset+4]
    return dict(accepted=True, kind='check_criteria', **value, entries=page,
        offset=offset, total_records=len(rows), next_offset=offset+len(page) if offset+len(page)<len(rows) else None,
        records_complete=True, all_records_shown=offset == 0 and len(page) == len(rows))
