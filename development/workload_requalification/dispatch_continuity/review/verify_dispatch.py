"""Post-seal exact custody, checkpoints, delivery and endpoint accounting."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bootstrap
import dispatch_task as study
from working_set_exp.decision_view import receipt_view
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file


def verify(module, output):
    folder = module.RUN
    seal = study.read(folder/'RESPONSE_SEAL.json')
    assert seal['actor'] == module.ACTOR and seal['port_free']
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    for row in seal['files']:
        raw = (folder/row['path']).read_bytes()
        assert len(raw) == row['size_bytes'] and sha256_bytes(raw) == row['sha256'],row['path']
    module.verify_sources(seal['source_sha256'])
    records = verify_records(folder/'records.jsonl',folder)
    assert len(records) == seal['record_count']
    received = {r['payload']['id']:r['payload']['elapsed_seconds']
                for r in records if r['record_type']=='response_received'}
    checkpoints = []
    for path in sorted(folder.rglob('*-state.json')):
        if not path.relative_to(folder).as_posix().startswith(('after/','starting','final','stopped')): continue
        candidate_path = path.with_name(path.name.replace('-state.json','-candidate.json'))
        state,candidate = study.read(path),study.read(candidate_path)
        restored = module.restore(state,candidate,folder,replay=True)
        assert canonical_json_bytes(module.snapshot(restored)) == path.read_bytes()
        checkpoints.append(path.relative_to(folder).as_posix())
    endpoints = []
    calls = sorted((folder/'calls').glob('*-endpoint-response.json'))
    feedback_delivery = []
    sequence = module.INHERITED_OPERATIONS
    for index,path in enumerate(calls):
        tag = path.name.split('-')[0]
        response = study.read(path)
        thinking = response['choices'][0]['message'].get('reasoning_content') or ''
        content = response['choices'][0]['message'].get('content') or ''
        assert (folder/f'calls/{tag}-assistant-reasoning.txt').read_bytes()==thinking.encode()
        assert (folder/f'calls/{tag}-assistant-content.txt').read_bytes()==content.encode()
        request = study.read(folder/f'calls/{tag}-wire-request.json')
        assert request['seed']==module.SEED and request['chat_template_kwargs']==dict(enable_thinking=True,reasoning_effort='medium')
        frame = json.loads(request['messages'][1]['content'])
        host_path = folder/f'calls/{tag}-host-result.json'
        if host_path.exists():
            reply = study.decode_reply(content)
            assert canonical_json_bytes(reply)==(folder/f'calls/{tag}-reply.json').read_bytes()
            host = study.read(host_path)
        else:
            # An empty or unfinished final remains an observation. Never parse
            # private thinking as work or manufacture an executed operation.
            assert seal['disposition']=='stopped_without_retry'
            assert index==len(calls)-1
            host = dict(operations=[])
        operation_sequences = []
        for operation in host['operations']:
            sequence += 1
            operation_sequences.append(sequence)
            checkpoint = study.read(folder/f'after/{tag}-O{len(operation_sequences):02d}-state.json')
            pair = checkpoint['pairs'][sequence-1]
            assert canonical_json_bytes(pair['response']) == canonical_json_bytes(operation['action'])
            assert canonical_json_bytes(pair['result']) == canonical_json_bytes(operation['result'])
        if index+1 < len(calls):
            next_tag = calls[index+1].name.split('-')[0]
            following = study.read(folder/f'calls/{next_tag}-wire-request.json')
            next_frame = json.loads(following['messages'][1]['content'])
            delivered = {r['sequence']:r for r in next_frame['preceding_operation_feedback']}
            latest = next_frame['workspace']['latest_feedback']
            if latest: delivered[latest['sequence']]=latest
            for operation,operation_sequence in zip(host['operations'],operation_sequences):
                assert operation_sequence in delivered,(tag,operation_sequence)
                shown = delivered[operation_sequence]
                expected = receipt_view(dict(sequence=operation_sequence,
                    action_summary=shown['action_summary'],result=operation['result']))
                # Accepted edit diffs have a separately bounded presentation;
                # source custody and original RES bytes remain exact.
                applied = expected['result'].pop('applied_diff', None)
                detail = shown.get('applied_change')
                if detail is not None:
                    assert applied is not None
                    assert detail['sha256']==sha256_bytes(applied.encode())
                    assert detail['byte_count']==len(applied.encode())
                    if detail['detail_status']=='complete_applied_diff':
                        assert detail['diff_utf8']==applied
                assert canonical_json_bytes(shown['result']) == canonical_json_bytes(expected['result']),(tag,operation_sequence)
                assert shown['action_summary']['action'] == operation['action']['action']
                acquired = ([operation['result']['source']] if 'source' in operation['result']
                            else operation['result'].get('sources', []))
                for source in acquired:
                    matching = [s for s in next_frame['workspace']['working_set']['sources']
                        if s['path']==source['path'] and s['file_sha256']==source['file_sha256']
                        and s['returned_start_line']<=source['returned_start_line']
                        and s['returned_end_line']>=source['returned_end_line']]
                    assert matching,(tag,source['path'])
                    current = matching[0]
                    first=source['returned_start_line']-current['returned_start_line']
                    count=source['returned_end_line']-source['returned_start_line']+1
                    excerpt=''.join(current['content'].splitlines(keepends=True)[first:first+count])
                    assert excerpt.encode()==source['content'].encode(),(tag,source['path'])
                feedback_delivery.append(dict(call=tag,operation_sequence=operation_sequence,following_call=next_tag))
        usage = response['usage'];timings = response.get('timings',{})
        endpoints.append(dict(call=tag,usage=usage,timings=timings,
            request_seconds=received[tag],finish_reason=response['choices'][0]['finish_reason'],
            host_processed=host_path.exists(),
            operation_names=[op['action']['action'] for op in host['operations']],
            sources=[{k:s[k] for k in ('path','returned_start_line','returned_end_line','file_sha256')}
                     for s in frame['workspace']['working_set']['sources']],
            account=frame['workspace']['working_account']))
    assert sequence == seal['cumulative_operations']
    first = next(r for r in records if r['record_type']=='invocation_started')
    last = next(r for r in reversed(records) if r['record_type'] in ('invocation_completed','attempt_stopped'))
    loop_seconds = (datetime.fromisoformat(last['created_at_utc'])-
                    datetime.fromisoformat(first['created_at_utc'])).total_seconds()
    result = dict(exact_artifacts=len(seal['files']),source_bindings=len(seal['source_sha256']),
        custody_records=len(records),checkpoints=checkpoints,feedback_delivery=feedback_delivery,
        endpoints=endpoints,disposition=seal['disposition'],sent_requests=seal['sent_requests'],
        actual_operations=seal['actual_operations'],memory=seal['memory'],port_free=seal['port_free'],
        runtime=seal['runtime'],task_loop_seconds=loop_seconds,
        total_model_request_seconds=sum(row['request_seconds'] for row in endpoints),
        total_input_tokens=sum(row['usage']['prompt_tokens'] for row in endpoints),
        total_output_tokens=sum(row['usage']['completion_tokens'] for row in endpoints),
        maximum_input_tokens=max(row['usage']['prompt_tokens'] for row in endpoints),
        maximum_combined_tokens=max(row['usage']['total_tokens'] for row in endpoints))
    study.save(output,'VERIFICATION.json',result)
    print(json.dumps({k:result[k] for k in ('disposition','sent_requests','actual_operations','exact_artifacts','source_bindings','custody_records','total_input_tokens','total_output_tokens','maximum_input_tokens','maximum_combined_tokens')}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',default='union');parser.add_argument('--version',default='002')
    parser.add_argument('--inherited');parser.add_argument('--output',required=True);args=parser.parse_args()
    if args.phase == 'dynamic':
        sys.path.insert(0,str(study.AREA/'dynamic'))
        from run_saved_dispatch import Task
    else:
        Task = study.Task
    verify(Task(args.phase,args.version,args.inherited),Path(args.output))
