"""Actual host and complete-view checks for the bounded-read development screen."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import qualify_configparser_reads as q
from working_set_exp.jsonutil import canonical_json_bytes


class ConfigparserReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=q.history_before(27)

    def test_counted_view_changes_all_read_contract_copies_and_only_read_schema(self):
        original=q.work.request_for(copy.deepcopy(self.before),22)
        value,detail=q.narrowed(self.before,27,30)
        request=q.counted_request(value,22)
        state=q.envelope.state_of(request)
        self.assertEqual(state['read_paging_mode'],'actor_selected_count')
        self.assertIn('line_count',state['tool_contract']['read'])
        self.assertIn('line_count: integer; minimum 1; maximum 500',request['messages'][0]['content'])
        self.assertNotIn('no line_count argument',request['messages'][0]['content'])
        self.assertIn(q.NEW_EFFECT,request['messages'][0]['content'])
        self.assertEqual(q.work.request_for(copy.deepcopy(self.before),22),original)
        self.assertTrue(q.work.latest_result_delivered(request,value))

    def test_actual_read_preserves_source_identity_exact_recovery_and_partial_coverage(self):
        before=copy.deepcopy(self.before)
        before.state.read_coverage.clear();before.state.complete_reads.clear()
        value,detail=q.narrowed(before,27,30)
        r=detail['result']
        self.assertEqual((r['returned_start_line'],r['returned_end_line'],r['next_start_line']),(320,349,350))
        self.assertEqual(value.state.read_coverage['Lib/configparser.py'],[(320,349)])
        self.assertNotIn('Lib/configparser.py',value.state.complete_reads)
        self.assertFalse(r['complete'])
        self.assertEqual(value.state.candidate.candidate_id,before.state.candidate.candidate_id)
        self.assertEqual(before.state.read_coverage,{})
        self.assertLessEqual(detail['source_bytes'],18000)
        self.assertLessEqual(detail['recovery_bytes'],22000)
        self.assertEqual(len(value.pairs),len(before.pairs)+1)

    def test_invalid_count_or_wrong_shape_is_rejected_without_coverage_or_mutation(self):
        for count in (0,501,True):
            value=copy.deepcopy(self.before);value.executor.read_mode='actor_selected_count'
            state_before=q.original.pilot.reference.session_bytes(value.state)
            result=value.executor.execute(dict(action='read',path='Lib/configparser.py',start_line=320,line_count=count))
            self.assertFalse(result['accepted'])
            self.assertEqual(q.original.pilot.reference.session_bytes(value.state),state_before)
        value=copy.deepcopy(self.before);value.executor.read_mode='actor_selected_count'
        self.assertFalse(value.executor.execute(dict(action='read',path='Lib/configparser.py',start_line=320))['accepted'])

    def test_native_variant_keeps_verified_envelope_and_includes_complete_reference(self):
        stem=q.RUN/'admission/C28-x025'
        original=q.original.task.read(Path(str(stem)+'-endpoint-request.json'))
        native=Path(str(stem)+'-native.txt').read_bytes().decode()
        value,_=q.narrowed(self.before,27,30)
        request=q.counted_request(value,22)
        envelope=copy.deepcopy(original);envelope['response_format']=request['response_format']
        rebuilt=q.envelope.native_for(request,envelope,native).decode()
        for message in request['messages']:
            self.assertIn(message['content'].strip(),rebuilt)
        self.assertTrue(rebuilt.endswith('<|im_start|>assistant\n<think>\n'))
        changed=copy.deepcopy(request);changed['seed']+=1
        with self.assertRaisesRegex(ValueError,'settings drift'):
            q.envelope.native_for(changed,envelope,native)


if __name__=='__main__':unittest.main()
