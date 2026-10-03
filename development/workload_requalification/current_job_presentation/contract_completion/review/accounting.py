"""Verify cumulative and job-relative opportunity without changing sealed records."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contract_task as entry
from working_set_exp.measurement import check_opportunities

task = entry.Task('001')
records = [json.loads(line) for line in (task.RUN/'records.jsonl').read_text(encoding='utf-8').splitlines()]
job = next(r['payload'] for r in records if r['record_type']=='job_accounting')
closed = next(r['payload'] for r in records if r['record_type']=='task_loop_completed')
state = entry.read(task.RUN/'final-state.json')
assert (job['inherited_requests'],job['inherited_operations'],job['additional_request_limit'],job['additional_operation_limit']) == (47,77,12,36)
assert closed['sent_requests'] == state['requests_used'] == 57
assert closed['actual_operations'] == len(state['pairs']) == 90
checks = [r for r in check_opportunities(state['pairs'],call_limit=113) if r['sequence'] > 77]
assert len(checks) == 1
expected = checks[0]
actual = closed['check_opportunities'][0]
assert expected['sequence'] == actual['sequence'] == 88 and actual['job_sequence'] == 11
assert actual['calls_remaining_before'] == expected['calls_remaining_before'] == 26
assert actual['calls_remaining_after'] == expected['calls_remaining_after'] == 25
assert actual['first_check'] and actual['passed']
result = dict(job=job,recorded_check_opportunities=closed['check_opportunities'],
    cumulative_requests=57,cumulative_operations=90,new_requests=10,new_operations=13,
    actual_remaining_requests=2,actual_remaining_operations=23,
    runner_task_loop_seconds=closed['task_loop_seconds'],
    basis='Cumulative limits agree with complete archived history; separate new-job indices and first-check status.',
    sealed_records_unchanged=True)
entry.study.save(Path(__file__).parent,'ACCOUNTING-001.json',result)
print(json.dumps(result))
