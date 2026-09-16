"""Native saved-state information paths and scripted complete work; no inference."""
import argparse
import copy
import json
from types import SimpleNamespace

import feedback_task as study
from manage import RUNTIME, legacy
import run_uncoached_contribution as runner
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file


def run(folder):
    folder.mkdir(parents=True,exist_ok=False)
    bound=study.source_identities()
    store=ArtifactStore(folder)
    module=study.Task()
    adapter=runner.Adapter(module)
    log=legacy.QualificationLog(folder/'records.jsonl','feedback-path-qualification',task_module=module)
    server,model,_=study.runtime_paths()
    results={}
    error=None
    try:
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,source_check=lambda:study.verify_sources(bound))
            def save_view(name,session):
                assert session._fits_feedback(loop.measure),name
                view=session.view();count=loop.measure(view)
                assert count<=23808
                store.put(name+'-view.json',canonical_json_bytes(view))
                results[name]=dict(tokens=count,mode=view['presentation']['mode'])
                session.mark_delivered(view)
                return view

            # Same preserved observation and candidate; only derived presentation
            # changes. The original report/result bytes are never rewritten.
            s=study.from_checkpoint('after/C05-O03',legacy_checks=True)
            view=save_view('C06-primary-failure',s)
            report=view['latest_feedback']['result']['report']
            rows={r['criterion']:r for r in report['criteria']}
            assert 'ValueError not raised' in rows['edited_suite.execution']['diagnostics'][0]['diagnostic']['text']
            assert rows['required_paths']['missing_paths_total']==17
            assert all(r['fault_detected'] is None for r in report['criteria'] if r['criterion'].startswith('detect.'))

            s=study.from_checkpoint('after/C12-O02',legacy_checks=True)
            save_view('C13-crowded-before',s)
            op=study.read(study.OLD/'calls/C13-reply.json')['operation']
            rejected=s.execute(op,loop.measure)
            assert not rejected['accepted'] and rejected['match_count']==2
            assert [r['start_line'] for r in rejected['match_regions']]==[133,319]
            view=save_view('C13-duplicate-rejection',s)
            assert view['latest_feedback']['result']['match_count']==2
            assert len(view['latest_feedback']['result']['match_regions'])==2
            # Mechanical fixture chooses the first returned address. It does not
            # infer which occurrence the actor wants or receive hidden coordinates.
            region=view['latest_feedback']['result']['match_regions'][0]['region_ref']
            s.execute(dict(action='work_on_exact',regions=[region],results=[]),loop.measure)
            view=save_view('C13-selected-returned-region',s)
            source,=view['working_set']['sources']
            assert source['returned_start_line']==133 and not source['whole_file_shown']
            original=s.candidate.file_map[study.DOC]
            text=source['content']+'\n   Qualification-only inserted line.\n'
            header=dict(discussion='Scripted boundary fixture, not actor work.',operation=dict(
                action='replace_region',region=source['region_ref'],expected_candidate_id=s.candidate.candidate_id))
            reply=study.decode_reply(json.dumps(header)+'\nSOURCE\n'+text.rstrip('\n'))
            r=s.execute(reply['operation'],loop.measure)
            assert r['accepted'] and r['supplied_boundary_separator']=='\n'
            assert s.pairs[-1]['response']['new']==text.rstrip('\n')
            save_view('C13-boundary-applied',s)
            assert original.splitlines(True)[source['returned_end_line']:] == s.candidate.file_map[study.DOC].splitlines(True)[source['returned_end_line']+2:]

            # Apply the actual terminal proposal: the repaired boundary retains
            # LF, but its separate paragraph rewrite still violates preservation.
            s=study.from_checkpoint('after/C15-O02',legacy_checks=True)
            save_view('C16-before',s)
            proposal=study.read(study.OLD/'calls/C16-reply.json')['operation']
            r=s.execute(proposal,loop.measure)
            assert r['accepted'] and r['supplied_boundary_separator']=='\n'
            assert b'A true value\n   indicates' in s.candidate.file_map[study.DOC]
            save_view('C16-boundary-corrected',s)

            # Complete contribution fixture through the same operations/checks.
            # The code/prose are explicitly researcher authored. Source coordinates
            # and insertion authority are acquired through actual returned matches.
            s=module.initial_session();study.attach_observations(s,folder,log)
            save_view('contribution-start',s)
            def operate(action):
                result=adapter.process_reply(s,dict(discussion='Researcher-authored engineering qualification.',operation=action),
                    loop.measure,adapter.preceding_feedback)
                assert all(o['result']['accepted'] for o in result['operations']),result
                return result
            for path,query,reference in (
                (study.TEST,'if __name__',study.ROOT/'development/working_account/url_ports/REFERENCE_TEST.py'),
                (study.DOC,'URL Parsing',study.ROOT/'development/working_account/url_ports/REFERENCE_DOC.txt')):
                operate(dict(action='search',path=path,query=query,offset=0,limit=8))
                view=save_view('test-search' if path==study.TEST else 'doc-search',s)
                result=view['latest_feedback']['result']
                match=next(m for m in result['matches'] if path==study.TEST or m['text']=='URL Parsing')
                region=next(r for r in result['regions'] if r.get('match_line')==match['line'])
                operate(dict(action='work_on_exact',regions=[region['region_ref']],results=[]))
                view=save_view('test-source' if path==study.TEST else 'doc-source',s)
                source,=view['working_set']['sources']
                anchor='if __name__ == "__main__":\n    unittest.main()\n' if path==study.TEST else 'URL Parsing\n-----------\n'
                assert anchor in source['content']
                code=reference.read_text(encoding='utf-8')+'\n'
                operate(dict(action='replace_region',region=source['region_ref'],expected_candidate_id=s.candidate.candidate_id,
                    new=source['content'].replace(anchor,code+anchor,1)))
                view=save_view('tests-passed' if path==study.TEST else 'public-passed',s)
                check=view['verification']['checks']['tests' if path==study.TEST else 'public']
                assert check['passed'] and check['applies_to_current'],check
            operate(dict(action='submit',expected_candidate_id=s.candidate.candidate_id))
            assert s.submitted
            store.put('contribution-final-candidate.json',study.candidate_bytes(s.candidate))
            store.put('contribution-final-state.json',canonical_json_bytes(study.snapshot(s)))
            assert all(not r['payload'].get('completion_sent') for r in verify_records(folder/'records.jsonl',folder))
            assert bound==study.source_identities()
            study.save(folder,'RESULTS.json',dict(status='passed',completion_requests=0,counterfactuals=results,
                scripted_contribution_submitted=s.submitted,information_source='actual returned addresses; researcher-authored contribution',
                correction_does_not_repair_original_prose=True))
    except BaseException as problem:
        error=problem
        study.save(folder,'FAILED.json',dict(type=type(problem).__name__,message=str(problem)))
    finally:
        study.save(folder,'CLOSURE.json',dict(port_free=RUNTIME.port_free(RUNTIME.PORT),memory=RUNTIME.memory_stats(folder/'memory.csv')))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--folder',default='qualification-001')
    run(study.AREA/parser.parse_args().folder)
