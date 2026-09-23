"""Qualify/run one preserved entry with no coaching or implicit inference."""
import argparse,copy,json
from types import SimpleNamespace
import saved_task as study
import run_uncoached_contribution as runner
from manage import RUNTIME,legacy
from working_set_exp.custody import ArtifactStore
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file


def prepare(module):
    folder=module.PACKAGE;folder.mkdir(exist_ok=False)
    bound=module.source_identities();store=ArtifactStore(folder)
    log=legacy.QualificationLog(folder/'records.jsonl','saved-library-entry-preparation',task_module=module)
    session,adapter=module.initial_session(),runner.Adapter(module)
    trials=[];initial=None;error=None;checks=0
    try:
        proof=study.previous.previous.decoder_reuse_bindings()
        request=adapter.request_for(session.view())
        old=study.read(study.previous.previous.DECODER/'wire-request.json')
        assert {k:v for k,v in request.items() if k!='messages'}=={k:v for k,v in old.items() if k!='messages'}
        store.put('decoder-reuse.json',canonical_json_bytes(dict(cases=31,bindings=proof,completion_requests=0)))
        module.attach_observations(session,folder,log)
        server,model,_=module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,source_check=lambda:module.verify_sources(bound))
            assert loop.measure(session.view())<=23808
            selected=loop.cache[sha256_bytes(canonical_json_bytes(request))]
            initial={k:selected[k] for k in ('prompt_tokens','request_sha256','native_sha256','wire_request_sha256')}
            loop.snapshot(session,'starting');store.put('initial-wire-request.json',completion_request_bytes(request))
            original=dict(session.candidate.file_map)
            def action(tag,operation,why):
                nonlocal checks
                before=session.view();session.mark_delivered(before)
                store.put(tag+'-input.json',canonical_json_bytes(before));store.put(tag+'-basis.txt',why.encode())
                if operation['action']=='check':checks+=1;assert checks<=2
                result=module.process_reply(session,dict(discussion='Evaluator-scripted engineering qualification.',operation=operation),loop.measure,adapter.preceding_feedback)
                assert all(o['result']['accepted'] for o in result['operations']),result
                count=loop.measure(session.view());assert count<=23808 and not session.delivery_blocked
                assert session.candidate.file_map['Lib/configparser.py']==original['Lib/configparser.py']
                store.put(tag+'-outcome.json',canonical_json_bytes(result));store.put(tag+'-view.json',canonical_json_bytes(session.view()))
                trials.append(dict(stage=tag,tokens=count,action=operation['action']))
                return result['operations'][-1]['result']
            recovered=action('historical-source',dict(action='reopen_result',handle='RES-0005',offset=0),
                'Engineering recovery probe of an actual archived read; not an actor-selected need or new current-source acquisition.')
            payload=session.payload('RES-0005')
            # Exact record or an explicitly bounded prefix; no invented old observation.
            assert recovered['exact_utf8'].encode()==payload[:len(recovered['exact_utf8'].encode())]
            def locate(tag,path,query):
                result=action(tag,dict(action='search',path=path,query=query,offset=0,limit=16),
                    'The task or evaluator proposal names the symbol/anchor; the actual search supplies coordinates. No source coordinates are guessed.')
                assert result['regions'];return result['regions'][0]['region_ref']
            rows=study.read(study.previous.original.ORIGINAL/'REFERENCE_EDITS.json')['rows']
            rows=[r for r in rows if r['path']!='Lib/configparser.py'];assert len(rows)==3
            testrow=rows[0];testpath=testrow['path']
            testanchor=locate('test-anchor',testpath,testrow['old'].splitlines()[0])
            classref=locate('exception-source','Lib/configparser.py','class MultilineContinuationError')
            raiseref=locate('raise-source','Lib/configparser.py','raise MultilineContinuationError')
            header=action('test-imports',dict(action='read',path=testpath,start_line=1,end_line=12),
                'Existing imports determine available names for the proposed regression.')['source']['region_ref']
            action('test-group',dict(action='work_on_exact',regions=[testanchor,classref,raiseref,header],results=[]),
                'Returned exact references assemble the insertion point, imports and relevant saved behavior; assisted feasibility only.')
            def patch(tag,row,new=None):
                assert any(row['old'] in s['content'] for s in session.view()['working_set']['sources'] if s['path']==row['path'])
                return action(tag,dict(action='patch',path=row['path'],old=row['old'],new=row['new'] if new is None else new,
                    expected_candidate_id=session.candidate.candidate_id,expected_file_sha256=session.candidate.file_sha256(row['path'])),
                    'Exact old text is visible. This evaluator-authored proposal is never supplied in the initial model input.')
            wrong=testrow['new'].replace('("customer.ini", 3,','("customer.ini", 4,')
            assert wrong!=testrow['new'];patch('test-wrong-expectation',testrow,wrong)
            failed=action('observe-failure',dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),
                'The provisional test is saved; actual execution decides whether its expected line matches behavior.')
            assert not failed['passed']
            report=session.view()['verification']['checks']['public']['assessment']
            assert 'candidate_tests.execution' in report['failed_criteria']
            assert report['diagnostics_shown']>0
            fix=dict(path=testpath,old='("customer.ini", 4,',new='("customer.ini", 3,')
            patch('correct-observed-line',fix)
            for i,row in enumerate(rows[1:],1):
                anchor=locate(f'doc-anchor-{i}',row['path'],row['old'].splitlines()[0].strip())
                action(f'doc-group-{i}',dict(action='work_on_exact',regions=[anchor,classref,raiseref],results=[]),
                    'Task requires documentation; search returns its actual anchor. Saved library support stays exact and tests remain durable.')
                patch(f'doc-edit-{i}',row)
            passed=action('check-complete',dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),
                'Saved tests and docs change the candidate; public execution observes the current version.')
            assert passed['passed']
            action('submit',dict(action='submit',expected_candidate_id=session.candidate.candidate_id),
                'Actual current public pass plus independently reviewed evaluator contribution support scripted submission.')
            assert session.submitted
            tests=session.candidate.file_map[testpath].decode();assert tests.replace(testrow['new'],testrow['old'],1).encode()==original[testpath]
            loop.snapshot(session,'scripted-final');module.verify_sources(bound)
    except BaseException as exc:
        error=exc;study.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        study.save(folder,'QUALIFICATION.json',dict(initial=initial,trials=trials,completion_requests=0,checks_executed=checks,
            inherited_operations=32,new_allowance=True,memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    study.save(module.AREA,module.MANIFEST.name,dict(actor=module.ACTOR,seed=module.SEED,maximum_requests=32,maximum_operations=96,
        source_sha256=bound,preparation_seal_sha256=sha256_file(folder/'SEAL.json'),preparation_package=folder.name,initial=initial,
        owner_direction=study.OWNER_DIRECTION,starting_candidate=study.STARTING_ID,inherited_operations=32,
        no_live_coaching=True,automatic_retry=False))
    runner.verify_package(module)
    print(json.dumps(dict(status='qualified',initial=initial,trials=trials),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('prepare','run'));p.add_argument('--version',default='001')
    args=p.parse_args();module=study.Task(args.version)
    if args.mode=='prepare':prepare(module)
    else:runner.run_once(SimpleNamespace(owner_direction=study.OWNER_DIRECTION,manifest_sha256=sha256_file(module.MANIFEST)),module)
