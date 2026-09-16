"""Freeze an admitted same-task continuation, then execute its finite allowance."""
import argparse
import json
from types import SimpleNamespace

import diagnostic_task as study
import run_uncoached_contribution as runner
from manage import RUNTIME,legacy
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import sha256_file


def prepare(module):
    qualified=study.QUALIFIED
    seal=study.read(qualified/'SEAL.json')
    assert seal['status']=='qualified_no_model_inference'
    study.verify_sources(seal['source_sha256'])
    for row in seal['files']:
        assert sha256_file(qualified/row['path'])==row['sha256']
    folder=module.PACKAGE;folder.mkdir(parents=True,exist_ok=False)
    bound=module.source_identities();store=ArtifactStore(folder)
    log=legacy.QualificationLog(folder/'records.jsonl','coherent-report-preparation',task_module=module)
    session,adapter=module.initial_session(),runner.Adapter(module)
    assert not session.submitted and session.requests_used==session.calls_used==0
    error=None;initial=None
    try:
        server,model,_=module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,
                            source_check=lambda:study.verify_sources(bound))
            view=session.view();count=loop.measure(view);assert count<=23808
            selected=next(iter(loop.cache.values()))
            initial={k:selected[k] for k in ('prompt_tokens','request_sha256','native_sha256','wire_request_sha256')}
            loop.snapshot(session,'starting')
            store.put('initial-wire-request.json',completion_request_bytes(adapter.request_for(view)))
    except BaseException as exc:
        error=exc;study.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        study.save(folder,'QUALIFICATION.json',dict(initial=initial,completion_requests=0,
            memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    study.save(study.AREA,module.MANIFEST.name,dict(actor=study.ACTOR,seed=study.SEED,
        maximum_requests=study.MAX_REQUESTS,maximum_operations=study.MAX_OPERATIONS,source_sha256=bound,
        preparation_seal_sha256=sha256_file(folder/'SEAL.json'),preparation_package=folder.name,
        qualification_seal_sha256=sha256_file(qualified/'SEAL.json'),initial=initial,
        owner_direction=study.OWNER_DIRECTION,starting_candidate=session.candidate.candidate_id,
        inherited_operations=len(session.pairs),no_live_coaching=True,automatic_retry=False,
        subsequent_declared_attempts_authorized=True))
    runner.verify_package(module)
    print(json.dumps(initial),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('prepare','run'))
    parser.add_argument('--version',default='001');args=parser.parse_args()
    module=study.Task(args.version)
    if args.mode=='prepare':prepare(module)
    else:
        manifest=study.read(module.MANIFEST);module.PACKAGE=study.AREA/manifest['preparation_package']
        runner.run_once(SimpleNamespace(owner_direction=study.OWNER_DIRECTION,
            manifest_sha256=sha256_file(module.MANIFEST)),module)
