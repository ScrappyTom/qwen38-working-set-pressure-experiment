"""Separate finite attempts; preserve original source tasks/checker bytes."""
import argparse
import json
from types import SimpleNamespace

import repair_task as study
import run_uncoached_contribution as runner
from manage import RUNTIME,legacy
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file
from working_set_exp.observations import ObservationStore

OWNER_DIRECTION='Repeat the repair/qualify/run process until the previously tested workloads pass.'


def prepare(module):
    study.prerequisite_bindings()  # Status, source closure and every captured byte.
    folder=module.PACKAGE;folder.mkdir(exist_ok=False)
    bound=module.source_identities();store=ArtifactStore(folder)
    log=legacy.QualificationLog(folder/'records.jsonl','small-repair-qualification',task_module=module)
    session,adapter=module.initial_session(),runner.Adapter(module)
    trials=[];error=None;initial=None
    try:
        server,model,_=module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,source_check=lambda:study.verify_sources(bound))
            view=session.view();assert loop.measure(view)<=23808
            selected=next(iter(loop.cache.values()))
            initial={k:selected[k] for k in ('prompt_tokens','request_sha256','native_sha256','wire_request_sha256')}
            loop.snapshot(session,'starting');store.put('initial-wire-request.json',completion_request_bytes(adapter.request_for(view)))
            session.observations=ObservationStore(folder/'scripted-observations')
            def action(tag,value):
                session.mark_delivered(session.view())
                reply=dict(discussion='Offline reference operation.',operation=value)
                result=module.process_reply(session,reply,loop.measure,adapter.preceding_feedback)
                assert all(o['result']['accepted'] for o in result['operations']),result
                view=session.view();tokens=loop.measure(view)
                assert tokens<=23808 and not session.delivery_blocked
                store.put(tag+'-view.json',canonical_json_bytes(view));store.put(tag+'-outcome.json',canonical_json_bytes(result))
                trials.append(dict(stage=tag,tokens=tokens,operations=len(result['operations'])))
            action('baseline',dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id))
            assert not session.last['result']['passed']
            path=module.legacy.TARGET
            text=session.candidate.file_map[path].decode();start=text[:text.index(module.legacy.BAD)].count('\n')+1
            end=start+len(module.legacy.BAD.splitlines())-1
            action('source',dict(action='work_on',sources=[dict(path=path,start_line=start,end_line=end)],results=[]))
            action('repair',dict(action='patch',path=path,old=module.legacy.BAD,new=module.legacy.GOOD,
                expected_candidate_id=session.candidate.candidate_id,expected_file_sha256=session.candidate.file_sha256(path)))
            assert session.last['action_summary']['action']=='patch'
            action('successor-check',dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id))
            assert session.last['result']['passed']
            action('submit',dict(action='submit',expected_candidate_id=session.candidate.candidate_id));assert session.submitted
    except BaseException as exc:
        error=exc;study.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        study.save(folder,'QUALIFICATION.json',dict(initial=initial,trials=trials,completion_requests=0,
            memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    study.save(module.AREA,module.MANIFEST.name,dict(actor=study.ACTOR,seed=study.SEED,maximum_requests=study.MAX_REQUESTS,
        maximum_operations=study.MAX_OPERATIONS,source_sha256=bound,preparation_seal_sha256=sha256_file(folder/'SEAL.json'),
        preparation_package=folder.name,initial=initial,owner_direction=OWNER_DIRECTION,
        starting_candidate=module.initial_session().candidate.candidate_id,inherited_operations=0,
        no_live_coaching=True,automatic_retry=False,subsequent_declared_attempts_authorized=True))
    runner.verify_package(module);print(json.dumps(dict(case=module.case,initial=initial,trials=trials)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('prepare','run'));p.add_argument('case',choices=study.MODULES)
    p.add_argument('--version',default='001');args=p.parse_args();module=study.Task(args.case,args.version)
    if args.mode=='prepare':prepare(module)
    else:runner.run_once(SimpleNamespace(owner_direction=OWNER_DIRECTION,manifest_sha256=sha256_file(module.MANIFEST)),module)
