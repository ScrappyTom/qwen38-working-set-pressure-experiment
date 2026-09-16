"""Replay the unmodified prefix, then execute only the actual public correction."""
import json
from types import SimpleNamespace

import reference_task as study
from manage import RUNTIME, legacy
import run_uncoached_contribution as runner
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore,verify_records
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.reference_session import ReferenceSession


def replay_prefix():
    folder=study.OLD
    seal=study.read(folder/'RESPONSE_SEAL.json')
    for row in seal['files']:
        assert sha256_file(folder/row['path'])==row['sha256'],row['path']
    records=verify_records(folder/'records.jsonl',folder)
    adapter=runner.Adapter(study.prior.Task(replay_folder=folder))
    session=adapter.initial_session();session.__class__=ReferenceSession
    counts={}
    for row in records:
        if row['record_type']=='native_input_prepared':
            stem=row['payload']['stem']
            request=study.read(folder/(stem+'-endpoint-request.json'))
            counts[sha256_bytes(canonical_json_bytes(request))]=row['payload']['prompt_tokens']
    def measure(view):
        return counts[sha256_bytes(canonical_json_bytes(adapter.request_for(view)))]
    for number in range(1,14):
        tag=f'C{number:02d}'
        view=session.view()
        assert completion_request_bytes(adapter.request_for(view))==(folder/f'calls/{tag}-wire-request.json').read_bytes()
        session.mark_delivered(view);session.begin_request()
        reply=study.read(folder/f'calls/{tag}-reply.json')
        def intermediate(n,operation):
            assert operation==study.read(folder/f'calls/{tag}-operation-{n:02d}.json')
            assert canonical_json_bytes(study.snapshot(session))==(folder/f'after/{tag}-O{n:02d}-state.json').read_bytes()
        result=adapter.process_reply(session,reply,measure,adapter.preceding_feedback,intermediate)
        assert result==study.read(folder/f'calls/{tag}-host-result.json')
    assert completion_request_bytes(adapter.request_for(session.view()))==(folder/'calls/C14-wire-request.json').read_bytes()
    return session,adapter


def run():
    folder=study.QUALIFIED;folder.mkdir(parents=True,exist_ok=False)
    bound=study.source_identities();store=ArtifactStore(folder)
    module=study.Task();log=legacy.QualificationLog(folder/'records.jsonl','reference-repair-qualification',task_module=module)
    error=None;results={}
    try:
        session,adapter=replay_prefix()
        results['prefix']=dict(replies_replayed=13,identical_wire_inputs=14,identical_results=True,
                              original_observations_replayed_not_executed=True)
        study.attach_observations(session,folder,log)
        server,model,_=study.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,source_check=lambda:study.verify_sources(bound))
            view=session.view();before=loop.measure(view)
            resolved=[]
            for source in view['working_set']['sources']:
                span=session.resolve_region(source['region_ref'])
                assert session.source(span)==source
                resolved.append(dict(reference=source['region_ref'],**span))
            results['all_displayed_references']=resolved
            # Full emitted final reply, not a frontier-authored patch or private draft.
            content=(study.OLD/'calls/C14-assistant-content.txt').read_bytes()
            store.put('public-C14-proposal.txt',content)
            reply=study.decode_reply(content.decode())
            assert reply==study.read(study.OLD/'calls/C14-reply.json')
            session.mark_delivered(view);session.begin_request()
            result=adapter.process_reply(session,reply,loop.measure,adapter.preceding_feedback)
            store.put('corrected-public-result.json',canonical_json_bytes(result))
            assert len(result['operations'])==3
            assert all(r['result']['accepted'] for r in result['operations']),result
            patch=result['operations'][1]['result'];check=result['operations'][2]['result']
            assert patch['supplied_boundary_separator']=='\n'
            assert patch['proposed_text_sha256']==sha256_bytes(reply['operation']['new'].encode())
            assert check['executed'] and check['passed'],check
            after=loop.measure(session.view());assert after<=23808
            for source in session.view()['working_set']['sources']:
                assert session.source(session.resolve_region(source['region_ref']))==source
            loop.snapshot(session,'corrected')
            store.put('corrected-view.json',canonical_json_bytes(session.view()))
            raw=json.loads((folder/'observations'/check['observation']/'stdout.bin').read_bytes())
            targets=[t for v in raw['fault_sensitivity'].values() for t in v['targets']]
            assert len(targets)==72 and all(t['detected'] for t in targets)
            assert raw['tests_passed']
            assert session.candidate.file_map[study.DOC]==study.prior.Task().initial_session().candidate.file_map[study.DOC]
            results.update(status='passed',before_tokens=before,after_tokens=after,
                corrected_candidate=session.candidate.candidate_id,observation=check['observation'],
                independent_faults_detected=len(targets),docs_unchanged=True,
                actual_public_reply_applied=True,completion_requests=0)
    except BaseException as exc:
        error=exc;study.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        study.save(folder,'RESULTS.json',results)
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    run()
