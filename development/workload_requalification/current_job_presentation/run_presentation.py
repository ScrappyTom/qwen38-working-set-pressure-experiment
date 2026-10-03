"""Thin comparison adapter; common frozen task, source, runtime and opportunity."""
import argparse
import json
import overlap_task as study
import overlap_qualification
import run_dispatch as execution
from working_set_exp.current_job_view import render
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


def isolation(version):
    control, treatment = study.Task('control',version), study.Task('current_job',version)
    a = study.read(control.PACKAGE/'initial-wire-request.json')
    b = study.read(treatment.PACKAGE/'initial-wire-request.json')
    x, y = study.read(control.PACKAGE/'starting-state.json'), study.read(treatment.PACKAGE/'starting-state.json')
    assert x == y
    va = json.loads(a['messages'][1]['content'])
    vb = json.loads(b['messages'][1]['content'])
    session = control.initial_session()
    va['workspace'] = render(va['workspace'],title=study.TITLE,pairs=session.pairs,
        boundary=session.starting_archive_length,submitted=False)
    assert va == vb
    a['messages'][1]['content'] = b['messages'][1]['content']
    assert a == b, 'Difference outside declared status composition'
    assert control.source_identities() == treatment.source_identities()
    result = dict(status='isolated', condition_order=['control','current_job'],
        identical_checkpoint=True, identical_task_source_account_text_checker_opportunity=True,
        only_status_composition_differs=True, source_identity_count=len(control.source_identities()),
        control_manifest_sha256=sha256_file(control.MANIFEST),
        treatment_manifest_sha256=sha256_file(treatment.MANIFEST))
    path = study.HERE/f'INITIAL-ISOLATION-{version}.json'
    with path.open('xb') as stream: stream.write(canonical_json_bytes(result))
    print(json.dumps(result),flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',choices=('prepare','run','isolation'))
    parser.add_argument('--condition',choices=('control','current_job'),default='control')
    parser.add_argument('--version',default='001')
    args = parser.parse_args()
    if args.mode == 'isolation':
        isolation(args.version); return
    module = study.Task(args.condition,args.version)
    execution.qualification_route = overlap_qualification
    if args.mode == 'prepare':
        execution.prepare(module)
        manifest = study.read(module.MANIFEST)
        manifest.update(condition=module.condition,
            comparison='current-job status composition only', assistance='uncoached new coverage; common saved-work source release is evaluator setup',
            maximum_new_requests=24,maximum_new_operations=72,
            no_account_policy_change=True,no_reasoning_or_format_change=True)
        module.MANIFEST.write_bytes(canonical_json_bytes(manifest))
    else:
        isolation_version = '002' if args.version == '003' else args.version
        assert study.read(study.HERE/f'INITIAL-ISOLATION-{isolation_version}.json')['status']=='isolated'
        if args.version == '003':
            proof = study.read(study.HERE/'SOURCE-RECONCILIATION-003.json')
            assert proof['status'] == 'qualified_source_binding_maintenance'
            assert proof['old_attempt_directory_absent'] and proof['completion_requests'] == 0
            assert proof['manifests'][args.condition] == sha256_file(module.MANIFEST)
        assert study.read(module.MANIFEST)['condition']==args.condition
        execution.run_once(module)


if __name__ == '__main__': main()
