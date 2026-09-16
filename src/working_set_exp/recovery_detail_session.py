"""Admit control detail independently after the recovery body arrangement fits."""
from . import decision_view
from .reference_session import ReferenceSession


class RecoveryDetailSession(ReferenceSession):
    # Immutable, copied with the session. Checkpoint adapters must preserve it.
    restored_control_fields = ()

    def view(self, **kwargs):
        value = super().view(**kwargs)
        if not self.recovery:
            return value
        if 'feedback' in self.restored_control_fields and self.last:
            value['latest_feedback'] = decision_view.receipt_view(self.last)
            result = value['latest_feedback']['result']
            if result.get('executed') and result.get('observation') and result.get('check_id'):
                result['report'] = self.assessment_api.overview(self._assessment(result['observation']))
        if 'account' in self.restored_control_fields:
            account = self.working_account()
            value['working_account'] = dict(account, text_complete=True) if account else None
        return value

    def _fits_feedback(self, measure):
        self.restored_control_fields = ()
        fitted = super()._fits_feedback(measure)
        if not self.recovery:
            return fitted
        # The parent chooses the existing source arrangement. Re-evaluate control
        # content in that arrangement, rather than inheriting its fixed byte cuts.
        # Either field can fit independently; neither forces loss of the other.
        for fields in (('feedback', 'account'), ('feedback',), ('account',), ()):
            self.restored_control_fields = fields
            if self._fits(measure, margin=0):
                return True
        return False
