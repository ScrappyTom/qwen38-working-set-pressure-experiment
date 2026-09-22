"""Prospective receipt labeling; exact archived operations remain unchanged."""
import interpolation_task as previous
import report_projection


class Session(previous.Session):
    assessment_api = report_projection

    def view(self, **kwargs):
        value = super().view(**kwargs)
        receipt = value.get('latest_feedback')
        if receipt is not None:
            value['latest_feedback'] = dict(receipt,
                episode='prior_work' if receipt['sequence'] <= self.starting_archive_length else 'this_contribution')
        if getattr(self, 'continuation_accounting', None):
            value['allowance']['inherited_attempt'] = dict(self.continuation_accounting)
        return value
