"""Read-only post-run audit; no inference, task execution or artifact repair."""
import importlib.util
import json
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import closure_task as entry
from working_set_exp.decision_view import receipt_view
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

task = entry.Task()
path = AREA.parents[1]/'dispatch_continuity/review/verify_dispatch.py'
spec = importlib.util.spec_from_file_location('closure_run_audit',path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
audit.study = task
output = Path(__file__).parent/'run-001'
output.mkdir(exist_ok=True)
audit.verify(task,output)
read = task.read
seal = read(task.RUN/'RESPONSE_SEAL.json')
for name,expected in seal['private_runtime_files_local_only'].items():
    assert sha256_file(task.RUN/'private-runtime'/name) == expected,name
calls = sorted((task.RUN/'calls').glob('*-wire-request.json'))
assert calls and len(calls) <= 2
assert calls[0].read_bytes() == (task.PACKAGE/'initial-wire-request.json').read_bytes()
first = json.loads(read(calls[0])['messages'][1]['content'])
receipts = [*first['preceding_operation_feedback'],first['workspace']['latest_feedback']]
assert [r['sequence'] for r in receipts] == [185,186,187]
for shown,operation in zip(receipts,read(entry.OLD/'calls/C80-host-result.json')['operations']):
    expected = receipt_view(dict(sequence=shown['sequence'],action_summary=shown['action_summary'],result=operation['result']))
    diff = expected['result'].pop('applied_diff',None)
    assert shown['result'] == expected['result']
    if shown.get('applied_change'):
        assert shown['applied_change']['sha256'] == sha256_bytes(diff.encode())
assert first['workspace']['verification']['submission']['eligible']
assert first['workspace']['working_account']['action_handle'] == 'EVT-0185'
versions = {}
for state_path in task.RUN.rglob('*-state.json'):
    if not state_path.relative_to(task.RUN).as_posix().startswith(('after/','starting','final','stopped')):
        continue
    for value in read(state_path)['source_versions']:
        candidate = task.candidate_from_snapshot(value)
        versions[candidate.candidate_id] = candidate
presentations = []
for path in calls:
    request = read(path)
    assert all(request[k] == -1 for k in ('max_tokens','n_predict','reasoning_budget_tokens','thinking_budget_tokens'))
    frame = json.loads(request['messages'][1]['content'])
    view = frame['workspace']
    candidate = versions[view['candidate_id']]
    for source in view['working_set']['sources']:
        raw = candidate.file_map[source['path']]
        assert source['file_sha256'] == sha256_bytes(raw)
        assert source['content'] == ''.join(raw.decode().splitlines(keepends=True)
            [source['returned_start_line']-1:source['returned_end_line']])
        presentations.append(dict(call=path.name.split('-')[0],path=source['path'],
            first=source['returned_start_line'],last=source['returned_end_line']))
last = read(task.RUN/'final-state.json')
assert last['pairs'][:187] == task.inherited_state['pairs']
final_bytes = (task.RUN/'final-candidate.json').read_bytes()
unchanged = final_bytes == (entry.OLD/'final-candidate.json').read_bytes()
new_pairs = last['pairs'][187:]
if last['submitted']:
    assert new_pairs[-1]['response']['action'] == 'submit' and new_pairs[-1]['result']['accepted']
    assert new_pairs[-1]['response']['expected_candidate_id'] == last['candidate_id']
if unchanged:
    assert last['candidate_id'] == task.inherited_candidate.candidate_id
result = dict(status='verified',initial_wire_identical_to_qualified=True,
    pending_receipts_first_presented=[185,186,187],pass_present_in_first_input=True,
    natural_account_preserved_at_entry=True,candidate_unchanged=unchanged,
    prior_history_preserved=True,submitted=last['submitted'],presentations=presentations,
    private_runtime_hashes_verified=len(seal['private_runtime_files_local_only']),
    new_actions=[p['response']['action'] for p in new_pairs])
task.save(output,'SOURCE_PRESENTATIONS.json',result)
v = read(output/'VERIFICATION.json')
prior = read(entry.previous.AREA/'review/run-001/CUMULATIVE_COST.json')
cost = dict(prior_interpolation_dispatched=prior['total_interpolation_dispatched'],
    prior_complete_responses=prior['total_interpolation_complete_responses'],
    new_dispatched=v['sent_requests'],new_complete_responses=len(v['endpoints']),
    total_interpolation_dispatched=prior['total_interpolation_dispatched']+v['sent_requests'],
    total_interpolation_complete_responses=prior['total_interpolation_complete_responses']+len(v['endpoints']),
    inherited_earlier_work_operations=55,prior_interpolation_operations=132,
    new_operations=v['actual_operations'],cumulative_operations=seal['cumulative_operations'],
    total_interpolation_operations=132+v['actual_operations'],
    known_model_request_seconds=prior['known_model_request_seconds']+v['total_model_request_seconds'],
    known_input_tokens=prior['known_input_tokens']+v['total_input_tokens'],
    known_generated_tokens=prior['known_generated_tokens']+v['total_output_tokens'],
    excluded_unknown_cost=prior['excluded_unknown_cost'],development_cost=prior['development_cost'],
    earlier_work_model_calls=prior['earlier_work_model_calls'])
task.save(output,'CUMULATIVE_COST.json',cost)
print(json.dumps({k:v for k,v in result.items() if k!='presentations'},indent=2),flush=True)
print('Verified exact source presentations:',len(presentations),flush=True)
