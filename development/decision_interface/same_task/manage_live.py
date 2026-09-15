"""Freeze native starting input, then execute one separately recorded attempt."""
import argparse
import json
from types import SimpleNamespace

import live_task as study
from manage import RUNTIME, legacy
import run_uncoached_contribution as runner
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file


def verify_parent():
    for name in ('qualification-003','native-003'):
        folder=study.parent.AREA/name
        seal=study.read(folder/'SEAL.json')
        assert sha256_bytes(canonical_json_bytes(seal['files']))==seal['aggregate_sha256']
        study.verify_sources(seal['source_sha256'])
        for row in seal['files']:
            path=folder/row['path']
            assert path.stat().st_size==row['size_bytes'] and sha256_file(path)==row['sha256']
    assert study.read(study.parent.AREA/'native-003/RESULTS.json')['status']=='passed'
    assert study.read(study.parent.AREA/'qualification-003/RESULTS.json')['submitted']


def prepare(module):
    verify_parent()
    folder=module.PACKAGE
    folder.mkdir(parents=True,exist_ok=False)
    bound=module.source_identities()
    store=ArtifactStore(folder)
    log=legacy.QualificationLog(folder/'records.jsonl','decision-same-task-preparation',task_module=module)
    session,adapter=module.initial_session(),runner.Adapter(module)
    assert (study.AREA/'SYSTEM.txt').read_bytes()==(study.parent.AREA/'SYSTEM.txt').read_bytes()
    server,model,_=module.runtime_paths()
    error,initial=None,None
    try:
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,
                source_check=lambda:module.verify_sources(bound))
            count=loop.measure(session.view());assert count<=23808
            selected=next(iter(loop.cache.values()))
            initial={k:selected[k] for k in ('prompt_tokens','request_sha256','native_sha256','wire_request_sha256')}
            loop.snapshot(session,'starting')
            store.put('initial-wire-request.json',completion_request_bytes(adapter.request_for(session.view())))
            store.put('initial-view.json',canonical_json_bytes(session.view()))
            assert adapter.request_for(session.view())['grammar']==study.parent.response_constraints()['grammar']
            assert all(not r['payload'].get('completion_sent') for r in verify_records(folder/'records.jsonl',folder))
            assert bound==module.source_identities()
    except BaseException as problem:
        error=problem
        study.save(folder,'FAILED.json',dict(type=type(problem).__name__,message=str(problem)))
    finally:
        study.save(folder,'QUALIFICATION.json',dict(initial=initial,completion_requests=0,
            memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:
        raise error
    manifest=dict(actor=study.ACTOR,seed=study.SEED,maximum_requests=16,maximum_operations=48,
        source_sha256=bound,preparation_seal_sha256=sha256_file(folder/'SEAL.json'),
        preparation_package=folder.name,initial=initial,owner_direction=study.OWNER_DIRECTION,
        starting_candidate=session.candidate.candidate_id,inherited_operations=5,
        checkpoint='development/operable_recovery/run-001/starting-state.json',
        no_live_coaching=True,automatic_retry=False,
        prior_engineering_seal=sha256_file(study.parent.AREA/'qualification-003/SEAL.json'),
        prior_native_seal=sha256_file(study.parent.AREA/'native-003/SEAL.json'))
    study.save(study.AREA,module.MANIFEST.name,manifest)
    runner.verify_package(module)
    print(json.dumps(initial),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('prepare','run'))
    parser.add_argument('--version',default='001')
    args=parser.parse_args();module=study.Task(args.version)
    if args.mode=='prepare':
        prepare(module)
    else:
        manifest=study.read(module.MANIFEST)
        module.PACKAGE=study.AREA/manifest['preparation_package']
        runner.run_once(SimpleNamespace(owner_direction=study.OWNER_DIRECTION,manifest_sha256=sha256_file(module.MANIFEST)),module)
