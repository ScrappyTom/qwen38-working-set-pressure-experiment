"""Reference coding path with actual discovery and source before every edit."""
import unnamed_material as material
import unnamed_reference as reference
from working_set_exp.jsonutil import canonical_json_bytes


def qualify(module, loop, adapter, store, folder):
    session = module.initial_session(folder/'scripted')
    module.attach_observations(session, folder/'scripted', loop.log)
    adapter.preceding_feedback = []
    trace = []

    def act(operation, support):
        before = session.view()
        count = loop.measure(before)
        assert count <= 23808
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion=support, operation=operation)
        host = module.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
        after = session.view()
        after_count = loop.measure(after)
        assert after_count <= 23808 and not session.delivery_blocked
        step = len(trace)+1
        for suffix, value in (('input', before), ('reply', reply), ('host', host),
            ('following', after), ('state', module.snapshot(session))):
            store.put(f'route/{step:02d}-{suffix}.json', canonical_json_bytes(value))
        result = session.pairs[-1]['result']
        trace.append(dict(step=step, action=operation['action'], support=support,
            input_tokens=count, following_tokens=after_count, accepted=result.get('accepted'),
            candidate_id=session.candidate.candidate_id))
        assert result['accepted'], result
        print('script', step, operation['action'], count, after_count, flush=True)
        return result

    def select(path, first, last):
        result = act(dict(action='work_on', sources=[dict(path=path, start_line=first, end_line=last)], results=[]),
            'Acquire the exact discovered anchor or named test target; replace unneeded prior source for this reference step.')
        row, = result['sources']
        assert row['requested_extent_complete']
        return row

    def patch(row, old, new, support):
        assert old in row['content']
        return act(dict(action='patch', path=row['path'], old=old, new=new,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256(row['path'])), support)

    initial = act(dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id),
        'The feature is absent in the saved baseline. Obtain actual unmet-contract feedback; no pass is inferred.')
    assert initial['passed'] is False
    for old, new in reference.CHANGES:
        query = old.splitlines()[0].strip()
        result = act(dict(action='search', path=material.LIBRARY, query=query, offset=0, limit=16),
            'The evaluator reference identifies this implementation anchor; search obtains current coordinates. '
            'This qualifies reference execution, not autonomous diagnosis or model selection.')
        assert len(result['matches']) == 1, (query, result['matches'])
        line = result['matches'][0]['line']
        row = select(material.LIBRARY, max(1,line-2), line+len(old.splitlines())+2)
        patch(row, old, new,
            'Apply this independently tested reference change to the delivered exact old text. '
            'The public task contract supports the behavior; reference authorship remains evaluator-side.')
    assert session.candidate.file_map[material.LIBRARY] == reference.library()
    row = select(material.NEW_TESTS, 1, 0)
    patch(row, material.SKELETON, reference.TESTS,
        'Save the independent reference regressions in the delivered empty target; not model-authored evidence.')
    # The existing public exception name is in the task and starting artifact.
    result = act(dict(action='search', path=material.DOC, query='.. exception:: InvalidWriteError', offset=0, limit=4),
        'Locate the saved write-safety documentation so the new feature can be added without replacing it.')
    line = result['matches'][0]['line']
    row = select(material.DOC, line, 0)
    original = material.baseline_files()[material.DOC]
    assert original.endswith(row['content'].encode())
    patch(row, row['content'], row['content']+reference.DOC_ADDITION,
        'Preserve the delivered existing tail and append the qualified feature description and ordinary example.')
    assert session.candidate.file_map == reference.files()
    checked = act(dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id),
        'Run the actual registered check on the saved successor; reference expectations are not an observation.')
    assert checked['passed'], checked
    act(dict(action='submit', expected_candidate_id=session.candidate.candidate_id),
        'The actual current public pass is in this input. Submit this scripted contribution.')
    assert session.submitted and session.requests_used <= module.MAX_REQUESTS
    return dict(submitted=True, decisions=len(trace), failed_then_passed=True,
                trace=trace, candidate_id=session.candidate.candidate_id)
