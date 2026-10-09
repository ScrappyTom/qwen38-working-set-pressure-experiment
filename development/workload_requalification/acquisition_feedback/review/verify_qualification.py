"""Replay the saved native acquisition cases without model or checker execution."""
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA.parent / 'evolving_source_entry/continuation_entry'))
import bootstrap
import continuation_task
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify():
    folder = AREA / 'qualification-002'
    audit = load('acquisition_native_audit_helpers',
        continuation_task.AREA / 'review/verify_run.py')
    task = continuation_task.previous
    module = task.Task()
    report, seal = task.read(folder / 'QUALIFICATION.json'), task.read(folder / 'SEAL.json')
    assert report['status'] == 'qualified' and report['completion_requests'] == 0
    assert not report['policy_changed'] and report['port_free']
    audit._inventory(folder, seal)
    task.verify_sources(seal['source_sha256'])
    records = verify_records(folder / 'records.jsonl', folder)
    assert not any(row['record_type'] == 'invocation_started' for row in records)
    runner = audit._runner()
    adapter = runner.Adapter(module)
    counts = audit._native_counts(folder, records, adapter)
    checked = []

    def measure(view):
        key = sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
        assert key in counts, 'replay requires missing saved native measurement'
        return counts[key]

    with patch('working_set_exp.observations.subprocess.Popen',
               side_effect=AssertionError('no checker during acquisition replay')):
        for row in report['cases']:
            tag = row['case']
            state = task.read(folder / (tag + '-input-state.json'))
            candidate = task.read(folder / (tag + '-input-candidate.json'))
            session = task.restore(state, candidate, task.AREA / 'run-001', replay=True)
            if tag.endswith('hard-ceiling-diagnostic'):
                class HardCeilingOnly(type(session)):
                    def _fits(self, measure, *, margin=1024):
                        return super()._fits(measure, margin=0)
                session.__class__ = HardCeilingOnly
            adapter.preceding_feedback = task.read(folder / (tag + '-input-preceding-feedback.json'))
            assert session.view() == task.read(folder / (tag + '-input-view.json'))
            assert measure(session.view()) == row['admitted_input_tokens']
            session.mark_delivered(session.view())
            session.begin_request()
            operation = task.read(folder / (tag + '-operation.json'))
            result = task.process_reply(session, operation['reply'], measure, adapter.preceding_feedback)
            assert result == operation['result']
            assert measure(session.view()) == row['following_input_tokens']
            assert session.view() == task.read(folder / (tag + '-after-view.json'))
            assert canonical_json_bytes(task.snapshot(session)) == (folder / (tag + '-after-state.json')).read_bytes()
            assert task.candidate_bytes(session.candidate) == (folder / (tag + '-after-candidate.json')).read_bytes()
            assert adapter.preceding_feedback == task.read(folder / (tag + '-after-preceding-feedback.json'))
            checked.append(tag)
    closed = [r['payload'] for r in records if r['record_type'] == 'runtime_closed']
    assert len(closed) == 1 and closed[0]['owned_server_shutdown_verified'] and closed[0]['dedicated_port_free']
    return dict(status='saved_admitted_transitions_replayed_exactly', cases=checked,
        artifacts=len(seal['files']), source_bindings=len(seal['source_sha256']),
        custody_records=len(records), native_inputs=len(counts),
        qualification_seal_sha256=sha256_file(folder / 'SEAL.json'),
        verification_source_sha256=sha256_file(Path(__file__)),
        no_new_model_or_checker_or_tokenizer_execution=True,
        scope='Replay starts at each saved admitted input. The preceding optional-history admission fallback is preserved in the qualification records, not replayed by this audit.')


if __name__ == '__main__':
    result = verify()
    output = Path(__file__).with_name('VERIFICATION-002.json')
    raw = canonical_json_bytes(result)
    if output.exists():
        assert output.read_bytes() == raw
    else:
        output.write_bytes(raw)
    print(json.dumps(result, indent=2))
