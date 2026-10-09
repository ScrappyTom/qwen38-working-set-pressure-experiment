"""Use existing observation grammar specimens with this task's actual probe id."""
import compass_bootstrap
import probe_native_forms


def cases(checks):
    for row in probe_native_forms.cases(checks):
        yield {key: value.replace('integrity', 'compatibility') if isinstance(value, str) else value
               for key, value in row.items()}


def qualify(module, folder, url, store, log):
    return probe_native_forms.source.core.qualify(module, folder, url, store, log, specimens=cases,
        required_forms={'fork_ready': {'action','expected_candidate_id'}, 'probe': {'action','probe_id'},
            'observation_history': {'action','before'}, 'reopen_observation': {'action','handle'}})
