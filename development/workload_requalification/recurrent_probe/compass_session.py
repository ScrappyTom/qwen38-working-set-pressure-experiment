"""Three actual fixture productions over the original four-phase session."""
import copy

import compass_bootstrap
import recurrent_session
import probe_session
import phase_session
from current_facts import CurrentFactsMixin


def probe_forms():
    forms = copy.deepcopy(probe_session.probe_forms())
    forms[0]['properties']['probe_id']['const'] = 'compatibility'
    return forms


def reply_schema_for(checks):
    schema = phase_session.reply_schema_for(checks)
    schema['json_schema']['name'] = 'original_recurrent_probe_v1'
    for form in schema['json_schema']['schema']['oneOf']:
        if 'operation' in form['properties']:
            rule = copy.deepcopy(form['properties']['operation'])
            rule['oneOf'].extend(probe_forms())
            form['properties']['operation'] = rule
    return schema


class Session(CurrentFactsMixin, recurrent_session.Session, probe_session.Session):
    def __init__(self, *args, probe_bodies, **kwargs):
        if set(probe_bodies) != {'A', 'B', 'C'} or any(
                not isinstance(body, str) or not 0 < len(body.encode()) <= 16384
                for body in probe_bodies.values()):
            raise ValueError('three original bounded phase probe bodies are required')
        self.probe_bodies = dict(probe_bodies)
        super().__init__(*args, probe_body=probe_bodies['A'], **kwargs)

    def action_rule(self):
        rule = super().action_rule()
        form, = [f for f in rule['oneOf'] if f['properties']['action'].get('const') == 'probe']
        assert form['properties']['probe_id']['const'] == 'integrity'
        form['properties']['probe_id']['const'] = 'compatibility'
        return rule

    def reply_schema(self):
        return reply_schema_for(self.checkers)

    def current_probe(self):
        # A prior phase's production remains recoverable and may still match
        # candidate bytes. It cannot fulfil this phase's new production duty.
        boundary = max((i for i, p in enumerate(self.pairs, 1)
            if p['response']['action'] == 'fork_ready' and p['result'].get('accepted')), default=0)
        return next((r for r in reversed(self.observation_rows())
            if r['operation_sequence'] > boundary and r['action'] == 'probe'
            and r['target'] == 'compatibility'
            and r['observed_candidate_id'] == self.candidate.candidate_id), None)

    def _ordinary(self, action):
        name = action['action']
        if name == 'probe':
            if self.phase not in self.probe_bodies:
                return dict(accepted=False, error='Phase D recovers the saved compatibility observation; it does not produce another probe.')
            return dict(accepted=True, executed=True, probe_id='compatibility',
                candidate_id=self.candidate.candidate_id,
                observation=self.probe_bodies[self.phase], observation_kind='authored_fixture_output')
        if name in ('observation_history', 'reopen_observation'):
            return probe_session.Session._ordinary(self, action)
        if name == 'fork_ready' and self.phase != 'D' and self.current_probe() is None:
            return dict(accepted=False, error='This phase requires a compatibility observation produced in this phase on the current candidate; an older production does not satisfy the boundary.')
        return super()._ordinary(action)


# Retain the already-qualified exact alias/directory/recovery explanation.
REFERENCE = '''
probe: Available in A, B and C. Executes that phase's original authored compatibility
fixture on the actual current candidate and preserves its exact result. It is
fixture output, not a subprocess, external measurement or passing check. No
expected-candidate argument is used. Later edits do not update its binding.
Phase D recovers a saved observation and cannot produce a new compatibility probe.
'''.strip() + '\n\nobservation_directory lists' + probe_session.REFERENCE.split('observation_directory lists', 1)[1].split(
    '\n\nIn this configuration fork_ready', 1)[0] + '''

Each nonterminal fork also requires a compatibility result produced during that
phase on its current candidate. This is a production/binding guard, not semantic
validation of the observation. The ordinary boundary releases selected bodies,
preserves every exact observation and advances the phase without resetting the
overall opportunity. The task requires selecting and reopening the applicable
preceding observation before the dependent repair; that remains your work.
'''
