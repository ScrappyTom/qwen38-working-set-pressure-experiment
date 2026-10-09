"""Exact four-phase information path; scripted choices are not model evidence."""
import ast
import copy
import re

import recurrent_bootstrap
import qualification_route as prior
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes


def journey(module, session, measure, feedback, *, variant, record):
    if variant == 'crowded-recovery':
        return prior.journey(module, session, measure, feedback, variant=variant, record=record)
    assert variant == 'complete'
    trials, initial = [], session.candidate

    def step(name, action, support, *, accepted=True, account=None):
        before, preceding = copy.deepcopy(session.view()), copy.deepcopy(feedback)
        count = measure(before)
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion='Declared engineering qualification, not model work.', operation=action)
        if account is not None:
            reply['account'] = account
        outcome = module.process_reply(session, reply, measure, feedback)
        result = outcome['operations'][-1]['result']
        assert result['accepted'] is accepted, (name, result)
        after, following = session.view(), measure(session.view())
        assert max(count, following) <= 23808 and not session.delivery_blocked
        assert all(session.candidate.file_map[p] == raw for p, raw in initial.files
                   if p not in ('workflow/progress.py', 'api/name.py', 'policies/current.py', 'api/footer.py'))
        row = dict(name=name, variant=variant, input_support=support, before_view=before,
            preceding_before=preceding, reply=reply, outcome=outcome, after_view=after,
            preceding_after=copy.deepcopy(feedback), input_tokens=count, next_input_tokens=following)
        record(row, session)
        trials.append({k: row[k] for k in ('name', 'input_support', 'input_tokens', 'next_input_tokens')})
        return after

    def select(name, *paths, first=1):
        return step(name, dict(action='work_on', sources=[dict(path=p, start_line=first, end_line=0) for p in paths], results=[]),
            'The task names the target or preceding exact P0 result identifies it. Selection is researcher-chosen; its returned bytes support the later decision.')

    def records(phase):
        for index, path in enumerate(session.phase_required[phase]):
            view = select(f'{phase}-record-{index}', path)
            while not prior.exact_or_partial_complete(view, path):
                row, = [r for r in view['working_set']['sources'] if r['path'] == path]
                first = row['returned_end_line'] + 1
                view = select(f'{phase}-record-{index}-from-{first}', path, first=first)

    def patch(name, path, old, new, support):
        row = prior.exact_source(session.view(), path)
        assert old in row['content']
        return step(name, dict(action='patch', path=path, old=old, new=new,
            expected_candidate_id=session.candidate.candidate_id, expected_file_sha256=row['file_sha256']), support)

    def check(name):
        scope = session.view()['phase']['current_check']
        return step(name, dict(action='check', check_id=scope, expected_candidate_id=session.candidate.candidate_id),
            'The actual phase names its scope. Execute on the saved candidate; an account cannot establish the observation.')

    def boundary(name):
        before = session.clone()
        phase, candidate = before.phase, before.candidate.candidate_id
        scope = 'prefork' if phase == 'A' else 'public'
        state = before.scoped_check_state(scope)
        assert state['applies_to_current'] and state['passed']
        old_account, old_pairs = before.working_account(), canonical_json_bytes(before.pairs)
        step(name, dict(action='fork_ready', expected_candidate_id=candidate),
            'The actual active pass and complete required delivery justify the original boundary; it does not execute the next phase check.')
        assert before.phase == phase and before.checkers[scope] == module.checker(phase)
        assert before.scoped_check_state(scope)['applies_to_current']
        assert not session.ranges and not session.saved and not session.delivered_sources
        assert session.candidate.candidate_id == candidate and session.working_account() == old_account
        assert canonical_json_bytes(session.pairs[:-1]) == old_pairs
        if phase != 'A':
            old = session.scoped_check_state('public')
            assert old['candidate_matches'] and not old['check_definition_matches'] and not old['applies_to_current']
            handle = session.pairs[int(old['handle'].split('-')[1]) - 1]['result']['observation']
            assert session._assessment(handle)['checker_sha256'] == sha256_bytes(module.checker(phase))
        assert not session.view()['verification']['submission']['eligible']

    def prefix():
        text = prior.exact_source(session.view(), 'policies/current.py')['content']
        tree = ast.parse(text)
        assignment, = [n for n in tree.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'POLICY_PREFIX' for t in n.targets)]
        value = ast.literal_eval(assignment.value)
        assert isinstance(value, str) and 'return POLICY_PREFIX' in text
        return value

    step('unread-boundary-rejected', dict(action='fork_ready', expected_candidate_id=session.candidate.candidate_id),
        'Negative fixture: required A sources are not delivered.', accepted=False)
    records('A')
    select('progress-source', 'workflow/progress.py')
    patch('deliberately-wrong-progress', 'workflow/progress.py', 'return 0', 'return 2',
        'Negative repair fixture: deliberately contradict the task value one; this is not an actor proposal.')
    wrong = session.candidate.candidate_id
    check('saved-wrong-progress-fails')
    assert not session.scoped_check_state('prefork')['passed'] and session.candidate.candidate_id == wrong
    patch('correct-progress', 'workflow/progress.py', 'return 2', 'return 1',
        'The task specifies one and the exact visible source returns two. The failed check refutes that saved work, not the source-specified correction.')
    check('current-A-pass')
    step('stale-boundary-rejected', dict(action='fork_ready', expected_candidate_id=initial.candidate_id),
        'Negative candidate guard fixture: old initial identifier after a saved edit.', accepted=False)
    boundary('A-to-B')
    step('released-source-rejected', dict(action='patch', path='workflow/progress.py', old='return 1', new='return 2',
        expected_candidate_id=session.candidate.candidate_id, expected_file_sha256=session.candidate.file_sha256('workflow/progress.py')),
        'Negative authority fixture: historical delivery did not retain present source after the boundary.', accepted=False)
    assert any(r['path'] == 'policies' for r in session.view()['current_p0']['entries'])
    step('policy-directory', dict(action='p0_page', path='policies', offset=0),
        'Root P0 exposes the policies directory; the assignment asks to locate the current policy definition.')
    assert 'policies/current.py' in canonical_json_bytes(session.pairs[-1]['result']).decode()
    step('policy-outline', dict(action='p0_page', path='policies/current.py', offset=0),
        'The actual directory result supplies this path; its outline locates the named function.')
    assert 'active_policy_prefix' in canonical_json_bytes(session.pairs[-1]['result']).decode()
    select('B-policy-and-name', 'policies/current.py', 'api/name.py')
    original_prefix = prefix()
    patch('B-name', 'api/name.py', 'return value.strip().casefold()',
        'return ' + repr(original_prefix) + ' + value.strip().casefold()',
        'The delivered exact policy establishes this literal; the delivered target establishes strip/casefold. No reference candidate supplies it.')
    saved_name = session.candidate.file_map['api/name.py']
    records('B')
    check('current-B-pass')
    step('B-cannot-submit', dict(action='submit', expected_candidate_id=session.candidate.candidate_id),
        'Negative terminal-boundary fixture: a B public pass does not finish C/D.', accepted=False)
    boundary('B-to-C')
    check('C-distinct-definition-fails')
    assert not session.scoped_check_state('public')['passed']
    select('C-policy', 'policies/current.py')
    authorized, = re.findall(r'authorized current value becomes `([^`]+)`', session.view()['phase']['active_assignment'])
    old = prefix()
    patch('C-policy-change', 'policies/current.py', 'POLICY_PREFIX = "' + old + '"',
        'POLICY_PREFIX = "' + authorized + '"',
        'The actual C assignment explicitly authorizes this value; exact reacquired source supplies the old assignment. Preserve the earlier name bytes.')
    assert session.candidate.file_map['api/name.py'] == saved_name
    records('C')
    check('current-C-pass')
    boundary('C-to-D')
    assert session.candidate.file_map['api/name.py'] == saved_name
    step('D-cannot-fork', dict(action='fork_ready', expected_candidate_id=session.candidate.candidate_id),
        'Negative boundary fixture: D is terminal.', accepted=False)
    step('C-pass-cannot-submit-D', dict(action='submit', expected_candidate_id=session.candidate.candidate_id),
        'Negative applicability fixture: candidate is unchanged but D has a different public checker.', accepted=False)
    select('D-reacquired-policy-and-footer', 'policies/current.py', 'api/footer.py')
    new_prefix = prefix()
    assert new_prefix != original_prefix
    patch('D-footer', 'api/footer.py', 'return value.strip().upper()',
        'return ' + repr(new_prefix) + ' + value.strip().upper()',
        'The actual post-boundary policy body establishes its new literal. The exact footer supplies its existing normalization; earlier name work stays unchanged.')
    assert session.candidate.file_map['api/name.py'] == saved_name
    check('current-D-pass')
    assert session.scoped_check_state('public')['passed']
    assert all(r['complete'] for p in session.order for r in session.coverage_status(p))
    step('submit', dict(action='submit', expected_candidate_id=session.candidate.candidate_id),
        'The actual D pass, acquired post-C policy, preserved earlier contribution and complete required delivery support final submission.')
    return dict(classification='scripted_information_path_not_actor_behavior', submitted=session.submitted,
        trials=trials, requests=session.requests_used, operations=session.calls_used,
        final_candidate=session.candidate.candidate_id, all_required_delivered=True)


