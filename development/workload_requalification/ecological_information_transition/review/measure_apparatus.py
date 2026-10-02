"""Verify closed apparatus custody and recompute timings/memory without inference."""
import copy
from datetime import datetime
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap
import transition_task as study
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

HERE = Path(__file__).resolve().parent
FOLDER = study.AREA / 'apparatus_qualification/run-001'


def moment(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def verify_and_measure():
    seal, result = [study.read(FOLDER / name) for name in ('SEAL.json', 'RESULT.json')]
    assert seal['status'] == result['status']
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    assert len({r['path'] for r in seal['files']}) == len(seal['files'])
    for row in seal['files']:
        path = (FOLDER / row['path']).resolve()
        assert path.is_relative_to(FOLDER.resolve())
        assert path.stat().st_size == row['size_bytes'] and sha256_file(path) == row['sha256']
    for name, digest in seal['private_runtime_files_local_only'].items():
        assert sha256_file(FOLDER / 'private-runtime' / name) == digest
    module = study.Task('unchanged')
    module.verify_sources(seal['source_sha256'])
    records = verify_records(FOLDER / 'records.jsonl', FOLDER)
    assert len(records) == seal['record_count']
    starts = [r for r in records if r['record_type'] == 'apparatus_invocation_started']
    returned = {r['payload']['id']: r for r in records if r['record_type'] == 'apparatus_response_preserved'}
    closed = [r for r in records if r['record_type'] == 'process_memory_monitor_closed']
    assert len(closed) == 1 and closed[0]['payload']['returncode'] == 0
    assert len(starts) == result['completion_requests']
    assert result['behavioral_operations'] == 0 and not result['runtime_policy_changed']
    assert result['port_free']
    samples = [json.loads(line) for line in (FOLDER / 'process-memory.jsonl').read_text(encoding='utf-8').splitlines()]
    pid = result['process_memory']['server_pid']

    def memory(rows):
        def bounds(key):
            values = [r[key] for r in rows if key in r]
            return {'min': min(values), 'max': max(values)} if values else None
        owned = [g for r in rows for g in r.get('gpu_process_memory', [])
                 if g.get('name', '').startswith('pid_' + str(pid) + '_')]
        return dict(samples=len(rows),
            working_set_bytes=bounds('server_working_set_bytes'),
            private_bytes=bounds('server_private_bytes'),
            system_available_bytes=bounds('system_available_bytes'),
            owned_counter_rows=len(owned),
            dedicated_bytes=({'min': min(g['dedicated_bytes'] for g in owned),
                              'max': max(g['dedicated_bytes'] for g in owned)} if owned else None),
            shared_bytes=({'min': min(g['shared_bytes'] for g in owned),
                           'max': max(g['shared_bytes'] for g in owned)} if owned else None),
            unavailable=sorted({str(v) for r in rows for k, v in r.items() if k.endswith('unavailable')}))

    calls = []
    for index, start in enumerate(starts, 1):
        row = start['payload']
        assert row['id'] == f'P{index:02d}'
        task = study.Task(row['condition'])
        assert sha256_file(task.MANIFEST) == result['prepared_manifests'][row['condition']]
        manifest = study.read(task.MANIFEST)
        expected = copy.deepcopy(study.read(task.PACKAGE / 'initial-wire-request.json'))
        expected['max_tokens'] = expected['n_predict'] = 32
        stem = FOLDER / 'calls' / row['id']
        assert Path(str(stem) + '-wire-request.json').read_bytes() == completion_request_bytes(expected)
        native = Path(str(stem) + '-native.txt').read_bytes()
        assert native == (task.PACKAGE / 'admission/I0001-native.txt').read_bytes()
        assert native == study.read(Path(str(stem) + '-template.json'))['prompt'].encode()
        entry = dict(id=row['id'], condition=row['condition'], input_tokens=row['prompt_tokens'],
                     started_at_utc=start['created_at_utc'])
        if row['id'] in returned:
            end = returned[row['id']]
            data = study.read(Path(str(stem) + '-endpoint-response.json'))
            usage, timings = data['usage'], data['timings']
            assert usage['prompt_tokens'] == row['prompt_tokens'] == manifest['initial']['prompt_tokens']
            assert 0 < usage['completion_tokens'] <= 32
            assert usage['total_tokens'] == usage['prompt_tokens'] + usage['completion_tokens']
            assert usage['prompt_tokens_details']['cached_tokens'] == timings['cache_n'] == 0
            entry.update(completed=True, usage=usage, timings=timings,
                elapsed_seconds=end['payload']['elapsed_seconds'],
                finish_reason=data['choices'][0]['finish_reason'],
                returned_at_utc=end['created_at_utc'])
            finish = moment(end['created_at_utc'])
        else:
            entry.update(completed=False, elapsed_seconds=None, usage=None, timings=None)
            finish = moment(closed[0]['created_at_utc'])
            partial = Path(str(stem) + '-partial-response.bin')
            entry['partial_response_bytes'] = partial.stat().st_size if partial.exists() else None
        entry['memory'] = memory([s for s in samples if moment(start['created_at_utc'])
                                  <= moment(s['timestamp_utc']) <= finish])
        calls.append(entry)
    assert sum(c['completed'] for c in calls) == result['completed_responses']
    evidence = dict(status='verified_exactly', apparatus_seal_sha256=sha256_file(FOLDER / 'SEAL.json'),
        source_bindings=len(seal['source_sha256']), artifacts=len(seal['files']), records=len(records),
        requests=len(starts), complete_responses=len(returned), no_model_or_checker_execution=True,
        verifier_sha256=sha256_file(Path(__file__)))
    measurements = dict(status=result['status'], server_pid=pid, calls=calls,
        baseline_sample=samples[0] if samples else None, overall_memory=memory(samples),
        nvidia_memory=result['memory'], observation_limit=study.read(FOLDER / 'FAILED.json')
            if (FOLDER / 'FAILED.json').exists() else None,
        shared_allocation_and_time_association_do_not_establish_spill_or_causation=True,
        incomplete_requests_are_not_complete_timing_measurements=True,
        no_behavioral_operation_or_generation_policy_comparison=True)
    for name, value in (('APPARATUS-VERIFICATION-001.json', evidence),
                        ('APPARATUS-METRICS-001.json', measurements)):
        path, raw = HERE / name, canonical_json_bytes(value)
        if path.exists():
            assert path.read_bytes() == raw, 'Preserve an earlier differing measurement'
        else:
            path.write_bytes(raw)
    return evidence


if __name__ == '__main__':
    print(json.dumps(verify_and_measure()), flush=True)
