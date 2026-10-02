"""Separate post-seal original hidden/probe checks; never actor feedback."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bootstrap
import transition_task as study
import run_transition as control
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file
from working_set_exp.observations import ObservationStore

HERE=Path(__file__).resolve().parent
HELPER=study.ROOT/'development/workload_requalification/ecological_import_entry/review/evaluate_artifact.py'
PROBE=study.ROOT/'maintenance/resume_after_020/import_boundary_probe.py'
PROBE_SHA='b5a2ac3f21015dd15212a7fda5c99329cac3199a736d491e9d2c02be54a7c8b6'
spec=importlib.util.spec_from_file_location('transition_original_artifact_helpers',HELPER)
helpers=importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


def evaluate(condition,version):
    task=study.Task(condition,version)
    run=task.RUN
    seal=study.read(run/'RESPONSE_SEAL.json')
    proof=study.read(HERE/f'VERIFICATION-{condition}-{version}.json')
    assert proof['status']=='replayed_exactly'
    assert proof['response_seal_sha256']==sha256_file(run/'RESPONSE_SEAL.json')
    control.verify_preparation(task)
    for row in seal['files']:
        assert sha256_file(run/row['path'])==row['sha256']
    assert sha256_file(PROBE)==PROBE_SHA
    stem='final' if (run/'final-candidate.json').exists() else 'stopped'
    state_raw=(run/(stem+'-state.json')).read_bytes()
    candidate_raw=(run/(stem+'-candidate.json')).read_bytes()
    candidate=study.original.candidate_from_snapshot(study.load_json_strict(candidate_raw))
    session=task.restore(study.load_json_strict(state_raw),candidate,run,replay=True)
    assert candidate.candidate_id==proof['final_candidate_id']
    assert task.candidate_bytes(session.candidate)==candidate_raw
    out=HERE/(f'evaluation-{condition}-{version}')
    out.mkdir(exist_ok=False)
    result=dict(status='started',classification='separate_post_response_seal_artifact_checks',
        condition=condition,version=version,actor_feedback=False,model_or_native_calls=0,
        response_seal_sha256=sha256_file(run/'RESPONSE_SEAL.json'),
        verification_sha256=sha256_file(HERE/f'VERIFICATION-{condition}-{version}.json'),
        candidate_id=candidate.candidate_id,submitted=session.submitted,
        evaluator_sha256=sha256_file(Path(__file__)),helper_sha256=sha256_file(HELPER),
        original_probe_sha256=PROBE_SHA,unchanged_twelve_cases_are_not_new_independent_cases=True)
    error=None
    try:
        assessment=helpers.artifact_assessment(study.original.starting_candidate(),candidate)
        (out/'ARTIFACT_ASSESSMENT.json').write_bytes(canonical_json_bytes(assessment))
        (out/'EVALUATED_CANDIDATE.json').write_bytes(candidate_raw)
        hidden=study.original.hidden_checker()
        (out/'HIDDEN_ORIGINAL.py').write_bytes(hidden)
        (out/'BOUNDARY_PROBE_ORIGINAL.py').write_bytes(PROBE.read_bytes())
        for index,diff in enumerate(assessment['diffs'].values(),1):
            (out/f'diff-{index:02d}.patch').write_bytes(diff.encode())
        hidden_store=ObservationStore(out/'hidden-observations')
        hidden_result=hidden_store.execute(candidate,hidden,'hidden','CHK-0001')
        assert hidden_result['executed'] and hidden_store.read('CHK-0001')==hidden_result
        boundary_store=ObservationStore(out/'boundary-observations')
        boundary=boundary_store.execute(candidate,PROBE.read_bytes(),'supplemental_import_boundaries','CHK-0001')
        assert boundary['executed'] and boundary_store.read('CHK-0001')==boundary
        cases=helpers.probe_assessment(boundary_store,boundary)
        (out/'BOUNDARY_ASSESSMENT.json').write_bytes(canonical_json_bytes(cases))
        preserved=(assessment['all_23_other_files_byte_identical'] and
                   assessment['all_existing_callable_interfaces_and_public_constants_preserved'])
        result.update(status='post_seal_contract_passed' if hidden_result['passed'] and
            cases['all_twelve_passed'] and preserved else 'post_seal_contract_open',
            original_hidden_observation=hidden_result,boundary_observation=boundary,
            boundary_assessment=cases,artifact_preservation_passed=preserved)
    except BaseException as problem:
        error=problem
        result.update(status='failed_preserved',error_type=type(problem).__name__,message=str(problem))
    finally:
        assert (run/(stem+'-state.json')).read_bytes()==state_raw
        assert (run/(stem+'-candidate.json')).read_bytes()==candidate_raw
        assert sha256_file(run/'RESPONSE_SEAL.json')==result['response_seal_sha256']
        assert sha256_file(PROBE)==PROBE_SHA
        result['sealed_work_and_original_probe_unchanged']=True
        (out/'RESULT.json').write_bytes(canonical_json_bytes(result))
        files=[dict(path=p.relative_to(out).as_posix(),size_bytes=p.stat().st_size,
                    sha256=sha256_file(p)) for p in sorted(out.rglob('*')) if p.is_file()]
        (out/'SEAL.json').write_bytes(canonical_json_bytes(dict(files=files,
            aggregate_sha256=sha256_bytes(canonical_json_bytes(files)))))
    if error:
        raise error
    return dict(condition=condition,status=result['status'],candidate_id=candidate.candidate_id,
                submitted=session.submitted,actor_grade_replaced=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--condition',choices=study.CONDITIONS,required=True)
    parser.add_argument('--version',required=True)
    args=parser.parse_args()
    print(json.dumps(evaluate(args.condition,args.version)),flush=True)
