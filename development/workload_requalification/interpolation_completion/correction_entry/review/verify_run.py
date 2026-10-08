"""Independent post-closure audit; read-only against the sealed live attempt."""
import importlib.util
import json
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import correction_task as entry
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

task = entry.Task()
path = AREA.parents[1]/'dispatch_continuity/review/verify_dispatch.py'
spec = importlib.util.spec_from_file_location('correction_run_audit', path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
audit.study = task
output = Path(__file__).parent/'run-001'
output.mkdir(exist_ok=True)
audit.verify(task, output)

read = entry.original.read
seal = read(task.RUN/'RESPONSE_SEAL.json')
for name, expected in seal['private_runtime_files_local_only'].items():
    assert sha256_file(task.RUN/'private-runtime'/name) == expected, name
calls = sorted((task.RUN/'calls').glob('*-wire-request.json'))
assert calls
assert calls[0].read_bytes() == (task.PACKAGE/'initial-wire-request.json').read_bytes()
first = json.loads(read(calls[0])['messages'][1]['content'])
pending = task.initial_preceding_feedback()
# The saved pending receipt also contains host-only rendering options. Those
# control presentation, and are correctly absent from the actual model receipt.
assert len(pending) == 1
assert set(pending[0]) == {'sequence', 'action_summary', 'result',
                          'immediate_change_detail_mode', 'navigation_projection_pages'}
assert first['preceding_operation_feedback'] == [
    {k:row[k] for k in ('sequence', 'action_summary', 'result')} for row in pending]
source, = first['workspace']['working_set']['sources']
assert source['content'] == task.inherited_state['last']['result']['source']['content']
assert source['returned_start_line'] == 2200 and source['returned_end_line'] == 2360
assert not task.inherited_state['delivered_sources']

versions = {}
for state_path in task.RUN.rglob('*-state.json'):
    if not state_path.relative_to(task.RUN).as_posix().startswith(('after/', 'starting', 'final', 'stopped')):
        continue
    for value in read(state_path)['source_versions']:
        candidate = entry.original.candidate_from_snapshot(value)
        versions[candidate.candidate_id] = candidate
presentations = []
for path in calls:
    frame = json.loads(read(path)['messages'][1]['content'])
    view = frame['workspace']
    candidate = versions[view['candidate_id']]
    for source in view['working_set']['sources']:
        raw = candidate.file_map[source['path']]
        assert source['file_sha256'] == sha256_bytes(raw)
        assert source['content'] == ''.join(raw.decode().splitlines(keepends=True)
            [source['returned_start_line']-1:source['returned_end_line']])
        presentations.append(dict(call=path.name.split('-')[0], path=source['path'],
            first=source['returned_start_line'], last=source['returned_end_line']))
result = dict(status='verified', presentations=presentations,
    final_c64_first_delivery_verified=True,
    inherited_pending_receipt_verified=True,
    private_runtime_hashes_verified=len(seal['private_runtime_files_local_only']))
(output/'SOURCE_PRESENTATIONS.json').write_bytes(canonical_json_bytes(result))
print(json.dumps({k:v for k,v in result.items() if k != 'presentations'}))
print('Verified current-source presentations:', len(presentations))
