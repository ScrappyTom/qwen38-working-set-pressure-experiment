"""Complete wire isolation and source-diff audit for the declared successor pair."""
import argparse
import copy
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bootstrap
import transition_task as study
import run_transition as control
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file


def verify(version):
    tasks=[study.Task(c,version) for c in study.CONDITIONS]
    manifests=[control.verify_preparation(m) for m in tasks]
    requests=[study.read(m.PACKAGE/'initial-wire-request.json') for m in tasks]
    views=[study.load_json_strict(r['messages'][1]['content']) for r in requests]
    altered=copy.deepcopy(requests[0])
    altered['messages'][1]['content']=requests[1]['messages'][1]['content']
    assert altered==requests[1]
    changed={k for k in views[0]['workspace'] if views[0]['workspace'][k]!=views[1]['workspace'][k]}
    assert changed=={'working_set','visibility'}
    altered=copy.deepcopy(views[0])
    altered['workspace']['working_set']['sources']=views[1]['workspace']['working_set']['sources']
    altered['workspace']['visibility']=views[1]['workspace']['visibility']
    assert altered==views[1]
    assert manifests[0]['source_sha256']==manifests[1]['source_sha256']
    old=[study.read(m.PACKAGE.parent/'EXECUTION_MANIFEST-001.json') for m in tasks]
    assert old[0]['source_sha256']==old[1]['source_sha256']
    original,current=old[0]['source_sha256'],manifests[0]['source_sha256']
    modified=sorted(k for k in original.keys()&current.keys() if original[k]!=current[k])
    added=sorted(current.keys()-original.keys())
    removed=sorted(original.keys()-current.keys())
    base='development/workload_requalification/ecological_information_transition/'
    assert modified==[base+'run_transition.py',base+'transition_task.py']
    assert added==[base+'review/APPARATUS-DECISION-001.json',base+'tests/test_apparatus_gate.py']
    assert removed==[]
    for task,manifest in zip(tasks,manifests):
        original_package=task.PACKAGE.parent/'preparation-001'
        assert (task.PACKAGE/'initial-wire-request.json').read_bytes()==(original_package/'initial-wire-request.json').read_bytes()
        assert (task.PACKAGE/'admission/I0001-native.txt').read_bytes()==(original_package/'admission/I0001-native.txt').read_bytes()
        prior=study.read(original_package/'QUALIFICATION.json')
        proof=study.read(task.PACKAGE/'QUALIFICATION.json')
        assert prior['native_forms']['cases']==proof['native_forms']['cases']
        assert proof['route']['candidate_id']==prior['route']['candidate_id']
        assert proof['route']['scripted_decisions']==prior['route']['scripted_decisions']
    result=dict(status='isolated_successor_pair',version=version,
        changed_workspace_keys=sorted(changed),source_bindings=len(current),
        source_difference=dict(modified=modified,added=added,removed=removed),
        same_initial_wire_and_native_as_001=True,same_native_decoder_forms_and_scripted_outcomes=True,
        no_actor_information_runtime_checker_or_opportunity_change=True,
        apparatus_seal_sha256=control.require_apparatus(),
        apparatus_repetition_and_cause_unqualified=True,
        manifests={m.condition:sha256_file(m.MANIFEST) for m in tasks},
        initial_tokens={m.condition:r['initial']['prompt_tokens'] for m,r in zip(tasks,manifests)})
    path=study.AREA/('INITIAL-ISOLATION-'+version+'.json')
    raw=canonical_json_bytes(result)
    if path.exists():
        assert path.read_bytes()==raw
    else:
        path.write_bytes(raw)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',required=True)
    print(json.dumps(verify(parser.parse_args().version)),flush=True)
