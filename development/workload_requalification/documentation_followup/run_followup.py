"""Qualify and run the separately declared prose-review assignment."""
import argparse,copy,json
from types import SimpleNamespace
import bootstrap
import followup_task as study
import run_continuity as driver
from manage import RUNTIME,legacy
from working_set_exp.custody import ArtifactStore
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file

driver.controller.INHERITED_REQUESTS,driver.controller.INHERITED_OPERATIONS=49,73
runner=driver.runner


def prepare(module):
    folder=module.PACKAGE;folder.mkdir(exist_ok=False)
    bound=module.source_identities();store=ArtifactStore(folder)
    log=legacy.QualificationLog(folder/'records.jsonl','review-directed-prose-preparation',task_module=module)
    session,adapter=module.initial_session(),runner.Adapter(module)
    initial,trials,error=None,[],None
    try:
        request=adapter.request_for(session.view())
        old=study.previous.read(study.previous.AREA/'preparation-002/initial-wire-request.json')
        assert {k:v for k,v in request.items() if k!='messages'}=={k:v for k,v in old.items() if k!='messages'}
        proof=study.previous.previous.decoder_reuse_bindings()
        store.put('decoder-reuse.json',canonical_json_bytes(dict(cases=31,bindings=proof,completion_requests=0)))
        module.attach_observations(session,folder,log)
        server,model,_=module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,source_check=lambda:module.verify_sources(bound))
            assert loop.measure(session.view())<=23808
            selected=loop.cache[sha256_bytes(canonical_json_bytes(request))]
            initial={k:selected[k] for k in driver.controller.INITIAL_KEYS}
            loop.snapshot(session,'starting');store.put('initial-wire-request.json',completion_request_bytes(request))
            original={k:v for k,v in session.candidate.file_map.items()}
            def action(tag,operation,why):
                view=session.view();store.put(tag+'-input-view.json',canonical_json_bytes(view));store.put(tag+'-justification.txt',why.encode())
                session.mark_delivered(view)
                outcome=module.process_reply(session,dict(discussion='Researcher-scripted prose qualification.',operation=operation),loop.measure,adapter.preceding_feedback)
                assert all(o['result']['accepted'] for o in outcome['operations'])
                count=loop.measure(session.view());assert count<=23808 and not session.delivery_blocked
                assert all(session.candidate.file_map[n]==value for n,value in original.items() if n!='Doc/library/configparser.rst')
                store.put(tag+'-outcome.json',canonical_json_bytes(outcome));store.put(tag+'-view.json',canonical_json_bytes(session.view()))
                trials.append(dict(stage=tag,tokens=count,operations=len(outcome['operations'])))
            oldtext=('   Exception raised when a continuation line (a line beginning with\n'
                     '   whitespace) follows an option that has no value.  This condition is\n'
                     '   only possible when :attr:`!allow_no_value` is ``True``.  Subclass of\n'
                     '   :exc:`ParsingError`.')
            newtext=('   Exception raised when a nonblank, non-comment line is treated as a\n'
                     '   continuation of an option with no value. Continuation depends on\n'
                     '   indentation deeper than the preceding option and the configured\n'
                     '   blank-line and comment handling. This applies when the\n'
                     '   *allow_no_value* constructor argument is ``True``. Subclass of\n'
                     '   :exc:`ParsingError`. The offending line is retained exactly,\n'
                     '   including its original line ending when present.')
            action('clarify-docs',dict(action='patch',path='Doc/library/configparser.rst',old=oldtext,new=newtext,
                expected_candidate_id=session.candidate.candidate_id,
                expected_file_sha256=session.candidate.file_sha256('Doc/library/configparser.rst')),
                'Reviewer task identifies the imprecision; inherited visible _read1010-1075 and constructor header establish the distinctions. Exact doc anchor is also visible. Reference wording is evaluator-only.')
            action('check-successor',dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),
                'The current documentation edit changes the candidate; run the unchanged public scope, without claiming semantic prose proof.')
            assert session.last['result']['passed']
            action('submit',dict(action='submit',expected_candidate_id=session.candidate.candidate_id),
                'The scripted accurate prose is saved and its unchanged current public check passed.')
            assert session.submitted
            loop.snapshot(session,'scripted-final');module.verify_sources(bound)
    except BaseException as exc:
        error=exc;study.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        starts=list((folder/'observations').glob('*/started.json'))
        study.save(folder,'QUALIFICATION.json',dict(initial=initial,trials=trials,completion_requests=0,
            inherited_requests=49,inherited_operations=73,maximum_new_requests=8,maximum_new_operations=24,
            inherited_observations=3,new_checks_executed=max(0,len(starts)-3),
            memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    study.save(module.AREA,module.MANIFEST.name,dict(actor=module.ACTOR,seed=module.SEED,maximum_requests=57,maximum_operations=97,
        source_sha256=bound,preparation_seal_sha256=sha256_file(folder/'SEAL.json'),preparation_package=folder.name,initial=initial,
        owner_direction=study.OWNER_DIRECTION,inherited_requests=49,inherited_operations=73,maximum_new_requests=8,maximum_new_operations=24,
        reviewer_directed_assignment=True,no_live_coaching=True,automatic_retry=False))
    runner.verify_package(module)
    print(json.dumps(dict(status='qualified',initial=initial,trials=trials,completion_requests=0)),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('prepare','run'));parser.add_argument('--version',default='001')
    args=parser.parse_args();module=study.Task(args.version)
    if args.mode=='prepare':prepare(module)
    else:runner.run_once(SimpleNamespace(owner_direction=study.OWNER_DIRECTION,manifest_sha256=sha256_file(module.MANIFEST)),module)
