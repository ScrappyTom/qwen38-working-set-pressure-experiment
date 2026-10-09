"""Information paths from actual input/feedback; no Qwen inference."""
import copy

import probe_bootstrap
import qualification_route as source_route
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict


def journey(module, session, measure, feedback, *, variant, record):
    if variant == 'crowded-recovery':
        return source_route.journey(module, session, measure, feedback, variant=variant, record=record)
    trials, initial = [], session.candidate

    def step(name, operation, support, *, accepted=True, account=None):
        before, preceding = copy.deepcopy(session.view()), copy.deepcopy(feedback)
        count = measure(before)
        assert count <= 23808 and not session.delivery_blocked
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion='Declared engineering qualification, not model work.', operation=operation)
        if account is not None:
            reply['account'] = account
        outcome = module.process_reply(session, reply, measure, feedback)
        result = outcome['operations'][-1]['result']
        assert result['accepted'] is accepted, (name, result)
        after, following = session.view(), measure(session.view())
        assert following <= 23808 and not session.delivery_blocked
        assert all(session.candidate.file_map[p] == raw for p, raw in initial.files
                   if p not in ('workflow/progress.py', 'codec/label.py'))
        row = dict(name=name, variant=variant, input_support=support,
            before_view=before, preceding_before=preceding, reply=reply, outcome=outcome,
            after_view=after, preceding_after=copy.deepcopy(feedback), input_tokens=count, next_input_tokens=following)
        record(row, session)
        trials.append({k: row[k] for k in ('name', 'input_support', 'input_tokens', 'next_input_tokens')})
        return after

    def select(name, path, support, first=1, results=None):
        return step(name, dict(action='work_on', sources=[dict(path=path, start_line=first, end_line=0)], results=results or []), support)

    def patch(name, path, old, new, support):
        row = source_route.exact_source(session.view(), path)
        assert old in row['content']
        return step(name, dict(action='patch', path=path, old=old, new=new,
            expected_candidate_id=session.candidate.candidate_id, expected_file_sha256=row['file_sha256']), support)

    def check(name, scope):
        return step(name, dict(action='check', check_id=scope, expected_candidate_id=session.candidate.candidate_id),
            'The current assignment and saved candidate identify the scope; only the following executed observation establishes its result.')

    def records(phase):
        for i, path in enumerate(session.phase_required[phase]):
            view = select(f'{phase}-record-{i}', path, 'The exact original phase assignment names this complete record file.')
            while not source_route.exact_or_partial_complete(view, path):
                row, = [r for r in view['working_set']['sources'] if r['path'] == path]
                first = row['returned_end_line'] + 1
                view = select(f'{phase}-record-{i}-from-{first}', path,
                    'The delivered extent, total lines and continuation coordinate identify the remaining part.', first)

    records('A')
    select('progress-source', 'workflow/progress.py', 'Phase A names the function; acquire its actual current implementation.')
    step('early-probe', dict(action='probe', probe_id='integrity'),
        'Negative applicability fixture: produce an actual observation before the required progress edit.')
    old_probe = session.current_probe()
    old_body = session.observation(old_probe['handle'])[1]
    check('initial-prefork-failure', 'prefork')
    assert session.scoped_check_state('prefork')['passed'] is False
    patch('progress-repair', 'workflow/progress.py', 'return 0', 'return 1',
        'The exact source returns zero, the task asks for one, and the real failing check is now available.')
    check('current-prefork-pass', 'prefork')
    assert session.scoped_check_state('prefork')['passed']
    step('stale-probe-boundary-rejected', dict(action='fork_ready', expected_candidate_id=session.candidate.candidate_id),
        'Negative binding fixture: the pass is current but the only probe belongs to the pre-edit candidate.', accepted=False)
    step('current-probe', dict(action='probe', probe_id='integrity'),
        'The actual boundary rejection identifies the missing current-candidate probe; request the named fixture.')
    current = session.current_probe()
    assert current and current['handle'] != old_probe['handle']
    assert session.observation(old_probe['handle'])[1] == old_body
    step('phase-boundary', dict(action='fork_ready', expected_candidate_id=session.candidate.candidate_id),
        'Both actual current outcomes and complete delivered A records now satisfy the declared boundary.',
        account='Phase A progress repair is saved and its actual prefork check passed. The current integrity output is archived; Phase B must recover its exact candidate-bound result.')
    assert session.phase == 'B' and not session.ranges and not session.saved and not session.delivered_sources
    assert session.candidate.candidate_id == module.fixture['phase_candidate_ids']['A']
    step('released-target-rejected', dict(action='patch', path='workflow/progress.py', old='return 1', new='return 2',
        expected_candidate_id=session.candidate.candidate_id, expected_file_sha256=session.candidate.file_sha256('workflow/progress.py')),
        'Negative authority fixture: historical acquisition does not make the released source currently editable.', accepted=False)
    step('observation-inventory', dict(action='observation_history', before=0),
        'The Phase B task requires the current integrity result. Inspect the bounded original-operation identities and candidate bindings.')
    entries = session.pairs[-1]['result']['entries']
    observed, = [r for r in entries if r['action'] == 'probe' and r['candidate_matches_current']]
    step('recover-current-observation', observed['retrieve'],
        'The actual inventory identifies integrity on the current candidate; reopen that exact record, not the older probe.')
    result = session.pairs[-1]['result']
    page, = result['saved_results']
    probe = load_json_strict(page['exact_utf8'])
    assert probe['candidate_id'] == session.candidate.candidate_id and probe['probe_id'] == 'integrity'
    marker, = [line.split('=', 1)[1] for line in probe['observation'].splitlines() if line.startswith('marker=')]
    view = select('label-and-observation', 'codec/label.py',
        'The task names the label target; retain the just-recovered original result together with its exact source.',
        results=[page['handle']])
    visible_pages = [*view['working_set']['saved_results'],
        *((view.get('latest_feedback') or {}).get('result', {}).get('saved_results', []))]
    assert any(r['handle'] == page['handle'] and r['next_offset'] is None
        and r['exact_utf8'] == page['exact_utf8'] for r in visible_pages)
    patch('label-repair', 'codec/label.py', 'return value.strip().upper()',
        'return ' + repr(marker) + ' + value.strip().upper()',
        'The actual recovered fixture body supplies the marker; preserve the exact existing strip/upper expression.')
    assert session.current_probe() is None  # Earlier observation is now historical.
    assert session.observation(old_probe['handle'])[1] == old_body
    records('B')
    check('current-public-pass', 'public')
    assert session.scoped_check_state('public')['passed'] and all(r['complete'] for r in session.coverage_status())
    step('submit', dict(action='submit', expected_candidate_id=session.candidate.candidate_id),
        'Both saved repairs, complete delivered B records and the actual current public pass support submission.')
    assert session.submitted
    return dict(classification='scripted_information_path_not_actor_behavior', submitted=True,
        trials=trials, requests=session.requests_used, operations=session.calls_used,
        final_candidate=session.candidate.candidate_id, all_required_delivered=True,
        old_probe=old_probe, recovered_current_probe=current)


