"""Source-supported engineering route, never supplied as actor instructions."""
import copy
from pathlib import Path

from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes

CLASSIFICATION = 'evaluator-scripted feasibility, not Qwen selection or continuity'

def current_source(view, path):
    sources = view['working_set']['sources']
    if view['latest_feedback']:
        result = view['latest_feedback']['result']
        sources = sources + result.get('sources', []) + ([result['source']] if 'source' in result else [])
    rows = [s for s in sources if s['path']==path and s['whole_file_shown']]
    if not rows:
        raise ValueError('Whole current source not actually displayed: '+path)
    return rows[0]

def qualify(module, loop, adapter, store, folder):
    preceding = copy.deepcopy(adapter.preceding_feedback)
    try:
        return _qualify(module, loop, adapter, store, Path(folder))
    finally:
        adapter.preceding_feedback[:] = preceding

def _qualify(module, loop, adapter, store, folder):
    branch = folder/'scripted/contribution'
    session = module.initial_session()
    module.attach_observations(session, branch, loop.log)
    adapter.preceding_feedback[:] = module.initial_preceding_feedback()
    initial, trials, checks = session.candidate, [], []

    def checkpoint(stem):
        state = canonical_json_bytes(module.snapshot(session))
        artifacts = [store.put(stem+'-state.json',state),
            store.put(stem+'-candidate.json',module.candidate_bytes(session.candidate)),
            store.put(stem+'-preceding-feedback.json',canonical_json_bytes(adapter.preceding_feedback))]
        loop.log.append('scripted_state_saved',dict(stem=stem,completion_sent=False),artifacts)
        restored = module.restore(load_json_strict(state),session.candidate,branch,replay=True)
        if module.snapshot(restored)!=module.snapshot(session) or restored.view()!=session.view():
            raise ValueError('Scripted checkpoint reconstruction differs')
        for i in range(1,len(session.pairs)+1):
            for prefix in ('EVT','RES'):
                if restored.payload(f'{prefix}-{i:04d}')!=session.payload(f'{prefix}-{i:04d}'):
                    raise ValueError('Restored historical payload differs')
        return sha256_bytes(state)

    def act(action,basis,evidence):
        before = copy.deepcopy(session.view())
        preceding_before = copy.deepcopy(adapter.preceding_feedback)
        request,count = adapter.request_for(before),loop.measure(before)
        if count>23808 or session.delivery_blocked:
            raise ValueError('Actual scripted decision input does not fit')
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion=basis,operation=action)
        outcome = module.process_reply(session,reply,loop.measure,adapter.preceding_feedback)
        if any(not row['result'].get('accepted') for row in outcome['operations']):
            raise ValueError('Source-supported scripted operation rejected: '+repr(outcome))
        result = outcome['operations'][-1]['result']
        following = loop.measure(session.view())
        if following>23808 or session.delivery_blocked:
            raise ValueError('Complete immediate feedback does not fit')
        if any(session.candidate.file_map[p]!=raw for p,raw in initial.files
               if p not in (module.TARGET,module.SAVED_RUNS)):
            raise ValueError('Non-target source changed')
        if action['action']=='check':
            observation = session.observations.read(result['observation'])
            if (not observation['capture_complete'] or not observation['executed']
                    or observation['candidate_id']!=session.candidate.candidate_id
                    or observation['checker_sha256']!=module.PUBLIC_SHA):
                raise ValueError('Actual check scope/candidate/capture differs')
            checks.append(copy.deepcopy(result))
        stem=f'scripted/contribution/steps/{len(trials)+1:02d}'
        artifact=store.put(stem+'.json',canonical_json_bytes(dict(before_view=before,
            preceding_before=preceding_before,before_request=request,reply=reply,outcome=outcome,
            after_view=session.view(),preceding_after=adapter.preceding_feedback,
            input_tokens=count,next_input_tokens=following,information_path_justification=basis,
            decision_support=evidence,classification=CLASSIFICATION)))
        loop.log.append('scripted_information_path_step',dict(step=len(trials)+1,
            input_tokens=count,next_input_tokens=following,completion_sent=False),[artifact])
        trials.append(dict(action=action['action'],input_tokens=count,next_input_tokens=following,
            candidate_id=session.candidate.candidate_id,snapshot_sha256=checkpoint(stem),
            information_path_justification=basis))
        return result

    def patch_source(path,old,new,basis):
        source=current_source(session.view(),path)
        if source['content'].count(old)!=1:
            raise ValueError('Actual displayed source anchor is absent or nonunique')
        return act(dict(action='patch',path=path,old=old,new=new,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=source['file_sha256']),basis,
            dict(region_ref=source['region_ref'],exact_old=old,task_contract=module.task_text()))

    checkpoint('scripted/contribution/starting')
    patch_source(module.SAVED_RUNS,
        '            if idx >= MAX_JSONL_LINES or len(artifacts) >= MAX_EMBEDDED_ARTIFACTS:',
        '            if idx > MAX_JSONL_LINES or len(artifacts) >= MAX_EMBEDDED_ARTIFACTS:',
        'Both initial inputs retain complete current saved-runs source. The original task permits the embedded artifact on line MAX; this visible loop stops at equality. Correct only that comparison, preserving the already-saved event behavior. The stale account does not establish whether a requirement is satisfied.')
    first=act(dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),
        'The embedded change is saved, not checked. Request the common actual full-contract observation; do not assume the historical count edit satisfies every count value.',
        dict(saved_change=session.pairs[-1]['result'],current_check=session.check_state()))
    if first['passed']:
        raise ValueError('Known zero-count gap unexpectedly passed')
    assessment=session.view()['verification']['checks']['public']['assessment']
    failed=[r for r in assessment['criteria'] if not r['met']
            and r.get('observation',{}).get('criterion_kind')=='behavioral_case']
    if (assessment['probe_cases_failed']!=3 or not failed or any(
            r['observation']['max_files']!=0 or r['observation']['expected']!=[]
            or r['observation']['actual']!=[{'path':'a.txt'}] for r in failed)):
        raise ValueError('Delivered failure does not establish the zero-count disagreement')
    if module.condition=='released':
        act(dict(action='read',path=module.TARGET,start_line=1,end_line=0),
            'Delivered boundary cases contradict zero-count behavior. The original task and current root identify importers.py; its implementation is absent after release. Read it rather than deriving behavior or edit authority from the stale account.',
            dict(delivered_failure=failed,task_names_target=True,source_absent=True))
    old='        rel = path.relative_to(root).as_posix()\n        artifacts.append({"path": rel})\n        if len(artifacts) >= max_files:\n            break\n'
    new='        if len(artifacts) >= max_files:\n            break\n        rel = path.relative_to(root).as_posix()\n        artifacts.append({"path": rel})\n'
    patch_source(module.TARGET,old,new,
        'The actual failure requires no files at zero, and current source appends before comparing the count. Relocate the existing guard before append. The comparison alone was already changed in historical EVT-0023 and did not establish this contract.')
    last=act(dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),
        'The correction is saved on a new candidate. Obtain its own full-contract check; neither the prior failure nor a saved expectation verifies this successor.',dict(saved_change=session.pairs[-1]['result']))
    if not last['passed'] or not session.view()['verification']['submission']['eligible']:
        raise ValueError('Actual corrected successor lacks full current pass')
    act(dict(action='submit',expected_candidate_id=session.candidate.candidate_id),
        'The actual public pass applies to the unchanged current candidate and common checker. Submit without treating the still-stale optional account as verification.',dict(current_pass=session.check_state()))
    if not session.submitted or [r['passed'] for r in checks]!=[False,True]:
        raise ValueError('Complete failed-check/correction/closure route absent')
    result=dict(classification=CLASSIFICATION,condition=module.condition,completion_requests=0,
        submitted=True,scripted_decisions=len(trials),checks_executed=len(checks),steps=trials,
        requests_used=session.requests_used,operations_used=session.calls_used,
        candidate_id=session.candidate.candidate_id,all_checkpoint_restorations_exact=True,
        primary_behavioral_failure_delivered=True,reference_work_not_in_actor_entry=True)
    store.put('scripted/contribution/RESULT.json',canonical_json_bytes(result))
    return result
