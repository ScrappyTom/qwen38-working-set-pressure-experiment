"""Task-supported scripted route and crowded capture transition; no model calls."""
import copy
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes
from temporal_audit import Trace


def source(view, path):
    row, = [r for r in view['working_set']['sources'] if r['path'] == path]
    assert row['whole_file_shown'] and sha256_bytes(row['content'].encode()) == row['file_sha256']
    return row


def journey(module, session, measure, *, feedback=None, record=None, request_for=None):
    feedback = [] if feedback is None else feedback
    trace, trials, original = Trace(module), [], session.candidate

    def step(name, operation, support):
        before, preceding = copy.deepcopy(session.view()), copy.deepcopy(feedback)
        count = measure(before)
        assert count <= 23808 and not session.delivery_blocked
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion='Offline engineering qualification.', operation=operation)
        outcome = module.process_reply(session, reply, measure, feedback)
        assert len(outcome['operations']) == 1 and outcome['operations'][0]['result']['accepted'], outcome
        trace.observe(name, before, outcome['operations'], session.versions, session.pairs, preceding)
        following = measure(session.view())
        assert following <= 23808 and not session.delivery_blocked
        assert all(session.candidate.file_map[p] == raw for p,raw in original.files if p not in (module.TARGET,module.SECONDARY))
        row = dict(name=name, input_support=support, before_view=before, preceding_before=preceding,
            before_request=request_for(before) if request_for else None, reply=reply, outcome=outcome,
            after_view=session.view(), preceding_after=copy.deepcopy(feedback), input_tokens=count, next_input_tokens=following)
        trials.append(dict(name=name,input_support=support,input_tokens=count,next_input_tokens=following))
        if record:
            record(row,session)
        return session.view()

    inventory = session.view()['imported_observations']['entries']
    chosen, = [r['handle'] for r in inventory if r['observed_candidate_id'] == session.candidate.candidate_id]
    view = step('marker',dict(action='reopen_observation',handle=chosen),
        'The actual initial directory has one row bound to the entry candidate. Obtain its recorded bytes; the older row is differently bound.')
    receipt = session.pairs[-1]['result']
    observed = load_json_strict(receipt['content_utf8'])
    assert observed['candidate_id'] == original.candidate_id and observed['probe_id'] == 'marker'
    marker = observed['observation'].removeprefix('marker=')
    assert observed['observation'] == 'marker='+marker and marker
    handle = receipt['exact_result_handle']
    for i,path in enumerate(module.REQUIRED_INSPECTION_PATHS):
        view = step('ledger-'+str(i),dict(action='work_on',sources=[dict(path=path,start_line=1,end_line=0)],results=[handle]),
            'The task names this complete ledger. Keep the already acquired marker receipt while replacing the preceding completed source; the task does not require all ledgers co-resident.')
        assert source(view,path)['content'].encode() == original.file_map[path]
    view = step('targets',dict(action='work_on',sources=[dict(path=p,start_line=1,end_line=0) for p in (module.TARGET,module.SECONDARY)],results=[handle]),
        'All ledger bodies reached preceding decisions. Obtain the two named target functions while retaining the exact observed marker.')
    row = source(view,module.TARGET)
    assert row['content'].count('return value.strip().upper()') == 1
    view = step('label',dict(action='patch',path=module.TARGET,old=row['content'],
        new=row['content'].replace('return value.strip().upper()', 'return '+repr(marker+'::')+' + value.strip().upper()'),
        expected_candidate_id=view['candidate_id'],expected_file_sha256=row['file_sha256']),
        'The acquired marker and task specify the prefix; the actual target gives its trim/uppercase expression. Save the first requested contribution.')
    label = session.candidate.file_map[module.TARGET]
    view = step('release',dict(action='work_on',sources=[dict(path=module.SECONDARY,start_line=1,end_line=0)],results=[]),
        'Declared engineering transition only: retain the second target and release the capture presentation. Preserve all saved label work and archived observations; this release is not imposed on the actor.')
    assert not any(r['shown_complete'] for r in view['imported_observations']['entries'])
    view = step('recover',dict(action='reopen_result',handle=handle,offset=0),
        'The task requires exact recovery if the marker body is absent. The observation directory still supplies its actual acquisition result handle. Recover that complete saved result without executing the probe.')
    # The existing saved-result operation keeps current sources. Qualify it rather
    # than assuming the target still has editing authority.
    row = source(view,module.SECONDARY)
    assert row['content'].count('return value.strip().casefold()') == 1
    view = step('footer',dict(action='patch',path=module.SECONDARY,old=row['content'],
        new=row['content'].replace('return value.strip().casefold()', 'return '+repr(marker+'::')+' + value.strip().casefold()'),
        expected_candidate_id=view['candidate_id'],expected_file_sha256=row['file_sha256']),
        'The complete historical marker receipt and exact footer source are again present together. Use the same observed marker and preserve the already saved label.')
    assert session.candidate.file_map[module.TARGET] == label
    view = step('check',dict(action='check',check_id='public',expected_candidate_id=view['candidate_id']),
        'Both ordered contributions are saved. Execute the original public checker on this actual successor; the imported probe does not establish a current pass.')
    assert view['verification']['submission']['eligible'] and view['verification']['checks']['public']['passed']
    step('submit',dict(action='submit',expected_candidate_id=view['candidate_id']),
        'The actual public pass is present and current. Submit the saved contribution without rewriting history or inferring coverage from that pass.')
    audit = trace.result()
    assert audit['temporal_contract_met'], audit
    return dict(classification='researcher_scripted_information_path_not_actor_behavior',submitted=session.submitted,
        trials=trials,audit=audit,requests=session.requests_used,operations=session.calls_used,completion_requests=0)


