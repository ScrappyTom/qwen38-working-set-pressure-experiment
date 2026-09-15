"""Native input and actual checker qualification with scripted, non-model replies."""
import argparse
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import decision_task as study
from manage import RUNTIME, legacy
import run_uncoached_contribution as runner
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


def scripted(view, number):
    sources=view['working_set']['sources']
    result=view['latest_feedback']['result'] if view['latest_feedback'] else {}
    def reply(operation, reason):
        return json.dumps(dict(discussion=reason,operation=operation),ensure_ascii=False),reason
    if number==1:
        failed=view['verification']['checks']['tests']
        assert failed['assessment']['failed_criteria']==['detect.error_class']
        return reply(failed['inspect'],'The current check names an undetected exact-class fault; inspect its complete criterion.')
    if number==2:
        assert result['entries'][0]['criterion']=='detect.error_class' and not result['entries'][0]['fault_detected']
        return reply(dict(action='search',path=study.TEST,query='def test_port_access_boundary_and_errors',offset=0,limit=4),
                     'The delivered criterion identifies exact-class coverage; find the existing added method by its visible name.')
    if number==3:
        method,=[r for r in result['regions'] if r.get('name')=='test_port_access_boundary_and_errors']
        regions=[method['region_ref'],*[s['region_ref'] for s in sources if s['path']=='Lib/urllib/parse.py']]
        return reply(dict(action='work_on_exact',regions=regions,results=[]),'Select the returned complete method and the already visible governing implementation together.')
    if number in (4,7):
        path=study.TEST if number==4 else study.DOC
        source,=[s for s in sources if s['path']==path]
        if number==4:
            old=source['content']
            assert old.count('                p.port\n')==7
            new=old.replace('                p.port\n','                p.port\n            self.assertIs(type(cm.exception), ValueError)\n')
            why='Researcher-authored correction: assert exact type after each observed exception; the failed criterion supplies the reason.'
        else:
            anchor='URL Parsing\n-----------\n'
            assert source['content'].count(anchor)==1
            reference=(study.ROOT/'development/working_account/url_ports/REFERENCE_DOC.txt').read_text(encoding='utf-8')
            new=source['content'].replace(anchor,reference+'\n'+anchor)
            why='Researcher-authored documentation fixture; current checked tests, implementation and exact heading are visible. This is not model-authored prose.'
        header=dict(discussion=why,operation=dict(action='replace_region',region=source['region_ref'],expected_candidate_id=view['candidate_id']))
        return json.dumps(header,ensure_ascii=False,separators=(',',':'))+'\nSOURCE\n'+new,why
    if number==5:
        assert view['verification']['checks']['tests']['passed']
        return reply(dict(action='search',path=study.DOC,query='URL Parsing',offset=0,limit=16),'The corrected tests pass; locate the documentation heading through actual search.')
    if number==6:
        match,=[m for m in result['matches'] if m.get('text',m.get('snippet','')).strip()=='URL Parsing']
        region,=[r for r in result['regions'] if r.get('match_line')==match['line']]
        return reply(dict(action='work_on_exact',regions=[region['region_ref'],*[s['region_ref'] for s in sources]],results=[]),
                     'Retain current checked test/implementation source with the returned documentation region; no manual location arithmetic.')
    if number==8:
        assert view['verification']['submission']['eligible']
        return reply(dict(action='submit',expected_candidate_id=view['candidate_id']),'The actual current public check passes after both saved contributions.')
    raise AssertionError('script exceeded its declared route')


