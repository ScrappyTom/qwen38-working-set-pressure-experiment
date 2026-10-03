"""Actual-input-supported engineering route; not a Qwen task outcome."""
import contract_task as entry
import engineering_reference as reference
from working_set_exp.jsonutil import canonical_json_bytes


def qualify(module, loop, adapter, store, folder):
    session = module.initial_session(folder / 'scripted')
    module.attach_observations(session, folder / 'scripted', loop.log)
    adapter.preceding_feedback = []
    trace = []
    def act(operation, support):
        before = session.view()
        count = loop.measure(before)
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion=support, operation=operation)
        host = module.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
        after = session.view()
        following = loop.measure(after)
        assert following <= 23808 and not session.delivery_blocked
        index = len(trace) + 1
        for suffix, value in (('input', before), ('reply', reply), ('host', host),
                              ('following', after), ('state', module.snapshot(session))):
            store.put(f'route/{index:02d}-{suffix}.json', canonical_json_bytes(value))
        trace.append(dict(step=index, support=support, action=operation['action'],
            input_tokens=count, following_tokens=following,
            accepted=session.pairs[-1]['result'].get('accepted')))
        return session.pairs[-1]['result']
    check = act(dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id),
        'The assignment identifies ungraded assertions and a new checker. Obtain its actual evidence before relying on the historical pass.')
    assert not check['passed'] and check['capture_complete']
    failed = check['report']['failed_criteria']
    assert 'authored_exact_exception_class' in failed and 'authored_exact_diagnostic_text' in failed
    assert 'No injected faults' not in check['report']['explanation']
    assert any(r.get('observation', {}).get('undetected_sites') for r in check['report']['criteria'])
    source = act(dict(action='read', path=entry.TEST, start_line=1, end_line=0),
        'The task and actual failure identify the editable test file and weak exception sites; acquire its exact current text before changing assertions.')
    shown = next(s for s in session.view()['working_set']['sources'] if s['path'] == entry.TEST)
    assert source['accepted'] and shown['whole_file_shown']
    assert 'assertRaises(RuntimeError)' in shown['content']
    corrected = reference.correct(shown['content'])
    edit = act(dict(action='replace_region', region=shown['region_ref'], new=corrected,
        expected_candidate_id=session.candidate.candidate_id),
        'The actual failure reports subtype-permitting sites and absent full messages. The delivered exact tests already contain full diagnostic expectations in companion cases; preserve them while making each raising site strict.')
    assert edit['accepted']
    check = act(dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id),
        'The edited assertions are authored work until the current successor executes. Run the actual declared checker.')
    assert check['passed']
    act(dict(action='submit', expected_candidate_id=session.candidate.candidate_id),
        'The actual current candidate/checker pass is present; seven non-test files are unchanged and the engineering contribution can submit.')
    assert session.submitted
    assert all(session.candidate.file_map[p] == raw for p, raw in module.inherited_candidate.file_map.items() if p != entry.TEST)
    return dict(submitted=True, decisions=len(trace), failed_then_passed=True, trace=trace,
        candidate_id=session.candidate.candidate_id,
        assistance='researcher-executed assertion correction supported by delivered check and source; not model capability')
