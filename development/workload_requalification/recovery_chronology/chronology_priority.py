"""Keep the admitted arrangement ahead of optional chronological rows."""
from working_set_exp.working_session import RECENT_COUNT,WorkingSession
from chronology import RecoveryChronologyMixin as InitialMixin


class RecoveryChronologyMixin(InitialMixin):
    def _fits_feedback(self, measure):
        self.recovery_recent_count=0
        # Bypass the initial mixin's optional-row loop, preserving its qualified
        # view implementation and the complete preexisting host admission path.
        fitted=super(InitialMixin,self)._fits_feedback(measure)
        if not fitted or not self.recovery:
            return fitted
        for count in range(min(RECENT_COUNT,len(self.pairs)),-1,-1):
            self.recovery_recent_count=count
            # Base measurement records the complete input without rerunning
            # navigation/change fallbacks that could displace admitted detail.
            if WorkingSession._fits(self,measure,margin=0):
                return True
        return False
