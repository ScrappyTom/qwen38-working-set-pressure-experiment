"""Correct derived opportunity counts without altering sealed execution records."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import overlap_task as entry
from working_set_exp.measurement import check_opportunity


def supplement(condition, version):
    task = entry.Task(condition, version)
    seal = entry.read(task.RUN / 'RESPONSE_SEAL.json')
    stem = 'stopped' if seal['disposition'] == 'stopped_without_retry' else 'final'
    state = entry.read(task.RUN / f'{stem}-state.json')
    pairs = state['pairs']
    boundary = state['starting_archive_length']
    assert boundary == task.INHERITED_OPERATIONS
    assert len(pairs) == seal['cumulative_operations']
    assert len(pairs) - boundary == seal['actual_operations']
    records = [json.loads(line) for line in (task.RUN / 'records.jsonl').read_text(encoding='utf-8').splitlines()]
    completions = [r['payload'] for r in records if r['record_type'] == 'task_loop_completed']
    corrected = []
    for sequence, pair in enumerate(pairs, 1):
        if sequence <= boundary or pair['response'].get('action') != 'check':
            continue
        corrected.append(dict(
            cumulative_sequence=sequence,
            job_sequence=sequence - boundary,
            first_check_in_current_job=not corrected,
            **check_opportunity(calls_used=sequence - 1, call_limit=state['call_limit'], result=pair['result'])))
    return dict(
        condition=condition, version=version,
        purpose='Post-seal correction of evaluator accounting only; model counters and execution remain unchanged',
        seal_sha256=hashlib.sha256((task.RUN / 'RESPONSE_SEAL.json').read_bytes()).hexdigest(),
        inherited_operations=boundary, new_operations=len(pairs)-boundary,
        cumulative_operations=len(pairs), cumulative_request_limit=state['request_limit'],
        cumulative_requests=state['requests_used'], new_requests=state['requests_used']-task.INHERITED_REQUESTS,
        original_derived_rows=[x['check_opportunities'] for x in completions],
        corrected_current_job_check_opportunities=corrected,
        original_records_preserved=True,
        remaining_actions_are_not_proof_of_physical_admission=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('condition', choices=('control', 'current_job'))
    parser.add_argument('--version', default='003')
    args = parser.parse_args()
    result = supplement(args.condition, args.version)
    path = entry.HERE / 'review' / f'ACCOUNTING-{args.condition}-{args.version}.json'
    with path.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__': main()
