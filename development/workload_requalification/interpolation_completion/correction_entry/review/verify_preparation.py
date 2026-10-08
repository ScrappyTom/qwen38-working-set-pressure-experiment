"""Post-seal custody, full entry and information-path audit; no inference."""
import json
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import correction_task as entry
import run_correction as run
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

run.configure()
task = entry.Task()
folder = task.PACKAGE
read = entry.original.read
seal = read(folder/'SEAL.json')
assert seal['status'] == 'qualified_no_model_inference' and seal['completion_requests'] == 0
assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
for row in seal['files']:
    raw = (folder/row['path']).read_bytes()
    assert len(raw) == row['size_bytes'] and sha256_bytes(raw) == row['sha256'], row['path']
task.verify_sources(seal['source_sha256'])
assert task.source_identities() == seal['source_sha256']
records = verify_records(folder/'records.jsonl', folder)
assert not any(r['record_type'] == 'invocation_started' for r in records)
q = read(folder/'QUALIFICATION.json')
assert q['completion_requests'] == 0 and q['port_free']
assert q['native_forms']['status'] == 'passed'
assert all(r['accepted_including_eos'] == r['expected'] for r in q['native_forms']['cases'])
wire = read(folder/'initial-wire-request.json')
assert wire['seed'] == entry.SEED and wire['chat_template_kwargs'] == dict(enable_thinking=True, reasoning_effort='medium')
assert all(wire[k] == -1 for k in ('max_tokens', 'n_predict', 'reasoning_budget_tokens', 'thinking_budget_tokens'))
frame = json.loads(wire['messages'][1]['content'])
view = frame['workspace']
assert view['allowance']['requests_remaining'] == 16 and view['allowance']['actions_remaining'] == 48
assert view['current_job']['starting_archive_operations'] == 152
assert view['working_account']['action_handle'] == 'EVT-0151'
assert 'UnboundLocalError' in str(view['verification'])
assert not view['verification']['submission']['eligible']
source, = view['working_set']['sources']
assert (source['returned_start_line'], source['returned_end_line']) == (2200, 2360)
assert source['content'] == task.inherited_state['last']['result']['source']['content']
assert frame['preceding_operation_feedback'][0]['sequence'] == 151
assert view == task.initial_session().view()
assert q['initial']['wire_request_sha256'] == sha256_file(folder/'initial-wire-request.json')
assert task.expected_native(wire) == (folder/'admission/I0001-native.txt').read_bytes()
versions, source_count, checkpoints = {}, 0, 0
for path in sorted((folder/'route').glob('*-state.json')):
    state = read(path)
    for value in state['source_versions']:
        candidate = task.candidate_from_snapshot(value); versions[candidate.candidate_id] = candidate
    restored = task.restore(state, versions[state['candidate_id']], folder/'scripted', replay=True)
    assert canonical_json_bytes(task.snapshot(restored)) == path.read_bytes()
    checkpoints += 1
for path in sorted((folder/'route').glob('*-input.json')):
    view = read(path)
    candidate = versions[view['candidate_id']]
    for source in view['working_set']['sources']:
        raw = candidate.file_map[source['path']]
        assert source['file_sha256'] == sha256_bytes(raw)
        assert source['content'] == ''.join(raw.decode().splitlines(keepends=True)
            [source['returned_start_line']-1:source['returned_end_line']])
        source_count += 1
    decision = read(path.with_name(path.name.replace('-input', '-reply')))['operation']
    if decision['action'] == 'patch' and decision['path'] == entry.DOC:
        assert any(s['path'] == entry.TEST and 'expected_message' in s['content'] for s in view['working_set']['sources'])
last = read(sorted((folder/'route').glob('*-state.json'))[-1])
assert last['submitted']
checks = [p['result'] for p in last['pairs'][152:] if p['response']['action'] == 'check']
assert [r['passed'] for r in checks] == [False, True, True]
final = versions[last['candidate_id']]
assert all(final.file_map[p] == raw for p, raw in task.inherited_candidate.file_map.items() if p not in (entry.TEST, entry.DOC))
run.execution.runner.verify_package(task)
result = dict(status='verified_no_inference', artifacts=len(seal['files']), source_bindings=len(seal['source_sha256']),
    custody_records=len(records), native_forms=len(q['native_forms']['cases']), checkpoints=checkpoints,
    exact_source_presentations=source_count, initial_tokens=q['initial']['prompt_tokens'],
    peak_route_tokens=max(max(r['input_tokens'], r['following_tokens']) for r in q['route']['trace']),
    check_outcomes=[r['passed'] for r in checks], preserved_non_target_files=8, inherited_operations=152,
    inherited_dispatches=64, final_c64_first_delivery_qualified=True, completion_requests=0,
    runtime_closed=q['port_free'], memory=q['memory'])
entry.original.save(Path(__file__).parent, 'PREPARATION_AUDIT.json', result)
print(json.dumps(result, indent=2), flush=True)
