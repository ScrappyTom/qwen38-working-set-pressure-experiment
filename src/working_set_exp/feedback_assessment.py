"""Opt-in coherent projection and baseline-qualified interpretation of observations."""
import copy

from . import check_assessment as prior
from .jsonutil import load_json_strict


def counts(row, key, total, limit):
    row[key] = row.get(key, [])[:limit]
    row[key + '_total'] = total
    row[key + '_shown'] = len(row[key])
    row[key + '_remaining'] = total - len(row[key])
    row.pop('additional_' + key, None)


def assessment(store, handle, contract=None):
    value = prior.assessment(store, handle, contract)
    if not value['assessment_available']:
        return value
    full = load_json_strict((store.directory(handle) / 'stdout.bin').read_bytes())
    baseline = all(full.get(k, {}).get('successful') is True
                   for k in ('saved_suite', 'edited_suite', 'observed_paths'))
    for row in value['criteria']:
        for key in ('diagnostics', 'missing_paths'):
            if key in row:
                counts(row, key, len(row[key]) + row.get('additional_' + key, 0), len(row[key]))
        if row['criterion'] == 'documentation_preserved':
            row['meaning'] = 'Keep every original documentation line unchanged and in order; insertions only.'
            differences = full.get('documentation_changes', [])
            row['changed_spans'] = differences[:4]
            counts(row, 'changed_spans', len(differences), 4)
        if row['criterion'].startswith('detect.'):
            name = row['criterion'][7:]
            raw = full['fault_sensitivity'][name]
            detected = raw.get('all_targets_detected', row['fault_detected']) if baseline else None
            row.update(met=detected, fault_detected=detected, normal_control_passed=baseline,
                meaning='After a passing ordinary control, the added tests must detect this fault at each declared target.',
                observed=('Assessment blocked: the ordinary control failed; mutation failures are not independent detection evidence.'
                          if not baseline else 'All declared targets detected.' if detected else
                          'At least one declared target was not detected; inspect the unmet targets.'))
            if 'targets' in raw:
                missing = [r['target'] for r in raw['targets'] if not r['detected']]
                row.update(targets_tested=len(raw['targets']), undetected_targets=missing[:4])
                counts(row, 'undetected_targets', len(missing), 4)
                row.pop('test_run_passed', None)  # An aggregate is not one test run.
    value['criteria'].sort(key=lambda r:(r['met'] is not False, r['met'] is not None))
    value['failed_criteria'] = [r['criterion'] for r in value['criteria'] if r['met'] is False]
    value['unassessed_criteria'] = [r['criterion'] for r in value['criteria'] if r['met'] is None]
    value['normal_control_passed'] = baseline
    value['explanation'] = ('Ordinary execution and its required path coverage must pass. Fault sensitivity is assessed only '
        'with a passing ordinary control, at the declared targets. Mutation-run path completeness is not required. '
        'A pass is scoped evidence, not verification of all prose or of the model account.')
    return value


def overview(value):
    result = copy.deepcopy(value)
    result['criteria'] = [c for c in result['criteria'] if c['met'] is not True]
    for row in result['criteria']:
        # Keep the useful primary failure and a small truthful sample. Full detail
        # remains in criterion pages and raw observation, not in removed-list counts.
        for key, limit in (('diagnostics', 1), ('missing_paths', 2), ('changed_spans', 2), ('undetected_targets', 2)):
            if key in row:
                counts(row, key, row[key + '_total'], limit)
    return result


def inspect_check(store, handle, offset, contract=None):
    value = assessment(store, handle, contract)
    rows = value.pop('criteria')
    if type(offset) is not int or not 0 <= offset <= len(rows):
        raise ValueError('assessment offset is outside complete criterion records')
    page = rows[offset:offset+4]
    return dict(accepted=True, kind='check_criteria', **value, entries=page, offset=offset,
        total_records=len(rows), next_offset=offset+len(page) if offset+len(page)<len(rows) else None,
        records_complete=True, all_records_shown=(offset == 0 and len(page) == len(rows)))
