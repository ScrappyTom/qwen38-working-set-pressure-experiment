"""Read-only post-run delivery/cost assessment; no model or checker execution."""
import ast
import difflib
import json
from hashlib import sha256
from pathlib import Path

AREA = Path(__file__).resolve().parents[1]
RUN = AREA / 'run-001'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def artifact_assessment():
    initial = read(RUN / 'starting-candidate.json')
    stopped = read(RUN / 'stopped-candidate.json')
    before = {f['path']: f['content_utf8'] for f in initial['files']}
    after = {f['path']: f['content_utf8'] for f in stopped['files']}
    assert before.keys() == after.keys()
    changed = [p for p in before if before[p] != after[p]]
    patch = ''.join(''.join(difflib.unified_diff(
        before[p].splitlines(True), after[p].splitlines(True),
        fromfile='before/' + p, tofile='saved/' + p)) for p in changed)
    (AREA / 'review' / 'saved-contribution.patch').write_text(patch, encoding='utf-8')
    target = 'Lib/test/test_urlparse.py'

    def methods(text):
        return {f'{cls.name}.{node.name}': ast.get_source_segment(text, node)
                for cls in ast.parse(text).body if isinstance(cls, ast.ClassDef)
                for node in cls.body if isinstance(node, ast.FunctionDef)}

    old_methods, new_methods = methods(before[target]), methods(after[target])
    original_methods_unchanged = all(new_methods.get(k) == v for k, v in old_methods.items())
    added = sorted(new_methods.keys() - old_methods.keys())
    opcodes = difflib.SequenceMatcher(None, before[target].splitlines(True),
                                     after[target].splitlines(True), autojunk=False).get_opcodes()
    last_saved = read(RUN / 'after' / 'C12-O01-candidate.json')
    assert stopped == last_saved, 'inspection/termination must preserve saved candidate'
    stdout = (RUN / 'observations' / 'CHK-0020' / 'stdout.bin').read_bytes()
    check = json.loads(stdout)
    faults = check['fault_sensitivity']
    return dict(
        initial_candidate=initial['candidate_id'], stopped_candidate=stopped['candidate_id'],
        changed_files=changed,
        file_sha256={p: sha256(text.encode()).hexdigest() for p, text in after.items()},
        preserved_files=[p for p in before if before[p] == after[p]],
        original_test_methods_unchanged=original_methods_unchanged,
        added_test_methods=added,
        inserted_test_lines=sum(j2-j1 for tag, i1, i2, j1, j2 in opcodes if tag == 'insert'),
        test_change_is_insertions_only=all(row[0] in ('equal', 'insert') for row in opcodes),
        stopped_candidate_equals_last_saved_candidate=True,
        actual_check=dict(
            source='Preserved CHK-0020 stdout; not a post-run checker execution.',
            stdout_bytes=len(stdout), stdout_sha256=sha256(stdout).hexdigest(),
            passed=check['passed'], tests_passed=check['tests_passed'],
            saved_suite=check['saved_suite'], edited_suite=check['edited_suite'],
            observed_paths=check['observed_paths'],
            fault_results={name: dict(tests=r['tests'], failures=r['failures'], errors=r['errors'],
                                     test_run_successful=r['successful'],
                                     fault_detected=bool(r['tests'] and not r['successful']))
                           for name, r in faults.items()}))


