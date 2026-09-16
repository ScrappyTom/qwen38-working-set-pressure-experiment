"""Post-run cost, presented-source, receipt-presence and artifact assessment.

Reads sealed evidence only. It executes neither the model nor the task checker.
Direct interpretation and prose review remain separate from these measurements.
"""
import ast
import csv
import difflib
import json
from hashlib import sha256
from pathlib import Path

AREA = Path(__file__).resolve().parents[1]
RUN = AREA / 'run-001'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def candidate(path):
    return {f['path']: f['content_utf8'] for f in read(path)['files']}


def methods(text):
    return {f'{c.name}.{n.name}': ast.get_source_segment(text, n)
            for c in ast.parse(text).body if isinstance(c, ast.ClassDef)
            for n in c.body if isinstance(n, ast.FunctionDef)}


def main():
    assert (RUN / 'RESPONSE_SEAL.json').exists(), 'review only after closure'
    records = [json.loads(line) for line in (RUN/'records.jsonl').read_text(encoding='utf-8').splitlines()]
    received = {r['payload']['id']: r['payload'] for r in records if r['record_type']=='response_received'}
    starts = {r['payload']['id']: r['payload'] for r in records if r['record_type']=='invocation_started'}
    snapshots = [RUN/'starting-candidate.json', *sorted((RUN/'after').glob('*-candidate.json'))]
    candidates = {read(p)['candidate_id']: candidate(p) for p in snapshots}
    calls, operations, deliveries, account_texts, literal_boundaries = [], [], [], [], []
    for wire in sorted((RUN/'calls').glob('*-wire-request.json')):
        tag = wire.name.split('-')[0]
        request = read(wire)
        user = json.loads(request['messages'][-1]['content'])
        view = user['workspace']
        visible = []
        for s in view['working_set']['sources']:
            full = candidates[s['candidate_id']][s['path']]
            assert sha256(full.encode()).hexdigest() == s['file_sha256']
            first, last = s['returned_start_line'], s['returned_end_line']
            assert s['content'] == ''.join(full.splitlines(True)[first-1:last]), (tag, s['path'])
            visible.append(dict(path=s['path'], first=first, last=last,
                                content_sha256=sha256(s['content'].encode()).hexdigest(),
                                file_sha256=s['file_sha256'], bytes=len(s['content'].encode())))
        row = dict(id=tag, input_tokens=starts[tag]['prompt_tokens'],
                   presentation=view['presentation'], visible_sources=visible,
                   account=view.get('working_account'), verification=view['verification'],
                   allowance=view['allowance'])
        reply_path=wire.with_name(tag+'-reply.json')
        if reply_path.exists():
            emitted=wire.with_name(tag+'-assistant-content.txt').read_bytes()
            op=(read(reply_path).get('operation') or {})
            if op.get('action')=='replace_region' and b'\nSOURCE\n' in emitted:
                body=emitted.split(b'\nSOURCE\n',1)[1]
                assert body==op['new'].encode(), 'literal decoder changed emitted source'
                original=next(s for s in view['working_set']['sources'] if s['region_ref']==op['region'])
                full=candidates[original['candidate_id']][original['path']]
                literal_boundaries.append(dict(id=tag,path=original['path'],
                    start=original['returned_start_line'],end=original['returned_end_line'],
                    total_file_lines=len(full.splitlines()),
                    original_extent_ends_lf=original['content'].endswith('\n'),
                    emitted_source_ends_lf=body.endswith(b'\n'),
                    emitted_source_bytes=len(body),emitted_source_sha256=sha256(body).hexdigest(),
                    exact_through_decoder=True))
        if tag in received:
            endpoint = read(wire.with_name(tag+'-endpoint-response.json'))
            choice = endpoint['choices'][0]
            row.update(usage=endpoint['usage'], elapsed_seconds=received[tag]['elapsed_seconds'],
                       finish_reason=choice['finish_reason'],
                       final_utf8_bytes=len((choice['message'].get('content') or '').encode()),
                       reasoning_utf8_bytes=len((choice['message'].get('reasoning_content') or '').encode()))
        calls.append(row)
        host_path = wire.with_name(tag+'-host-result.json')
        if not host_path.exists():
            continue
        following = wire.with_name(f'C{int(tag[1:])+1:02}-wire-request.json')
        receipts = None
        if following.exists():
            next_user = json.loads(read(following)['messages'][-1]['content'])
            rs = [*next_user.get('preceding_operation_feedback', []),
                  next_user['workspace']['latest_feedback']]
            receipts = {r['sequence']:r for r in rs if r}
        for number, op in enumerate(read(host_path)['operations'], 1):
            if op['action']['action']=='record_account':
                account_texts.append(op['action']['text'])
            state = read(RUN/f'after/{tag}-O{number:02}-state.json')
            seq = state['last']['sequence']
            result = op['result']
            operations.append(dict(id=tag, index=number, sequence=seq,
                                   origin=op['origin'], action=op['action']['action'],
                                   accepted=result.get('accepted'), passed=result.get('passed'),
                                   observation=result.get('observation')))
            receipts_present = seq in receipts if receipts is not None else None
            # Decision view intentionally relocates source bodies and derives check
            # assessments. Sequence presence is not a claim of raw-result identity.
            deliveries.append(dict(id=tag, index=number, sequence=seq,
                                   next_input_exists=receipts is not None,
                                   receipt_represented=receipts_present))
    ending = 'final' if (RUN/'final-candidate.json').exists() else 'stopped'
    before, after = candidate(RUN/'starting-candidate.json'), candidate(RUN/f'{ending}-candidate.json')
    assert before.keys() == after.keys()
    changed = [p for p in before if before[p] != after[p]]
    patch = ''.join(''.join(difflib.unified_diff(before[p].splitlines(True),after[p].splitlines(True),
                    fromfile='before/'+p,tofile='saved/'+p)) for p in changed)
    (AREA/'review/saved-contribution.patch').write_text(patch,encoding='utf-8')
    target='Lib/test/test_urlparse.py'
    old, new = methods(before[target]), methods(after[target])
    artifact = dict(changed_files=changed, preserved_files=[p for p in before if p not in changed],
                    original_test_methods_unchanged=all(new.get(k)==v for k,v in old.items()),
                    added_test_methods=sorted(new.keys()-old.keys()),
                    final_candidate=read(RUN/f'{ending}-candidate.json')['candidate_id'])
    returned=[c for c in calls if 'usage' in c]
    with (RUN/'memory.csv').open(encoding='utf-8') as stream:
        memory_rows = list(csv.reader(stream))
    free_mib = [int(row[-1].strip()) for row in memory_rows if len(row)==5]
    total=dict(requests=len(calls),returned=len(returned),operations=len(operations),
               input_tokens=sum(c['input_tokens'] for c in calls),
               generated_tokens=sum(c['usage']['completion_tokens'] for c in returned),
               request_seconds=sum(c['elapsed_seconds'] for c in returned),
               peak_input=max(c['input_tokens'] for c in calls),
               peak_input_plus_output=max(c['usage']['total_tokens'] for c in returned),
               processing_seconds=sum(r['payload']['processing_seconds'] for r in records if r['record_type']=='reply_processed'),
               account_updates=len(account_texts), unique_account_texts=len(set(account_texts)),
               unchanged_account_updates=sum(a==b for a,b in zip(account_texts,account_texts[1:])),
               minimum_sampled_free_mib=min(free_mib),memory_samples=len(free_mib))
    output=dict(evidence_scope=__doc__,totals=total,calls=calls,operations=operations,
                delivery=deliveries,artifact=artifact,literal_boundaries=literal_boundaries,
                closure=[r['payload'] for r in records if r['record_type'] in ('task_loop_completed','attempt_stopped','runtime_closed')])
    (AREA/'review/ASSESSMENT.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(total,indent=2))
    print('Receipt delivery exceptions:',[d for d in deliveries if d['next_input_exists'] and not d['receipt_represented']])
    print(json.dumps(artifact,indent=2))


if __name__ == '__main__':
    main()
