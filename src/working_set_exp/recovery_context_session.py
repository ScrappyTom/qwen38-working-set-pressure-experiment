"""Keep a still-applicable edit diagnostic through intervening acquisition."""
from . import decision_view
from .recovery_inspection_session import RecoveryInspectionSession


class RecoveryContextSession(RecoveryInspectionSession):
    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['recent_edit_rejection'] = None
        for index in range(len(self.pairs)-1, -1, -1):
            pair = self.pairs[index]
            result, action = pair['result'], pair['response']
            regions = result.get('match_regions')
            if result.get('accepted') or not regions:
                continue
            if any(region['path'] not in self.candidate.file_map or
                   self.candidate.file_sha256(region['path']) != region['file_sha256'] for region in regions):
                continue
            sequence = index+1
            if value['latest_feedback'] and value['latest_feedback']['sequence'] == sequence:
                break  # This record is already represented by immediate feedback.
            receipt = decision_view.receipt_view(dict(sequence=sequence,
                action_summary={k:action[k] for k in ('action','path','expected_candidate_id','expected_file_sha256') if k in action},
                result=result))
            value['recent_edit_rejection'] = dict(kind='historical_rejection_no_edit_committed',
                file_binding_matches_current=True, receipt=receipt)
            break
        return value
