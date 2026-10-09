"""Source-supported saved-work route, never supplied to the actor."""
import ast
import copy

from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict
from temporal_audit import Trace


def parent_trace(module, versions):
    trace = Trace(module.previous)
    records = [load_json_strict(line) for line in module.inherited_bytes('records.jsonl').splitlines()]
    for row in records:
        if row['record_type'] != 'invocation_started':
            continue
        tag = row['payload']['id']
        wire = load_json_strict(module.inherited_bytes(f'calls/{tag}-wire-request.json'))
        operations = [load_json_strict(module.inherited_bytes(item['artifacts'][0]['path'])) for item in records
            if item['record_type'] == 'contribution_operation' and item['payload']['id'] == tag]
        trace.observe(tag, load_json_strict(wire['messages'][-1]['content'])['workspace'], operations, versions)
    assert trace.sequence == 37 and trace.result()['all_ledgers_delivered']
    return trace


def journey(module, session, measure, *, feedback=None, record=None, request_for=None):
    trace = parent_trace(module, session.versions)
    feedback = [] if feedback is None else feedback
    trials = []
    initial = session.candidate

    def step(name, operation, support):
        before, preceding = copy.deepcopy(session.view()), copy.deepcopy(feedback)
        count = measure(before)
        assert count <= 23808
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion='Offline engineering qualification.', operation=operation)
        outcome = module.process_reply(session, reply, measure, feedback)
        assert len(outcome['operations']) == 1 and outcome['operations'][0]['result']['accepted'], outcome
        trace.observe(name, before, outcome['operations'], session.versions)
        following = measure(session.view())
        assert following <= 23808 and not session.delivery_blocked
        assert all(session.candidate.file_map[path] == body for path, body in initial.files
                   if path != module.previous.SECONDARY)
        row = dict(name=name, input_support=support, before_view=before,
            before_request=request_for(before) if request_for else None, preceding_before=preceding,
            reply=reply, outcome=outcome, after_view=session.view(), preceding_after=copy.deepcopy(feedback),
            input_tokens=count, next_input_tokens=following)
        trials.append(dict(name=name, input_support=support, input_tokens=count,
            next_input_tokens=following, candidate_id=session.candidate.candidate_id))
        if record:
            record(row, session)
        return session.view()

    view = step('current-support', dict(action='work_on', sources=[dict(path=p, start_line=1, end_line=0)
        for p in (module.previous.POLICY, module.previous.SECONDARY)], results=[]),
        'The actual last receipt names the changed policy file and the task requires its explicit reacquisition. '
        'The task names the unread secondary target. Acquire both exact current bodies together; no reference contribution is supplied.')
    policy, = [s for s in view['working_set']['sources'] if s['path'] == module.previous.POLICY]
    source, = [s for s in view['working_set']['sources'] if s['path'] == module.previous.SECONDARY]
    tree = ast.parse(policy['content'])
    prefix = next(node.value.value for node in tree.body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == 'PREFIX' for target in node.targets))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'active_prefix')
    assert isinstance(prefix, str) and isinstance(function.body[0], ast.Return) and function.body[0].value.id == 'PREFIX'
    assert source['content'].count('return value.strip().upper()') == 1
    view = step('secondary', dict(action='patch', path=module.previous.SECONDARY, old=source['content'],
        new=source['content'].replace('return value.strip().upper()', 'return ' + repr(prefix) + ' + value.strip().upper()'),
        expected_candidate_id=view['candidate_id'], expected_file_sha256=source['file_sha256']),
        'The explicitly reacquired policy returns its visible PREFIX assignment. The exact target supplies the trim/uppercase expression. '
        'Preserve primary and policy while adding that observed current value to secondary.')
    view = step('check', dict(action='check', check_id='public', expected_candidate_id=view['candidate_id']),
        'The actual secondary edit has produced a successor. Execute the unchanged registered public checker on it.')
    assert view['verification']['submission']['eligible'] and view['verification']['checks']['public']['passed']
    step('submit', dict(action='submit', expected_candidate_id=view['candidate_id']),
        'The actual current public pass is displayed; submit this saved contribution.')
    audit = trace.result()
    assert audit['temporal_contract_met'], audit
    return dict(classification='researcher_scripted_information_path_not_actor_behavior',
        submitted=session.submitted, trials=trials, audit=audit, completion_requests=0,
        new_requests=session.requests_used - 24, new_operations=session.calls_used - 37,
        final_candidate_id=session.candidate.candidate_id)


def qualify(module, loop, adapter, store, folder):
    session = module.initial_session()
    module.attach_observations(session, folder / 'scripted', loop.log)
    def record(row, current):
        stem = 'route/' + row['name']
        loop.log.append('scripted_information_path_step', dict(name=row['name'], completion_sent=False),
            [store.put(stem + '.json', canonical_json_bytes(row)),
             store.put(stem + '-state.json', canonical_json_bytes(module.snapshot(current))),
             store.put(stem + '-candidate.json', module.candidate_bytes(current.candidate))])
        restored = module.restore(module.snapshot(current), current.candidate, folder / 'scripted', replay=True)
        assert restored.view() == current.view()
    # The adapter's companion receipts are part of every measured complete input.
    return journey(module, session, loop.measure, feedback=adapter.preceding_feedback,
        record=record, request_for=adapter.request_for)
