"""Replay the closed probe entry through the existing exact-verification core."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import traceback
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import probe_task as study
import run_probe
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file

CORE = study.ROOT / 'development/workload_requalification/url_port_entry/review/verify_run.py'
spec = importlib.util.spec_from_file_location('probe_exact_replay_core', CORE)
core = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'url_task': study}):
    spec.loader.exec_module(core)


def preparation(module, seal):
    manifest = run_probe.controller.verify_preparation(module)
    assert module.MANIFEST.read_bytes() == (module.RUN / 'EXECUTION_MANIFEST.json').read_bytes()
    assert manifest['source_sha256'] == seal['source_sha256'] == module.source_identities()
    assert manifest['actor'] == seal['actor'] == module.ACTOR
    assert (manifest['maximum_requests'], manifest['maximum_operations']) == (32, 96)
    proof = module.read(module.PACKAGE / 'SEAL.json')
    core._inventory(module.PACKAGE, proof)
    assert proof['status'] == 'qualified_no_model_inference' and proof['completion_requests'] == 0
    first = module.RUN / 'calls/C01-wire-request.json'
    if first.exists():
        assert first.read_bytes() == (module.PACKAGE / 'initial-wire-request.json').read_bytes()
        assert sha256_file(first) == manifest['initial']['wire_request_sha256']
    return manifest


core._preparation = preparation


def verify(version='001'):
    return core.verify(version)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    version = parser.parse_args().version
    output = Path(__file__).with_name(f'VERIFICATION-{version}.json')
    try:
        value = verify(version)
    except BaseException as error:
        with output.with_name(output.stem + '-FAILED.json').open('xb') as stream:
            stream.write(canonical_json_bytes(dict(status='failed', type=type(error).__name__, message=str(error), traceback=traceback.format_exc())))
        raise
    raw = canonical_json_bytes(value)
    if output.exists():
        assert output.read_bytes() == raw
    else:
        with output.open('xb') as stream:
            stream.write(raw)
    print(json.dumps(value, indent=2))
