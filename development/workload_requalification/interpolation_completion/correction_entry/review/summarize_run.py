"""Post-closure accounting from exact requests, responses and recorded effects."""
from collections import Counter
import json
from pathlib import Path

AREA = Path(__file__).resolve().parents[1]
RUN, OUT = AREA/'run-001', AREA/'review/run-001'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


verified = read(OUT/'VERIFICATION.json')
seal = read(RUN/'RESPONSE_SEAL.json')
records = [json.loads(line) for line in (RUN/'records.jsonl').read_text(encoding='utf-8').splitlines()]
loop = next(r['payload'] for r in records if r['record_type'] == 'task_loop_completed')
counts, rows, rejected = Counter(), [], []
for endpoint in verified['endpoints']:
    call = endpoint['call']
    path = RUN/'calls'/f'{call}-host-result.json'
    host = read(path) if path.exists() else {'operations': []}
    operations = []
    for op in host['operations']:
        action, result = op['action'], op['result']
        counts[action['action']] += 1
        selected = {k:v for k,v in action.items() if k in
                    ('action','path','query','start_line','end_line','scope','candidate_id')}
        operations.append(dict(request=selected, accepted=result.get('accepted')))
        if result.get('accepted') is False:
            rejected.append(dict(call=call, request=selected, result=result))
    rows.append(dict(call=call, operations=operations, usage=endpoint['usage'],
        request_seconds=endpoint['request_seconds'], timings=endpoint['timings'],
        finish_reason=endpoint['finish_reason']))
save('DECISIONS_AND_COSTS.json', dict(
    classification='Actual emitted decisions and operations; no claim that every thinking token serves that operation',
    counts=dict(counts), rejected=rejected, calls=rows,
    recorded_task_loop_seconds=loop['task_loop_seconds'],
    audit_first_dispatch_to_last_completion_seconds=verified['task_loop_seconds'],
    response_processing_seconds=sum(r['payload']['processing_seconds'] for r in records if r['record_type']=='reply_processed'),
    native_prompt_seconds=sum(r['timings']['prompt_ms'] for r in rows)/1000,
    native_generation_seconds=sum(r['timings']['predicted_ms'] for r in rows)/1000))
prior = read(AREA.parent/'review/run-002/CUMULATIVE_COST.json')
save('CUMULATIVE_COST.json', dict(prior_interpolation_dispatched=64, prior_complete_responses=63,
    new_dispatched=verified['sent_requests'], new_complete_responses=len(rows),
    total_interpolation_dispatched=64+verified['sent_requests'],
    total_interpolation_complete_responses=63+len(rows),
    inherited_earlier_work_operations=55, prior_interpolation_operations=97,
    new_operations=verified['actual_operations'], cumulative_operations=seal['cumulative_operations'],
    total_interpolation_operations=97+verified['actual_operations'],
    known_model_request_seconds=prior['known_model_request_seconds']+verified['total_model_request_seconds'],
    known_input_tokens=prior['known_input_tokens']+verified['total_input_tokens'],
    known_generated_tokens=prior['known_generated_tokens']+verified['total_output_tokens'],
    excluded_unknown_cost='Original interpolation/run-002 C22 was dispatched without a preserved response or full cost; unknown is not zero.',
    development_cost='D1/D2 consultation, preparation, and review are additional, separately reported. Reviewer wall time was not independently metered.',
    earlier_work_model_calls='Outside this interpolation ledger; not asserted to be zero.'))
print(json.dumps(dict(counts=dict(counts), rejected=len(rejected), calls=len(rows),
    model_minutes=verified['total_model_request_seconds']/60,
    loop_minutes=loop['task_loop_seconds']/60)))
