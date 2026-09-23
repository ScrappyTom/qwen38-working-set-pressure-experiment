"""Optional chronological context after required recovery content is admitted."""
from working_set_exp.working_session import RECENT_COUNT


class RecoveryChronologyMixin:
    # Immutable presentation setting; successor checkpoint adapters must save it.
    recovery_recent_count = 0

    def view(self, **kwargs):
        value = super().view(**kwargs)
        if self.recovery:
            count = self.recovery_recent_count
            if type(count) is not int or not 0 <= count <= RECENT_COUNT:
                raise ValueError('invalid qualified recovery history count')
            value['recent_activity'] = [self.summary(i) for i in
                range(max(1, len(self.pairs)-count+1), len(self.pairs)+1)] if count else []
        return value

    def _fits_feedback(self, measure):
        self.recovery_recent_count = 0
        fitted = super()._fits_feedback(measure)
        if not fitted or not self.recovery:
            return fitted
        # Required source arrangement, account and immediate feedback have priority.
        # Zero rows reproduces the admitted parent view exactly.
        for count in range(min(RECENT_COUNT, len(self.pairs)), -1, -1):
            self.recovery_recent_count = count
            if self._fits(measure, margin=0):
                return True
        return False
