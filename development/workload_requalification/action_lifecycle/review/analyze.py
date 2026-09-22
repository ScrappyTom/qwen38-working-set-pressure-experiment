"""Exact replay and measurements for closed small-repair regressions.

No inference, tokenization or checker execution. Artifact meaning still requires
direct review; a valid host pass alone is not independent correctness evidence.
"""
import argparse
import collections
import csv
import difflib
import json
from pathlib import Path
from types import SimpleNamespace

import bootstrap
import continuation_task as study
from manage import load_helper
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    raw=canonical_json_bytes(value)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        assert path.read_bytes()==raw, 'Existing derived output differs: '+str(path)
    else:
        path.write_bytes(raw)


def candidate(path):
    value=read(path)
    return value['candidate_id'],{x['path']:x['content_utf8'] for x in value['files']}


def seal_count(run):
    return read(run/'RESPONSE_SEAL.json')['sent_requests']


def main(case,version):
    task=study.Task(version)
    area,run=task.AREA,task.RUN
    output=area/'review';output.mkdir(exist_ok=True)
    assert (run/'RESPONSE_SEAL.json').exists(), 'Do not assess an open run'
    replay=load_helper('small_repair_exact_replay','development/decision_interface/reference_repair/verify_reference.py')
    replay.study=SimpleNamespace(Task=lambda replay_folder:study.Task(version,replay_folder),
        read=read,verify_sources=task.verify_sources,decode_reply=task.decode_reply,
        candidate_bytes=task.candidate_bytes)
    verification=replay.verify(run)
    assert len(read(run/'starting-state.json')['pairs'])==5
    assert read(run/'starting-state.json')['requests_used']==5
    verification.update(case=case,inherited_operations=5,inherited_requests=5,
                        no_additional_checker_execution=True)
    save(output/'VERIFICATION.json',verification)

    records=[json.loads(x) for x in (run/'records.jsonl').read_text(encoding='utf-8').splitlines()]
    starts={r['payload']['id']:r['payload'] for r in records if r['record_type']=='invocation_started'}
    returned={r['payload']['id']:r['payload'] for r in records if r['record_type']=='response_received'}
    ending='final' if (run/'final-candidate.json').exists() else 'stopped'
    snapshots=[run/'starting-candidate.json',*sorted((run/'after').glob('*-candidate.json')),run/f'{ending}-candidate.json']
    candidates=dict(candidate(p) for p in snapshots)
    calls,operations,deliveries,literal=[],[],[],[]
    for wire in sorted((run/'calls').glob('*-wire-request.json')):
        tag=wire.name.split('-')[0];request=read(wire)
        user=json.loads(request['messages'][-1]['content']);view=user['workspace']
        sources=[]
        for s in view['working_set']['sources']:
            full=candidates[s['candidate_id']][s['path']]
            assert sha256_bytes(full.encode())==s['file_sha256']
            start,end=s['returned_start_line'],s['returned_end_line']
            assert s['content']==''.join(full.splitlines(True)[start-1:end]),(tag,s['path'])
            sources.append(dict(path=s['path'],start_line=start,end_line=end,
                content_sha256=sha256_bytes(s['content'].encode()),file_sha256=s['file_sha256']))
        row=dict(id=tag,input_tokens=starts[tag]['prompt_tokens'],candidate_id=view['candidate_id'],
            allowance=view['allowance'],presentation=view['presentation'],
            working_account=view.get('working_account'),verification=view['verification'],sources=sources)
        if tag in returned:
            response=read(run/f'calls/{tag}-endpoint-response.json');choice=response['choices'][0]
            row.update(usage=response['usage'],request_seconds=returned[tag]['elapsed_seconds'],
                finish_reason=choice['finish_reason'],
                final_utf8_bytes=len((choice['message'].get('content') or '').encode()),
                reasoning_utf8_bytes=len((choice['message'].get('reasoning_content') or '').encode()))
        reply_path=run/f'calls/{tag}-reply.json'
        if reply_path.exists():
            reply=read(reply_path);op=reply.get('operation') or {}
            emitted=(run/f'calls/{tag}-assistant-content.txt').read_bytes()
            if op.get('action')=='replace_region' and b'\nSOURCE\n' in emitted:
                body=emitted.split(b'\nSOURCE\n',1)[1]
                assert body==op['new'].encode()
                literal.append(dict(id=tag,bytes=len(body),sha256=sha256_bytes(body),
                                    emitted_source_ends_lf=body.endswith(b'\n')))
        calls.append(row)
        host_path=run/f'calls/{tag}-host-result.json'
        if not host_path.exists():continue
        following=run/f'calls/C{int(tag[1:])+1:02d}-wire-request.json'
        receipts=None
        if following.exists():
            u=json.loads(read(following)['messages'][-1]['content'])
            receipts={r['sequence']:r for r in [*u.get('preceding_operation_feedback',[]),u['workspace']['latest_feedback']] if r}
        for n,operation in enumerate(read(host_path)['operations'],1):
            state=read(run/f'after/{tag}-O{n:02d}-state.json');result=operation['result']
            sequence=state['last']['sequence']
            operations.append(dict(id=tag,index=n,sequence=sequence,action=operation['action'],origin=operation['origin'],
                accepted=result.get('accepted'),passed=result.get('passed'),observation=result.get('observation')))
            deliveries.append(dict(id=tag,index=n,sequence=sequence,next_input_exists=receipts is not None,
                receipt_represented=sequence in receipts if receipts is not None else None))
    start_id,before=candidate(run/'starting-candidate.json');end_id,after=candidate(run/f'{ending}-candidate.json')
    assert before.keys()==after.keys()
    changed=[p for p in before if before[p]!=after[p]]
    patch=''.join(''.join(difflib.unified_diff(before[p].splitlines(True),after[p].splitlines(True),
                fromfile='before/'+p,tofile='saved/'+p)) for p in changed)
    patch_path=output/'saved-contribution.patch'
    if patch_path.exists():assert patch_path.read_bytes()==patch.encode()
    else:patch_path.write_bytes(patch.encode())
    with (run/'memory.csv').open(encoding='utf-8') as f:
        free=[int(r[-1].strip()) for r in csv.reader(f) if len(r)==5]
    complete=[c for c in calls if 'usage' in c]
    closure=[r['payload'] for r in records if r['record_type'] in ('task_loop_completed','attempt_stopped','runtime_closed')]
    totals=dict(requests=len(calls),returned=len(complete),new_operations=len(operations),
        action_counts=dict(collections.Counter(x['action']['action'] for x in operations)),
        rejected_operations=sum(x['accepted'] is False for x in operations),
        input_tokens=sum(c['input_tokens'] for c in calls),
        generated_tokens=sum(c['usage']['completion_tokens'] for c in complete),
        request_seconds=sum(c['request_seconds'] for c in complete),
        peak_input=max((c['input_tokens'] for c in calls),default=0),
        peak_input_plus_generation=max((c['usage']['total_tokens'] for c in complete),default=0),
        processing_seconds=sum(r['payload']['processing_seconds'] for r in records if r['record_type']=='reply_processed'),
        minimum_sampled_free_mib=min(free),memory_samples=len(free),
        source_extents_verified=sum(len(c['sources']) for c in calls),
        nonterminal_receipts=sum(x['next_input_exists'] for x in deliveries),
        represented_nonterminal_receipts=sum(x['receipt_represented'] is True for x in deliveries))
    assert totals['new_operations']+5==verification['actual_operations']
    assert [c['id'] for c in calls]==[f'C{i:02d}' for i in range(6,6+len(calls))]
    account=[r['payload'] for r in records if r['record_type']=='continuation_accounting_closed']
    assert len(account)==1
    assert account[0]['new_dispatches']==totals['requests']==seal_count(run)
    assert account[0]['new_operations']==totals['new_operations']
    assert account[0]['cumulative_requests']==totals['requests']+5
    totals['inherited_requests']=5
    totals['inherited_operations']=5
    assessment=dict(case=case,run=run.name,totals=totals,calls=calls,operations=operations,delivery=deliveries,
        literal_source_replies=literal,closure=closure,artifact=dict(starting_candidate=start_id,final_candidate=end_id,
        changed_files=changed,unchanged_files=[p for p in before if p not in changed],
        independent_semantic_correctness='Requires direct source and artifact review; not inferred by this helper.'))
    save(output/'ASSESSMENT.json',assessment)
    save(output/'ANALYSIS_PROVENANCE.json',dict(case=case,version=version,
        analysis_source_sha256=sha256_file(Path(__file__)),
        replay_source_sha256=sha256_file(study.ROOT/'development/decision_interface/reference_repair/verify_reference.py'),
        adaptation='Bind the original exact-replay verifier to repair_task.Task(case,version,replay_folder). Cumulative receipt counters retain five inherited requests and operations; new metrics cover this continuation only.',
        model_requests=0,checker_executions=0,tokenizer_requests=0))
    print(json.dumps(dict(verification=verification,totals=totals,artifact=assessment['artifact']),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('case',choices=('receipts',));parser.add_argument('--version',default='001')
    args=parser.parse_args();main(args.case,args.version)
