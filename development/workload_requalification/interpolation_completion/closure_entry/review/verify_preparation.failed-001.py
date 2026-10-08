"""Independent custody and information-path audit of the finite closure entry."""
import json
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import closure_task as entry
import run_closure as run
from working_set_exp.custody import verify_records
from working_set_exp.decision_view import receipt_view
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

run.configure()
task = entry.Task()
folder, read = task.PACKAGE, task.read
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
assert q['native_forms']['status'] == 'reused_exact_decoder_contract'
assert q['native_forms']['previously_executed_cases'] == 44
assert q['native_forms']['new_decoder_cases'] == 0
old_task = entry.previous.Task()
for name, key in [('SEAL.json','preparation_seal_sha256'),
                  ('QUALIFICATION.json','source_qualification_sha256'),
                  ('initial-wire-request.json','source_wire_sha256')]:
    assert sha256_file(old_task.PACKAGE/name) == q['native_forms'][key]
wire = read(folder/'initial-wire-request.json')
old_wire = read(old_task.PACKAGE/'initial-wire-request.json')
assert wire['messages'][0] == old_wire['messages'][0]
assert {k:v for k,v in wire.items() if k!='messages'} == {k:v for k,v in old_wire.items() if k!='messages'}
assert wire['seed'] == entry.SEED
assert wire['chat_template_kwargs'] == dict(enable_thinking=True, reasoning_effort='medium')
assert all(wire[k] == -1 for k in ('max_tokens','n_predict','reasoning_budget_tokens','thinking_budget_tokens'))
frame = json.loads(wire['messages'][1]['content'])
view = frame['workspace']
assert view['allowance']['requests_remaining'] == 2 and view['allowance']['actions_remaining'] == 4
assert view['current_job']['starting_archive_operations'] == 187
assert view == task.initial_session().view()
assert view['working_account']['action_handle'] == 'EVT-0185'
old_session = old_task.restore(task.inherited_state, task.inherited_candidate, entry.OLD, replay=True)
assert view['working_account']['text'] == old_session.view()['working_account']['text']
assert view['verification']['submission']['eligible']
public = view['verification']['checks']['public']
assert public['applies_to_current'] and public['passed'] and public['handle'] == 'RES-0187'
receipts = [*frame['preceding_operation_feedback'], view['latest_feedback']]
assert [r['sequence'] for r in receipts] == [185,186,187]
operations = read(entry.OLD/'calls/C80-host-result.json')['operations']
for shown, operation in zip(receipts, operations):
    expected = receipt_view(dict(sequence=shown['sequence'],action_summary=shown['action_summary'],result=operation['result']))
    diff = expected['result'].pop('applied_diff', None)
    assert shown['result'] == expected['result']
    if shown.get('applied_change'):
        detail = shown['applied_change']
        assert detail['sha256'] == sha256_bytes(diff.encode())
        if detail['detail_status'] == 'complete_applied_diff':
            assert detail['diff_utf8'] == diff
assert q['initial']['wire_request_sha256'] == sha256_file(folder/'initial-wire-request.json')
assert task.expected_native(wire) == (folder/'admission/I0001-native.txt').read_bytes()
starting = read(folder/'starting-state.json')
before = {**task.inherited_state,'diffs':{int(k):v for k,v in task.inherited_state['diffs'].items()}}
changed = [k for k in before if canonical_json_bytes(before[k]) != canonical_json_bytes(starting[k])]
assert set(changed) == {'request_limit','call_limit','starting_archive_length'}
assert (folder/'starting-candidate.json').read_bytes() == (entry.OLD/'final-candidate.json').read_bytes()
state = read(folder/'route/01-state.json')
assert state['submitted'] and len(state['pairs']) == 188 and state['requests_used'] == 81
assert state['pairs'][:187] == task.inherited_state['pairs']
assert state['pairs'][-1]['response']['action'] == 'submit' and state['pairs'][-1]['result']['accepted']
assert not any(p['response']['action'] == 'check' for p in state['pairs'][187:])
assert (folder/'route/01-candidate.json').read_bytes() == (entry.OLD/'final-candidate.json').read_bytes()
restored = task.restore(state, task.inherited_candidate, folder/'scripted', replay=True)
assert canonical_json_bytes(task.snapshot(restored)) == (folder/'route/01-state.json').read_bytes()
sources = []
for label, shown_view in [('initial',view),('route-input',read(folder/'route/01-input.json')),
                          ('route-following',read(folder/'route/01-following.json'))]:
    for source in shown_view['working_set']['sources']:
        raw = task.inherited_candidate.file_map[source['path']]
        assert source['file_sha256'] == sha256_bytes(raw)
        assert source['content'] == ''.join(raw.decode().splitlines(keepends=True)
            [source['returned_start_line']-1:source['returned_end_line']])
        sources.append(dict(view=label,path=source['path'],first=source['returned_start_line'],last=source['returned_end_line']))
run.execution.runner.verify_package(task)
result = dict(status='verified_no_inference',artifacts=len(seal['files']),source_bindings=len(seal['source_sha256']),
    custody_records=len(records),new_decoder_cases=0,reused_native_cases=44,checkpoints=1,
    exact_source_presentations=len(sources),sources=sources,initial_tokens=q['initial']['prompt_tokens'],
    following_tokens=q['route']['following_tokens'],scripted_new_checks=0,scripted_operations=1,
    candidate_unchanged=True,inherited_dispatches=80,inherited_operations=187,
    pending_receipts_first_delivery=[185,186,187],snapshot_changed_fields=sorted(changed),
    completion_requests=0,runtime_closed=q['port_free'],memory=q['memory'])
task.save(Path(__file__).parent,'PREPARATION_AUDIT.json',result)
print(json.dumps(result,indent=2),flush=True)
