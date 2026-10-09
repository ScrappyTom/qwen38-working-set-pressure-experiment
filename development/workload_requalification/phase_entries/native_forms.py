"""Use the existing native matcher with task-appropriate fork specimens."""
import importlib.util
import json

import bootstrap

PATH = bootstrap.ROOT / 'development/workload_requalification/compiler_entry/native_forms.py'
spec = importlib.util.spec_from_file_location('phase_native_matcher_core', PATH)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def cases(checks):
    for row in core.cases(checks):
        if row['name'].startswith('imported_') or row['name'] == 'account_and_imported':
            continue
        yield row
    for name, op, accepted, account in (
        ('fork', dict(action='fork_ready', expected_candidate_id='a'*64), True, False),
        ('account_fork', dict(action='fork_ready', expected_candidate_id='a'*64), True, True),
        ('fork_missing_guard', dict(action='fork_ready'), False, False),
        ('fork_extra_phase', dict(action='fork_ready', expected_candidate_id='a'*64, phase='B'), False, False),
        ('fork_bad_guard', dict(action='fork_ready', expected_candidate_id='short'), False, False),
    ):
        value = dict(discussion='Request the phase boundary.')
        if account:
            value['account'] = 'Interpretation remains model-authored.'
        value['operation'] = op
        final = json.dumps(value, separators=(',', ':'))
        yield dict(name=name, text='Consider the next operation.\n</think>\n'+final,
                   final=final, expected=accepted)


def qualify(module, folder, url, store, log):
    return core.qualify(module, folder, url, store, log, specimens=cases,
                        required_forms={'fork_ready': {'action', 'expected_candidate_id'}})
