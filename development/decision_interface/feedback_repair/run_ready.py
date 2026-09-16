"""Freeze a qualified successor input, then execute one separately owned attempt."""
import argparse
import json
from types import SimpleNamespace

import feedback_task as study
from manage import RUNTIME,legacy
import run_uncoached_contribution as runner
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore,verify_records
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file


def prepare(module,qualification):
    qualified=study.AREA/qualification
    seal=study.read(qualified/'SEAL.json')
    study.verify_sources(seal['source_sha256'])
    assert study.read(qualified/'RESULTS.json')['status']=='passed'
    for row in seal['files']:
        assert sha256_file(qualified/row['path'])==row['sha256']
    folder=module.PACKAGE;folder.mkdir(parents=True,exist_ok=False)
    bound=module.source_identities();store=ArtifactStore(folder)
    log=legacy.QualificationLog(folder/'records.jsonl','feedback-rerun-preparation',task_module=module)
    session,adapter=module.initial_session(),runner.Adapter(module)
    server,model,_=module.runtime_paths();error=None;initial=None
    try:
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,source_check=lambda:study.verify_sources(bound))
            count=loop.measure(session.view());assert count<=23808
            selected=next(iter(loop.cache.values()))
            initial={k:selected[k] for k in ('prompt_tokens','request_sha256','native_sha256','wire_request_sha256')}
            loop.snapshot(session,'starting')
            request=adapter.request_for(session.view())
            store.put('initial-wire-request.json',completion_request_bytes(request))
            store.put('initial-view.json',canonical_json_bytes(session.view()))
            old=study.read(study.OLD/'calls/C01-wire-request.json')
            assert {k:v for k,v in request.items() if k!='messages'}=={k:v for k,v in old.items() if k!='messages'}
            assert all(not r['payload'].get('completion_sent') for r in verify_records(folder/'records.jsonl',folder))
    except BaseException as problem:
        error=problem;study.save(folder,'FAILED.json',dict(type=type(problem).__name__,message=str(problem)))
    finally:
        study.save(folder,'QUALIFICATION.json',dict(initial=initial,completion_requests=0,
            memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    study.save(study.AREA,module.MANIFEST.name,dict(actor=study.ACTOR,seed=study.SEED,maximum_requests=16,maximum_operations=48,
        source_sha256=bound,preparation_seal_sha256=sha256_file(folder/'SEAL.json'),preparation_package=folder.name,initial=initial,
        qualification_package=qualification,qualification_seal_sha256=sha256_file(qualified/'SEAL.json'),
        owner_direction=study.OWNER_DIRECTION,starting_candidate=session.candidate.candidate_id,inherited_operations=5,
        no_live_coaching=True,automatic_retry=False))
    runner.verify_package(module);print(json.dumps(initial),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('prepare','run'))
    parser.add_argument('--version',default='001');parser.add_argument('--qualification',default='qualification-001')
    args=parser.parse_args();module=study.Task(args.version)
    if args.mode=='prepare':prepare(module,args.qualification)
    else:
        manifest=study.read(module.MANIFEST);module.PACKAGE=study.AREA/manifest['preparation_package']
        runner.run_once(SimpleNamespace(owner_direction=study.OWNER_DIRECTION,manifest_sha256=sha256_file(module.MANIFEST)),module)
