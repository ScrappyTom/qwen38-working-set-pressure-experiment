"""Read-only accounting after verify_run; emitted action is not a thought taxonomy."""
from collections import Counter
import ast
import difflib
import json
from pathlib import Path

AREA = Path(__file__).resolve().parents[1]
RUN = AREA / 'run-002'
OUT = AREA / 'review/run-002'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


verified = read(OUT / 'VERIFICATION.json')
seal = read(RUN / 'RESPONSE_SEAL.json')
counts, rejected, rows = Counter(), [], []
records = [json.loads(line) for line in (RUN / 'records.jsonl').read_text(encoding='utf-8').splitlines()]
loop = next(r['payload'] for r in records if r['record_type'] == 'task_loop_completed')
for row in verified['endpoints']:
    path = RUN / 'calls' / (row['call'] + '-host-result.json')
    host = read(path) if path.exists() else {'operations': []}
    operations = []
    for op in host['operations']:
        action, result = op['action'], op['result']
        counts[action['action']] += 1
        selected = {k: v for k, v in action.items()
                    if k in ('action', 'path', 'query', 'start_line', 'end_line', 'offset', 'limit', 'sources', 'results')}
        operations.append(dict(request=selected, accepted=result.get('accepted')))
        if result.get('accepted') is False:
            rejected.append(dict(call=row['call'], request=selected, result=result))
    rows.append(dict(call=row['call'], operations=operations, usage=row['usage'],
                     request_seconds=row['request_seconds'], timings=row['timings'],
                     finish_reason=row['finish_reason']))
save('DECISIONS_AND_COSTS.json', dict(classification='Actual operations, not a classification of every thought token',
    counts=dict(counts), rejected=rejected, calls=rows,
    recorded_task_loop_seconds=loop['task_loop_seconds'],
    audit_first_dispatch_to_last_completion_seconds=verified['task_loop_seconds'],
    response_processing_seconds=sum(r['payload']['processing_seconds'] for r in records if r['record_type']=='reply_processed'),
    native_prompt_seconds=sum(r['timings']['prompt_ms'] for r in rows)/1000,
    native_generation_seconds=sum(r['timings']['predicted_ms'] for r in rows)/1000))

final_path = RUN / 'final-candidate.json'
if not final_path.exists():
    final_path = RUN / 'stopped-candidate.json'
starting, final = read(RUN / 'starting-candidate.json'), read(final_path)
before = {r['path']: r['content_utf8'] for r in starting['files']}
after = {r['path']: r['content_utf8'] for r in final['files']}
changed = [p for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)]
diff = ''.join(''.join(difflib.unified_diff(before.get(p, '').splitlines(keepends=True),
    after.get(p, '').splitlines(keepends=True), fromfile='a/' + p, tofile='b/' + p)) for p in changed)
(OUT / 'saved-contribution.patch').write_text(diff, encoding='utf-8')
test = 'Lib/test/test_configparser.py'
tree_before, tree_after = ast.parse(before[test]), ast.parse(after[test])
added = [n for n in tree_after.body if isinstance(n, ast.ClassDef)
         and n.name == 'InterpolationMissingOptionErrorTransportTestCase']
assert len(added) == 1
tree_after.body.remove(added[0])
assert ast.dump(tree_before, include_attributes=False) == ast.dump(tree_after, include_attributes=False)
save('ARTIFACT_COMPARISON.json', dict(initial_candidate=starting['candidate_id'],
    final_candidate=final['candidate_id'], changed=changed,
    original_test_module_ast_preserved=True, added_class=added[0].name,
    new_test_methods=[n.name for n in added[0].body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')],
    unchanged=[p for p in sorted(before) if p in after and before[p] == after[p]]))

prior = read(AREA.parent / 'interpolation_revision/review/CUMULATIVE_COST.json')
save('CUMULATIVE_COST.json', dict(prior_interpolation_dispatched=32, prior_complete_responses=31,
    new_dispatched=verified['sent_requests'], new_complete_responses=len(rows),
    total_interpolation_dispatched=32 + verified['sent_requests'],
    inherited_earlier_work_operations=55, prior_interpolation_operations=46,
    new_operations=verified['actual_operations'], cumulative_operations=seal['cumulative_operations'],
    known_model_request_seconds=prior['known_completed_request_seconds'] + verified['total_model_request_seconds'],
    known_input_tokens=prior['prior_completed_prompt_tokens'] + prior['new_prompt_tokens'] + verified['total_input_tokens'],
    known_generated_tokens=prior['known_generated_tokens'] + verified['total_output_tokens'],
    excluded_unknown_cost='Original interpolation/run-002 C22 was dispatched without a preserved response or full cost.',
    earlier_work_model_calls='Not included in this interpolation dispatch ledger; not asserted to be zero.',
    development_and_review_cost='Preparation and review are additional; reviewer wall time was not independently metered.'))
print(json.dumps(dict(counts=dict(counts), rejected=len(rejected), changed=changed)))
