"""Post-seal exact replay and separately recorded saved-artifact checks."""
import ast
import difflib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contract_task as entry
sys.path.insert(0, str(entry.study.AREA / 'review'))
from verify_dispatch import verify
from working_set_exp.jsonutil import load_json_strict, sha256_bytes, sha256_file

task = entry.Task('001')
output = Path(__file__).parent / 'run-001'
assert not output.exists(), 'Preserve the first audit.'
verify(task, output)
seal = entry.read(task.RUN / 'RESPONSE_SEAL.json')
stem = 'stopped' if seal['disposition'] == 'stopped_without_retry' else 'final'
candidate = entry.study.candidate_from_snapshot(entry.read(task.RUN / f'{stem}-candidate.json'))
state = entry.read(task.RUN / f'{stem}-state.json')
session = task.restore(state, candidate, task.RUN, replay=True)
assert state['pairs'][:77] == task.inherited_state['pairs']
protected = {p:candidate.file_map[p] == raw for p,raw in task.inherited_candidate.file_map.items() if p != entry.TEST}
assert len(protected) == 7 and all(protected.values())
def methods(source):
    return {(c.name,n.name):ast.dump(n) for c in ast.parse(source).body if isinstance(c,ast.ClassDef)
            for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test')}
baseline = entry.parent.Task('control','003').inherited_candidate.file_map[entry.TEST].decode()
old = methods(baseline)
current = candidate.file_map[entry.TEST].decode()
new = methods(current)
preserved = {'.'.join(key):new.get(key) == value for key,value in old.items()}
assert len(preserved) == 2 and all(preserved.values())
store = entry.ObservationStore(output / 'postseal-check', timeout=60)
observation = store.execute(candidate, entry.checker(task.inherited_candidate), 'public', 'CHK-0001')
rows = [load_json_strict(line) for line in (store.directory('CHK-0001') / 'stdout.bin').read_bytes().splitlines()]
private = {}
for name,digest in seal.get('private_runtime_files_local_only', {}).items():
    path = task.RUN / 'private-runtime' / name
    private[name] = sha256_file(path) == digest
assert all(private.values())
opportunities = entry.read(task.RUN / 'check-opportunities.json') if (task.RUN / 'check-opportunities.json').exists() else None
summary = dict(disposition=seal['disposition'],candidate_id=candidate.candidate_id,
    protected_files_exact=protected,original_methods_preserved=preserved,
    inherited_history_exact=True,new_method_names=['.'.join(key) for key in new if key not in old],
    changed_files=[p for p,raw in candidate.file_map.items() if task.inherited_candidate.file_map[p] != raw],
    file_sha256={p:sha256_bytes(raw) for p,raw in candidate.file_map.items()},
    postseal_public_pass=observation['passed'],postseal_capture_complete=observation['capture_complete'],
    checker_records=rows,private_runtime_hashes_match=private,
    final_account=session.working_account(),final_verification=session.view()['verification'],
    repeated_checker_is_not_new_coverage=True,assistance='review-directed assignment; no live coaching')
entry.study.save(output,'ARTIFACT_AUDIT.json',summary)
entry.study.save(output,'saved-test_virtual_registration.py',candidate.file_map[entry.TEST])
delta=''.join(difflib.unified_diff(task.inherited_candidate.file_map[entry.TEST].decode().splitlines(keepends=True),
    current.splitlines(keepends=True),fromfile='saved-control-tests',tofile='contract-completed-tests'))
entry.study.save(output,'APPLIED_TEST_CHANGE.diff',delta.encode())
print(json.dumps({k:summary[k] for k in ('disposition','candidate_id','changed_files','postseal_public_pass')}))
