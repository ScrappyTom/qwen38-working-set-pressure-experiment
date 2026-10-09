"""Replay the saved qualification without inference, native calls or checks."""
import argparse
import json
from pathlib import Path
import sys
import traceback
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_run as replay
import continuation_route as qualification_route
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes


def verify(version):
    task = replay.study.Task(version)
    runner = replay.run_continuation.runner.runner
    manifest = runner.verify_package(task)
    seal = task.read(task.PACKAGE/'SEAL.json')
    replay.core._inventory(task.PACKAGE, seal)
    records = verify_records(task.PACKAGE/'records.jsonl', task.PACKAGE)
    adapter = runner.Adapter(task)
    counts = replay.core._native_counts(task.PACKAGE, records, adapter)
    proof = task.read(task.PACKAGE/'QUALIFICATION.json')
    assert proof['completion_requests'] == 0 and proof['port_free']
    assert all(c['expected'] == c['accepted_including_eos'] for c in proof['native_forms']['cases'])
    assert manifest['source_sha256'] == seal['source_sha256'] == task.source_identities()

    task.replay_folder = task.PACKAGE/'scripted'
    task.attach_observations = lambda *args: None
    measurements = []

    def measure(view):
        key = sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
        assert key in counts, 'No recorded native measurement for reconstructed input'
        measurements.append(key)
        return counts[key]

    compared = []

    def put(name, raw):
        assert (task.PACKAGE/name).read_bytes() == raw, name
        compared.append(name)

    result = qualification_route.qualify(task, SimpleNamespace(measure=measure, log=None),
        adapter, SimpleNamespace(put=put), task.PACKAGE)
    assert result == proof['route']
    for step in range(1, result['decisions']+1):
        state = task.read(task.PACKAGE/f'route/{step:02d}-state.json')
        candidate = next(v for v in state['source_versions'] if v['candidate_id'] == state['candidate_id'])
        restored = task.restore(state, candidate, task.PACKAGE/'scripted', replay=True)
        assert canonical_json_bytes(task.snapshot(restored)) == canonical_json_bytes(state)

    return dict(status='passed', completion_requests=0, check_executions=0,
        sealed_artifacts=len(seal['files']), source_bindings=len(seal['source_sha256']),
        custody_records=len(records), native_inputs=len(counts), native_forms=len(proof['native_forms']['cases']),
        scripted_decisions=result['decisions'], compared_artifacts=len(compared),
        restored_states=result['decisions'], initial_tokens=proof['initial']['prompt_tokens'],
        peak_scripted_tokens=max(max(t['input_tokens'], t['following_tokens']) for t in result['trace']),
        submitted=result['submitted'], failed_then_passed=result['failed_then_passed'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    path = Path(__file__).with_name(f'PREPARATION-VERIFICATION-{args.version}.json')
    try:
        value = verify(args.version)
    except BaseException as error:
        replay.save(path.with_name(path.stem+'-FAILED.json'), dict(status='failed',
            type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
        raise
    replay.save(path, value)
    print(json.dumps(value, indent=2))
