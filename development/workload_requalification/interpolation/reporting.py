"""Task-specific interpretation of preserved interpolation acceptance observations."""
from working_set_exp import coherent_diagnostics as base
from working_set_exp.jsonutil import load_json_strict
from working_set_exp.observations import text_tail


def assessment(store, handle, contract=None):
    value = base.assessment(store, handle, contract)
    if not value['assessment_available']:
        return value
    full = load_json_strict((store.directory(handle)/'stdout.bin').read_bytes())
    for row in value['criteria']:
        if row['criterion'] == 'examples.execution' and full['examples']['examples'] == 0:
            row['observed'] = ('No newly added executable examples were run. This does not pass the documentation obligation.'
                if not full['examples']['failures'] else 'The added example source could not be parsed; inspect its diagnostic.')
        if row['criterion'].startswith('detect.') and full.get('observed_paths',{}).get('tests') == 0:
            row.update(met=None, fault_detected=None, normal_control_passed=False,
                observed='No added tests ran. Fault detection is unassessed until the requested tests exist and execute.')
    if full.get('observed_paths',{}).get('tests') == 0:
        value['normal_control_passed'] = False
    if full['scope'] != 'examples':
        part = full['backport_contract']
        diagnostics = [dict(test=d['test'], diagnostic=text_tail(d['trace'].encode(), 4096))
                       for d in part['details'][:2]]
        value['criteria'].extend([
            dict(criterion='backport_contract', met=part['successful'],
                 meaning='The saved library behavior must still pass its independent backport contract.',
                 diagnostics=diagnostics, diagnostics_total=len(part['details']),
                 diagnostics_shown=len(diagnostics), diagnostics_remaining=len(part['details'])-len(diagnostics)),
            dict(criterion='added_tests', met=bool(full['added_tests']),
                 meaning='Add tests for the requested contribution; old tests alone do not complete it.')])
    if full['scope'] == 'public':
        legacy = full['legacy_report']
        value['criteria'].append(dict(criterion='legacy_public_acceptance', met=full['legacy_public_passed'],
            meaning='The original public acceptance remains required, in addition to the declared extra checks.',
            documentation_added_preserving_existing=legacy['documentation_added_preserving_existing']))
    value['criteria'].sort(key=lambda r:(r['met'] is not False, r['met'] is not None))
    value['failed_criteria'] = [r['criterion'] for r in value['criteria'] if r['met'] is False]
    value['unassessed_criteria'] = [r['criterion'] for r in value['criteria'] if r['met'] is None]
    return value


overview = base.overview


def inspect_check(store, handle, offset, contract=None):
    value = assessment(store, handle, contract)
    rows = value.pop('criteria')
    if type(offset) is not int or not 0 <= offset <= len(rows):
        raise ValueError('assessment offset is outside complete criterion records')
    page = rows[offset:offset+4]
    return dict(accepted=True, kind='check_criteria', **value, entries=page, offset=offset,
        total_records=len(rows), next_offset=offset+len(page) if offset+len(page)<len(rows) else None,
        records_complete=True, all_records_shown=offset==0 and len(page)==len(rows))
