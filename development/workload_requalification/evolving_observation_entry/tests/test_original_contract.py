"""Original task acceptance is broader than the old sufficient-condition screen."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import original_contract_next as contract
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes


class OriginalContractTests(unittest.TestCase):
    def fixtures(self):
        audit=dict(edits=[dict(sequence=2,path=contract.study.TARGET,all_ledgers_delivered=False,
            bound_marker_previously_delivered=True,bound_marker_body_in_this_input=True),
            dict(sequence=5,path=contract.study.SECONDARY,all_ledgers_delivered=False,
            bound_marker_previously_delivered=True,bound_marker_body_in_this_input=True)],
            decisions=[dict(all_ledgers_delivered=True,effects=[dict(sequence=9,action='submit',accepted=True)])],
            label_before_footer=True,submitted_from_current_pass=True)
        artifact=dict(ordinary_behavior_passed=True,only_target_files_changed=True,unchanged_other_files=128)
        return audit,artifact

    def test_ledgers_can_complete_after_edits_but_before_submission(self):
        audit,artifact=self.fixtures()
        self.assertTrue(contract.criteria(audit,artifact,{})['original_contract_supported'])
        audit['decisions'][0]['all_ledgers_delivered']=False
        self.assertFalse(contract.criteria(audit,artifact,{})['original_contract_supported'])

    def test_alternate_exact_payload_is_reviewed_not_automatically_promoted_or_rejected(self):
        audit,artifact=self.fixtures()
        audit['edits'][1]['bound_marker_body_in_this_input']=False
        self.assertFalse(contract.criteria(audit,artifact,{})['original_contract_supported'])
        value=contract.criteria(audit,artifact,{5:[dict(handle='EVT-0002')]})
        self.assertIsNone(value['original_contract_supported'])
        self.assertEqual(value['payloads_needing_direct_review'],[5])

    def test_only_complete_authenticated_delivered_pages_count_as_exact_payloads(self):
        action=dict(action='patch',path='codec/label.py',new='actual recorded source')
        pair=dict(response=action,result=dict(accepted=True))
        raw=canonical_json_bytes(action)
        page=dict(kind='saved_bytes',handle='EVT-0001',offset=0,next_offset=None,
            total_bytes=len(raw),sha256=sha256_bytes(raw),exact_utf8=raw.decode())
        view=dict(archive=dict(action_count=1),working_set=dict(saved_results=[page]),latest_feedback=None)
        envelope=dict(workspace=view)
        result=contract.exact_historical_pages(envelope,[pair])
        self.assertEqual(result[0]['exact_payload'],action)
        page['next_offset']=len(raw)-1
        self.assertEqual(contract.exact_historical_pages(envelope,[pair]),[])
        page['next_offset']=None
        page['exact_utf8']='different'
        with self.assertRaises(AssertionError):
            contract.exact_historical_pages(envelope,[pair])
        view['working_set']['saved_results']=[]
        view['working_account']=dict(text='The marker has been recovered.')
        self.assertEqual(contract.exact_historical_pages(envelope,[pair]),[])

    def test_actual_run001_remains_incomplete_under_original_contract(self):
        result=contract.evaluate('001')
        self.assertFalse(result['original_contract_supported'])
        self.assertFalse(result['criteria']['complete_required_ledger_delivery_by_submission'])
        self.assertFalse(result['criteria']['exact_marker_available_or_permitted_recovery'])
        self.assertFalse(result['prospective_contract'])


if __name__=='__main__':
    unittest.main()
