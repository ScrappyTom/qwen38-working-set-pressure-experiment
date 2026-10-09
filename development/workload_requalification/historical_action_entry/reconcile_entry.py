"""Pin the constructed boundary against the original consumed evidence (CPU only)."""
from pathlib import Path
import bootstrap
from working_set_exp.event_frame_v2_qualification import _signal_fixture
from working_set_exp.event_frame_v2 import event_from_pair_v2
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent
OLD = ROOT / 'experiments/017_signal_bearing_event_frame_v2'


def put(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == raw, 'Existing reconciled material differs: ' + str(path)
    else:
        path.write_bytes(raw)


def reconcile():
    fixture, state, pairs, binding = _signal_fixture()
    request_path = OLD / 'development_run/cell-05/transcript/001-coding-request.json'
    request = load_json_strict(request_path.read_bytes())
    signal = request['active_phase_event_frame']['events'][0]
    assert event_from_pair_v2(pairs[0]['response'], pairs[0]['result'], sequence=1,
        event_handle='EVT-0001', result_handle='RES-0001', payload_residency='external') == signal
    assert sha256_bytes(canonical_json_bytes(pairs)) == binding['event_prefix_sha256'] == request['boundary_binding']['event_prefix_sha256']
    assert fixture.task == request['task'] and state.candidate.candidate_id == request['candidate_id']
    records_path = OLD / 'development_run/cell-05/records.jsonl'
    records = [load_json_strict(line) for line in records_path.read_bytes().splitlines()]
    entry = AREA / 'entry'
    source_paths = []
    for path, raw in state.candidate.files:
        row, = [row for row in records[0]['artifacts'] if row['path'].endswith('/' + path)]
        stored = OLD / 'development_run/cell-05' / row['path']
        assert stored.read_bytes() == raw
        assert len(raw) == row['size_bytes'] and sha256_file(stored) == row['sha256']
        source_paths.append(stored)
        put(entry / 'candidate' / path, raw)
    put(entry / 'action-result.json', canonical_json_bytes(pairs[0]))
    checker = fixture.phases['B'].checker
    assert checker == fixture.hidden_checker
    put(entry / 'public.py', checker)
    put(AREA / 'TASK.txt', fixture.task.encode())
    inputs = [OLD / 'execution_package/cell-05/initial-coding-request.json', request_path,
        ROOT / 'src/working_set_exp/event_frame_v2_qualification.py',
        ROOT / 'src/working_set_exp/event_frame_v2.py', records_path,
        OLD / 'development_run/cell-05/SUMMARY.json', *source_paths]
    for pattern in ('*-assistant-content.json', '*-assistant-reasoning.txt', '*-result.json'):
        inputs += sorted((OLD / 'development_run/cell-05/transcript').glob(pattern))
    proof = dict(status='exact_original_entry_reconciled', fixture=fixture.fixture_id,
        initial_candidate=state.candidate.candidate_id,
        pair_sha256=sha256_bytes(canonical_json_bytes(pairs[0])), binding=binding,
        event_signal=signal, checker_sha256=sha256_bytes(checker),
        task_sha256=sha256_bytes(fixture.task.encode()), old_visible_calls=request['resource_state']['phase_call_limit'],
        old_runner_completion_limit=6,
        files={p.relative_to(AREA).as_posix(): sha256_file(p) for p in sorted(entry.rglob('*'))
            if p.is_file() and p.name != 'RECONCILIATION.json'},
        original_sources={p.relative_to(ROOT).as_posix(): sha256_file(p) for p in inputs})
    put(entry / 'RECONCILIATION.json', canonical_json_bytes(proof))
    return proof


if __name__ == '__main__':
    value = reconcile()
    print(value['initial_candidate'], value['pair_sha256'], value['checker_sha256'])
