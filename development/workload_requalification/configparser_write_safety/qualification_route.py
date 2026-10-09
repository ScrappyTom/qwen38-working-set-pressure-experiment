"""Scripted code contribution with actual evidence before every guarded edit."""
import material
import reference_work
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
        trace.append(dict(step=step, support=support, action=operation['action'],
            input_tokens=count, following_tokens=after_count, accepted=result.get('accepted'),
            candidate_id=session.candidate.candidate_id))
        assert result['accepted'], result
        return result

    def locate(query, path=material.LIBRARY):
        result = act(dict(action='search', path=path, query=query, offset=0, limit=4),
                     'Task names this API/target. Locate its current implementation or declaration.')
        assert len(result['matches']) == 1
        return result

    def select(path, start, end):
        result = act(dict(action='work_on', sources=[dict(path=path, start_line=start, end_line=end)], results=[]),
                     'The preceding discovery or named small target supplies this current extent. Obtain exact source before editing.')
        row, = result['sources']
        assert row['requested_extent_complete']
        return row

    def patch(row, old, new, support):
        assert old in row['content']
        return act(dict(action='patch', path=row['path'], old=old, new=new,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256(row['path'])), support)

    failed = act(dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id),
                 'The new requirement is unverified. Run its actual public acceptance to identify unmet behavior.')
    assert failed['passed'] is False
    assessment = session.view()['verification']['checks']['public']['assessment']
    assert 'Add executable public write()' in canonical_json_bytes(assessment).decode()

    result = locate('"ConfigParser", "RawConfigParser"')
    line = result['matches'][0]['line']
    row = select(material.LIBRARY, line-3, line+3)
    patch(row, '"ConfigParser", "RawConfigParser"', '"InvalidWriteError", "ConfigParser", "RawConfigParser"',
          'The visible export tuple omits the exception explicitly required by the task. Add that public export; the initial check has not established working behavior.')

    result = locate('class Interpolation:')
    line = result['matches'][0]['line']
    row = select(material.LIBRARY, line, line+10)
    upstream = material.reference_source()
    start = upstream.index('class InvalidWriteError(Error):')
    exception = upstream[start:upstream.index('\n\nUNNAMED_SECTION =', start)]
    patch(row, 'class Interpolation:', exception+'\n\nclass Interpolation:',
          'The task defines an Error subclass, and this visible class boundary is a valid insertion anchor. Save the exception without claiming behavior is implemented.')

    result = locate('def _write_section(')
    region, = [r for r in result['regions'] if r.get('extent_kind') == 'enclosing Python function']
    row = select(material.LIBRARY, region['start_line'], region['end_line'])
    start = upstream.index('    def _validate_key_contents(self, key):')
    method = upstream[start:upstream.index('    def _validate_value_types(', start)]
    old = row['content']
    assert old.count('        for key, value in section_items:\n') == 1
    new = method + old.replace('        for key, value in section_items:\n',
                              '        for key, value in section_items:\n            self._validate_key_contents(key)\n')
    patch(row, old, new,
          'The delivered write loop handles each default/section option before rendering. Add the two requested key checks before that option is emitted; keep interpolation and formatting unchanged.')

    row = select(material.NEW_TESTS, 1, 0)
    patch(row, row['content'], reference_work.TESTS,
          'The named test module is an empty delivered target. Exercise the requested public write behavior and a valid custom-delimiter round trip.')

    result = locate('.. exception:: MultilineContinuationError', material.DOC)
    line = result['matches'][0]['line']
    row = select(material.DOC, line, line+10)
    original = material.baseline_files()[material.DOC].decode()
    replacement = reference_work.documentation().decode()
    before, after = original.split('.. exception:: MultilineContinuationError', 1)
    addition = replacement[len(before):].removesuffix(after)
    patch(row, '.. exception:: MultilineContinuationError', addition,
          'The visible exception declaration provides the insertion anchor. Document the implemented write-time checks and limits; preserve the earlier multiline declaration.')

    passed = act(dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id),
                 'Implementation, tests and documentation are saved. Execute the current checker; authored expectations are not a pass.')
    assert passed['passed'] is True, passed
    act(dict(action='submit', expected_candidate_id=session.candidate.candidate_id),
        'The actual current public pass has arrived after all saved edits. Submit the completed local contribution.')
    assert session.submitted
    return dict(submitted=True, decisions=len(trace), failed_then_passed=True,
                trace=trace, candidate_id=session.candidate.candidate_id)