def run(folder):
    folder.mkdir(parents=True,exist_ok=False)
    bound=study.source_identities()
    shutil.copytree(study.OLD/'observations',folder/'observations')
    session=study.from_checkpoint(observation_root=folder/'observations')
    adapter=runner.Adapter(study.Task())
    store=ArtifactStore(folder)
    log=legacy.QualificationLog(folder/'records.jsonl','decision-engineering',task_module=study.Task())
    study.prior.attach_observations(session,folder,log)
    server,model,_=study.runtime_paths()
    outcome=None
    try:
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            def fixture_response(url,route,wire,timeout):
                assert route=='/v1/chat/completions'  # Intercepted here; never sent to the server.
                request=json.loads(wire)
                view=json.loads(request['messages'][1]['content'])['workspace']
                content,reason=scripted(view,loop.sent)
                count=loop.cache[sha256_bytes(canonical_json_bytes(request))]['prompt_tokens']
                store.put(f'information-path/C{loop.sent:02d}.json',canonical_json_bytes(dict(reason=reason,researcher_script=True)))
                return canonical_json_bytes(dict(choices=[dict(finish_reason='stop',message=dict(reasoning_content='',content=content))],
                    usage=dict(prompt_tokens=count,completion_tokens=1,total_tokens=count+1,prompt_tokens_details=dict(cached_tokens=0)),timings=dict(cache_n=0)))
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,post=fixture_response,
                source_check=lambda:study.verify_sources(bound))
            # A large authored account and many retained designations must still
            # permit truthful rejection and an explicit joint replacement.
            crowded=session.clone()
            crowded.ranges=[dict(path=study.TEST,start_line=n,end_line=n) for n in range(1,800,2)]
            account='Provisional. '*60000
            crowded._record(dict(action='record_account',text=account),
                dict(accepted=True,input_candidate_id=crowded.candidate.candidate_id,written_during_request=0))
            crowded.enter_recovery('Synthetic control transition qualification; not task evidence.')
            assert crowded._fits_feedback(loop.measure)
            before=crowded.view()
            assert not before['working_account']['text_complete'] and crowded.working_account()['text']==account
            rejected=crowded.execute(dict(action='work_on',sources=[],results=[]),loop.measure)
            assert not rejected['accepted'] and not crowded.delivery_blocked
            crowded.mark_delivered(crowded.view())
            replacement=adapter.process_reply(crowded,dict(discussion='Engineering control qualification.',
                account='Pending: inspect evidence before drafting.',operation=dict(action='work_on',sources=[],results=[])),
                loop.measure,adapter.preceding_feedback)
            assert all(op['result']['accepted'] for op in replacement['operations'])
            assert not crowded.recovery and crowded.working_account()['text']=='Pending: inspect evidence before drafting.'
            store.put('CONTROL_PATH.json',canonical_json_bytes(dict(synthetic=True,retained_designations=400,
                stored_account_bytes=len(account.encode()),displayed_account_bytes=len(before['working_account']['text_prefix'].encode()),
                rejection_delivered=True,joint_replacement_accepted=True)))
            adapter.preceding_feedback.clear()
            # Actual C04: restore the account in full at its real next-input size.
            c04=study.from_checkpoint('after/C03-O01')
            view=c04.view(); assert len(view['working_account']['text'].encode())==725
            store.put('C04-counterfactual-view.json',canonical_json_bytes(view))
            count=loop.measure(view); assert count<=23808
            # Actual implementation inspection followed by test imports must coexist.
            retained=study.from_checkpoint('after/C02-O02')
            retained.execute(dict(action='read',path=study.TEST,start_line=1,end_line=50),loop.measure)
            assert len(retained.view()['working_set']['sources'])==2
            store.put('retained-inspections-view.json',canonical_json_bytes(retained.view()))
            # Loop.execute owns the immutable starting snapshot.
            outcome=loop.execute(session)
            assert outcome['submitted']
            checks=[p['result'] for p in session.pairs[session.starting_archive_length:] if p['response']['action']=='check']
            assert [r['passed'] for r in checks]==[True,True]
            assert all(not r['payload'].get('completion_sent') for r in verify_records(folder/'records.jsonl',folder))
            assert study.source_identities()==bound
            study.save(folder,'RESULTS.json',dict(status='qualified_no_model_inference',counterfactual_account_tokens=count,
                retained_inspection_tokens=loop.measure(retained.view()),submitted=True,scripted_replies=loop.sent,
                new_checks=[dict(scope=r['check_id'],passed=r['passed'],observation=r['observation']) for r in checks],
                generated_tokens_not_measured=True,completion_requests_sent_to_runtime=0))
    except BaseException as error:
        study.save(folder,'FAILED.json',dict(type=type(error).__name__,message=str(error)))
        raise
    finally:
        study.save(folder,'CLOSURE.json',dict(port_free=RUNTIME.port_free(RUNTIME.PORT),memory=RUNTIME.memory_stats(folder/'memory.csv'),outcome=outcome))
        files=RUNTIME.file_inventory(folder)
        study.save(folder,'SEAL.json',dict(files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),source_sha256=bound,
            private_runtime_files_local_only={p.name:sha256_file(p) for p in (folder/'private-runtime').glob('*') if p.is_file()}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',default='qualification-001')
    run(study.AREA/p.parse_args().folder)
