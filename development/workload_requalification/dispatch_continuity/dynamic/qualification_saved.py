"""Engineering route justified by actual saved source and new check feedback."""
import dispatch_task as study
import reference_work
from working_set_exp.jsonutil import canonical_json_bytes

OLD_CACHE = """        if cache_token is None and hasattr(cls, '__abstractmethods__'):
            cache_token = get_cache_token()
"""
NEW_CACHE = """        if cache_token is None:
            members = cls.__args__ if _is_union(cls) else (cls,)
            if any(hasattr(member, '__abstractmethods__') for member in members):
                cache_token = get_cache_token()
"""


def qualify(module, loop, adapter, store, folder):
    session = module.initial_session(folder/'scripted')
    module.attach_observations(session, folder/'scripted', loop.log)
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
        after_count = loop.measure(after)
        assert after_count <= 23808 and not session.delivery_blocked
        step = len(trace)+1
        for suffix,value in (('input',before),('reply',reply),('host',host),
                             ('following',after),('state',module.snapshot(session))):
            store.put(f'route/{step:02d}-{suffix}.json', canonical_json_bytes(value))
        trace.append(dict(step=step, support=support, operation=operation['action'],
            input_tokens=count, following_tokens=after_count,
            candidate_id=session.candidate.candidate_id,
            accepted=session.pairs[-1]['result'].get('accepted')))
        assert session.pairs[-1]['result']['accepted']
        return session.pairs[-1]['result']

    check = act(dict(action='check', check_id='public',
                     expected_candidate_id=session.candidate.candidate_id),
        'The previous pass has a different definition. Execute the actual new contract before diagnosing it.')
    assert not check['passed']
    late_failed = 'late_virtual_registration_contract' in check['report']['failed_criteria']
    if late_failed:
        found = act(dict(action='search',path='Lib/functools.py',
                         query='def singledispatch(',offset=0,limit=3),
            'The new task and actual dynamic failure identify dispatch behavior; obtain its exact location.')
        region, = [r for r in found['regions'] if r.get('name')=='singledispatch']
        act(dict(action='work_on_exact',regions=[region['region_ref']],results=[]),
            'The preceding search returned this enclosing-function reference. Inspect the actual saved implementation.')
        source, = [s for s in session.view()['working_set']['sources'] if s['path']=='Lib/functools.py']
        body = source['content']
        assert body.count(OLD_CACHE)==1
        assert '_is_union(cls)' in body and 'for type_ in cls.__args__:' in body
        new = body.replace(OLD_CACHE, NEW_CACHE, 1)
        act(dict(action='replace_region',region=region['region_ref'],
                 expected_candidate_id=session.candidate.candidate_id,new=new),
            'Delivered source expands union members but initializes the ABC token from the union object. Keep the existing registration and validate membership-sensitive invalidation.',
            account='The new dynamic check fails after virtual membership changes. Current registration expands members but does not initialize ABC tracking from them. This is an engineering diagnosis, not an observed successful correction.')
    for path, new, support in (
        ('tests/test_virtual_registration.py',reference_work.DYNAMIC_TESTS,
         'The task requires both union forms and late registration. Write real before/after dispatch assertions in the delivered new target.'),
        ('Doc/howto/union-dispatch.rst',reference_work.DOC,
         'The task requests executable examples and the generic limitation. The delivered implementation and checks support these proposed examples; execution still must establish their output.')):
        act(dict(action='read',path=path,start_line=1,end_line=0),
            'The task names this small new target; acquire its exact current text before replacement.')
        source, = [s for s in session.view()['working_set']['sources'] if s['path']==path]
        act(dict(action='replace_region',region=source['region_ref'],
                 expected_candidate_id=session.candidate.candidate_id,new=new),support)
    check = act(dict(action='check',check_id='public',
                     expected_candidate_id=session.candidate.candidate_id),
        'Saved code, tests and prose are proposals. Execute the actual current new definition, preserving the first contribution.')
    assert check['passed']
    act(dict(action='submit',expected_candidate_id=session.candidate.candidate_id),
        'The actual current new-job pass is present; the completed new contribution and earlier work are saved.')
    assert session.submitted
    return dict(submitted=True,decisions=len(trace),failed_then_passed=True,
        late_contract_initially_failed=late_failed,trace=trace,
        candidate_id=session.candidate.candidate_id)
