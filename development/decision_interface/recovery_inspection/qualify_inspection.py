"""Native replay of the exact failed read and further bounded source inspection."""
import json
from pathlib import Path
from types import SimpleNamespace

import cycle_task as prior
import run_uncoached_contribution as runner
from manage import RUNTIME, legacy
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file
from working_set_exp.recovery_inspection_session import RecoveryInspectionSession

AREA = Path(__file__).resolve().parent


def snapshot(session):
    return {**prior.snapshot(session), 'parked_source_regions':list(session.parked_source_regions)}


def main():
    folder=AREA/'qualification-001'
    folder.mkdir(parents=True,exist_ok=False)
    paths=[Path(__file__),AREA/'PLAN.md',prior.ROOT/'src/working_set_exp/recovery_inspection_session.py',
           prior.ROOT/'tests/test_recovery_inspection.py',prior.AREA/'run-001/RESPONSE_SEAL.json']
    bound={**prior.source_identities(),**{p.relative_to(prior.ROOT).as_posix():sha256_file(p) for p in paths}}
    store=ArtifactStore(folder)
    module=prior.Task()
    log=legacy.QualificationLog(folder/'records.jsonl','recovery-inspection-qualification',task_module=module)
    session=module.initial_session()
    session.__class__=RecoveryInspectionSession
    adapter=runner.Adapter(module)
    actual=(module.RUN/'calls/C01-wire-request.json').read_bytes()
    assert completion_request_bytes(adapter.request_for(session.view()))==actual
    initial_candidate=session.candidate.candidate_id
    original_designations=list(session.ranges)
    error=None;results={}
    try:
        server,model,_=prior.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,
                source_check=lambda:prior.verify_sources(bound))
            assert loop.measure(session.view())==6656
            session.mark_delivered(session.view());session.begin_request()
            reply=prior.read(module.RUN/'calls/C01-reply.json')
            outcome=adapter.process_reply(session,reply,loop.measure,adapter.preceding_feedback)
            assert outcome['operations'][0]['result']['accepted']
            assert session.ranges==original_designations
            view=session.view();count=loop.measure(view)
            source,=view['working_set']['sources']
            assert (source['returned_start_line'],source['returned_end_line'])==(125,145)
            assert source['path']=='Doc/library/urllib.parse.rst'
            assert view['presentation']['selected_bodies_omitted']
            assert session.candidate.candidate_id==initial_candidate
            for name,value in [('corrected-view.json',view),('corrected-state.json',snapshot(session)),
                               ('actual-C01-outcome.json',outcome)]:
                store.put(name,canonical_json_bytes(value))
            store.put('corrected-candidate.json',prior.candidate_bytes(session.candidate))
            first_ref=source['region_ref']
            # Researcher inspection of the second reported location is a host
            # path qualification, not a model-selected group or a live action.
            session.mark_delivered(view);session.begin_request()
            second=dict(discussion='Researcher qualification of the other reported location.',
                operation=dict(action='read',path=source['path'],start_line=315,end_line=333))
            outcome=adapter.process_reply(session,second,loop.measure,adapter.preceding_feedback)
            assert outcome['operations'][0]['result']['accepted']
            view=session.view();second_count=loop.measure(view)
            assert [(s['returned_start_line'],s['returned_end_line']) for s in view['working_set']['sources']]==[(125,145),(315,333)]
            store.put('comparison-view.json',canonical_json_bytes(view))
            store.put('comparison-state.json',canonical_json_bytes(snapshot(session)))
            session.mark_delivered(view);session.begin_request()
            overlap=dict(discussion='Researcher qualification of a contained reread.',
                operation=dict(action='read',path=source['path'],start_line=128,end_line=135))
            outcome=adapter.process_reply(session,overlap,loop.measure,adapter.preceding_feedback)
            assert outcome['operations'][0]['result']['accepted']
            view=session.view();overlap_count=loop.measure(view)
            assert [(s['returned_start_line'],s['returned_end_line']) for s in view['working_set']['sources']]==[(125,145),(315,333)]
            assert session.resolve_region(first_ref)==dict(path=source['path'],start_line=125,end_line=145)
            assert session.candidate.candidate_id==initial_candidate
            store.put('overlap-view.json',canonical_json_bytes(view))
            store.put('overlap-state.json',canonical_json_bytes(snapshot(session)))
            results=dict(status='passed',original_input_byte_identical=True,initial_tokens=6656,
                actual_C01_now_accepted=True,corrected_tokens=count,corrected_extent=[125,145],
                second_region_tokens=second_count,overlap_tokens=overlap_count,
                original_designations_preserved=True,candidate_unchanged=True,
                comparison_partner_preserved=True,no_duplicate_source_body=True,
                researcher_followup_inspections=2,completion_requests=0,checks_executed=0)
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
