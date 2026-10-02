"""Saved-only replay/accounting of one closed branch; no model or check execution."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bootstrap
import transition_task as study
import run_transition as controller
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

HELPER=study.ROOT/'development/workload_requalification/ecological_contract_continuation/review/verify_run.py'
spec=importlib.util.spec_from_file_location('transition_saved_replay_helpers',HELPER)
core=importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
core.study=study
core.INHERITED_REQUESTS,core.INHERITED_OPERATIONS=16,24

def verify_and_measure(condition,version='001'):
    module=study.Task(condition,version)
    run=module.RUN
    seal=study.read(run/'RESPONSE_SEAL.json')
    core._inventory(run,seal)
    manifest=controller.verify_preparation(module)
    assert manifest['source_sha256']==seal['source_sha256']
    assert manifest['source_sha256'][HELPER.relative_to(study.ROOT).as_posix()]==sha256_file(HELPER)
    assert (run/'EXECUTION_MANIFEST.json').read_bytes()==module.MANIFEST.read_bytes()
    assert (run/'calls/C17-wire-request.json').read_bytes()==(module.PACKAGE/'initial-wire-request.json').read_bytes()
    records=verify_records(run/'records.jsonl',run)
    assert len(records)==seal['record_count']
    replay=study.Task(condition,version,replay_folder=run)
    session,adapter=replay.initial_session(),controller.Adapter(replay)
    counts=core._native_counts(run,records,adapter)
    controller.declared_entry(replay,session)
    starts=[r for r in records if r['record_type']=='invocation_started']
    assert [r['payload']['id'] for r in starts]==[f'C{i:02d}' for i in range(17,17+len(starts))]
    replayed,states,operations,delivery=[],[],[],[]
    def measure(view):
        key=sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
        assert key in counts,'Actual replay requires an absent native measurement'
        return counts[key]
    def checkpoint(stem):
        raw=canonical_json_bytes(module.snapshot(session))
        assert raw==(run/(stem+'-state.json')).read_bytes(),stem
        assert module.candidate_bytes(session.candidate)==(run/(stem+'-candidate.json')).read_bytes(),stem
        assert canonical_json_bytes(adapter.preceding_feedback)==(run/(stem+'-preceding-feedback.json')).read_bytes(),stem
        restored=module.restore(study.load_json_strict(raw),session.candidate,run,replay=True)
        assert module.snapshot(restored)==module.snapshot(session)
        assert restored.view()==session.view()
        for number in range(1,len(session.pairs)+1):
            for prefix in ('RES','EVT'):
                assert restored.payload(f'{prefix}-{number:04d}')==session.payload(f'{prefix}-{number:04d}')
        states.append(stem)
    checkpoint('starting')
    with patch('working_set_exp.observations.subprocess.Popen',side_effect=AssertionError('Replay executes no subprocess')):
        for started in starts:
            row=started['payload']
            tag=row['id']
            request=adapter.request_for(session.view())
            assert completion_request_bytes(request)==(run/f'calls/{tag}-wire-request.json').read_bytes()
            assert row['prompt_tokens']==measure(session.view())
            # Receipt delivery is measured on actual following dispatch, not prepared feedback.
            shown=study.load_json_strict(request['messages'][1]['content'])
            delivery.append(dict(id=tag,latest_sequence=(shown['workspace']['latest_feedback'] or {}).get('sequence'),
                companion_sequences=[p['sequence'] for p in shown['preceding_operation_feedback']]))
            session.mark_delivered(session.view())
            session.begin_request()
            reply,reason=core._response(module,run,tag,row['prompt_tokens'],seal['disposition']=='stopped_without_retry')
            if reply is None:
                replayed.append(dict(id=tag,incomplete=reason))
                continue
            def record(number,operation):
                assert canonical_json_bytes(operation)==(run/f'calls/{tag}-operation-{number:02d}.json').read_bytes()
                operations.append(dict(id=tag,number=number,origin=operation['origin'],
                    action=operation['action']['action'],accepted=operation['result'].get('accepted')))
                checkpoint(f'after/{tag}-O{number:02d}')
            outcome=module.process_reply(session,reply,measure,adapter.preceding_feedback,record)
            assert canonical_json_bytes(outcome)==(run/f'calls/{tag}-host-result.json').read_bytes()
            replayed.append(dict(id=tag,operations=len(outcome['operations']),following_input_tokens=measure(session.view())))
    checkpoint('stopped' if seal['disposition']=='stopped_without_retry' else 'final')
    witnesses=core._coverage_wires(module,session)
    assert len(operations)==seal['new_operations']
    assert len(starts)==seal['sent_requests'] and session.requests_used==seal['cumulative_requests_used']
    assert session.calls_used==seal['actual_operations']
    proof=dict(status='replayed_exactly',condition=condition,fresh_original_entry=False,
        response_seal_sha256=sha256_file(run/'RESPONSE_SEAL.json'),records_sha256=sha256_file(run/'records.jsonl'),
        inherited_requests=16,inherited_operations=24,new_requests=len(starts),new_operations=len(operations),
        cumulative_requests=session.requests_used,cumulative_operations=session.calls_used,
        final_candidate_id=session.candidate.candidate_id,submitted=session.submitted,
        checkpoints=states,native_inputs=len(counts),dispatched_coverage=witnesses,
        replayed=replayed,operations=operations,actual_delivery=delivery,
        verifier_sha256=sha256_file(Path(__file__)),helper_sha256=sha256_file(HELPER),
        checker_model_native_executions=0)
    calls=[]
    for row in starts:
        tag=row['payload']['id']
        response=run/f'calls/{tag}-endpoint-response.json'
        if response.exists():
            data=study.read(response)
            elapsed=next(r['payload']['elapsed_seconds'] for r in records
                if r['record_type']=='response_received' and r['payload']['id']==tag)
            calls.append(dict(id=tag,usage=data['usage'],timings=data['timings'],elapsed_seconds=elapsed))
        else:
            calls.append(dict(id=tag,usage=None,timings=None,elapsed_seconds=None))
    complete=[c for c in calls if c['usage'] is not None]
    loops=[r['payload'] for r in records if r['record_type']=='task_loop_completed']
    metrics=dict(status='recomputed_from_saved_endpoints',condition=condition,disposition=seal['disposition'],
        inherited_requests=16,inherited_operations=24,new_requests=len(starts),new_operations=len(operations),
        cumulative_requests=session.requests_used,cumulative_operations=session.calls_used,
        model_request_seconds=sum(c['elapsed_seconds'] for c in complete),
        input_tokens=sum(c['usage']['prompt_tokens'] for c in complete),
        generated_tokens=sum(c['usage']['completion_tokens'] for c in complete),
        prompt_processing_seconds=sum(c['timings']['prompt_ms'] for c in complete)/1000,
        generation_seconds=sum(c['timings']['predicted_ms'] for c in complete)/1000,
        peak_sent_input=max((r['payload']['prompt_tokens'] for r in starts),default=None),
        peak_input_plus_generation=max((c['usage']['total_tokens'] for c in complete),default=None),
        task_loop_seconds=loops[0]['task_loop_seconds'] if loops else None,
        final_candidate_id=session.candidate.candidate_id,submitted=session.submitted,memory=seal['memory'],
        calls=calls,no_causal_efficiency_or_account_benefit_claim=True)
    for name,value in (('VERIFICATION-'+condition+'-'+version+'.json',proof),
                       ('METRICS-'+condition+'-'+version+'.json',metrics)):
        path=Path(__file__).parent/name
        raw=canonical_json_bytes(value)
        if path.exists():
            assert path.read_bytes()==raw,'Preserve an earlier differing replay/accounting result'
        else:
            path.write_bytes(raw)
    return dict(condition=condition,status=proof['status'],new_requests=len(starts),new_operations=len(operations),
        submitted=session.submitted,candidate_id=session.candidate.candidate_id,model_seconds=metrics['model_request_seconds'])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--condition',choices=study.CONDITIONS,required=True)
    parser.add_argument('--version',default='001')
    args=parser.parse_args()
    print(json.dumps(verify_and_measure(args.condition,args.version)),flush=True)
