"""Native decoder specimens for the declared in-task observation operations."""
import json

import probe_bootstrap
import native_forms as source


def cases(checks):
    yield from source.cases(checks)
    for name, op, expected, account in (
        ('probe', dict(action='probe', probe_id='integrity'), True, False),
        ('account_probe', dict(action='probe', probe_id='integrity'), True, True),
        ('probe_wrong_id', dict(action='probe', probe_id='other'), False, False),
        ('probe_extra_guard', dict(action='probe', probe_id='integrity', expected_candidate_id='a'*64), False, False),
        ('observation_history', dict(action='observation_history', before=0), True, False),
        ('observation_history_older', dict(action='observation_history', before=3), True, False),
        ('observation_history_negative', dict(action='observation_history', before=-1), False, False),
        ('reopen_observation', dict(action='reopen_observation', handle='OBS-0004'), True, False),
        ('account_reopen_observation', dict(action='reopen_observation', handle='OBS-0004'), True, True),
        ('reopen_observation_wrong_handle', dict(action='reopen_observation', handle='RES-0004'), False, False),
    ):
        value = dict(discussion='Request the next operation.')
        if account:
            value['account'] = 'Model-authored interpretation, separate from executed observations.'
        value['operation'] = op
        final = json.dumps(value, separators=(',', ':'))
        yield dict(name=name, text='Consider the next operation.\n</think>\n'+final,
                   final=final, expected=expected)


def qualify(module, folder, url, store, log):
    return source.core.qualify(module, folder, url, store, log, specimens=cases,
        required_forms={'fork_ready': {'action', 'expected_candidate_id'}, 'probe': {'action', 'probe_id'},
            'observation_history': {'action', 'before'}, 'reopen_observation': {'action', 'handle'}})
