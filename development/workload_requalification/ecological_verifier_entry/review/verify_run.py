"""Compose existing exact replay, imported-record and delivery-witness audits."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ecological_task as study
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file
from working_set_exp.custody import verify_records

base = study.load_private('verifier_observation_audit', study.ROOT /
    'development/workload_requalification/ecological_observation_entry/review/verify_run.py')
base.study = study
delivery = study.load_private('verifier_delivery_audit', study.ROOT /
    'development/workload_requalification/ecological_import_entry/review/verify_run.py')
delivery.study = study

def preparation(module,seal,inventory):
    manifest=study.read(module.RUN/'EXECUTION_MANIFEST.json')
    assert manifest['source_sha256']==seal['source_sha256']==module.source_identities()
    module.verify_sources(manifest['source_sha256'])
    assert manifest['actor']==seal['actor']==module.ACTOR and manifest['seed']==module.SEED
    assert (manifest['maximum_requests'],manifest['maximum_operations'])==(32,96)
    assert manifest['starting_candidate_id']==study.STARTING_ID and manifest['starting_archive_operations']==0
    assert manifest['original_entry'] and manifest['selection_assistance']=='none; fresh empty selected group'
    assert manifest['literal_source_reply'] and manifest['no_live_coaching'] and not manifest['automatic_retry']
    assert manifest['automatic_edit_checks']=={}
    assert manifest['checker_contracts']=={'public':{'checker_sha256':study.PUBLIC_SHA}}
    assert manifest['hidden_evaluation']=='after_response_seal_only'
    assert manifest['imported_observation_bindings']==study.original_observation_state()
    assert manifest['imported_capture_retention']=='retain-requested-immutable-captures-v1'
    assert module.MANIFEST.read_bytes()==(module.RUN/'EXECUTION_MANIFEST.json').read_bytes()
    assert sha256_file(module.PACKAGE/'SEAL.json')==manifest['preparation_seal_sha256']
    proof=study.read(module.PACKAGE/'SEAL.json')
    assert proof['status']=='qualified_no_model_inference' and proof['completion_requests']==0
    assert proof['source_sha256']==manifest['source_sha256']
    inventory(module.PACKAGE,proof)
    q=study.read(module.PACKAGE/'QUALIFICATION.json')
    assert q['status']=='qualified' and q['entry_unchanged_after_qualification']
    assert q['initial']==manifest['initial'] and q['native_forms']['status']=='passed' and q['route']['submitted']
    first=module.RUN/'calls/C01-wire-request.json'
    if first.exists():
        assert first.read_bytes()==(module.PACKAGE/'initial-wire-request.json').read_bytes()
    return manifest

base._preparation=preparation

def verify(version='001'):
    result=base.verify(version)
    module=study.Task(version)
    ending=study.read(module.RUN/('final-state.json' if (module.RUN/'final-state.json').is_file() else 'stopped-state.json'))
    result.update(delivery._coverage_wires(module,ending))
    result.update(entry='fresh_E20_OBS_with_declared_expanded_public_contract',
        original_public_sha256=study.ORIGINAL_PUBLIC_SHA,registered_public_sha256=study.PUBLIC_SHA,
        verification_source_sha256=sha256_file(Path(__file__)))
    return result

def verify_preparation(version='001'):
    module=study.Task(version)
    seal=study.read(module.PACKAGE/'SEAL.json')
    strong=base._load('verifier_preparation_inventory',base.STRONG_CORE,'url_task')
    strong._inventory(module.PACKAGE,seal)
    assert seal['source_sha256']==module.source_identities()
    rows=verify_records(module.PACKAGE/'records.jsonl',module.PACKAGE)
    q=study.read(module.PACKAGE/'QUALIFICATION.json')
    assert q['status']=='qualified' and q['completion_requests']==0
    restored=0
    for path in sorted((module.PACKAGE/'scripted/verifier/steps').glob('*-state.json')):
        stem=path.name.removesuffix('-state.json')
        state=study.read(path)
        candidate=study.candidate_from_snapshot(study.read(path.with_name(stem+'-candidate.json')))
        session=study.restore(state,candidate,module.PACKAGE/'scripted/verifier',replay=True)
        assert canonical_json_bytes(study.snapshot(session))==canonical_json_bytes(state)
        step=study.read(path.with_name(stem+'.json'))
        assert step['before_request']['messages'][1]['content']
        assert step['after_view']==session.view()
        restored+=1
    return dict(status='verified',source_bindings=len(seal['source_sha256']),custody_records=len(rows),
        checkpoints=restored,completion_requests=0,initial=q['initial'],
        peak_input=max(max(t['input_tokens'],t['next_input_tokens']) for t in q['route']['trials']),
        native_cases=len(q['native_forms']['cases']),submitted_scripted_route=q['route']['submitted'])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',default='001')
    parser.add_argument('--preparation',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    value=(verify_preparation if args.preparation else verify)(args.version)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('xb') as f:f.write(canonical_json_bytes(value))
    print(json.dumps(value,indent=2))
