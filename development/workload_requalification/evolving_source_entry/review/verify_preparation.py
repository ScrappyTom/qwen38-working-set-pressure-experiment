"""Replay sealed qualification from saved native counts and actual observations."""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap
import source_task as study
import qualification_route
import run_evolving
import verify_run
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore


def verify(version='001'):
    module = study.Task(version)
    manifest = run_evolving.verify_preparation(module)
    folder = module.PACKAGE
    seal = study.read(folder / 'SEAL.json')
    strong = verify_run._load('e18_qualification_counts', verify_run.STRONG_CORE, 'url_task')
    strong._inventory(folder, seal)
    assert seal['source_sha256'] == manifest['source_sha256']
    records = verify_records(folder / 'records.jsonl', folder)
    assert records and records[-1]['sequence'] == len(records)
    assert not any(row['record_type'] == 'invocation_started' for row in records)
    adapter = run_evolving.runner.Adapter(module)
    counts = strong._native_counts(folder, records, adapter)

    def measure(view):
        key = sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
        assert key in counts, 'Scripted input lacks a saved native measurement'
        return counts[key]

    class ReplayTask:
        def __getattr__(self, name):
            return getattr(module, name)

        def attach_observations(self, session, output, log):
            session.observations = ObservationStore(output / 'observations', replay=True)

    class ExactStore:
        def put(self, name, raw):
            assert (folder / name).read_bytes() == raw, name
            return dict(path=name, sha256=sha256_bytes(raw), size_bytes=len(raw))

    class Log:
        def append(self, *args):
            pass

    with patch('working_set_exp.observations.subprocess.Popen',
               side_effect=AssertionError('No execution during qualification replay')):
        route = qualification_route.qualify(ReplayTask(), SimpleNamespace(measure=measure, log=Log()),
            adapter, ExactStore(), folder)
    proof = study.read(folder / 'QUALIFICATION.json')
    assert route == proof['route'] and route['audit']['temporal_contract_met']
    native = proof['native_forms']
    assert native['status'] == 'passed'
    assert all(row['accepted_including_eos'] == row['expected'] for row in native['cases'])
    return dict(status='replayed_exactly', preparation_seal_sha256=sha256_file(folder / 'SEAL.json'),
        artifacts=len(seal['files']), source_bindings=len(seal['source_sha256']),
        custody_records=len(records), native_inputs=len(counts), native_forms=len(native['cases']),
        scripted_decisions=len(route['trials']), submitted=route['submitted'],
        temporal_contract_met=True, observations_replayed_without_execution=1,
        no_model_inference=True, no_additional_tokenization=True,
        verifier_sha256=sha256_file(Path(__file__)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    result = verify(args.version)
    target = Path(__file__).with_name('PREPARATION-VERIFICATION-' + args.version + '.json')
    raw = canonical_json_bytes(result)
    if target.exists():
        assert target.read_bytes() == raw
    else:
        target.write_bytes(raw)
    print(json.dumps(result, indent=2))
