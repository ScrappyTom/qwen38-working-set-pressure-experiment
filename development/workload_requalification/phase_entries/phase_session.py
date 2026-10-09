"""Original source-task phase boundary on the current exact-work host."""
import copy

import bootstrap
import repair_task
import operational_reply
from navigation import NavigationMixin
from search_navigation import SearchNavigationMixin
from working_set_exp import decision_view, working_view
from working_set_exp.jsonutil import sha256_bytes


def fork_rule():
    return working_view.obj(dict(action=dict(type='string', const='fork_ready'),
        expected_candidate_id=dict(type='string', pattern='^[0-9a-f]{64}$')))


def reply_schema_for(checks):
    value = operational_reply.reply_schema(checks)
    value['json_schema']['name'] = 'original_two_phase_contribution_v1'
    rule = decision_view.action_rule(checks)
    rule['oneOf'].append(fork_rule())
    for form in value['json_schema']['schema']['oneOf']:
        if 'operation' in form['properties']:
            form['properties']['operation'] = rule
    return value


def merge_ranges(ranges):
    result = []
    for first, last in sorted(ranges):
        if not result or first > result[-1][1] + 1:
            result.append([first, last])
        else:
            result[-1][1] = max(result[-1][1], last)
    return result


class Session(SearchNavigationMixin, NavigationMixin, repair_task.Session):
    """Phase is derived from the accepted boundary, not a competing status flag.

    Coverage is historical presentation evidence. It never populates the current
    delivered_sources guard and is not semantic proof of reading/understanding.
    """
    def __init__(self, *args, phase_texts, phase_required, **kwargs):
        if set(phase_texts) != {'A', 'B'} or set(phase_required) != {'A', 'B'}:
            raise ValueError('exactly the original two phases are required')
        self.phase_texts = dict(phase_texts)
        self.phase_required = {k: tuple(v) for k, v in phase_required.items()}
        self.presented_coverage = []
        super().__init__(*args, **kwargs)

    def clone(self):
        value = super().clone()
        value.presented_coverage = copy.deepcopy(self.presented_coverage)
        return value

    @property
    def phase(self):
        return 'B' if any(p['response']['action'] == 'fork_ready' and p['result'].get('accepted')
                          for p in self.pairs) else 'A'

    def action_rule(self):
        rule = copy.deepcopy(super().action_rule())
        rule['oneOf'].append(fork_rule())
        return rule

    def reply_schema(self):
        return reply_schema_for(self.checkers)

    def mark_delivered(self, view):
        super().mark_delivered(view)
        for source in self.delivered_sources:
            path = source['path']
            if path not in self.phase_required[self.phase]:
                continue
            raw = self.candidate.file_map[path]
            first, last = source['returned_start_line'], source['returned_end_line']
            # Recovered historical source may qualify only for unchanged bytes.
            if source['file_sha256'] != sha256_bytes(raw):
                continue
            exact = ''.join(raw.decode().splitlines(keepends=True)[first-1:last])
            if source['content'] != exact:
                raise ValueError('presented coverage differs from exact current source')
            key = (self.phase, path, source['file_sha256'])
            matches = [r for r in self.presented_coverage
                       if (r['phase'], r['path'], r['file_sha256']) == key]
            if matches:
                row, = matches
                row['ranges'] = merge_ranges([*row['ranges'], [first, last]])
            else:
                self.presented_coverage.append(dict(phase=self.phase, path=path,
                    file_sha256=source['file_sha256'], ranges=[[first, last]]))

    def coverage_status(self, phase=None):
        phase = phase or self.phase
        rows = []
        for path in self.phase_required[phase]:
            raw = self.candidate.file_map[path]
            digest, count = sha256_bytes(raw), len(raw.decode().splitlines(keepends=True))
            ranges = [span for row in self.presented_coverage
                      if row['phase'] == phase and row['path'] == path and row['file_sha256'] == digest
                      for span in row['ranges']]
            merged = merge_ranges(ranges)
            complete = bool(merged) and merged[0][0] == 1 and merged[0][1] >= count
            rows.append(dict(path=path, file_sha256=digest, file_total_lines=count,
                             previously_presented_ranges=merged, complete=complete))
        return rows

    def view(self, **kwargs):
        value = super().view(**kwargs)
        scope = 'prefork' if self.phase == 'A' else 'public'
        value['phase'] = dict(current=self.phase, active_assignment=self.phase_texts[self.phase],
            completed=['A'] if self.phase == 'B' else [], current_check=scope,
            required_source_delivery=self.coverage_status(),
            coverage_meaning='Previously presented exact file extents, not present edit authority or proof of understanding.',
            boundary='fork_ready' if self.phase == 'A' else 'submit')
        value['episode_annotation'] = (
            'This is one two-phase task. Current phase and its assignment are shown in phase. '
            'Recent activity and recoverable history belong to this task; completed Phase A is not '
            'a failed or restarted job. fork_ready releases selected source/result bodies by the '
            'declared phase-entry policy, preserving files, exact history and the authored account. '
            'Historical coverage does not make source currently visible. No prior conversation is supplied.')
        if self.phase == 'A':
            value['verification']['submission'].update(eligible=False, reason='Phase A requires fork_ready, not submission')
        return value

    def _ordinary(self, action):
        name = action['action']
        if name == 'check' and action['check_id'] != ('prefork' if self.phase == 'A' else 'public'):
            return dict(accepted=False, error='Check is not active in this phase; consult phase.current_check.')
        if name == 'submit' and self.phase != 'B':
            return dict(accepted=False, error='Complete Phase A with fork_ready before submission.')
        if name != 'fork_ready':
            return super()._ordinary(action)
        if self.phase != 'A':
            return dict(accepted=False, error='Phase A is already complete; fork_ready does not restart it.')
        if action['expected_candidate_id'] != self.candidate.candidate_id:
            return dict(accepted=False, error='Stale fork candidate binding.')
        missing = [r['path'] for r in self.coverage_status() if not r['complete']]
        if missing:
            return dict(accepted=False, error='Required Phase A source was not completely presented.', missing_paths=missing)
        check = self.scoped_check_state('prefork')
        if not (check and check['applies_to_current'] and check['passed']):
            return dict(accepted=False, error='Current candidate has no passing prefork check.')
        # Staged transition; the accepted archived result determines phase B.
        # Neither a source edit nor a checker execution occurs at this boundary.
        self.ranges, self.saved, self.delivered_sources = [], {}, []
        self.recovery, self.recovery_obstacle, self.control_tier = False, None, 0
        self.recovery_focus, self.parked_source_regions = [], ()
        return dict(accepted=True, fork_ready=True, candidate_id=self.candidate.candidate_id,
                    completed_phase='A', next_phase='B', selected_bodies_released=True,
                    files_and_archive_preserved=True, applicable_prefork_result=check['handle'])
