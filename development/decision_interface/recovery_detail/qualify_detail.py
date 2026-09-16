"""Actual C05 replay and native control/selection path, with zero model calls."""
import json
from pathlib import Path
from types import SimpleNamespace

import reference_task as prior
import run_uncoached_contribution as runner
from manage import RUNTIME,legacy
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore,verify_records
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file
from working_set_exp.recovery_detail_session import RecoveryDetailSession

AREA=Path(__file__).resolve().parent


def snapshot(session):
    return {**prior.snapshot(session),'restored_control_fields':list(session.restored_control_fields)}


def main():
    folder=AREA/'qualification-001';folder.mkdir(parents=True,exist_ok=False)
    paths=[Path(__file__),AREA/'PLAN.md',prior.ROOT/'src/working_set_exp/recovery_detail_session.py',
           prior.ROOT/'tests/test_recovery_detail.py',prior.AREA/'run-001/RESPONSE_SEAL.json']
    bound={**prior.source_identities(),**{p.resolve().relative_to(prior.ROOT).as_posix():sha256_file(p) for p in paths}}
    store=ArtifactStore(folder);module=prior.Task()
    log=legacy.QualificationLog(folder/'records.jsonl','recovery-detail-qualification',task_module=module)
    session=prior.restore(module.RUN,'after/C04-O02');session.__class__=RecoveryDetailSession
    adapter=runner.Adapter(module)
    adapter.preceding_feedback=prior.read(module.RUN/'after/C04-O02-preceding-feedback.json')
    actual=(module.RUN/'calls/C05-wire-request.json').read_bytes()
    assert completion_request_bytes(adapter.request_for(session.view()))==actual
    results={};error=None
    try:
        server,model,_=prior.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,source_check=lambda:prior.verify_sources(bound))
            before=loop.measure(session.view());assert before==23798
            session.mark_delivered(session.view());session.begin_request()
            reply=prior.read(module.RUN/'calls/C05-reply.json')
            outcome=adapter.process_reply(session,reply,loop.measure,adapter.preceding_feedback)
            assert outcome==prior.read(module.RUN/'calls/C05-host-result.json')
            assert session.candidate.candidate_id==prior.read(module.RUN/'starting-state.json')['candidate_id']
            view=session.view();count=loop.measure(view)
            regions=view['latest_feedback']['result']['match_regions']
            assert len(regions)==2 and view['latest_feedback']['result']['match_count']==2
            assert view['working_account']['text']==reply['account']
            assert view['working_account']['text_complete'] and view['working_set']['sources']==[]
            assert count==6757
            store.put('corrected-view.json',canonical_json_bytes(view))
            store.put('corrected-state.json',canonical_json_bytes(snapshot(session)))
            store.put('unchanged-operation-outcomes.json',canonical_json_bytes(outcome))
            # Demonstrate an operable choice, not that Qwen chose it. No source or
            # documentation solution is supplied to the running/closed actor.
            session.mark_delivered(view);session.begin_request()
            chosen=regions[0]['region_ref']
            select=dict(action='work_on_exact',regions=[chosen],results=[])
            outcome=adapter.process_reply(session,dict(discussion='Researcher selection of the first returned address.',
                operation=select),loop.measure,adapter.preceding_feedback)
            assert all(r['result']['accepted'] for r in outcome['operations'])
            selected=session.view();after=loop.measure(selected)
            source,=selected['working_set']['sources']
            assert (source['returned_start_line'],source['returned_end_line'])==(133,137)
            assert source['region_ref']==chosen and not session.recovery
            session.mark_delivered(selected)
            store.put('selected-view.json',canonical_json_bytes(selected))
            store.put('selected-state.json',canonical_json_bytes(snapshot(session)))
            store.put('researcher-selection-result.json',canonical_json_bytes(outcome))
            results=dict(status='passed',actual_C05_wire_unchanged=True,actual_operations_unchanged=True,
                candidate_unchanged=True,initial_tokens=before,corrected_feedback_tokens=count,
                exact_match_addresses_delivered=2,complete_account_delivered=True,
                selected_tokens=after,selected_extent=[133,137],researcher_selected=True,
                completion_requests=0,checks_executed=0)
            assert not any(r['record_type']=='invocation_started' for r in verify_records(folder/'records.jsonl',folder))
    except BaseException as exc:
        error=exc;prior.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        prior.save(folder,'RESULTS.json',results)
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    main()
