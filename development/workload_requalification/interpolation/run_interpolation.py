"""Qualify the exact information path, freeze, and run a separate uncoached attempt."""
import argparse
import json
from types import SimpleNamespace

import interpolation_task as study
import run_uncoached_contribution as runner
from manage import RUNTIME, legacy
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file
from working_set_exp.observations import ObservationStore


def prepare(module):
    cpu=study.AREA/'checker-qualification-002'
    seal=study.read(cpu/'SEAL.json')
    assert seal['status']=='qualified_no_model_inference'
    for row in seal['files']:
        assert sha256_file(cpu/row['path'])==row['sha256']
    folder=module.PACKAGE;folder.mkdir(parents=True,exist_ok=False)
    bound=module.source_identities();store=ArtifactStore(folder)
    log=legacy.QualificationLog(folder/'records.jsonl','interpolation-preparation',task_module=module)
    session,adapter=module.initial_session(),runner.Adapter(module)
    error=None;initial=None;trials=[]
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
            # Scripted qualification is separate from the frozen actor entry.
            # Its choices only qualify operations/delivery, not model discovery.
            session.observations=ObservationStore(folder/'scripted-observations')
            def action(tag, value):
                session.mark_delivered(session.view())
                outcome=module.process_reply(session,dict(discussion='Offline engineering qualification.',operation=value),
                    loop.measure,adapter.preceding_feedback)
                view=session.view();tokens=loop.measure(view)
                assert tokens<=23808 and not session.delivery_blocked
                store.put(tag+'-view.json',canonical_json_bytes(view))
                store.put(tag+'-outcome.json',canonical_json_bytes(outcome))
                trials.append(dict(stage=tag,tokens=tokens,operations=len(outcome['operations'])))
                return outcome
            action('baseline-check',dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id))
            assert session.last['result']['accepted']
            test=(study.legacy.AREA/'REFERENCE_TEST.py').read_text(encoding='utf-8')
            doc=(study.legacy.AREA/'REFERENCE_DOC.txt').read_text(encoding='utf-8')
            for tag,path,addition in [('tests',study.TEST,test),('documentation',study.DOC,doc)]:
                content=session.candidate.file_map[path].decode();lines=content.splitlines(keepends=True)
                action(tag+'-anchor',dict(action='work_on',sources=[dict(path=path,start_line=max(1,len(lines)-8),end_line=len(lines))],results=[]))
                anchor=''.join(lines[-5:]);assert content.count(anchor)==1
                result=action(tag+'-edit',dict(action='patch',path=path,old=anchor,new=anchor+'\n\n'+addition,
                    expected_candidate_id=session.candidate.candidate_id,expected_file_sha256=session.candidate.file_sha256(path)))
                assert all(o['result']['accepted'] for o in result['operations']),result
                assert session.last['result']['passed'], session.last
            action('submit',dict(action='submit',expected_candidate_id=session.candidate.candidate_id))
            assert session.submitted
    except BaseException as exc:
        error=exc;study.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        study.save(folder,'QUALIFICATION.json',dict(initial=initial,completion_requests=0,trials=trials,
            memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    study.save(study.AREA,module.MANIFEST.name,dict(actor=study.ACTOR,seed=study.SEED,
        maximum_requests=study.MAX_REQUESTS,maximum_operations=study.MAX_OPERATIONS,source_sha256=bound,
        preparation_seal_sha256=sha256_file(folder/'SEAL.json'),preparation_package=folder.name,
        qualification_seal_sha256=sha256_file(cpu/'SEAL.json'),initial=initial,
        owner_direction=study.OWNER_DIRECTION,starting_candidate=study.legacy.STARTING_ID,
        inherited_operations=len(module.initial_session().pairs),no_live_coaching=True,automatic_retry=False,
        subsequent_declared_attempts_authorized=True))
    runner.verify_package(module)
    print(json.dumps(dict(initial=initial,trials=trials)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('prepare','run'))
    parser.add_argument('--version',default='001');args=parser.parse_args()
    module=study.Task(args.version)
    if args.mode=='prepare':prepare(module)
    else:
        manifest=study.read(module.MANIFEST);module.PACKAGE=study.AREA/manifest['preparation_package']
        runner.run_once(SimpleNamespace(owner_direction=study.OWNER_DIRECTION,
            manifest_sha256=sha256_file(module.MANIFEST)),module)
