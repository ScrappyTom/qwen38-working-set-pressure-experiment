"""Replay actual native preparation with the existing independent verifier."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import traceback
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import compass_task as study
import compass_qualification
import run_compass
import verify_run
from working_set_exp.jsonutil import sha256_file

SOURCE = study.ROOT / 'development/workload_requalification/phase_entries/review/verify_preparation.py'
assert sha256_file(SOURCE) == '5f5c5a75161ea424c0139589856091913e435e26cd9b34d5ac4edea4a4525085'
spec = importlib.util.spec_from_file_location('compass_preparation_replay_core', SOURCE)
core = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'phase_task': study, 'qualification_route': compass_qualification,
                             'run_phase': run_compass.configure(), 'verify_run': verify_run}):
    spec.loader.exec_module(core)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    output = Path(__file__).with_name(f'PREPARATION-VERIFICATION-{args.version}.json')
    try:
        value = dict(core.verify(args.version), adapter_sha256=sha256_file(Path(__file__)),
                     serialized_checkpoint_roundtrips=True)
    except BaseException as error:
        verify_run.save(output.with_name(output.stem + '-FAILED.json'), dict(status='failed',
            type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
        raise
    verify_run.save(output, value)
    print(json.dumps(value, indent=2))
