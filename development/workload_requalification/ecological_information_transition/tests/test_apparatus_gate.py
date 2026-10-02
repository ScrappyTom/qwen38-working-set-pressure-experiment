"""The limited apparatus basis must not admit other failures or altered input."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bootstrap
import run_transition as control
import transition_task as study


class ApparatusGate(unittest.TestCase):
    def setUp(self):
        self.folder=study.AREA/'apparatus_qualification/run-001'
        self.result=study.read(self.folder/'RESULT.json')
        self.records=control.verify_records(self.folder/'records.jsonl',self.folder)

    def test_actual_deadline_and_two_exact_inputs(self):
        self.assertEqual(control.require_apparatus(),control.sha256_file(self.folder/'SEAL.json'))

    def test_early_transport_or_cuda_failure_is_not_the_exception(self):
        altered=copy.deepcopy(self.records)
        start=next(r for r in altered if r['record_type']=='process_memory_monitor_started')
        stop=next(r for r in altered if r['record_type']=='apparatus_transport_stopped')
        stop['created_at_utc']=start['created_at_utc']
        with self.assertRaises(AssertionError):
            control._timebox_basis(self.result,altered)
        altered=copy.deepcopy(self.records)
        ready=next(r for r in altered if r['record_type']=='runtime_ready')
        ready['payload']['effective_runtime']['cuda_failure_observed']=True
        with self.assertRaises(AssertionError):
            control._timebox_basis(self.result,altered)

    def test_changed_actual_generation_or_input_does_not_qualify(self):
        original=study.read
        def changed(path):
            value=original(path)
            if str(path).endswith('P02-wire-request.json'):
                value['max_tokens']=33
            return value
        with patch.object(study,'read',side_effect=changed),self.assertRaises(AssertionError):
            control.require_apparatus()


if __name__=='__main__':
    unittest.main()
