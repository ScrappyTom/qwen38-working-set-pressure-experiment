"""Qualify and run one separately bounded closure continuation."""
import argparse,json
from types import SimpleNamespace
import bootstrap
import closure_task as study
import run_continuity as driver
from manage import RUNTIME,legacy
from working_set_exp.custody import ArtifactStore
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file
driver.controller.INHERITED_REQUESTS,driver.controller.INHERITED_OPERATIONS=24,34
runner=driver.runner

def prepare(module):
    folder=module.PACKAGE;folder.mkdir(exist_ok=False)
    bound=module.source_identities();store=ArtifactStore(folder)
    log=legacy.QualificationLog(folder/'records.jsonl','transport-closure-preparation',task_module=module)
    session,adapter=module.initial_session(),runner.Adapter(module)
    initial,trials,error=None,[],None
    try:
        request=adapter.request_for(session.view());old=study.read(study.OLD/'calls/C24-wire-request.json')
        assert {k:v for k,v in request.items() if k!='messages'}=={k:v for k,v in old.items() if k!='messages'}
        assert request['messages'][0]==old['messages'][0]
        store.put('decoder-reuse.json',canonical_json_bytes(dict(cases=31,bindings=study.decoder_reuse_bindings(),completion_requests=0)))
        module.attach_observations(session,folder,log)
        assert session.check_state()['applies_to_current'] and session.check_state()['passed']
        server,model,_=module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,source_check=lambda:module.verify_sources(bound))
            count=loop.measure(session.view());assert count<=23808
            selected=loop.cache[sha256_bytes(canonical_json_bytes(request))];initial={k:selected[k] for k in driver.controller.INITIAL_KEYS}
            loop.snapshot(session,'starting');store.put('initial-wire-request.json',completion_request_bytes(request))
            before=module.candidate_bytes(session.candidate)
            store.put('submit-justification.txt',b'The exact preceding CHK0073 observation is a passing public check on this current candidate and checker. The unchanged task requests submission after that pass. This is scripted host qualification, not a model choice.')
            session.mark_delivered(session.view())
            result=module.process_reply(session,dict(discussion='Scripted closure qualification.',operation=dict(action='submit',expected_candidate_id=session.candidate.candidate_id)),loop.measure,adapter.preceding_feedback)
            assert session.submitted and all(o['result']['accepted'] for o in result['operations'])
            count=loop.measure(session.view());assert count<=23808 and module.candidate_bytes(session.candidate)==before
            store.put('submit-outcome.json',canonical_json_bytes(result));trials.append(dict(stage='submit_actual_checked_work',tokens=count,operations=len(result['operations'])))
            loop.snapshot(session,'scripted-final');module.verify_sources(bound)
    except BaseException as exc:
        error=exc;study.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        study.save(folder,'QUALIFICATION.json',dict(initial=initial,trials=trials,completion_requests=0,new_checks_executed=0,
            inherited_observations=2,inherited_requests=24,inherited_operations=34,maximum_new_requests=2,maximum_new_operations=4,
            memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    study.save(module.AREA,module.MANIFEST.name,dict(actor=module.ACTOR,seed=module.SEED,maximum_requests=26,maximum_operations=38,
        source_sha256=bound,preparation_seal_sha256=sha256_file(folder/'SEAL.json'),preparation_package=folder.name,initial=initial,
        owner_direction=study.OWNER_DIRECTION,inherited_requests=24,inherited_operations=34,maximum_new_requests=2,maximum_new_operations=4,
        no_live_coaching=True,automatic_retry=False))
    runner.verify_package(module);print(json.dumps(dict(status='qualified',initial=initial,trials=trials,completion_requests=0)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('prepare','run'));p.add_argument('--version',default='001')
    args=p.parse_args();module=study.Task(args.version)
    if args.mode=='prepare':prepare(module)
    else:runner.run_once(SimpleNamespace(owner_direction=study.OWNER_DIRECTION,manifest_sha256=sha256_file(module.MANIFEST)),module)
