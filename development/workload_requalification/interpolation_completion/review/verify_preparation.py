"""Read-only preparation audit; no runtime, checking or inference."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import completion_task as entry
import qualified_task
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file
import run_dispatch as execution

task=qualified_task.Task()
folder=task.PACKAGE
seal=entry.read(folder/'SEAL.json')
assert seal['status']=='qualified_no_model_inference'
for row in seal['files']:
    raw=(folder/row['path']).read_bytes()
    assert len(raw)==row['size_bytes'] and sha256_bytes(raw)==row['sha256'],row['path']
task.verify_sources(seal['source_sha256'])
records=verify_records(folder/'records.jsonl',folder)
assert not any(r['record_type']=='invocation_started' for r in records)
qualification=entry.read(folder/'QUALIFICATION.json')
assert qualification['completion_requests']==0 and qualification['port_free']
forms=qualification['native_forms']
assert forms['status']=='passed' and all(r['accepted_including_eos']==r['expected'] for r in forms['cases'])
wire=entry.read(folder/'initial-wire-request.json')
assert wire['chat_template_kwargs']==dict(enable_thinking=True,reasoning_effort='medium')
assert all(wire[k]==-1 for k in ('max_tokens','n_predict','reasoning_budget_tokens','thinking_budget_tokens'))
assert wire['cache_prompt'] is False
frame=json.loads(wire['messages'][1]['content'])
assert frame['workspace']['working_set']==dict(saved_results=[],sources=[])
assert frame['workspace']['allowance']['requests_remaining']==32
assert frame['workspace']['allowance']['actions_remaining']==96
assert frame['workspace']['working_account']['action_handle']=='EVT-0097'
assert frame['workspace']['current_job']['submission']=='open'
assert not frame['workspace']['verification']['submission']['eligible']
assert entry.canonical_json_bytes(frame['workspace'])==canonical_json_bytes(task.initial_session().view())
assert task.expected_native(wire)==(folder/'admission/I0001-native.txt').read_bytes()
assert qualification['initial']['wire_request_sha256']==sha256_file(folder/'initial-wire-request.json')
versions={task.inherited_candidate.candidate_id:task.inherited_candidate}
source_bodies=0
for path in sorted((folder/'route').glob('*-state.json')):
    state=entry.read(path)
    for value in state['source_versions']:
        candidate=entry.candidate_from_snapshot(value);versions[candidate.candidate_id]=candidate
    restored=task.restore(state,versions[state['candidate_id']],folder/'scripted',replay=True)
    assert canonical_json_bytes(entry.snapshot(restored))==path.read_bytes()
for path in sorted((folder/'route').glob('*-input.json')):
    view=entry.read(path); candidate=versions[view['candidate_id']]
    for source in view['working_set']['sources']:
        raw=candidate.file_map[source['path']]
        assert source['file_sha256']==sha256_bytes(raw)
        expected=''.join(raw.decode().splitlines(keepends=True)[source['returned_start_line']-1:source['returned_end_line']])
        assert source['content']==expected
        source_bodies+=1
    decision=entry.read(path.with_name(path.name.replace('-input','-reply')))
    if decision['operation']['action']=='patch' and decision['operation']['path']==entry.DOC:
        assert any(s['path']==entry.TEST and 'MissingInterpolationTransportTests' in s['content'] for s in view['working_set']['sources'])
last_state=entry.read(sorted((folder/'route').glob('*-state.json'))[-1])
assert last_state['submitted']
final=versions[last_state['candidate_id']]
assert all(final.file_map[p]==raw for p,raw in task.inherited_candidate.file_map.items() if p not in (entry.TEST,entry.DOC))
actual_checks=[p['result'] for p in last_state['pairs'][task.INHERITED_OPERATIONS:] if p['response']['action']=='check']
assert [p['passed'] for p in actual_checks]==[False,False,True,True]
execution.runner.verify_package(task)
value=dict(status='verified_no_inference',sealed_files=len(seal['files']),source_bindings=len(seal['source_sha256']),
    custody_records=len(records),native_forms=len(forms['cases']),route_decisions=qualification['route']['decisions'],
    current_source_bodies_verified=source_bodies,initial_tokens=qualification['initial']['prompt_tokens'],
    peak_route_tokens=max(r['following_tokens'] for r in qualification['route']['trace']),
    actual_check_outcomes=[p['passed'] for p in actual_checks],preserved_non_target_files=8,
    prior_dispatches_charged=32,prior_operations_preserved=101,prior_unknown_response='original C22',
    runtime_closed=qualification['port_free'],memory=qualification['memory'],completion_requests=0)
entry.save(Path(__file__).parent,'PREPARATION_VERIFICATION-002.json',value)
print(json.dumps(value),flush=True)
