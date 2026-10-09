"""Exact replay of native probe qualification, with no further execution."""
import argparse
import json
from pathlib import Path
import sys
import traceback
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import probe_task as study
import probe_qualification
import run_probe
import verify_run
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore


def verify(version='001'):
    module = study.Task(version)
    manifest = run_probe.controller.verify_preparation(module)
    folder = module.PACKAGE
    seal = module.read(folder / 'SEAL.json')
    verify_run.core._inventory(folder, seal)
    records = verify_records(folder / 'records.jsonl', folder)
    assert seal['source_sha256'] == manifest['source_sha256']
    assert seal['completion_requests'] == 0 and seal['status'] == 'qualified_no_model_inference'
    assert not any(r['record_type'] == 'invocation_started' for r in records)
    adapter = run_probe.controller.runner.Adapter(module)
    counts = verify_run.core._native_counts(folder, records, adapter)

    def measure(view):
        key = sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
        assert key in counts, 'Transition has no recorded native input'
        return counts[key]

    class ReplayTask:
        def __getattr__(self, name):
            return getattr(module, name)

        def attach_observations(self, session, output, log):
            session.observations = ObservationStore(output / 'observations', replay=True)

    class ExactStore:
        def put(self, name, raw):
            assert (folder / name).read_bytes() == raw, name

    with patch('working_set_exp.observations.subprocess.Popen', side_effect=AssertionError('No execution during replay')):
        route = probe_qualification.qualify(ReplayTask(), SimpleNamespace(measure=measure, log=None), adapter, ExactStore(), folder)
    proof = module.read(folder / 'QUALIFICATION.json')
    assert route == proof['route']
    native = proof['native_forms']
    assert native['status'] == 'passed' and all(r['accepted_including_eos'] == r['expected'] for r in native['cases'])
    closed = [r['payload'] for r in records if r['record_type'] == 'runtime_closed']
    assert len(closed) == 1 and closed[0]['owned_server_shutdown_verified'] and closed[0]['dedicated_port_free']
    return dict(status='replayed_exactly', case=module.CASE, preparation_seal_sha256=sha256_file(folder / 'SEAL.json'),
        artifacts=len(seal['files']), source_bindings=len(seal['source_sha256']), custody_records=len(records),
        native_inputs=len(counts), native_forms=len(native['cases']),
        scripted_decisions=sum(len(v['trials']) for v in route['variants'].values()),
        submitted=route['submitted'], serialized_checkpoint_roundtrips=True,
        no_model_inference=True, no_additional_tokenization=True,
        no_additional_checker_execution=True, verifier_sha256=sha256_file(Path(__file__)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    version = parser.parse_args().version
    output = Path(__file__).with_name(f'PREPARATION-VERIFICATION-{version}.json')
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
