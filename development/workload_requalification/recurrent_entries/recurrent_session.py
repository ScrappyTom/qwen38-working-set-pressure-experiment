"""Ordered original phases over the existing phase/delivery host."""
import copy

import recurrent_bootstrap
import phase_session
from working_set_exp.jsonutil import sha256_bytes


class Session(phase_session.Session):
    order = ('A', 'B', 'C', 'D')

    def __init__(self, *args, phase_texts, phase_required, phase_checkers,
                 phase_contracts, **kwargs):
        if any(set(value) != set(self.order) for value in
               (phase_texts, phase_required, phase_checkers, phase_contracts)):
            raise ValueError('exactly four original ordered phases are required')
        self.phase_checkers = dict(phase_checkers)
        self.phase_contracts = copy.deepcopy(phase_contracts)
        for phase in self.order:
            if phase_contracts[phase]['checker_sha256'] != sha256_bytes(phase_checkers[phase]):
                raise ValueError('phase contract belongs to another checker')
        # Reuse initialization and coverage without widening the frozen A/B host.
        super().__init__(*args,
            phase_texts={p: phase_texts[p] for p in ('A', 'B')},
            phase_required={p: phase_required[p] for p in ('A', 'B')}, **kwargs)
        self.phase_texts = dict(phase_texts)
        self.phase_required = {p: tuple(phase_required[p]) for p in self.order}
        self.sync_checkers()

    @property
    def phase(self):
        forks = [p for p in self.pairs if p['response']['action'] == 'fork_ready'
                 and p['result'].get('accepted')]
        if len(forks) >= len(self.order):
            raise ValueError('too many accepted phase boundaries')
        for index, pair in enumerate(forks):
            if (pair['result']['completed_phase'], pair['result']['next_phase']) != self.order[index:index+2]:
                raise ValueError('accepted phase boundary order differs')
        return self.order[len(forks)]

    def sync_checkers(self):
        public_phase = 'B' if self.phase == 'A' else self.phase
        # Replace mappings; a staged clone must not mutate its predecessor.
        self.checkers = {'prefork': self.phase_checkers['A'], 'public': self.phase_checkers[public_phase]}
        self.checker = self.checkers['public']
        self.check_contracts = {'prefork': copy.deepcopy(self.phase_contracts['A']),
                               'public': copy.deepcopy(self.phase_contracts[public_phase])}

    def _record(self, action, result):
        super()._record(action, result)
        self.sync_checkers()

    def _contract(self, handle):
        record = self.observations.read(handle)
        for phase in self.order:
            scope = 'prefork' if phase == 'A' else 'public'
            contract = self.phase_contracts[phase]
            if record['check_id'] == scope and record['checker_sha256'] == contract['checker_sha256']:
                return contract
        return None

    def view(self, **kwargs):
        value = super().view(**kwargs)
        index = self.order.index(self.phase)
        scope = 'prefork' if index == 0 else 'public'
        value['phase'] = dict(current=self.phase, active_assignment=self.phase_texts[self.phase],
            completed=list(self.order[:index]), current_check=scope,
            current_checker_sha256=sha256_bytes(self.checkers[scope]),
            required_source_delivery=self.coverage_status(),
            coverage_meaning='Previously presented exact file extents, not present edit authority or proof of understanding.',
            boundary='submit' if self.phase == 'D' else 'fork_ready')
        value['episode_annotation'] = (
            'This is one four-phase task in order A, B, C, D. The current assignment is in phase. '
            'Accepted boundaries release selected source/result bodies and preserve files, exact '
            'history and the authored account. They do not reset the overall opportunity. '
            'Each phase uses its original checker definition; an earlier public pass remains '
            'historical and may not apply even on unchanged candidate bytes. Historical delivery '
            'does not establish current visibility. No prior conversation is supplied.')
        if self.phase != 'D':
            value['verification']['submission'].update(eligible=False,
                reason='This nonterminal phase requires fork_ready; only Phase D permits submission.')
        return value

    def _ordinary(self, action):
        name = action['action']
        scope = 'prefork' if self.phase == 'A' else 'public'
        if name == 'check' and action['check_id'] != scope:
            return dict(accepted=False, error='Check is not active in this phase; consult phase.current_check.')
        if name == 'submit' and self.phase != 'D':
            return dict(accepted=False, error='Only Phase D permits final submission.')
        if name != 'fork_ready':
            # Preserve navigation and the exact-work dispatcher, bypassing only
            # the parent's fixed two-phase gates which this adapter replaces.
            return super(phase_session.Session, self)._ordinary(action)
        if self.phase == 'D':
            return dict(accepted=False, error='Phase D is terminal; use submit after its current public pass.')
        if action['expected_candidate_id'] != self.candidate.candidate_id:
            return dict(accepted=False, error='Stale fork candidate binding.')
        missing = [r['path'] for r in self.coverage_status() if not r['complete']]
        if missing:
            return dict(accepted=False, error='Required current-phase source was not completely presented.', missing_paths=missing)
        check = self.scoped_check_state(scope)
        if not (check and check['applies_to_current'] and check['passed']):
            return dict(accepted=False, error='Current candidate has no passing active-phase check.')
        current, following = self.phase, self.order[self.order.index(self.phase) + 1]
        self.ranges, self.saved, self.delivered_sources = [], {}, []
        self.recovery, self.recovery_obstacle, self.control_tier = False, None, 0
        self.recovery_focus, self.parked_source_regions = [], ()
        return dict(accepted=True, fork_ready=True, candidate_id=self.candidate.candidate_id,
            completed_phase=current, next_phase=following, selected_bodies_released=True,
            files_and_archive_preserved=True, applicable_phase_result=check['handle'],
            next_check='public', next_checker_sha256=sha256_bytes(self.phase_checkers[following]))
