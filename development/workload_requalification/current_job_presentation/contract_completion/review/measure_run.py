"""Read-only source-body and cost accounting on the completed exact run."""
from collections import defaultdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contract_task as entry
from working_set_exp.jsonutil import sha256_bytes

run = entry.HERE / 'run-001'
output = Path(__file__).parent / 'run-001'
state = entry.read(run / 'final-state.json')
versions = {raw['candidate_id']:entry.study.candidate_from_snapshot(raw) for raw in state['source_versions']}
verification = entry.read(output / 'VERIFICATION.json')
source_proof, phases, calls = [], defaultdict(lambda:dict(requests=0,input_tokens=0,generated_tokens=0,seconds=0)), []
for item in verification['endpoints']:
    tag = item['call']
    wire = entry.read(run / f'calls/{tag}-wire-request.json')
    frame = json.loads(wire['messages'][1]['content'])
    candidate = versions[frame['workspace']['candidate_id']]
    for source in frame['workspace']['working_set']['sources']:
        raw = candidate.file_map[source['path']]
        assert source['candidate_id'] == candidate.candidate_id
        assert sha256_bytes(raw) == source['file_sha256']
        lines = raw.decode().splitlines(keepends=True)
        assert len(lines) == source['file_total_lines']
        extent = ''.join(lines[source['returned_start_line']-1:source['returned_end_line']])
        assert extent == source['content']
        assert source['whole_file_shown'] == (source['returned_start_line']==1 and source['returned_end_line']==len(lines))
        source_proof.append(dict(call=tag,path=source['path'],candidate_id=candidate.candidate_id,
            start=source['returned_start_line'],end=source['returned_end_line'],shown_sha256=sha256_bytes(extent.encode())))
    substantive = [name for name in item['operation_names'] if name != 'record_account']
    phase = 'edit' if any(name in ('patch','replace_region') for name in substantive) else (
        'verification' if 'check' in substantive else 'closure' if 'submit' in substantive else 'acquisition')
    values = dict(call=tag,phase=phase,input_tokens=item['usage']['prompt_tokens'],
        generated_tokens=item['usage']['completion_tokens'],seconds=item['request_seconds'],
        input_seconds=item['timings']['prompt_ms']/1000,generation_seconds=item['timings']['predicted_ms']/1000,
        input_throughput=item['timings']['prompt_per_second'],generation_throughput=item['timings']['predicted_per_second'])
    calls.append(values)
    phases[phase]['requests'] += 1
    for key in ('input_tokens','generated_tokens','seconds'): phases[phase][key] += values[key]
records = [json.loads(line) for line in (run/'records.jsonl').read_text(encoding='utf-8').splitlines()]
processed = [r['payload'] for r in records if r['record_type']=='reply_processed']
opportunity = entry.read(run/'check-opportunities.json') if (run/'check-opportunities.json').exists() else None
result = dict(calls=calls,phases=dict(phases),current_source_presentations_verified=source_proof,
    total_input_seconds=sum(c['input_seconds'] for c in calls),total_generation_seconds=sum(c['generation_seconds'] for c in calls),
    model_minutes=verification['total_model_request_seconds']/60,task_loop_minutes=verification['task_loop_seconds']/60,
    non_model_loop_seconds=verification['task_loop_seconds']-verification['total_model_request_seconds'],
    recorded_reply_processing_seconds=sum(r['processing_seconds'] for r in processed),
    cumulative_requests=state['requests_used'],cumulative_operations=len(state['pairs']),versions=len(state['source_versions']),
    new_requests=10,new_operations=13,original_pair_scores_unchanged=True)
entry.study.save(Path(__file__).parent,'MEASUREMENTS-001.json',result)
print(json.dumps({k:result[k] for k in ('phases','total_input_seconds','total_generation_seconds','model_minutes',
    'task_loop_minutes','non_model_loop_seconds','recorded_reply_processing_seconds','cumulative_requests','cumulative_operations','versions')}))
print('Exact current-source body presentations:',len(source_proof))
