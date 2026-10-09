"""In-task fixture observations as aliases of the ordinary exact result archive."""
import copy
import re

import probe_bootstrap
import phase_session
from working_set_exp import working_view
from working_set_exp.accounted_contribution import AccountedSession
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes

DIRECTORY_PAGE = 6


def probe_forms():
    return [working_view.obj(dict(action=dict(type='string', const='probe'),
                probe_id=dict(type='string', const='integrity'))),
            working_view.obj(dict(action=dict(type='string', const='observation_history'),
                before=dict(type='integer', minimum=0))),
            working_view.obj(dict(action=dict(type='string', const='reopen_observation'),
                handle=dict(type='string', pattern='^OBS-[0-9]{4}$')))]


def extend(rule):
    result = copy.deepcopy(rule)
    result['oneOf'].extend(probe_forms())
    return result


def reply_schema_for(checks):
    schema = phase_session.reply_schema_for(checks)
    schema['json_schema']['name'] = 'original_phase_probe_contribution_v1'
    for form in schema['json_schema']['schema']['oneOf']:
        if 'operation' in form['properties']:
            form['properties']['operation'] = extend(form['properties']['operation'])
    return schema


class Session(phase_session.Session):
    def __init__(self, *args, probe_body, **kwargs):
        if not isinstance(probe_body, str) or not 0 < len(probe_body.encode()) <= 16384:
            raise ValueError('probe fixture body exceeds the declared storage allowance')
        self.probe_body = probe_body
        super().__init__(*args, **kwargs)

    def action_rule(self):
        return extend(super().action_rule())

    def reply_schema(self):
        return reply_schema_for(self.checkers)

    def observation_rows(self):
        rows = []
        for operation_sequence, pair in enumerate(self.pairs, 1):
            action, result = pair['response'], pair['result']
            if action['action'] not in ('check', 'probe', 'fork_ready') or not result.get('accepted'):
                continue
            raw = canonical_json_bytes(result)
            # All three producers return their actual operation candidate.
            candidate = result.get('checked_candidate_id', result.get('candidate_id'))
            if not isinstance(candidate, str) or re.fullmatch('[0-9a-f]{64}', candidate) is None:
                raise ValueError('observation-producing result has no exact candidate binding')
            sequence = len(rows) + 1
            rows.append(dict(handle=f'OBS-{sequence:04d}', sequence=sequence,
                operation_sequence=operation_sequence, action=action['action'],
                target=action.get('probe_id', action.get('check_id', 'phase_boundary')),
                observed_candidate_id=candidate, result_handle=f'RES-{operation_sequence:04d}',
                size_bytes=len(raw), sha256=sha256_bytes(raw)))
        return rows

    def observation(self, handle):
        matching = [r for r in self.observation_rows() if r['handle'] == handle]
        if not matching:
            raise ValueError('observation address is unavailable in this task archive')
        row, = matching
        raw = self.payload(row['result_handle'])
        if len(raw) != row['size_bytes'] or sha256_bytes(raw) != row['sha256']:
            raise ValueError('observation alias differs from its original result')
        return row, raw

    def observation_page(self, before=0):
        rows = self.observation_rows()
        boundary = before or len(rows) + 1
        page = [r for r in reversed(rows) if r['sequence'] < boundary][:DIRECTORY_PAGE]
        return dict(entries=[dict(**r,
            candidate_matches_current=r['observed_candidate_id'] == self.candidate.candidate_id,
            retrieve=dict(action='reopen_observation', handle=r['handle'])) for r in page],
            total_entries=len(rows), next_before=page[-1]['sequence'] if page and page[-1]['sequence'] > 1 else None,
            inventory_is_not_observation_content=True,
            scope='This task archive. Candidate equality is an identity fact, not fresh execution or semantic assurance.')

    def current_probe(self):
        return next((r for r in reversed(self.observation_rows()) if r['action'] == 'probe'
            and r['target'] == 'integrity' and r['observed_candidate_id'] == self.candidate.candidate_id), None)

    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['observation_directory'] = self.observation_page()
        return value

    def _ordinary(self, action):
        name = action['action']
        if name == 'probe':
            if self.phase != 'A':
                return dict(accepted=False, error='The integrity fixture probe is available in Phase A; Phase B recovers its saved observation.')
            return dict(accepted=True, executed=True, probe_id='integrity',
                candidate_id=self.candidate.candidate_id, observation=self.probe_body,
                observation_kind='authored_fixture_output')
        if name == 'observation_history':
            return dict(accepted=True, **self.observation_page(action['before']))
        if name == 'reopen_observation':
            row, raw = self.observation(action['handle'])
            # Retain the original result using the existing selected saved-result
            # representation. No duplicated observation store or invented event.
            handle = row['result_handle']
            page = dict(kind='saved_bytes', handle=handle, offset=0, next_offset=None,
                total_bytes=len(raw), sha256=row['sha256'], exact_utf8=raw.decode())
            self.saved[handle] = page
            return dict(accepted=True, kind='task_observation', handle=row['handle'],
                original_result_handle=handle, observed_candidate_id=row['observed_candidate_id'],
                target=row['target'], retrieval_only=True, source_edit_authority=False,
                saved_results=[page])
        if name == 'fork_ready' and self.phase == 'A' and self.current_probe() is None:
            return dict(accepted=False, error='Phase A requires an integrity observation on the current candidate; an older candidate observation does not satisfy this boundary.')
        return super()._ordinary(action)

    def _fits_feedback(self, measure):
        if (not self.recovery and self.last and
                self.last['action_summary'].get('action') == 'reopen_observation' and
                self.last['result'].get('accepted')):
            # Whole selected result or an explicit rejection. Avoid silently
            # claiming retention when ordinary presentation cannot deliver it.
            return AccountedSession._fits_feedback(self, measure)
        return super()._fits_feedback(measure)

    def commit_admission_error(self, action):
        if action['action'] == 'reopen_observation':
            return ('The exact observation cannot fit beside the selected group; no retrieval or selection change committed. '
                    'Its original result remains stored. Use work_on to replace the selected group or reopen_result for bounded exact pages.')
        return super().commit_admission_error(action)


