"""Opt-in exact edited-source presentation; no new archive or authority channel."""
import copy


class CorrectionContextMixin:
    def recent_replacement(self):
        """Identify only the accepted edit or the check immediately following it."""
        if not self.pairs:
            return None
        index = len(self.pairs) - 1
        last = self.pairs[index]
        if last['response']['action'] == 'check':
            result = last['result']
            if (not result.get('executed') or
                    result.get('checked_candidate_id') != self.candidate.candidate_id):
                return None
            index -= 1
        if index < 0:
            return None
        pair = self.pairs[index]
        action, result = pair['response'], pair['result']
        if (action['action'] not in self.mutation_actions or not result.get('accepted')
                or result.get('candidate_id') != self.candidate.candidate_id):
            return None
        before = self.versions.get(result.get('previous_candidate_id'))
        path = result.get('path')
        if before is None or path not in self.candidate.file_map:
            return None
        original = before.file_map[path].decode()
        current = self.candidate.file_map[path].decode()
        if action['action'] == 'patch':
            old, replacement = action['old'], action['new']
            if not old or original.count(old) != 1:
                return None
            start = original.index(old)
        else:
            # A region address supplies coordinates, not editing authority.
            previous = self.clone()
            previous.candidate = before
            try:
                span = previous.resolve_region(action['region'])
            except ValueError:
                return None
            lines = original.splitlines(keepends=True)
            start = len(''.join(lines[:span['start_line'] - 1]))
            old = ''.join(lines[span['start_line'] - 1:span['end_line']])
            replacement = action['new'] + result.get('supplied_boundary_separator', '')
        if current != original[:start] + replacement + original[start + len(old):]:
            return None
        # An empty replacement has no successor text to preserve. Do not invent
        # a nearby semantic correction target for a deletion.
        if not replacement:
            return None
        first = current[:start].count('\n') + 1
        last = current[:start + len(replacement) - 1].count('\n') + 1
        return dict(path=path, start_line=first, end_line=last)

    def _fits_feedback(self, measure):
        fitted = super()._fits_feedback(measure)
        if not fitted or not self.recovery:
            return fitted
        span = self.recent_replacement()
        if span is None:
            return fitted
        focus, tier = copy.deepcopy(self.recovery_focus), self.control_tier
        # Keep every existing focus extent; do not evict another inspection to
        # force the new region in. Account and assessment choices stay as fitted.
        self.recovery_focus = self._verified_source_ranges(
            [self.source(s) for s in [*focus, span]])
        self.control_tier = min(tier, 1)  # tier 2 suppresses all source bodies
        if self._fits(measure, margin=0):
            return True
        self.recovery_focus, self.control_tier = focus, tier
        return fitted
