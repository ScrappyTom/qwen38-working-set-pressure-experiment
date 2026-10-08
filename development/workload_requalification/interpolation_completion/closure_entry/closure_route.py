"""A scripted closure supported by the real next input, with no new check."""
from working_set_exp.jsonutil import canonical_json_bytes


def qualify(module, loop, adapter, store, folder):
    session = module.initial_session(folder/'scripted')
    module.attach_observations(session, folder/'scripted', loop.log)
    adapter.preceding_feedback = module.initial_preceding_feedback()
    before = session.view()
    count = loop.measure(before)
    assert before['latest_feedback']['sequence'] == 187
    assert before['latest_feedback']['result']['passed']
    assert before['verification']['submission']['eligible']
    source = module.candidate_bytes(session.candidate)
    session.mark_delivered(before)
    session.begin_request()
    support = ('The actual preceding public CHK-0187 passed on this unchanged candidate and registered checker. '
               'The unchanged contribution contract requests submission after a public pass. '
               'This is a scripted engineering transition, not a model choice.')
    reply = dict(discussion=support, operation=dict(action='submit', expected_candidate_id=session.candidate.candidate_id))
    result = module.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
    following = session.view()
    after_count = loop.measure(following)
    assert session.submitted and not session.delivery_blocked
    assert len(result['operations']) == 1 and result['operations'][0]['result']['accepted']
    assert module.candidate_bytes(session.candidate) == source
    assert max(count, after_count) <= 23808
    restored = module.restore(module.snapshot(session), session.candidate, folder/'scripted', replay=True)
    assert restored.view() == session.view()
    for name, value in (('input', before), ('reply', reply), ('host', result), ('following', following),
                        ('state', module.snapshot(session)), ('candidate', module.read_bytes(source))):
        store.put(f'route/01-{name}.json', canonical_json_bytes(value))
    return dict(decisions=1, submitted=True, candidate_id=session.candidate.candidate_id,
        input_tokens=count, following_tokens=after_count, actual_operations=1,
        new_checks_executed=0, assistance=support)
