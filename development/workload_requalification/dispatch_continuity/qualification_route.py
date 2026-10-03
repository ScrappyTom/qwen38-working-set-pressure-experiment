"""Actual information paths; every choice states the input supporting it."""
import copy
import dispatch_task as study
import reference_work
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
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion=support, operation=operation)
        if account is not None: reply['account'] = account
        host = module.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
        after = session.view()
        after_count = loop.measure(after)
        assert after_count <= 23808 and not session.delivery_blocked
        index = len(trace)+1
        for suffix,value in (('input',before),('reply',reply),('host',host),('following',after),('state',module.snapshot(session))):
            store.put(f'route/{index:02d}-{suffix}.json', canonical_json_bytes(value))
        trace.append(dict(step=index, support=support, operation=operation['action'],
            input_tokens=count, following_tokens=after_count,
            candidate_id=session.candidate.candidate_id, accepted=session.pairs[-1]['result'].get('accepted')))
        return session.pairs[-1]['result']

    def select_file(path):
        act(dict(action='read',path=path,start_line=1,end_line=0),
            'Task names this small authored target; obtain its exact current text.')
        view = session.view()
        source, = [row for row in view['working_set']['sources'] if row['path'] == path]
        return source

    # An initial real failure is acquired, not inferred from an oracle.
    check = act(dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id),
        'The task defines a new contract; execution determines which starting obligations fail.')
    assert check['passed'] is False
    found = act(dict(action='search',path='Lib/functools.py',query='def singledispatch(',offset=0,limit=3),
        'The task names single dispatch; locate its exact governing implementation.')
    region, = [r for r in found['regions'] if r.get('name') == 'singledispatch']
    act(dict(action='work_on_exact',regions=[region['region_ref']],results=[]),
        'The preceding search supplied this exact enclosing-function address; inspect it before editing.')
    source, = [row for row in session.view()['working_set']['sources'] if row['path']=='Lib/functools.py']
    # Text is taken from the actual delivered body, never a guessed line extent.
    body = source.get('content', source.get('text', source.get('content_utf8')))
    if body is None:
        body = source['source_text']
    replacement = reference_work.library_replacement(body)
    act(dict(action='replace_region', region=region['region_ref'],
             expected_candidate_id=session.candidate.candidate_id, new=replacement),
        'Delivered source exposes class-only registration and per-key ABC tracking; implement class-member validation/registration and preserve cache invalidation.',
        account='Union members must be real runtime classes. Validation precedes registry updates; ABC tracking concerns members, not the union object. This is proposed understanding, not a passing check.')
    path = 'tests/test_union_registration.py'
    if module.phase == 'dynamic': path = 'tests/test_virtual_registration.py'
    source = select_file(path)
    # Read source references are mechanical host output; no location arithmetic.
    ref = source['region_ref']
    tests = reference_work.UNION_TESTS if module.phase=='union' else reference_work.DYNAMIC_TESTS
    act(dict(action='replace_region',region=ref,expected_candidate_id=session.candidate.candidate_id,new=tests),
        'The delivered target is the exact regression file; write independently executable examples of the requested behavior.')
    if module.phase == 'dynamic':
        source = select_file('Doc/howto/union-dispatch.rst')
        act(dict(action='replace_region',region=source['region_ref'],expected_candidate_id=session.candidate.candidate_id,new=reference_work.DOC),
            'Task names the documentation target; delivered exact text authorizes replacement and observed implementation supports these examples.')
    check = act(dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),
        'Saved changes are only proposals until the named current contract is executed.')
    assert check['passed'], check
    act(dict(action='submit',expected_candidate_id=session.candidate.candidate_id),
        'The actual applicable current public pass is present; all declared local work is saved.')
    assert session.submitted
    return dict(submitted=True, decisions=len(trace), failed_then_passed=True,
                trace=trace, candidate_id=session.candidate.candidate_id)