def main():
    assert (RUN / 'RESPONSE_SEAL.json').exists(), 'assess only after attempt closure'
    records = [json.loads(line) for line in (RUN / 'records.jsonl').read_text(encoding='utf-8').splitlines()]
    completed = {r['payload']['id']: r['payload'] for r in records if r['record_type'] == 'invocation_completed'}
    received = {r['payload']['id']: r['payload'] for r in records if r['record_type'] == 'response_received'}
    candidates = {}
    for path in [RUN / 'starting-candidate.json', *sorted((RUN / 'after').glob('*-candidate.json'))]:
        candidate = read(path)
        candidates[candidate['candidate_id']] = {f['path']: f['content_utf8'] for f in candidate['files']}
    calls, operations, delivery = [], [], []
    for wire in sorted((RUN / 'calls').glob('*-wire-request.json')):
        tag = wire.name.split('-')[0]
        request = read(wire)
        user = json.loads(request['messages'][-1]['content'])
        workspace = user['workspace']
        visible = []
        for item in nodes(user):
            if item.get('kind') != 'current_source' or 'content' not in item:
                continue
            full = candidates[item['candidate_id']][item['path']]
            assert sha256(full.encode()).hexdigest() == item['file_sha256']
            first, last = item['returned_start_line'], item['returned_end_line']
            expected = ''.join(full.splitlines(keepends=True)[first - 1:last])
            assert expected == item['content'], (tag, item['path'], first, last)
            entry = dict(path=item['path'], first=first, last=last,
                         file_sha256=item['file_sha256'], bytes=len(item['content'].encode()))
            if entry not in visible:
                visible.append(entry)
        account = workspace.get('working_account')
        row = dict(id=tag, presentation=workspace['presentation'], allowance=workspace['allowance'],
                   visible_sources=visible, account=account, current_check=workspace['current_check'],
                   request_kwargs=request.get('chat_template_kwargs'),
                   request_limits={k: request.get(k) for k in ('max_tokens', 'n_predict', 'reasoning_budget_tokens', 'thinking_budget_tokens')})
        if tag in received:
            endpoint = read(wire.with_name(tag + '-endpoint-response.json'))
            row.update(usage=endpoint['usage'], finish_reason=endpoint['choices'][0]['finish_reason'],
                       elapsed_seconds=received[tag]['elapsed_seconds'])
        result_path = wire.with_name(tag + '-host-result.json')
        if result_path.exists():
            host = read(result_path)
            following = wire.with_name(f'C{int(tag[1:])+1:02}-wire-request.json')
            next_nodes = None
            if following.exists():
                next_user = json.loads(read(following)['messages'][-1]['content'])
                next_nodes = {canonical(n) for n in nodes(next_user)}
            for index, operation in enumerate(host['operations'], 1):
                result = operation['result']
                operations.append(dict(id=tag, index=index, origin=operation['origin'],
                                       action=operation['action']['action'], accepted=result.get('accepted'),
                                       passed=result.get('passed'), observation=result.get('observation')))
                delivery.append(dict(id=tag, index=index, action=operation['action']['action'],
                    next_call_exists=next_nodes is not None,
                    exact_result_present=(canonical(result) in next_nodes if next_nodes is not None else None)))
        calls.append(row)
    loop = [r['payload'] for r in records if r['record_type'] == 'task_loop_completed']
    output = dict(
        evidence_scope='Post-run mechanical delivery and source checks; interpretation remains in direct transcript review.',
        calls=calls, operations=operations, delivery=delivery, loop=loop,
        artifact=artifact_assessment(),
        totals=dict(requests=len(calls), completed_invocations=len(completed),
                    returned=len(received), operations=len(operations),
                    input_tokens=sum(c.get('usage', {}).get('prompt_tokens', 0) for c in calls),
                    output_tokens=sum(c.get('usage', {}).get('completion_tokens', 0) for c in calls),
                    request_seconds=sum(c.get('elapsed_seconds', 0) for c in calls),
                    peak_input=max(c.get('usage', {}).get('prompt_tokens', 0) for c in calls),
                    peak_input_plus_output=max(c.get('usage', {}).get('total_tokens', 0) for c in calls),
                    response_processing_seconds=sum(r['payload']['processing_seconds'] for r in records if r['record_type']=='reply_processed')))
    target = AREA / 'review' / 'ASSESSMENT.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(output['totals'], indent=2))
    print('Delivery exceptions:', [d for d in delivery if d['next_call_exists'] and not d['exact_result_present']])


if __name__ == '__main__':
    main()