REFERENCE = '''
probe: Phase A only. Executes the authored integrity fixture on the actual current
candidate and preserves its exact result. It is fixture output, not a subprocess,
an external measurement or a passing check. No expected-candidate argument is used.
The accepted result records the actual candidate; later edits do not update it.

observation_directory lists at most six recent observations produced in this task.
Accepted checks (including an executed failure), probes and fork outcomes receive
OBS aliases in production order. Each alias resolves to its original RES bytes.
The inventory identifies the producing action, target and candidate; it is not the
observation body. candidate_matches_current reports identity equality only.
observation_history: before=0 starts at the newest; otherwise use next_before.
It returns another bounded inventory page without executing or retrieving a body.

reopen_observation: Retrieves the exact original result named by OBS and retains
that complete original RES in the selected group. It executes nothing, changes no
candidate/check/account and grants no source-edit authority. Normal presentation
must fit the complete result or retrieval is rejected, leaving the prior selection.
In recovery mode designated bodies can remain explicitly omitted; acquisition alone
does not resume normal presentation. work_on/work_on_exact can select the listed RES
with source, or release it; reopen_result provides exact byte pages when needed.
The returned saved_results describes what actually arrived. Old observations stay
bound to their producing candidate, even when retrieved after an edit.

In this configuration fork_ready also requires an integrity result on the current
candidate. This explicit current-binding guard replaces the historical probe_done
flag; it does not establish the meaning of the observation. The normal fork releases
selected bodies, preserves exact observations and begins Phase B without resetting
opportunity. Phase B cannot rerun the Phase A probe. A subsequent Phase B edit leaves
the recovered observation historical; it does not require a new probe.
'''.strip()
