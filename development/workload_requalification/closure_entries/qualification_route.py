"""Evidence-supported closure plus separate negative/recovery qualification."""
import copy
from working_set_exp.jsonutil import canonical_json_bytes


def journey(module, session, measure, feedback, *, variant, record=lambda row, session: None):
    trials = []

    def step(name, operation, support, accepted=True):
        before = session.view()
        preceding = copy.deepcopy(feedback)
        input_tokens = measure(before)
        session.mark_delivered(before)
        session.begin_request()
        outcome = module.process_reply(session, dict(discussion='Declared CPU/native qualification.', operation=operation), measure, feedback)
        assert len(outcome['operations']) == 1
        result = outcome['operations'][0]['result']
        assert result['accepted'] is accepted
        after = session.view()
        count = measure(after)
        assert count <= 23808 and not session.delivery_blocked
        row = dict(name=name, variant=variant, action=operation, input_support=support,
            before_view=before, preceding_before=preceding, input_tokens=input_tokens,
            outcome=outcome, after_view=after, preceding_after=copy.deepcopy(feedback), next_input_tokens=count)
        record(row, session)
        trials.append(dict(name=name, input_support=support, feedback_tokens=count, accepted=accepted))
        return after

    start = session.candidate
    view = session.view()
    assert len(view['recent_activity']) == 5 and not view['verification']['submission']['eligible']
    for row in view['recent_activity'][-2:]:
        assert row['historical_acquisition']['whole_file_returned']

    if variant == 'closure':
        view = step('current-check', dict(action='check', check_id='public', expected_candidate_id=view['candidate_id']),
            'Active Phase B requires a current public pass. Prior-work rows identify the accepted repair and complete named reads; the current verification is absent or inapplicable.')
        check = view['verification']['checks']['public']
        assert check['passed'] and check['applies_to_current'] and view['verification']['submission']['eligible']
        view = step('submit', dict(action='submit', expected_candidate_id=view['candidate_id']),
            'The actual current-candidate/current-checker pass has arrived. Original setup already supplied the acquisitions and repair; no new mutation occurred.')
        assert session.submitted and session.candidate == start
    elif variant == 'historical':
        for name, action in [('original-capture', dict(action='reopen_observation', handle='OBS-0003')),
                ('original-patch', dict(action='reopen_event', handle='EVT-0003', offset=0)),
                ('original-read', dict(action='reopen_result', handle='RES-0002', offset=0))]:
            view = step(name, action,
                'Address is in the original observation inventory or recent prior-work rows. This engineering branch qualifies exact recovery, not required actor work.')
        assert not view['verification']['submission']['eligible']
        step('old-assurance-rejected', dict(action='submit', expected_candidate_id=view['candidate_id']),
            'Negative qualification only: recovered historical data supplies no current pass. A truthful rejection must arrive.', accepted=False)
        assert session.candidate == start and not session.submitted
    elif variant == 'failed-check':
        path, broken = (('codec/label.py', 'def codec_label(value):\n    return value\n') if module.CASE == 'E14-CLOSURE-MINT'
            else ('invariants/stable.py', 'def invariant_ok():\n    return False\n'))
        view = step('read-target', dict(action='read', path=path, start_line=1, end_line=0),
            'Evaluator negative branch selects the implementation exercised by the original public checker. This is not a model-supplied diagnosis.')
        source, = [r for r in view['working_set']['sources'] if r['path'] == path]
        original = source['content']
        view = step('introduce-known-failure', dict(action='replace_region', region=source['region_ref'],
            expected_candidate_id=view['candidate_id'], new=broken),
            'Deliberate engineering counterexample using actual current source. Do not attribute this failure injection to the actor.')
        view = step('actual-failure', dict(action='check', check_id='public', expected_candidate_id=view['candidate_id']),
            'The just-saved deliberate counterexample needs execution; no outcome is fabricated.')
        assert view['verification']['checks']['public']['passed'] is False
        assert 'AssertionError' in canonical_json_bytes(session.pairs[-1]['result']).decode()
        source, = [r for r in view['working_set']['sources'] if r['path'] == path]
        view = step('restore-qualified-original', dict(action='replace_region', region=source['region_ref'],
            expected_candidate_id=view['candidate_id'], new=original),
            'Researcher restores the exact earlier acquired source after receiving actual failure. This tests transport/transition, not inference of a repair from the diagnostic.')
        assert session.candidate == start
        view = step('current-pass', dict(action='check', check_id='public', expected_candidate_id=view['candidate_id']),
            'The restored successor is the original saved work; execute the check rather than infer its result.')
        assert view['verification']['checks']['public']['passed']
        step('submit', dict(action='submit', expected_candidate_id=view['candidate_id']),
            'The actual applicable pass is delivered; the unchanged original contribution can close.')
        assert session.submitted
    else:
        raise ValueError('Unknown qualification variant')
    assert session.pairs[:5] == module.inherited_pairs()
    assert session.calls_used == session.requests_used == len(trials)
    return dict(classification='researcher_qualification_not_actor_behavior', variant=variant,
        submitted=session.submitted, requests=session.requests_used, new_operations=session.calls_used,
        inherited_operations=5, trials=trials, final_candidate=session.candidate.candidate_id)


def qualify(module, loop, adapter, store, folder):
    results = {}
    for variant in ('closure', 'historical', 'failed-check'):
        session = module.initial_session()
        module.attach_observations(session, folder / variant, loop.log)
        adapter.preceding_feedback.clear()
        def record(row, current):
            prefix = variant + '/' + row['name']
            store.put(prefix + '.json', canonical_json_bytes(row))
            store.put(prefix + '-state.json', canonical_json_bytes(module.snapshot(current)))
            store.put(prefix + '-candidate.json', module.candidate_bytes(current.candidate))
            restored = module.restore(module.snapshot(current), current.candidate, folder / variant, replay=True)
            assert canonical_json_bytes(restored.view()) == canonical_json_bytes(current.view())
        results[variant] = journey(module, session, loop.measure, adapter.preceding_feedback, variant=variant, record=record)
    adapter.preceding_feedback.clear()
    return dict(submitted=results['closure']['submitted'], variants=results,
        no_completion_calls=True, account_required=False)
