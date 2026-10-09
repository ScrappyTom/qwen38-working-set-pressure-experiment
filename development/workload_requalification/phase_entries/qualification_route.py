"""Original source-task information paths, separate from model behavior."""
import ast
import copy

from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes


def exact_source(view, path):
    row, = [r for r in view['working_set']['sources'] if r['path'] == path]
    assert row['whole_file_shown'] and sha256_bytes(row['content'].encode()) == row['file_sha256']
    return row


def journey(module, session, measure, feedback, *, variant, record):
    trials, initial = [], session.candidate

    def step(name, operation, support, *, accepted=True, account=None):
        before, preceding = copy.deepcopy(session.view()), copy.deepcopy(feedback)
        count = measure(before)
        assert count <= 23808 and not session.delivery_blocked
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion='Declared engineering qualification; not model work.', operation=operation)
        if account is not None:
            reply['account'] = account
        outcome = module.process_reply(session, reply, measure, feedback)
        result = outcome['operations'][-1]['result']
        assert result['accepted'] is accepted, (name, outcome)
        after = session.view()
        following = measure(after)
        assert following <= 23808 and not session.delivery_blocked
        assert all(session.candidate.file_map[p] == raw for p, raw in initial.files
                   if p not in ('workflow/progress.py', 'api/name.py'))
        row = dict(name=name, variant=variant, input_support=support,
            before_view=before, preceding_before=preceding, reply=reply, outcome=outcome,
            after_view=after, preceding_after=copy.deepcopy(feedback),
            input_tokens=count, next_input_tokens=following)
        record(row, session)
        trials.append({k: row[k] for k in ('name', 'input_support', 'input_tokens', 'next_input_tokens')})
        return after

    def select(name, path, support, first=1):
        return step(name, dict(action='work_on', sources=[dict(path=path, start_line=first, end_line=0)], results=[]), support)

    def patch(name, path, old, new, support, **kwargs):
        view = session.view()
        row = exact_source(view, path)
        assert old in row['content']
        return step(name, dict(action='patch', path=path, old=old, new=new,
            expected_candidate_id=view['candidate_id'], expected_file_sha256=row['file_sha256']), support, **kwargs)

    def check(name, scope):
        return step(name, dict(action='check', check_id=scope, expected_candidate_id=session.candidate.candidate_id),
            'The actual saved candidate needs the active named check; execution, not an authored account, establishes its outcome.')

    if variant == 'crowded-recovery':
        # Intentionally inefficient evaluator acquisitions. This is a capacity
        # transition fixture, not a purported information-minimal actor route.
        index, first, rejected = 0, 1, None
        for n in range(12):
            before = session.view()
            # Probe the resulting state through ordinary execution, admitting
            # either a truthful accepted page or a complete capacity rejection.
            session.mark_delivered(before)
            # step itself marks the same view; repeated exact delivery is idempotent.
            op = dict(action='read', path=f'records_a/module_{index:03d}.py', start_line=first, end_line=0)
            # Do not predict the token fit using an approximate measurement.
            # The staged host result decides; step's allowed result is relaxed
            # only for this synthetic crowding branch below.
            count = measure(before)
            session.begin_request()
            preceding = copy.deepcopy(feedback)
            reply = dict(discussion='Deliberate engineering crowding.', operation=op)
            outcome = module.process_reply(session, reply, measure, feedback)
            result = outcome['operations'][-1]['result']
            after = session.view()
            following = measure(after)
            assert following <= 23808 and not session.delivery_blocked
            row = dict(name=f'broad-{n+1}', variant=variant, input_support='Evaluator-selected inefficient broad acquisition; not actor evidence.',
                before_view=before, preceding_before=preceding, reply=reply, outcome=outcome,
                after_view=after, preceding_after=copy.deepcopy(feedback), input_tokens=count, next_input_tokens=following)
            record(row, session)
            trials.append({k: row[k] for k in ('name', 'input_support', 'input_tokens', 'next_input_tokens')})
            if not result['accepted']:
                rejected = result
                break
            source = result['source']
            if source['next_start_line'] is None:
                index, first = index + 1, 1
            else:
                first = source['next_start_line']
        assert rejected is not None and session.view()['presentation']['mode'] == 'recovery'
        assert session.candidate == initial
        select('replace-crowded-selection', 'workflow/progress.py',
            'The actual capacity rejection and task-named target justify replacing the broad selection; the evaluator chooses this route.')
        assert session.view()['presentation']['mode'] == 'ordinary'
        patch('save-after-recovery', 'workflow/progress.py', 'return 0', 'return 1',
            'The delivered complete target and Phase A task establish the requested behavior.')
        check('check-after-recovery', 'prefork')
        assert session.scoped_check_state('prefork')['passed']
        return dict(classification='scripted_capacity_transition_not_actor_behavior', submitted=False,
            trials=trials, actual_rejection=rejected, final_candidate=session.candidate.candidate_id)

    assert variant == 'complete'
    # Each complete required file is presented to the following actual decision.
    for i, path in enumerate(session.phase_required['A']):
        view = select(f'phase-a-record-{i}', path, 'The original active assignment explicitly names this complete file.')
        first = 1
        while not exact_or_partial_complete(view, path):
            row, = [r for r in view['working_set']['sources'] if r['path'] == path]
            first = row['returned_end_line'] + 1
            view = select(f'phase-a-record-{i}-from-{first}', path,
                'The actual returned extent and continuation show remaining required lines.', first)
    select('progress-source', 'workflow/progress.py', 'Phase A names this function; its exact current source is needed for the edit.')
    check('observed-prefork-failure', 'prefork')
    assert session.scoped_check_state('prefork')['passed'] is False
    assert 'AssertionError' in canonical_json_bytes(session.pairs[-1]['result']).decode()
    patch('progress-repair', 'workflow/progress.py', 'return 0', 'return 1',
        'The acquired function returns zero; the task requests one. The actual initial check failure is now available.',
        account='The inspected progress function returns zero; Phase A requires one. Saving that change still requires its actual prefork check.')
    check('observed-prefork-pass', 'prefork')
    assert session.scoped_check_state('prefork')['passed']
    step('stale-fork-rejected', dict(action='fork_ready', expected_candidate_id=initial.candidate_id),
        'Negative guard fixture: deliberately use the original candidate instead of the visible successor.', accepted=False)
    prior_pairs = canonical_json_bytes(session.pairs)
    prior_account = session.working_account()
    step('phase-boundary', dict(action='fork_ready', expected_candidate_id=session.candidate.candidate_id),
        'The actual current prefork pass and complete prior delivered records meet Phase A. Request the task-declared boundary.')
    assert session.phase == 'B' and not session.ranges and not session.saved and not session.delivered_sources
    assert canonical_json_bytes(session.pairs[:-1]) == prior_pairs and session.working_account() == prior_account
    assert not session.view()['verification']['submission']['eligible']
    step('released-source-not-editable', dict(action='patch', path='workflow/progress.py', old='return 1', new='return 2',
        expected_candidate_id=session.candidate.candidate_id, expected_file_sha256=session.candidate.file_sha256('workflow/progress.py')),
        'Negative authority fixture: the released earlier target is not currently presented. Historical coverage cannot authorize this edit.', accepted=False)
    assert session.candidate.candidate_id == module.fixture['phase_candidate_ids']['A']
    # P0 discovery supplies the previously unacquired path, then its symbols.
    assert any(r['path'] == 'policies' for r in session.view()['current_p0']['entries'])
    step('policy-directory', dict(action='p0_page', path='policies', offset=0),
        'The active task asks for the current policy definition; root P0 shows policies. Inspect that discovered directory.')
    assert 'policies/current.py' in canonical_json_bytes(session.pairs[-1]['result']).decode()
    step('policy-outline', dict(action='p0_page', path='policies/current.py', offset=0),
        'The actual directory result supplies policies/current.py; inspect its readable source outline.')
    assert 'active_policy_prefix' in canonical_json_bytes(session.pairs[-1]['result']).decode()
    view = select('policy-source', 'policies/current.py',
        'The P0 outline identifies the named function. Its exact current definition, not the outline alone, establishes the value.')
    policy = exact_source(view, 'policies/current.py')['content']
    tree = ast.parse(policy)
    assignment, = [n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'POLICY_PREFIX' for t in n.targets)]
    prefix = ast.literal_eval(assignment.value)
    assert 'return POLICY_PREFIX' in policy and isinstance(prefix, str)
    view = step('name-and-policy', dict(action='work_on', sources=[dict(path=p, start_line=1, end_line=0)
        for p in ('api/name.py', 'policies/current.py')], results=[]),
        'The task names the target and the just-acquired policy supplies its governing value; present both exact sources together.')
    patch('name-repair', 'api/name.py', 'return value.strip().casefold()',
        'return ' + repr(prefix) + ' + value.strip().casefold()',
        'The actual policy returns the acquired literal. Add it while retaining the exact existing strip/casefold expression.')
    for i, path in enumerate(session.phase_required['B']):
        view = select(f'phase-b-record-{i}', path, 'The original Phase B task explicitly requires this complete file.')
        while not exact_or_partial_complete(view, path):
            row, = [r for r in view['working_set']['sources'] if r['path'] == path]
            first = row['returned_end_line'] + 1
            view = select(f'phase-b-record-{i}-from-{first}', path,
                'The delivered page supplies the next coordinate; complete the remaining required extent.', first)
    check('observed-public-pass', 'public')
    assert session.scoped_check_state('public')['passed'] and all(r['complete'] for r in session.coverage_status())
    step('submit', dict(action='submit', expected_candidate_id=session.candidate.candidate_id),
        'The current public pass arrived after both saved contributions and the actual required file presentations. Submit without another edit.')
    assert session.submitted
    return dict(classification='scripted_information_path_not_actor_behavior', submitted=True,
        trials=trials, requests=session.requests_used, operations=session.calls_used,
        final_candidate=session.candidate.candidate_id, all_required_delivered=True)


