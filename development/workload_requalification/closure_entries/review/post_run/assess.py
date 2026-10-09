"""Assess sealed closure work; keep constructed setup and actor work distinct."""
import argparse
from collections import Counter
import difflib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

AREA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AREA))
import closure_task as study
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


def save(path, value):
    raw = canonical_json_bytes(value)
    if path.exists():
        assert path.read_bytes() == raw, 'Preserve differing assessments separately'
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)


def main(case, version):
    task = study.Task(case, version)
    run = task.RUN
    verification = task.read(AREA / f'review/VERIFICATION-{case}-{version}.json')
    assert verification['status'] == 'replayed_exactly'
    assert verification['response_seal_sha256'] == sha256_file(run/'RESPONSE_SEAL.json')
    assert verification['records_sha256'] == sha256_file(run/'records.jsonl')
    source = study.ROOT/'development/workload_requalification/url_port_continuation/review/measure_run.py'
    spec = importlib.util.spec_from_file_location('closure_cost_reader', source)
    metric = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(metric)
    metric.checked_seal(run)
    records = metric.records(run)
    calls = metric.calls(run, records)
    operations = [(r['payload']['id'], task.read(run/r['artifacts'][0]['path'])) for r in records
        if r['record_type'] == 'contribution_operation']
    common = dict(case=case, version=version, response_seal_sha256=sha256_file(run/'RESPONSE_SEAL.json'),
        assessment_source_sha256=sha256_file(Path(__file__)), inherited_setup_operations=5)
    folder = AREA/'review'/f'{case}-{version}'
    save(folder/'METRICS.json', dict(**common, aggregate=metric.aggregate(calls), calls=calls,
        new_operations=len(operations), operation_types=dict(Counter(op['action']['action'] for _,op in operations)),
        rejected_operations=[dict(id=tag, operation=op) for tag,op in operations if not op['result']['accepted']],
        task_loop=[r['payload'] for r in records if r['record_type']=='task_loop_completed'],
        limits=['Five constructed setup operations are not new model actions.',
                'Inference cost excludes preparation, independent grading and reviewer work.']))

    stem = 'final' if (run/'final-state.json').exists() else 'stopped'
    state = task.read(run/(stem+'-state.json'))
    candidate = task.candidate_from_snapshot(task.read(run/(stem+'-candidate.json')))
    assert state['pairs'][:5] == task.inherited_pairs()
    before, after = task.starting_files(), candidate.file_map
    changed = [p for p in before if before[p] != after[p]]
    assert set(before) == set(after)
    diff = ''.join(''.join(difflib.unified_diff(before[p].decode().splitlines(True),after[p].decode().splitlines(True),
        fromfile='constructed_entry/'+p,tofile='saved/'+p)) for p in changed)
    folder.mkdir(parents=True, exist_ok=True)
    diff_path=folder/'SAVED-PATCH.diff'
    if diff_path.exists():
        assert diff_path.read_bytes()==diff.encode()
    else:
        diff_path.write_bytes(diff.encode())

    if case=='E14-CLOSURE-MINT':
        independent="""import json
from codec.label import codec_label
from codec.wire import encode_wire
values=['',' a ',' MiX ',' B7 ',' 0 ','\\tblue\\n']
rows=[dict(value=v,label=codec_label(v),wire_hex=encode_wire(v).hex()) for v in values]
for row in rows:
    expected='M8::'+row['value'].strip().upper()
    assert row['label']==expected
    assert bytes.fromhex(row['wire_hex'])==expected.encode('ascii')
print(json.dumps(rows,ensure_ascii=False))
"""
    else:
        independent="""import json
from api.name import normalize_name
from invariants.stable import invariant_ok
values=['',' a ',' MiX ',' Straße ',' Åß ','\\tNAME\\n']
rows=[dict(value=v,name=normalize_name(v)) for v in values]
assert invariant_ok()
for row in rows: assert row['name']=='sable-'+row['value'].strip().casefold()
print(json.dumps(rows,ensure_ascii=False))
"""
    checks=[]
    with tempfile.TemporaryDirectory(prefix='closure-artifact-review-') as temp:
        root=Path(temp)
        for name,raw in after.items():
            path=root/name
            assert path.resolve().is_relative_to(root.resolve())
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(raw)
        for label,program in [('original_public',task.public_checker()),('original_hidden',task.hidden_checker()),
                              ('independent_examples',independent.encode())]:
            name='_'+label+'.py'; (root/name).write_bytes(program)
            result=subprocess.run([sys.executable,'-B','-X','utf8',name],cwd=root,capture_output=True,timeout=30)
            checks.append(dict(label=label,returncode=result.returncode,stdout=result.stdout.decode(),stderr=result.stderr.decode()))

    decisions=[]
    consumed=False
    for call in calls:
        tag=call['id']; wire=task.read(run/f'calls/{tag}-wire-request.json')
        envelope=json.loads(wire['messages'][-1]['content']); view=envelope['workspace']
        own=[op for selected,op in operations if selected==tag]
        assert view['task']==task.task_text() and view['active_user_authored_step']==task.exact('ACTIVE_STEP.txt').decode()
        accepted_submit=any(op['action']['action']=='submit' and op['result']['accepted'] for op in own)
        if accepted_submit:
            current=view['verification']['checks']['public']
            consumed=bool(current and current['passed'] and current['applies_to_current'] and
                current['candidate_matches'] and current['check_definition_matches'])
        decisions.append(dict(id=tag,candidate_id=view['candidate_id'],verification=view['verification'],
            account=view['working_account'],recent_activity=view['recent_activity'],
            imported_observations=view['imported_observations'],
            source_extents=[{k:v for k,v in s.items() if k!='content'} for s in view['working_set']['sources']],
            actions=[op['action'] for op in own],accepted_submit=accepted_submit))
    save(folder/'ASSESSMENT.json',dict(**common,candidate_id=candidate.candidate_id,changed_files=changed,
        unchanged_files=len(before)-len(changed),checks=checks,ordinary_behavior_passed=all(r['returncode']==0 for r in checks),
        submitted=state['submitted'],consumed_current_public_pass=consumed,decisions=decisions,
        environment=dict(interpreter=sys.executable,flags=['-B','-X','utf8'],cwd='fresh saved-candidate root'),
        limits=['Constructed work begins already repaired; closure is not new discovery of that repair.',
            'SABLE public checks only its stable invariant; hidden/examples separately assess names.',
            'Repeated grading is artifact qualification, not additional model success.',
            'Exact replay, complete response review and entry provenance remain separate requirements.']))
    print(json.dumps(dict(case=case,metrics=metric.aggregate(calls),changed_files=changed,submitted=state['submitted'],
        consumed_current_public_pass=consumed,checks=checks),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',required=True,choices=tuple(study.CASES))
    parser.add_argument('--version',default='001')
    args=parser.parse_args()
    main(args.case,args.version)