def qualify(module, loop, adapter, store, folder):
    results, initial_feedback = {}, copy.deepcopy(adapter.preceding_feedback)
    try:
        for variant in ('complete', 'crowded-recovery'):
            session = module.initial_session()
            module.attach_observations(session, folder / variant, loop.log)
            adapter.preceding_feedback.clear()
            def record(row, current):
                stem = variant + '/' + row['name']
                state = canonical_json_bytes(module.snapshot(current))
                candidate = module.candidate_bytes(current.candidate)
                artifacts = [store.put(stem + '.json', canonical_json_bytes(row)),
                    store.put(stem + '-state.json', state), store.put(stem + '-candidate.json', candidate)]
                if loop.log is not None:
                    loop.log.append('scripted_phase_step', dict(variant=variant, name=row['name'], completion_sent=False), artifacts)
                restored = module.restore(load_json_strict(state), load_json_strict(candidate), folder / variant, replay=True)
                assert canonical_json_bytes(restored.view()) == canonical_json_bytes(current.view())
                assert canonical_json_bytes(module.snapshot(restored)) == state
            results[variant] = journey(module, session, loop.measure, adapter.preceding_feedback, variant=variant, record=record)
        return dict(submitted=results['complete']['submitted'], variants=results, no_completion_calls=True)
    finally:
        adapter.preceding_feedback[:] = initial_feedback
