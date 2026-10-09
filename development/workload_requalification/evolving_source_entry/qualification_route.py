"""Source-supported engineering journey, separate from the later actor choices."""
import ast
import copy

from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes
from temporal_audit import Trace


def shown(view, path):
    row, = [row for row in view['working_set']['sources'] if row['path'] == path]
    assert row['whole_file_shown'] and row['returned_extent_complete']
    assert sha256_bytes(row['content'].encode()) == row['file_sha256']
    return row


def prefix(view, module):
    tree = ast.parse(shown(view, module.POLICY)['content'])
    value = next(node.value.value for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == 'PREFIX' for target in node.targets))
    assert isinstance(value, str)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'active_prefix')
    assert isinstance(function.body[0], ast.Return) and function.body[0].value.id == 'PREFIX'
    return value


def journey(module, session, measure, *, record=None, request_for=None):
    trace, feedback, trials = Trace(module), [], []
    original = session.candidate

    def step(name, operation, support, *, accepted=True):
        before, preceding = copy.deepcopy(session.view()), copy.deepcopy(feedback)
        count = measure(before)
        assert count <= 23808 and not session.delivery_blocked
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion='Offline engineering qualification.', operation=operation)
        outcome = module.process_reply(session, reply, measure, feedback)
        assert len(outcome['operations']) == 1 and outcome['operations'][0]['result']['accepted'] is accepted, outcome
        trace.observe(name, before, outcome['operations'], session.versions)
        after, following = copy.deepcopy(session.view()), measure(session.view())
        assert following <= 23808 and not session.delivery_blocked
        assert all(session.candidate.file_map[p] == body for p, body in original.files
                   if p not in (module.TARGET, module.POLICY, module.SECONDARY))
        row = dict(name=name, input_support=support, before_view=before,
            before_request=request_for(before) if request_for else None,
            preceding_before=preceding, reply=reply, outcome=outcome, after_view=after,
            preceding_after=copy.deepcopy(feedback), input_tokens=count, next_input_tokens=following)
        trials.append(dict(name=name, input_support=support, input_tokens=count, next_input_tokens=following,
            accepted=accepted, candidate_id=session.candidate.candidate_id))
        if record:
            record(row, session)
        return after

    for index, path in enumerate(module.REQUIRED_INSPECTION_PATHS):
        view = step(f'ledger-{index}', dict(action='work_on', sources=[dict(path=path, start_line=1, end_line=0)], results=[]),
            'The actual task names this entire ledger. Replace the completed preceding selection with this exact source; no task rule requires both bodies resident together.')
        assert shown(view, path)['content'].encode() == original.file_map[path]

    view = step('primary-support', dict(action='work_on', sources=[dict(path=path, start_line=1, end_line=0)
                for path in (module.POLICY, module.TARGET)], results=[]),
        'The task names policy and primary; their relationship governs the next edit. All four ledger bodies have been delivered at their preceding decisions. Obtain exact current governing and target source together.')
    old_prefix, row = prefix(view, module), shown(view, module.TARGET)
    old = row['content']
    assert old.count('return value.strip().casefold()') == 1
    proposal = dict(action='patch', path=module.TARGET, old=old,
        new=old.replace('return value.strip().casefold()', 'return ' + repr(old_prefix) + ' + value.strip().casefold()'),
        expected_candidate_id=view['candidate_id'], expected_file_sha256=row['file_sha256'])
    rejected = step('binding-negative', {**proposal, 'expected_file_sha256': '0' * 64},
        'Deliberate apparatus negative test: supply a wrong file fingerprint while keeping the exact current candidate. This is not a recommended model action.', accepted=False)
    assert rejected['latest_feedback']['result']['mismatched_bindings'] == ['expected_file_sha256']
    view = step('preserve-primary', proposal,
        'The displayed policy returns its PREFIX assignment. The task clarification requires that value to survive the later policy change. Preserve the value obtained from this actual source in the displayed primary function.')
    row = shown(view, module.POLICY)
    view = step('change-policy', dict(action='patch', path=module.POLICY, old=row['content'],
        new=row['content'].replace(repr(old_prefix), repr('quartz-')) if repr(old_prefix) in row['content']
            else row['content'].replace('"'+old_prefix+'"', '"quartz-"'),
        expected_candidate_id=view['candidate_id'], expected_file_sha256=row['file_sha256']),
        'Primary is saved. The original task authorizes the next policy value quartz-. Modify only the displayed policy assignment, keeping its accessor unchanged.')
    view = step('reacquire-policy', dict(action='read', path=module.POLICY, start_line=1, end_line=0),
        'The task explicitly requests exact current policy acquisition after mutation. The edit receipt identifies the successor. Request the current source rather than treating automatic refresh as the requested acquisition.')
    new_prefix = prefix(view, module)
    view = step('secondary-support', dict(action='read', path=module.SECONDARY, start_line=1, end_line=0),
        'The actual current policy was reacquired. The task names the secondary target, whose exact source is still absent.')
    row = shown(view, module.SECONDARY)
    assert row['content'].count('return value.strip().upper()') == 1
    view = step('secondary-work', dict(action='patch', path=module.SECONDARY, old=row['content'],
        new=row['content'].replace('return value.strip().upper()', 'return '+repr(new_prefix)+' + value.strip().upper()'),
        expected_candidate_id=view['candidate_id'], expected_file_sha256=row['file_sha256']),
        'The reacquired policy supplies the now-current value; exact secondary source supplies its trim/uppercase expression. Save that bounded contribution while preserving primary and policy.')
    view = step('check', dict(action='check', check_id='public', expected_candidate_id=view['candidate_id']),
        'All three contributions are saved in the declared order, and all four ledger bodies were delivered. Execute the original public checker on this actual successor.')
    assert view['verification']['checks']['public']['passed'] and view['verification']['submission']['eligible']
    step('submit', dict(action='submit', expected_candidate_id=view['candidate_id']),
        'The actual current public pass is displayed and applies to this candidate. Submit the saved contribution; no repeat check or account update is needed.')
    audit = trace.result()
    assert audit['temporal_contract_met'], audit
    return dict(submitted=session.submitted, trials=trials, audit=audit,
        final_candidate_id=session.candidate.candidate_id,
        classification='evaluator_scripted_information_path_not_model_behavior',
        requests=session.requests_used, new_operations=session.calls_used, completion_requests=0)


def qualify(module, loop, adapter, store, folder):
    session = module.initial_session()
    branch = folder / 'scripted'
    module.attach_observations(session, branch, loop.log)

    def record(row, current):
        stem = 'route/' + row['name']
        artifacts = [store.put(stem + '.json', canonical_json_bytes(row)),
            store.put(stem + '-state.json', canonical_json_bytes(module.snapshot(current))),
            store.put(stem + '-candidate.json', module.candidate_bytes(current.candidate))]
        loop.log.append('scripted_information_path_step', dict(name=row['name'], completion_sent=False), artifacts)
        restored = module.restore(module.snapshot(current), current.candidate, branch, replay=True)
        assert canonical_json_bytes(restored.view()) == canonical_json_bytes(current.view())
        assert canonical_json_bytes(module.snapshot(restored)) == canonical_json_bytes(module.snapshot(current))

    return journey(module, session, loop.measure, record=record, request_for=adapter.request_for)
