"""CPU reconstruction matched to the consumed E15/E17 closure boundaries."""
import json
from pathlib import Path
import sys
import traceback

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
sys.path.insert(0, str(ROOT/'src'))
from working_set_exp.event_frame_placement import constructed_world
from working_set_exp.event_frame_v2 import event_from_pair_v2
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.phase_receipts import _successor
from working_set_exp.request import observation_directory_v2
from working_set_exp.unified_receipts import case_definitions

BANK = ROOT/'experiments/014_unified_active_phase_receipts/fresh_bank'
OLD = ROOT/'experiments/017_signal_bearing_event_frame_v2'
EARLIER = ROOT/'experiments/015_event_frame_placement_qualification'
CASES = {'E14-CLOSURE-MINT':'cell-01','E14-STALE-SABLE':'cell-03'}


def put(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes()==raw, 'Existing reconciliation differs: '+str(path)
    else:
        path.write_bytes(raw)


def read(path):
    return load_json_strict(path.read_bytes())


def reconcile(case_id, cell):
    fixture, state, pairs, receipts, observations, bodies, results, binding = constructed_world(BANK,case_id)
    folder = AREA/'entries'/case_id
    original_request = OLD/'development_run'/cell/'transcript/001-coding-request.json'
    request = read(original_request)
    assert len(pairs)==5
    assert binding==request['boundary_binding']
    assert sha256_bytes(canonical_json_bytes(pairs))==binding['event_prefix_sha256']
    assert fixture.task==request['task'] and state.candidate.candidate_id==request['candidate_id']
    assert observation_directory_v2(observations)==request['observation_directory']
    for i,pair in enumerate(pairs,1):
        assert event_from_pair_v2(pair['response'],pair['result'],sequence=i,
            event_handle=f'EVT-{i:04}',result_handle=f'RES-{i:04}',payload_residency='external')==request['active_phase_event_frame']['events'][i-1]
    comparable = ['task','active_user_authored_step','candidate_id','boundary_binding','observation_directory','completed_phase_ids']
    inputs = [original_request, OLD/'execution_package'/cell/'initial-coding-request.json']
    for condition in ['D15-UNIFIED-DUP','D15-EVENT-FRAME']:
        path=EARLIER/'development_run'/cell/condition/'transcript/001-coding-request.json'
        earlier=read(path)
        assert all(earlier[key]==request[key] for key in comparable)
        inputs.append(path)
    records_path=OLD/'development_run'/cell/'records.jsonl'
    records=[load_json_strict(line) for line in records_path.read_bytes().splitlines()]
    inputs.append(records_path)
    for name,raw in state.candidate.files:
        match,=[row for row in records[0]['artifacts'] if row['path'].endswith('/'+name)]
        stored=OLD/'development_run'/cell/match['path']
        assert stored.read_bytes()==raw and len(raw)==match['size_bytes'] and sha256_file(stored)==match['sha256']
        inputs.append(stored)
        put(folder/'candidate'/name,raw)
    definition,=[row for row in case_definitions() if row['fixture_id']==case_id]
    predecessor=_successor(definition,1)
    snapshot=lambda value:dict(candidate_id=value.candidate_id,max_file_bytes=value.max_file_bytes,
        files=[dict(path=name,content_utf8=raw.decode()) for name,raw in value.files])
    put(folder/'predecessor.json',canonical_json_bytes(snapshot(predecessor)))
    put(folder/'candidate.json',canonical_json_bytes(snapshot(state.candidate)))
    put(folder/'pairs.json',canonical_json_bytes(pairs))
    put(folder/'observations.json',canonical_json_bytes(observations))
    for handle,raw in bodies.items():put(folder/'observations'/f'{handle}.json',raw)
    put(folder/'TASK.txt',fixture.task.encode())
    put(folder/'ACTIVE_STEP.txt',fixture.phases['B'].text.encode())
    put(folder/'public.py',fixture.phases['B'].checker)
    put(folder/'hidden.py',fixture.hidden_checker)
    for name in ['src/working_set_exp/event_frame_placement.py','src/working_set_exp/event_frame_v2.py',
                 'src/working_set_exp/unified_receipts.py','src/working_set_exp/phase_receipts.py']:
        inputs.append(ROOT/name)
    proof=dict(status='exact_consumed_boundary_reconciled',case_id=case_id,source_cell=cell,
        candidate_id=state.candidate.candidate_id,predecessor_id=predecessor.candidate_id,
        setup_operations=5,binding=binding,observation_count=len(observations),
        task_sha256=sha256_bytes(fixture.task.encode()),public_sha256=sha256_bytes(fixture.phases['B'].checker),
        hidden_sha256=sha256_bytes(fixture.hidden_checker),
        files={p.relative_to(folder).as_posix():sha256_file(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and p.name!='RECONCILIATION.json'},
        original_sources={p.relative_to(ROOT).as_posix():sha256_file(p) for p in inputs},
        compared_across=['E15 duplicated receipts','E15 event frame','E17 event frame v2'],
        provenance='Original constructed setup, not model work. CPU construction may execute its original checker; exact pair/event hashes must match consumed records. No historical outcome is rewritten.',
        no_model_or_native_execution=True,reconciliation_source_sha256=sha256_file(Path(__file__)))
    put(folder/'RECONCILIATION.json',canonical_json_bytes(proof))
    return dict(case_id=case_id,candidate_id=state.candidate.candidate_id,
        files=len(state.candidate.files),bytes=sum(len(raw) for _,raw in state.candidate.files),
        setup_operations=5,observations=len(observations),status=proof['status'])


if __name__=='__main__':
    try:
        result=[reconcile(case,cell) for case,cell in CASES.items()]
    except BaseException as error:
        put(AREA/'RECONCILIATION-FAILED-001.json',canonical_json_bytes(dict(
            error=type(error).__name__,message=str(error),traceback=traceback.format_exc(),
            script_sha256=sha256_file(Path(__file__)))))
        raise
    print(json.dumps(result,indent=2))
