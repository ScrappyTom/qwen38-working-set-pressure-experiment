"""Preserve002; qualify input-identical source-enumeration maintenance, no runtime."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import overlap_task as entry
import run_dispatch as execution
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file


def main():
    assert not (entry.HERE/'control/run-002').exists()
    proof = dict(status='qualified_source_binding_maintenance',completion_requests=0,
        native_requests=0, old_attempt_directory_absent=True,manifests={},conditions={})
    for condition in ('control','current_job'):
        old=entry.Task(condition,'002'); new=entry.Task(condition,'003')
        previous=entry.read(old.MANIFEST)
        bound=new.source_identities()
        removed=sorted(set(previous['source_sha256'])-set(bound))
        changed={p:dict(before=d,after=bound[p]) for p,d in previous['source_sha256'].items()
                 if p in bound and d!=bound[p]}
        assert removed and all(p.endswith(('.stdout.txt','.stderr.txt')) for p in removed)
        assert set(changed)=={(entry.HERE/name).relative_to(entry.study.ROOT).as_posix()
            for name in ('overlap_task.py','run_presentation.py')}
        assert canonical_json_bytes(old.snapshot(old.initial_session()))==canonical_json_bytes(new.snapshot(new.initial_session()))
        adapter=execution.runner.Adapter(new)
        actual=completion_request_bytes(adapter.request_for(new.initial_session().view()))
        assert actual==(new.PACKAGE/'initial-wire-request.json').read_bytes()
        manifest={**previous, 'source_sha256':bound,
            'preparation_reused_from_version':'002',
            'source_maintenance':'Exclude generated output logs from immutable code/task-input discovery; validate unchanged checkpoint and exact qualified wire.'}
        with new.MANIFEST.open('xb') as stream: stream.write(canonical_json_bytes(manifest))
        execution.runner.verify_package(new)
        proof['manifests'][condition]=sha256_file(new.MANIFEST)
        proof['conditions'][condition]=dict(removed_output_bindings=removed,
            changed_administrative_code=changed,exact_input_unchanged=True,
            exact_starting_state_unchanged=True,source_binding_count=len(bound),
            reused_native_forms=44,reused_scripted_decisions=11)
    assert entry.Task('control','003').source_identities()==entry.Task('current_job','003').source_identities()
    proof['qualifier_sha256']=sha256_file(Path(__file__))
    with (entry.HERE/'SOURCE-RECONCILIATION-003.json').open('xb') as stream:
        stream.write(canonical_json_bytes(proof))
    print('Both003 manifests qualified: same exact native input/state; output logs removed from source bindings; zero new runtime/model requests.')


if __name__=='__main__':main()