def qualify(module, loop, adapter, store, folder):
    results, initial_feedback = {}, copy.deepcopy(adapter.preceding_feedback)
    try:
        for variant in ('complete', 'crowded-recovery'):
            session = module.initial_session()
            module.attach_observations(session, folder / variant, loop.log)
            adapter.preceding_feedback.clear()
            def record(row, current):
                stem = variant + '/' + row['name']
                state_raw, candidate_raw = canonical_json_bytes(module.snapshot(current)), module.candidate_bytes(current.candidate)
                artifacts = [store.put(stem + '.json', canonical_json_bytes(row)),
                    store.put(stem + '-state.json', state_raw), store.put(stem + '-candidate.json', candidate_raw)]
                if loop.log is not None:
                    loop.log.append('scripted_phase_step', dict(variant=variant, name=row['name'], completion_sent=False), artifacts)
                # Test the persistence boundary, not just the in-memory object.
                restored = module.restore(load_json_strict(state_raw), load_json_strict(candidate_raw), folder / variant, replay=True)
                assert canonical_json_bytes(restored.view()) == canonical_json_bytes(current.view())
                assert canonical_json_bytes(module.snapshot(restored)) == state_raw
                assert restored.observation_rows() == current.observation_rows()
                for entry in current.observation_rows():
                    assert restored.observation(entry['handle']) == current.observation(entry['handle'])
            results[variant] = journey(module, session, loop.measure, adapter.preceding_feedback,
                variant=variant, record=record)
        return dict(submitted=results['complete']['submitted'], variants=results, no_completion_calls=True)
    finally:
        adapter.preceding_feedback[:] = initial_feedback
