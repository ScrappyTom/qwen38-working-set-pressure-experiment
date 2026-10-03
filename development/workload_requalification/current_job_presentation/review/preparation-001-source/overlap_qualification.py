"""Actual evidence paths and separately recorded checks; evaluator choices only."""
import overlap_reference as reference
import overlap_task as entry
from working_set_exp.jsonutil import canonical_json_bytes


def qualify(module, loop, adapter, store, folder):
    session = module.initial_session(folder/'scripted')
    module.attach_observations(session, folder/'scripted', loop.log)
    adapter.preceding_feedback = []
    trace = []
    def act(operation, support, account=None):
        before = session.view()
        count = loop.measure(before)
        assert count <= 23808
        session.mark_delivered(before); session.begin_request()
        reply = dict(discussion=support, operation=operation)
        if account is not None: reply['account'] = account
        host = module.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
        after = session.view(); following = loop.measure(after)
        assert following <= 23808 and not session.delivery_blocked
        index = len(trace)+1
        for suffix, value in (('input',before),('reply',reply),('host',host),
                              ('following',after),('state',module.snapshot(session))):
            store.put(f'route/{index:02d}-{suffix}.json', canonical_json_bytes(value))
        trace.append(dict(step=index, support=support, action=operation['action'],
            input_tokens=count, following_tokens=following,
            accepted=session.pairs[-1]['result'].get('accepted')))
        return session.pairs[-1]['result']

    first = act(dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id),
        'The task introduces a different coverage/checker contract; acquire its actual observation before treating prior acceptance as current verification.')
    assert not first['passed']
    regions = []
    for query in ('def _find_impl(', 'def singledispatch('):
        found = act(dict(action='search',path='Lib/functools.py',query=query,offset=0,limit=3),
            'The task names single dispatch, and its supplied source/reference exposes resolution helpers; obtain exact addresses rather than estimate lines.')
        regions += [r['region_ref'] for r in found['regions'] if r.get('name') in ('_find_impl','singledispatch')]
    assert len(regions) == 2
    act(dict(action='work_on_exact', regions=regions, results=[]),
        'The preceding searches return the governing resolver and dispatcher regions. Inspect their exact source together to determine ambiguity and cache behavior.')
    resolver = next(s['content'] for s in session.view()['working_set']['sources'] if 'def _find_impl(' in s['content'])
    assert 'Ambiguous dispatch:' in resolver and 'not issubclass(match, t)' in resolver
    for path, transform in ((entry.TEST, reference.tests), (entry.DOC, reference.documentation)):
        act(dict(action='read',path=path,start_line=1,end_line=0),
            'The task names this exact editable target; its complete current text is needed to preserve existing work and obtain editing authority.')
        source = next(s for s in session.view()['working_set']['sources'] if s['path']==path)
        act(dict(action='replace_region',region=source['region_ref'],
            expected_candidate_id=session.candidate.candidate_id,new=transform(source['content'])),
            'The delivered resolver refuses unrelated implicit ABC choices and the dispatcher tracks membership changes. The exact target permits an additive contribution; the result still needs execution.',
            account='The inspected resolver distinguishes unrelated implicit ABC choices from related bases and explicit concrete registrations. New expectations are authored work until the current checker executes.')
    check = act(dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),
        'New tests and examples have been saved but do not verify themselves. Execute the registered current acceptance, including ordinary standalone documentation.')
    assert check['passed'], check
    act(dict(action='submit',expected_candidate_id=session.candidate.candidate_id),
        'The actual applicable current public pass is visible; the saved additive contribution and protected files satisfy this engineering specimen.')
    assert session.submitted
    return dict(submitted=True, decisions=len(trace), failed_then_passed=True,
        trace=trace, candidate_id=session.candidate.candidate_id,
        assistance='researcher-selected operations/reference additions; not actor capability evidence')