def exact_or_partial_complete(view, path):
    row, = [r for r in view['working_set']['sources'] if r['path'] == path]
    # Only controls forward paging. Historical union is independently checked at
    # the boundary/submission; EOF alone never claims complete file coverage.
    return row['returned_end_line'] == row['file_total_lines']


def qualify(module, loop, adapter, store, folder):
    results, initial_feedback = {}, copy.deepcopy(adapter.preceding_feedback)
    try:
        for variant in ('complete', 'crowded-recovery'):
            session = module.initial_session()
            module.attach_observations(session, folder / variant, loop.log)
            adapter.preceding_feedback.clear()
            def record(row, current):
                stem = variant + '/' + row['name']
                artifacts = [store.put(stem + '.json', canonical_json_bytes(row)),
                    store.put(stem + '-state.json', canonical_json_bytes(module.snapshot(current))),
                    store.put(stem + '-candidate.json', module.candidate_bytes(current.candidate))]
                if loop.log is not None:
                    loop.log.append('scripted_phase_step', dict(variant=variant, name=row['name'], completion_sent=False), artifacts)
                restored = module.restore(module.snapshot(current), current.candidate, folder / variant, replay=True)
                assert canonical_json_bytes(restored.view()) == canonical_json_bytes(current.view())
            results[variant] = journey(module, session, loop.measure, adapter.preceding_feedback,
                variant=variant, record=record)
        return dict(submitted=results['complete']['submitted'], variants=results, no_completion_calls=True)
    finally:
        adapter.preceding_feedback[:] = initial_feedback
