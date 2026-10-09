"""Original recurrent observation information path; scripted, not model evidence."""
import copy

import compass_bootstrap
import qualification_route as source_route
import probe_qualification
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict


def journey(module, session, measure, feedback, *, variant, record):
    if variant == 'crowded-recovery':
        return source_route.journey(module, session, measure, feedback, variant=variant, record=record)
    assert variant == 'complete'
    trials, initial, produced, recovered = [], session.candidate, [], []

    def step(name, action, support, *, accepted=True, account=None):
        before, preceding = copy.deepcopy(session.view()), copy.deepcopy(feedback)
        count = measure(before)
        assert count <= 23808 and not session.delivery_blocked
        session.mark_delivered(before); session.begin_request()
        reply = dict(discussion='Declared engineering qualification, not model work.', operation=action)
        if account is not None:
            reply['account'] = account
        outcome = module.process_reply(session, reply, measure, feedback)
        result = outcome['operations'][-1]['result']
        assert result['accepted'] is accepted, (name, result)
        after, following = session.view(), measure(session.view())
        assert following <= 23808 and not session.delivery_blocked
        assert all(session.candidate.file_map[p] == raw for p, raw in initial.files
            if p not in ('workflow/progress.py', 'codec/label.py', 'codec/header.py', 'codec/footer.py'))
        row = dict(name=name, variant=variant, input_support=support, before_view=before,
            preceding_before=preceding, reply=reply, outcome=outcome, after_view=after,
            preceding_after=copy.deepcopy(feedback), input_tokens=count, next_input_tokens=following)
        record(row, session)
        trials.append({k: row[k] for k in ('name','input_support','input_tokens','next_input_tokens')})
        return after

    def select(name, path, *, first=1, results=None):
        return step(name, dict(action='work_on', sources=[dict(path=path, start_line=first, end_line=0)], results=results or []),
            'The original assignment names this source; any continuation uses the exact returned extent. The evaluator selects this route.')

    def records(phase):
        for i, path in enumerate(session.phase_required[phase]):
            view = select(f'{phase}-record-{i}', path)
            while not source_route.exact_or_partial_complete(view, path):
                row, = [r for r in view['working_set']['sources'] if r['path'] == path]
                first = row['returned_end_line'] + 1
                view = select(f'{phase}-record-{i}-from-{first}', path, first=first)

    def patch(name, path, old, new, support):
        row = source_route.exact_source(session.view(), path)
        assert old in row['content']
        return step(name, dict(action='patch', path=path, old=old, new=new,
            expected_candidate_id=session.candidate.candidate_id, expected_file_sha256=row['file_sha256']), support)

    def check(name):
        return step(name, dict(action='check', check_id=session.view()['phase']['current_check'],
            expected_candidate_id=session.candidate.candidate_id),
            'The original phase identifies the check; only its actual execution establishes the current outcome.')

    def boundary(name):
        before = session.clone()
        phase, candidate = before.phase, before.candidate.candidate_id
        current = before.current_probe()
        assert current and all(r['complete'] for r in before.coverage_status())
        step(name, dict(action='fork_ready', expected_candidate_id=candidate),
            'The complete delivered records, actual current phase pass and actual current phase probe support this boundary.',
            account=f'Phase {phase} work is saved and its active check passed. The current compatibility result is archived; the next phase must recover its exact candidate-bound body.')
        assert not session.ranges and not session.saved and not session.delivered_sources
        assert session.candidate.candidate_id == candidate and session.current_probe() is None
        for old, raw in produced:
            assert session.observation(old['handle'])[1] == raw
        if phase != 'A':
            old = session.scoped_check_state('public')
            assert old['candidate_matches'] and not old['check_definition_matches'] and not old['applies_to_current']
        assert before.phase == phase and before.current_probe() == current

    records('A')
    select('A-progress-source', 'workflow/progress.py')
    step('A-early-probe', dict(action='probe', probe_id='compatibility'),
        'Negative applicability fixture: record an actual observation before the progress edit.')
    early = session.observation(session.current_probe()['handle'])
    check('A-initial-failure')
    assert not session.scoped_check_state('prefork')['passed']
    patch('A-progress-repair', 'workflow/progress.py', 'return 0', 'return 1',
        'Exact current source returns zero; the assignment requires one and the actual prefork check failed.')
    check('A-current-pass')
    assert session.scoped_check_state('prefork')['passed']
    step('A-stale-probe-rejected', dict(action='fork_ready', expected_candidate_id=session.candidate.candidate_id),
        'Negative binding fixture: the saved pass is current, but the probe predates the edit.', accepted=False)
    step('A-current-probe', dict(action='probe', probe_id='compatibility'),
        'The original task and actual rejection require compatibility on this saved candidate.')
    produced.append(session.observation(session.current_probe()['handle']))
    assert session.observation(early[0]['handle']) == early
    boundary('A-to-B')

    for phase, path, expression in (('B', 'codec/label.py', 'value.strip().upper()'),
            ('C', 'codec/header.py', 'value.strip().casefold()'), ('D', 'codec/footer.py', 'value.strip().upper()')):
        assert session.phase == phase
        previous_files = {p: session.candidate.file_map[p] for p in ('workflow/progress.py', 'codec/label.py', 'codec/header.py') if p != path}
        step(phase+'-released-edit-rejected', dict(action='patch', path=path,
            old=expression, new='"not authorized"', expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256(path)),
            'Negative authority fixture: inventory and prior coverage do not authorize an edit to released source.', accepted=False)
        step(phase+'-inventory', dict(action='observation_history', before=0),
            'The current task requires selecting the candidate-bound compatibility record; inspect the actual bounded inventory.')
        entries = session.pairs[-1]['result']['entries']
        row, = [r for r in entries if r['action'] == 'probe' and r['target'] == 'compatibility' and r['candidate_matches_current']]
        step(phase+'-exact-recovery', row['retrieve'],
            'The actual inventory identifies a compatibility production on the current candidate, distinct from older stale probes.')
        result = session.pairs[-1]['result']
        page, = result['saved_results']
        observed = load_json_strict(page['exact_utf8'])
        assert observed['candidate_id'] == session.candidate.candidate_id and observed['probe_id'] == 'compatibility'
        marker, = [line.split('=',1)[1] for line in observed['observation'].splitlines() if line.startswith('marker=')]
        recovered.append(dict(phase=phase, observation=row['handle'], original_result=page['handle']))
        view = select(phase+'-source-and-observation', path, results=[page['handle']])
        visible = [*view['working_set']['saved_results'],
            *((view.get('latest_feedback') or {}).get('result', {}).get('saved_results', []))]
        assert any(r['handle'] == page['handle'] and r['next_offset'] is None and r['exact_utf8'] == page['exact_utf8'] for r in visible)
        patch(phase+'-marker-repair', path, 'return '+expression, 'return '+repr(marker)+' + '+expression,
            'The exact recovered original observation supplies this marker; the current source supplies its normalization expression. No reference patch is consulted.')
        assert session.current_probe() is None
        assert all(session.candidate.file_map[p] == raw for p, raw in previous_files.items())
        if phase != 'D':
            records(phase)
        check(phase+'-current-pass')
        assert session.scoped_check_state('public')['passed']
        if phase != 'D':
            step(phase+'-current-probe', dict(action='probe', probe_id='compatibility'),
                'This phase explicitly requires producing compatibility after its saved repair and actual check.')
            produced.append(session.observation(session.current_probe()['handle']))
            boundary(phase+'-to-'+session.order[session.order.index(phase)+1])
        else:
            step('D-probe-rejected', dict(action='probe', probe_id='compatibility'),
                'Negative scope fixture: D has no new probe production.', accepted=False)
    assert len(produced) == len(recovered) == 3
    assert len({row['observed_candidate_id'] for row, raw in produced}) == 3
    assert all(r['complete'] for p in session.order for r in session.coverage_status(p))
    step('submit', dict(action='submit', expected_candidate_id=session.candidate.candidate_id),
        'The completed contributions, exact candidate-bound recoveries and actual final public pass support submission.')
    return dict(classification='scripted_information_path_not_actor_behavior', submitted=session.submitted,
        trials=trials, requests=session.requests_used, operations=session.calls_used,
        final_candidate=session.candidate.candidate_id, recovered=recovered, all_required_delivered=True)


def qualify(module, loop, adapter, store, folder):
    # Reuse exact serialized-state and observation-alias roundtrip recording.
    original = probe_qualification.journey
    try:
        probe_qualification.journey = journey
        return probe_qualification.qualify(module, loop, adapter, store, folder)
    finally:
        probe_qualification.journey = original
