"""Evaluator-only correction journey, with each decision supported in its input."""
import re
import correction_task as entry
import engineering_reference as reference
from working_set_exp.jsonutil import canonical_json_bytes


def qualify(module, loop, adapter, store, folder):
    session = module.initial_session(folder/'scripted')
    module.attach_observations(session, folder/'scripted', loop.log)
    adapter.preceding_feedback = module.initial_preceding_feedback()
    trace = []

    def act(operation, support):
        before = session.view()
        count = loop.measure(before)
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion=support, operation=operation)
        outcome = module.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
        after = session.view()
        following = loop.measure(after)
        index = len(trace)+1
        for suffix, value in (('input', before), ('reply', reply), ('host', outcome), ('following', after),
                              ('state', module.snapshot(session)),
                              ('candidate', module.read_bytes(module.candidate_bytes(session.candidate)))):
            store.put(f'route/{index:02d}-{suffix}.json', canonical_json_bytes(value))
        trace.append(dict(step=index, support=support, action=operation['action'], input_tokens=count,
            following_tokens=following, operations=[r['action']['action'] for r in outcome['operations']]))
        assert following <= 23808 and not session.delivery_blocked
        assert all(r['result']['accepted'] for r in outcome['operations']), outcome
        restored = module.restore(module.snapshot(session), session.candidate, folder/'scripted', replay=True)
        assert restored.view() == session.view()
        return outcome

    view = session.view()
    assert 'UnboundLocalError' in str(view['verification'])
    shown = next(s for s in view['working_set']['sources'] if s['path'] == entry.TEST)
    old = shown['content']
    needle = 'except configparser.InterpolationMissingOptionError as e:\n            pass'
    assert old.count(needle) == 3
    fixed_lifetime = old.replace(needle, 'except configparser.InterpolationMissingOptionError as caught:\n            e = caught')
    result = act(dict(action='patch', path=entry.TEST, old=old, new=fixed_lifetime,
        expected_candidate_id=session.candidate.candidate_id, expected_file_sha256=session.candidate.file_sha256(entry.TEST)),
        'The actual prior check reports an exception variable used after its handler, and C64 now supplies the complete three affected methods. Retain the caught object in a separate local for the later assertions.')
    failed = result['operations'][-1]['result']
    assert not failed['passed'] and 'Bad value substitution:' in str(failed['report'])
    assert 'AssertionError' in str(failed['report'])
    target = next(s for s in session.view()['working_set']['sources'] if s['path'] == entry.TEST)
    assert '_assert_error_transport' in target['content']

    assert 'Lib/configparser.py' in str(session.view())
    page = act(dict(action='p0_page', path='Lib/configparser.py', offset=0),
        'The diagnostic disagrees with str(expected_args). The test names the library exception and the existing designated-source inventory identifies its file. Inspect the outline to locate its implementation and inherited behavior.')
    found = {r['name']: r['region_ref'] for r in page['operations'][0]['result'].get('regions', [])}
    needed = ('Error', 'InterpolationError', 'InterpolationMissingOptionError', 'BasicInterpolation', 'ExtendedInterpolation')
    while any(name not in found for name in needed):
        offset = page['operations'][0]['result']['next_offset']; assert offset is not None
        page = act(dict(action='p0_page', path='Lib/configparser.py', offset=offset),
            'Follow the actual outline continuation to locate the still-missing named policy or exception definition.')
        found.update({r['name']: r['region_ref'] for r in page['operations'][0]['result'].get('regions', [])})
    acquired = act(dict(action='work_on_exact', regions=[target['region_ref'], *[found[n] for n in needed]], results=[]),
        'Keep the actual saved test with exact exception bases and interpolation policies identified by the outline. The original diagnostic and source must establish the replacement expectation before editing it.')
    source = '\n'.join(s['content'] for s in acquired['operations'][0]['result']['sources'])
    assert 'self.message = msg' in source and '__str__ = __repr__' in source
    old = next(s for s in acquired['operations'][0]['result']['sources'] if s['path'] == entry.TEST)['content']
    new, count = re.subn(r'self\.assertIsInstance\(\n(\s+)(e[234]?), configparser.InterpolationMissingOptionError\)',
        r'self.assertIs(\n\1type(\2), configparser.InterpolationMissingOptionError)', old)
    assert count == 4
    wrong = '        self.assertEqual(str(e), str(expected_args))'
    assert new.count(wrong) == 1
    new = new.replace(wrong, '''        option, section, rawval, reference = expected_args
        expected_message = (
            "Bad value substitution: option {!r} in section {!r} contains "
            "an interpolation key {!r} which is not a valid option name. "
            "Raw value: {!r}".format(option, section, reference, rawval))
        self.assertEqual(str(e), expected_message)''')
    corrected = act(dict(action='patch', path=entry.TEST, old=old, new=new,
        expected_candidate_id=session.candidate.candidate_id, expected_file_sha256=session.candidate.file_sha256(entry.TEST)),
        'The delivered Error base preserves the diagnostic separately from args; the constructor supplies its exact template, and the task requires the exact class. Correct these assertions while preserving the actual lookup/transport cases.')
    assert corrected['operations'][-1]['result']['passed']
    test = next(s for s in session.view()['working_set']['sources'] if s['path'] == entry.TEST)
    retained = dict(path=entry.TEST, start_line=test['returned_start_line'], end_line=test['returned_end_line'])
    head = act(dict(action='work_on', sources=[retained, dict(path=entry.DOC, start_line=1, end_line=50)], results=[]),
        'The corrected tests have passed. Retain their exact current source while inspecting the named document and its reported extent for an additive contribution.')
    doc = next(s for s in head['operations'][0]['result']['sources'] if s['path'] == entry.DOC)
    tail = act(dict(action='work_on', sources=[retained, dict(path=entry.DOC,
        start_line=max(1, doc['file_total_lines']-40), end_line=doc['file_total_lines'])], results=[]),
        'The actual document metadata supplies its end. Obtain that exact tail while keeping the checked tests; preserve every existing document line and append a separate runnable explanation.')
    doc = next(s for s in tail['operations'][0]['result']['sources'] if s['path'] == entry.DOC)
    assert doc['next_start_line'] is None
    anchor = ''.join(doc['content'].splitlines(keepends=True)[-5:])
    assert anchor and session.candidate.file_map[entry.DOC].decode().count(anchor) == 1
    documented = act(dict(action='patch', path=entry.DOC, old=anchor, new=anchor+'\n\n'+reference.doc_addition(),
        expected_candidate_id=session.candidate.candidate_id, expected_file_sha256=session.candidate.file_sha256(entry.DOC)),
        'The visible checked tests establish missing/raw/resolved behavior for both policies and cross-section lookup. Append corresponding runnable examples at the exact visible document boundary; leave the earlier text unchanged.')
    assert documented['operations'][-1]['result']['passed']
    act(dict(action='submit', expected_candidate_id=session.candidate.candidate_id),
        'The actual current public check passed on the documentation successor. Submit the unchanged checked candidate.')
    assert session.submitted
    assert all(session.candidate.file_map[p] == raw for p, raw in module.inherited_candidate.file_map.items()
               if p not in (entry.TEST, entry.DOC))
    return dict(decisions=len(trace), trace=trace, submitted=True, actual_failure_then_correction=True,
        candidate_id=session.candidate.candidate_id,
        assistance='Evaluator-only supported sequence on actual failing work; no task-model completion')
