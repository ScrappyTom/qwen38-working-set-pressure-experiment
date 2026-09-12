"""Actual-tool and identity checks for offline delivery probes, not actor behavior."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import qualify_compiler_delivery as probe
import prepare_incident_pressure as task
from working_set_exp.candidate import Candidate
from working_set_exp.interface_consultation import toy, patch
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict
from working_set_exp.event_frame_v3 import resident_pair_v3


def request(value):
    reference=task.pilot.tool_reference(task.pilot.grammar_for(value))
    return task.request_for(value,reference,externalized=len(value.pairs))


def read(value):
    return value.execute(dict(action='read',path='service.py',start_line=1))


class DeliveryProbeTests(unittest.TestCase):
    def test_nonprefix_retention_preserves_signals_identity_and_original(self):
        value=toy('delivery',b'old\n','inspect exact source',b'')
        read(value)
        value.execute(dict(action='tree',path='.',offset=0))
        read(value)
        old=request(value);saved=canonical_json_bytes(old)
        probe.exact_pairs_match(old,value.pairs)
        new=probe.grouped_request(old,value.pairs,{1,3})
        a,b=probe.state_of(old),probe.state_of(new)
        frame=b['active_phase_event_frame']
        self.assertNotIn('externalized_payload_through_sequence',frame)
        self.assertEqual(frame['resident_payload_sequences'],[1,3])
        for i,event in enumerate(frame['events']):
            previous=a['active_phase_event_frame']['events'][i]
            for key in ('action','result','exact_pair_identity','sequence','event_handle'):
                self.assertEqual(event[key],previous[key])
        self.assertEqual(resident_pair_v3(frame['events'][0]),value.pairs[0])
        self.assertIsNone(frame['events'][1]['result_body']['fields'])
        for key in a.keys()-{'active_phase_event_frame','event_frame_verification'}:
            self.assertEqual(a[key],b[key])
        self.assertEqual(canonical_json_bytes(old),saved)
        self.assertEqual(new['response_format'],old['response_format'])

    def test_changed_file_requires_current_content_unchanged_file_can_reuse(self):
        value=toy('versions',b'old\n','inspect',b'')
        read(value)
        current=value.state.candidate.file_sha256('service.py')
        self.assertEqual(probe.material_sequence(value.pairs,'service.py',{'service.py':current}),1)
        value.execute(patch(value,'old','new'))
        with self.assertRaisesRegex(ValueError,'no acquired complete current'):
            probe.material_sequence(value.pairs,'service.py',{'service.py':value.state.candidate.file_sha256('service.py')})
        read(value)
        self.assertEqual(probe.material_sequence(value.pairs,'service.py',
            {'service.py':value.state.candidate.file_sha256('service.py')}),3)
        # A changed candidate ID alone does not invalidate the identical file.
        other=Candidate.create({'service.py':b'old\n','other.txt':b'new candidate\n'})
        self.assertEqual(probe.material_sequence(value.pairs[:1],'service.py',
            {'service.py':other.file_sha256('service.py')}),1)

    def test_escaped_return_storage_recovery_and_next_input_are_exact(self):
        value=toy('escaping',(('"'*89+'\n')*200).encode(),'serialization probe',b'')
        original=read(value)
        self.assertTrue(original['accepted'])
        self.assertIsNotNone(original['next_start_line'])
        raw=canonical_json_bytes(original)
        with tempfile.TemporaryDirectory() as directory:
            archive=Path(directory)/'result.json';archive.write_bytes(raw)
            value.result_payloads['RES-0001']=archive.read_bytes()
            absent=request(value)
            self.assertIsNone(probe.state_of(absent)['active_phase_event_frame']['events'][0]['result_body']['fields'])
            recovered=value.execute(dict(action='reopen_result',handle='RES-0001'))
        self.assertEqual(recovered['exact_result_utf8'].encode(),raw)
        self.assertLessEqual(len(canonical_json_bytes(recovered)),22000)
        next_input=probe.grouped_request(request(value),value.pairs,{2})
        delivered=resident_pair_v3(probe.state_of(next_input)['active_phase_event_frame']['events'][1])['result']
        self.assertEqual(delivered,recovered)
        self.assertEqual(load_json_strict(delivered['exact_result_utf8'].encode())['content'],original['content'])

    def test_rejected_patch_retains_error_without_claiming_new_candidate(self):
        value=toy('rejection',b'old\n','inspect',b'')
        read(value);before=value.state.candidate.candidate_id
        rejected=value.execute(patch(value,'not present','new'))
        self.assertFalse(rejected['accepted'])
        req=probe.grouped_request(request(value),value.pairs,{2})
        state=probe.state_of(req)
        self.assertEqual(state['candidate_id'],before)
        self.assertEqual(resident_pair_v3(state['active_phase_event_frame']['events'][1])['result'],rejected)

    def test_bad_recovery_identity_and_missing_groups_fail_closed(self):
        value=toy('hash',b'old\n','inspect',b'');read(value)
        value.execute(dict(action='reopen_result',handle='RES-0001'))
        broken=copy.deepcopy(value.pairs);broken[-1]['result']['exact_result_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'identity differs'):
            probe.material_sequence(broken,'service.py',{'service.py':value.state.candidate.file_sha256('service.py')})
        with self.assertRaisesRegex(ValueError,'no acquired complete current'):
            probe.material_sequence(value.pairs,'missing.py',{})
        with self.assertRaisesRegex(ValueError,'invalid retained sequence'):
            probe.grouped_request(request(value),value.pairs,{3})

    def test_native_substitution_rejects_settings_changes_and_ambiguous_text(self):
        old={'messages':[{'role':'system','content':'instructions'},{'role':'user','content':'state'}], 'seed':1}
        native='<|im_start|>system\ninstructions<|im_end|>\n<|im_start|>user\nstate<|im_end|>\n<|im_start|>assistant\n<think>\n'
        self.assertEqual(probe.native_for(old,old,native),native.encode())
        changed=copy.deepcopy(old);changed['seed']=2
        with self.assertRaisesRegex(ValueError,'settings drift'):
            probe.native_for(changed,old,native)
        with self.assertRaisesRegex(ValueError,'ambiguous native'):
            probe.native_for(old,old,native+'state')


if __name__=='__main__':
    unittest.main()
