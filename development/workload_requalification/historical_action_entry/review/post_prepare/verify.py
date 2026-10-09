"""Replay the sealed information path using saved native counts and observations."""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import bootstrap
import historical_task as study
import qualification_route
import run_entry
import verify_run
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore


def verify(version='001'):
    module = study.Task(version)
    manifest = run_entry.verify_preparation(module)
    folder = module.PACKAGE
    seal = study.read(folder / 'SEAL.json')
    verify_run._inventory(folder, seal)
    assert seal['source_sha256'] == manifest['source_sha256']
    records = verify_records(folder / 'records.jsonl', folder)
    # The frozen preparation seal authenticates records.jsonl in its inventory;
    # unlike a live RESPONSE_SEAL it has no record_count field.
    assert records and records[-1]['sequence'] == len(records)
    assert not any(row['record_type'] == 'invocation_started' for row in records)
    adapter = run_entry.runner.Adapter(module)
    counts = verify_run._native_counts(folder, records, adapter)

    def measure(view):
        key = sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
        assert key in counts, 'Scripted transition has no saved native input measurement'
        return counts[key]

    class ReplayTask:
        def __getattr__(self, name):
            return getattr(module, name)

        def attach_observations(self, session, output, log):
            session.observations = ObservationStore(output / 'observations', replay=True)

    class ExactStore:
        def put(self, name, raw):
            assert (folder / name).read_bytes() == raw, name

    with patch('working_set_exp.observations.subprocess.Popen',
            side_effect=AssertionError('No checker execution during qualification replay')):
        route = qualification_route.qualify(ReplayTask(), SimpleNamespace(measure=measure, log=None),
            adapter, ExactStore(), folder)
    proof = study.read(folder / 'QUALIFICATION.json')
    assert route == proof['route']
    native = proof['native_forms']
    assert native['status'] == 'passed'
    assert all(row['accepted_including_eos'] == row['expected'] for row in native['cases'])
    return dict(status='replayed_exactly', preparation_seal_sha256=sha256_file(folder / 'SEAL.json'),
        artifacts=len(seal['files']), source_bindings=len(seal['source_sha256']),
        custody_records=len(records), native_inputs=len(counts), native_forms=len(native['cases']),
        scripted_decisions=len(route['trials']), submitted=route['submitted'],
        observations_replayed_without_execution=2, no_model_inference=True, no_additional_tokenization=True,
        original_history_preserved=True, verifier_sha256=sha256_file(Path(__file__)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    result = verify(args.version)
    path = Path(__file__).with_name('PREPARATION-VERIFICATION-' + args.version + '.json')
    raw = canonical_json_bytes(result)
    if path.exists():
        assert path.read_bytes() == raw
    else:
        path.write_bytes(raw)
    print(json.dumps(result, indent=2))
