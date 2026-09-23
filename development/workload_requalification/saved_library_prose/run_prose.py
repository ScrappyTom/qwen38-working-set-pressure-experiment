"""Qualify and run the separately declared prose-review assignment."""
import argparse,copy,json
from types import SimpleNamespace
import bootstrap
import prose_task as study
import run_continuity as driver
from manage import RUNTIME,legacy
from working_set_exp.custody import ArtifactStore
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file

driver.controller.INHERITED_REQUESTS,driver.controller.INHERITED_OPERATIONS=17,26
runner=driver.runner


def prepare(module):
    folder=module.PACKAGE;folder.mkdir(exist_ok=False)
    bound=module.source_identities();store=ArtifactStore(folder)
    log=legacy.QualificationLog(folder/'records.jsonl','review-directed-prose-preparation',task_module=module)
    session,adapter=module.initial_session(),runner.Adapter(module)
    initial,trials,error=None,[],None
    try:
        request=adapter.request_for(session.view())
        old=study.previous.read(study.previous.AREA/'preparation-001/initial-wire-request.json')
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
                return outcome
            search=action('find-source-interface',dict(action='search',path='Lib/configparser.py',query='def read_string',offset=0,limit=8),
                'The reviewer assignment distinguishes supplied source names from defaults. Search the existing method named in the source header and task; do not infer its signature.')
            regions=search['operations'][-1]['result']['regions']
            region=next(r for r in regions if r.get('name')=='read_string')
            action('read-source-interface',dict(action='read',path=region['path'],start_line=region['start_line'],end_line=region['end_line']),
                'Use the actual enclosing-function extent returned by search, which contains both the default and the call forwarding the supplied source.')
            text=session.candidate.file_map['Doc/library/configparser.rst'].decode()
            oldtext=text.split('.. exception:: MultilineContinuationError\n',1)[1].split('.. rubric:: Footnotes',1)[0]
            newtext=('\n   Exception raised when a nonblank, non-comment line is treated as a\n'
                '   continuation of an option with no value. Continuation requires\n'
                '   greater indentation than the preceding option and depends on the\n'
                '   configured blank-line and comment handling. This applies when the\n'
                '   *allow_no_value* constructor argument is ``True``. Subclass of\n'
                '   :exc:`ParsingError`.\n\n'
                '   The constructor arguments ``source``, ``lineno`` and ``line`` are\n'
                '   available as attributes and preserved in ``args`` for copying and\n'
                '   pickling. ``source`` identifies the input; :meth:`read_string`\n'
                '   uses a supplied source name, defaulting to ``<string>``. ``lineno``\n'
                '   is the one-based offending line number. ``line`` retains that raw\n'
                '   line exactly, including a final newline only when present.\n\n')
            action('clarify-docs',dict(action='patch',path='Doc/library/configparser.rst',old=oldtext,new=newtext,
                expected_candidate_id=session.candidate.candidate_id,
                expected_file_sha256=session.candidate.file_sha256('Doc/library/configparser.rst')),
                'The inherited current loop establishes comment/blank/relative-indentation behavior; the acquired read_string function establishes default versus supplied source. The assignment identifies the unsupported release marker. The exact documentation anchor is visible. Reference wording remains evaluator-only.')
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
            inherited_requests=17,inherited_operations=26,maximum_new_requests=8,maximum_new_operations=24,
            inherited_observations=1,new_checks_executed=max(0,len(starts)-1),
            memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    study.save(module.AREA,module.MANIFEST.name,dict(actor=module.ACTOR,seed=module.SEED,maximum_requests=25,maximum_operations=50,
        source_sha256=bound,preparation_seal_sha256=sha256_file(folder/'SEAL.json'),preparation_package=folder.name,initial=initial,
        owner_direction=study.OWNER_DIRECTION,inherited_requests=17,inherited_operations=26,maximum_new_requests=8,maximum_new_operations=24,
        reviewer_directed_assignment=True,no_live_coaching=True,automatic_retry=False))
    runner.verify_package(module)
    print(json.dumps(dict(status='qualified',initial=initial,trials=trials,completion_requests=0)),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('prepare','run'));parser.add_argument('--version',default='001')
    args=parser.parse_args();module=study.Task(args.version)
    if args.mode=='prepare':prepare(module)
    else:runner.run_once(SimpleNamespace(owner_direction=study.OWNER_DIRECTION,manifest_sha256=sha256_file(module.MANIFEST)),module)