def qualify(module, loop, adapter, store, folder):
    initial_feedback = copy.deepcopy(adapter.preceding_feedback)
    try:
        session = module.initial_session()
        module.attach_observations(session,folder/'scripted',loop.log)
        def record(row,current):
            stem='route/'+row['name']
            loop.log.append('scripted_information_path_step',dict(name=row['name'],completion_sent=False),[
                store.put(stem+'.json',canonical_json_bytes(row)),
                store.put(stem+'-state.json',canonical_json_bytes(module.snapshot(current))),
                store.put(stem+'-candidate.json',module.candidate_bytes(current.candidate))])
            restored=module.restore(module.snapshot(current),current.candidate,folder/'scripted',replay=True)
            assert restored.view()==current.view()
        result=journey(module,session,loop.measure,feedback=adapter.preceding_feedback,record=record,request_for=adapter.request_for)
        result['crowded_transition']=crowded(module,loop,adapter,store,folder)
        return result
    finally:
        adapter.preceding_feedback[:]=initial_feedback


def crowded(module,loop,adapter,store,folder):
    session=module.initial_session()
    adapter.preceding_feedback.clear()
    rows=[]
    def act(action):
        before=copy.deepcopy(session.view()); count=loop.measure(before)
        assert count<=23808
        session.mark_delivered(before);session.begin_request()
        outcome=module.process_reply(session,dict(discussion='Declared crowded engineering case.',operation=action),loop.measure,adapter.preceding_feedback)
        following=loop.measure(session.view())
        assert following<=23808 and not session.delivery_blocked
        row=dict(before_view=before,action=action,outcome=outcome,after_view=session.view(),input_tokens=count,next_input_tokens=following)
        rows.append(row)
        loop.log.append('crowded_capture_transition',dict(step=len(rows),completion_sent=False),[
            store.put('crowded/'+str(len(rows))+'.json',canonical_json_bytes(row))])
        return outcome['operations'][-1]['result']
    chosen,=[r['handle'] for r in session.view()['imported_observations']['entries'] if r['observed_candidate_id']==session.candidate.candidate_id]
    handle=act(dict(action='reopen_observation',handle=chosen))['exact_result_handle']
    paths=list(module.REQUIRED_INSPECTION_PATHS); index=0; start=1; rejected=None
    for _ in range(12):
        result=act(dict(action='read',path=paths[index],start_line=start,end_line=0))
        if not result['accepted']:
            rejected=result;break
        source=result['source']
        if source['next_start_line'] is None:
            index+=1;start=1
        else: start=source['next_start_line']
        assert index<len(paths), 'crowding case did not reach rejection before consuming all ledgers'
    assert rejected is not None and session.view()['presentation']['mode']=='recovery'
    assert handle in session.saved and session.candidate.candidate_id==module.STARTING_ID
    assert not any(r['shown_complete'] for r in session.view()['imported_observations']['entries'])
    result=act(dict(action='work_on',sources=[dict(path=module.TARGET,start_line=1,end_line=0)],results=[handle]))
    assert result['accepted'] and session.view()['presentation']['mode']=='ordinary'
    assert any(r['handle']==chosen and r['shown_complete'] for r in session.view()['imported_observations']['entries'])
    return dict(classification='researcher_selected_crowding_and_recovery_not_actor_behavior',steps=len(rows),
        actual_rejection=rejected,maximum_input=max(max(r['input_tokens'],r['next_input_tokens']) for r in rows),
        recovered_input=rows[-1]['next_input_tokens'],candidate_unchanged=True,exact_capture_available_after_replacement=True)
