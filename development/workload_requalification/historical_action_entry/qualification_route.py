"""Scripted information path, distinct from Qwen's later choices."""
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes


def shown_action(view):
    pages = list(view['working_set']['saved_results'])
    latest = view.get('latest_feedback')
    if latest and latest['result'].get('kind') == 'saved_bytes':
        pages.append(latest['result'])
    rows = [row for row in pages if row.get('handle') == 'EVT-0001']
    assert rows
    page = rows[0]
    assert page['offset'] == 0 and page['next_offset'] is None
    assert len(page['exact_utf8'].encode()) == page['total_bytes']
    assert sha256_bytes(page['exact_utf8'].encode()) == page['sha256']
    return load_json_strict(page['exact_utf8'])


def target(view):
    row, = [row for row in view['working_set']['sources'] if row['path'] == 'report.py']
    assert row['whole_file_shown'] and row['returned_extent_complete']
    assert sha256_bytes(row['content'].encode()) == row['file_sha256']
    return row


def replacement(view):
    action, source = shown_action(view), target(view)
    before, after = action['old'], action['new']
    assert before.startswith('legacy_marker=') and after == 'legacy_marker=retired\n'
    marker = before.removeprefix('legacy_marker=').removesuffix('\n')
    assert '\n' not in marker and source['content'].count('"missing"') == 1
    return dict(action='patch', path=source['path'], old=source['content'],
        new=source['content'].replace('"missing"', repr(marker)),
        expected_candidate_id=view['candidate_id'], expected_file_sha256=source['file_sha256'])


def qualify(module, loop, adapter, store, folder):
    session = module.initial_session()
    module.attach_observations(session, folder / 'scripted', loop.log)
    trials = []
    feedback = []  # Do not alter the prospective actor adapter's first request.

    def step(name, operation, justification, accepted=True):
        before = session.view()
        session.mark_delivered(before)
        session.begin_request()
        result = module.process_reply(session, dict(discussion='Offline qualification.', operation=operation),
            loop.measure, feedback)
        assert len(result['operations']) == 1 and result['operations'][0]['result']['accepted'] is accepted
        after = session.view()
        count = loop.measure(after)
        assert count <= 23808 and not session.delivery_blocked
        prefix = 'route/' + name
        store.put(prefix + '-input.json', canonical_json_bytes(before))
        store.put(prefix + '-result.json', canonical_json_bytes(result))
        store.put(prefix + '-next-view.json', canonical_json_bytes(after))
        store.put(prefix + '-state.json', canonical_json_bytes(module.snapshot(session)))
        restored = module.restore(module.snapshot(session), session.candidate, folder / 'scripted', replay=True)
        assert canonical_json_bytes(restored.view()) == canonical_json_bytes(after)
        trials.append(dict(name=name, input_support=justification, feedback_tokens=count,
            candidate=session.candidate.candidate_id, accepted=accepted))
        return after

    initial = session.view()
    row, = initial['recent_activity']
    assert row['action'] == 'patch' and row['path'] == 'archive/source.dat' and row['episode'] == 'prior_work'
    view = step('recover-action', dict(action='reopen_event', handle=row['action_handle'], offset=0),
        'The task requires the old/new patch payload; the visible prior-work row gives EVT-0001 and the archive/source.dat target.')
    assert shown_action(view) == module.inherited_pair()['response']
    assert session.candidate.candidate_id == module.STARTING_ID and not session.delivered_sources
    view = step('read-target', dict(action='read', path='report.py', start_line=1, end_line=0),
        'The assignment names report.py, the root lists it, and no current source body has been displayed.')
    proposal = replacement(view)
    view = step('existing-failure', dict(action='check', check_id='public', expected_candidate_id=view['candidate_id']),
        'Recovered old marker differs from the displayed placeholder. The existing public check can observe that original defect.')
    assert view['verification']['checks']['public']['passed'] is False
    step('stale-guard', {**proposal, 'expected_candidate_id': module.inherited_pair()['response']['expected_candidate_id']},
        'Negative guard test only: deliberately supply the visible historical predecessor, not the current binding. This is not a recommended model step.', accepted=False)
    view = step('save-repair', proposal,
        'The complete recovered action establishes the removed marker; exact report.py supplies the replacement and current guards.')
    assert view['candidate_id'] != module.STARTING_ID
    assert session.candidate.file_map['archive/source.dat'] == module.starting_files()['archive/source.dat']
    view = step('check-successor', dict(action='check', check_id='public', expected_candidate_id=view['candidate_id']),
        'The actual edit receipt names the successor. The earlier failing check does not apply to it.')
    check = view['verification']['checks']['public']
    assert check['passed'] and check['applies_to_current'] and view['verification']['submission']['eligible']
    step('submit', dict(action='submit', expected_candidate_id=view['candidate_id']),
        'The actual current public pass is displayed, the target returns the recovered marker, and the retired source is unchanged.')
    assert session.submitted and session.requests_used == session.calls_used == 7
    assert session.pairs[0] == module.inherited_pair() and session.starting_archive_length == 1
    return dict(classification='evaluator_scripted_information_path_not_model_behavior',
        submitted=True, requests=7, new_operations=7, inherited_operations=1, trials=trials,
        final_candidate=session.candidate.candidate_id, account_required=False)
