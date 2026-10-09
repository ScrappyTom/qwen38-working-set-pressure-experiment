"""Reuse qualified probe paths; add the original SABLE predecessor-check sequence."""
import copy

import receipt_bootstrap
import probe_qualification
import qualification_route as source_route
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict


def journey(module, session, measure, feedback, *, variant, record):
    if module.config['probe']:
        return probe_qualification.journey(module, session, measure, feedback, variant=variant, record=record)
    if variant == 'crowded-recovery':
        return source_route.journey(module, session, measure, feedback, variant=variant, record=record)
    trials, initial = [], session.candidate

    def step(name, action, support, *, account=None, accepted=True):
        before, preceding = copy.deepcopy(session.view()), copy.deepcopy(feedback)
        count = measure(before)
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion='Declared engineering qualification, not model work.', operation=action)
        if account is not None:
            reply['account'] = account
        outcome = module.process_reply(session, reply, measure, feedback)
        result = outcome['operations'][-1]['result']
        assert result['accepted'] is accepted, (name, result)
        after, following = session.view(), measure(session.view())
        assert max(count, following) <= 23808 and not session.delivery_blocked
        assert all(session.candidate.file_map[p] == raw for p, raw in initial.files
                   if p not in ('workflow/progress.py', 'api/name.py'))
        row = dict(name=name, variant=variant, input_support=support, before_view=before,
            preceding_before=preceding, reply=reply, outcome=outcome, after_view=after,
            preceding_after=copy.deepcopy(feedback), input_tokens=count, next_input_tokens=following)
        record(row, session)
        trials.append({k: row[k] for k in ('name','input_support','input_tokens','next_input_tokens')})
        return after

    def select(name, path, first=1):
        return step(name, dict(action='work_on', sources=[dict(path=path,start_line=first,end_line=0)],results=[]),
            'The actual phase assignment names this file; returned extent and continuation coordinate determine remaining acquisition.')

    def records(phase):
        for i, path in enumerate(session.phase_required[phase]):
            view = select(f'{phase}-record-{i}',path)
            while not source_route.exact_or_partial_complete(view,path):
                row, = [r for r in view['working_set']['sources'] if r['path']==path]
                first = row['returned_end_line']+1
                view = select(f'{phase}-record-{i}-from-{first}',path,first)

    def patch(name,path,old,new):
        row = source_route.exact_source(session.view(),path)
        assert old in row['content']
        return step(name,dict(action='patch',path=path,old=old,new=new,
            expected_candidate_id=session.candidate.candidate_id,expected_file_sha256=row['file_sha256']),
            'The task states the desired behavior; this exact delivered current source supplies the replacement anchor and guards.')

    def check(name,scope):
        return step(name,dict(action='check',check_id=scope,expected_candidate_id=session.candidate.candidate_id),
            'The actual assignment names this scope and current candidate; only execution establishes its scoped outcome.')

    records('A')
    select('progress-source','workflow/progress.py')
    check('initial-prefork-failure','prefork')
    assert session.scoped_check_state('prefork')['passed'] is False
    patch('progress-repair','workflow/progress.py','return 0','return 1')
    check('current-prefork-pass','prefork')
    step('phase-boundary',dict(action='fork_ready',expected_candidate_id=session.candidate.candidate_id),
        'Actual complete A coverage, saved progress and the current prefork pass justify the boundary.',
        account='Progress is saved and passed prefork. Phase B requires its own public check before the name edit and another on the successor.')
    assert session.phase=='B' and not session.ranges and not session.delivered_sources
    assert session.candidate.candidate_id==module.fixture['phase_candidate_ids']['A']
    check('predecessor-public-pass','public')
    earlier=session.scoped_check_state('public')
    assert earlier['passed'] and 'does not test normalized-name' in session.view()['verification']['checks']['public']['assessment']['explanation']
    step('released-source-edit-rejected',dict(action='patch',path='workflow/progress.py',old='return 1',new='return 2',
        expected_candidate_id=session.candidate.candidate_id,expected_file_sha256=session.candidate.file_sha256('workflow/progress.py')),
        'Negative authority fixture: old delivered coverage is not currently visible exact source.',accepted=False)
    select('name-source','api/name.py')
    patch('name-repair','api/name.py','return value.strip().casefold()',"return 'sable-' + value.strip().casefold()")
    current=session.scoped_check_state('public')
    assert current['passed'] and not current['applies_to_current'] and current['candidate_id']==earlier['candidate_id']
    step('stale-pass-submit-rejected',dict(action='submit',expected_candidate_id=session.candidate.candidate_id),
        'Negative applicability fixture: the public pass belongs to the predecessor; no successor check has occurred.',accepted=False)
    records('B')
    check('successor-public-pass','public')
    assert session.scoped_check_state('public')['applies_to_current']
    assert all(r['complete'] for r in session.coverage_status())
    step('submit',dict(action='submit',expected_candidate_id=session.candidate.candidate_id),
        'The actual successor pass, saved changes and full B delivery support closure; independent review still checks name behavior.')
    return dict(classification='scripted_information_path_not_actor_behavior',submitted=session.submitted,
        trials=trials,requests=session.requests_used,operations=session.calls_used,
        final_candidate=session.candidate.candidate_id,all_required_delivered=True)


def qualify(module,loop,adapter,store,folder):
    results, initial_feedback = {}, copy.deepcopy(adapter.preceding_feedback)
    try:
        for variant in ('complete','crowded-recovery'):
            session=module.initial_session()
            module.attach_observations(session,folder/variant,loop.log)
            adapter.preceding_feedback.clear()
            def record(row,current):
                stem=variant+'/'+row['name']
                state_raw=canonical_json_bytes(module.snapshot(current))
                candidate_raw=module.candidate_bytes(current.candidate)
                artifacts=[store.put(stem+'.json',canonical_json_bytes(row)),store.put(stem+'-state.json',state_raw),
                    store.put(stem+'-candidate.json',candidate_raw)]
                if loop.log is not None:
                    loop.log.append('scripted_phase_step',dict(variant=variant,name=row['name'],completion_sent=False),artifacts)
                restored=module.restore(load_json_strict(state_raw),load_json_strict(candidate_raw),folder/variant,replay=True)
                assert canonical_json_bytes(restored.view())==canonical_json_bytes(current.view())
                assert canonical_json_bytes(module.snapshot(restored))==state_raw
                if module.config['probe']:
                    assert restored.observation_rows()==current.observation_rows()
                    for entry in current.observation_rows():
                        assert restored.observation(entry['handle'])==current.observation(entry['handle'])
            results[variant]=journey(module,session,loop.measure,adapter.preceding_feedback,variant=variant,record=record)
        return dict(submitted=results['complete']['submitted'],variants=results,no_completion_calls=True)
    finally:
        adapter.preceding_feedback[:]=initial_feedback
