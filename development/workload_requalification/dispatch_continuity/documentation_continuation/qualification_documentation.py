"""Exact saved-entry failure, ordinary source, scoped correction and actual pass."""
import dispatch_task as study
import reference_documentation
from working_set_exp.jsonutil import canonical_json_bytes


def qualify(module, loop, adapter, store, folder):
    session = module.initial_session(folder / 'scripted')
    module.attach_observations(session, folder / 'scripted', loop.log)
    adapter.preceding_feedback = []
    trace = []

    def act(operation, support, account=None):
        before = session.view()
        count = loop.measure(before)
        assert count <= 23808
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion=support, operation=operation)
        if account is not None: reply['account'] = account
        host = module.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
        after = session.view()
        following = loop.measure(after)
        assert following <= 23808 and not session.delivery_blocked
        step = len(trace) + 1
        for suffix, value in (('input', before), ('reply', reply), ('host', host),
                              ('following', after), ('state', module.snapshot(session))):
            store.put(f'route/{step:02d}-{suffix}.json', canonical_json_bytes(value))
        trace.append(dict(step=step, support=support, operation=operation['action'],
            input_tokens=count, following_tokens=following,
            candidate_id=session.candidate.candidate_id,
            accepted=session.pairs[-1]['result'].get('accepted')))
        assert session.pairs[-1]['result']['accepted']
        return session.pairs[-1]['result']

    result = act(dict(action='check', check_id='public',
                      expected_candidate_id=session.candidate.candidate_id),
        'The task describes a new namespace and a historical pass; execute the actual current definition.')
    assert not result['passed']
    assert result['report']['failed_criteria'] == ['executable_documentation']
    current = session.view()
    assert '__main__.Payload' in str(current['latest_feedback'])
    path = 'Doc/howto/union-dispatch.rst'
    act(dict(action='read', path=path, start_line=1, end_line=0),
        'The delivered actual diagnostic and task identify this exact target. Acquire it before editing.')
    source, = [s for s in session.view()['working_set']['sources'] if s['path'] == path]
    new = reference_documentation.correction(source['content'])
    act(dict(action='replace_region', region=source['region_ref'],
             expected_candidate_id=session.candidate.candidate_id, new=new),
        'The review-directed task supplies the precedence fact; the actual new check supplies the namespace mismatch. This is an evaluator correction specimen, not a model choice.',
        account='The prior doc pass used a different namespace. The new observed failure concerns the class display; the review also identifies an overbroad precedence claim. Correction remains unverified.')
    result = act(dict(action='check', check_id='public',
                      expected_candidate_id=session.candidate.candidate_id),
        'The saved document is proposed work; execute the same new definition on its actual successor.')
    assert result['passed']
    act(dict(action='submit', expected_candidate_id=session.candidate.candidate_id),
        'The actual current pass is present; the scoped document correction is saved and all seven protected files remain exact.')
    assert session.submitted
    assert all(session.candidate.file_map[p] == raw
               for p, raw in module.inherited_candidate.file_map.items() if p != path)
    return dict(submitted=True, decisions=len(trace), failed_then_passed=True,
                trace=trace, candidate_id=session.candidate.candidate_id)
