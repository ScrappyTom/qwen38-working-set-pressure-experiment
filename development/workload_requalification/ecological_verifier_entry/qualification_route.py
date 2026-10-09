"""Evaluator-only source-supported route; never supplied to Qwen."""
import copy
from pathlib import Path
import ecological_task as study
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, load_json_strict

helpers = study.load_private('verifier_route_helpers', study.ROOT /
    'development/workload_requalification/ecological_observation_entry/qualification_route.py')
CLASSIFICATION = 'evaluator-authored information-path qualification; zero model inference'

def capture_shown(view, handle, raw):
    latest = view['latest_feedback']['result'] if view['latest_feedback'] else {}
    results = [latest]
    for page in [*view['working_set']['saved_results'], *latest.get('saved_results', [])]:
        if page.get('offset') == 0 and page.get('next_offset') is None:
            results.append(load_json_strict(page['exact_utf8']))
    matches = [r for r in results if r.get('kind') == 'imported_observation' and r.get('handle') == handle]
    assert len(matches) == 1 and matches[0]['content_utf8'].encode() == raw

def repair(body, stage):
    """Engineering specimen only, derived from the exact task/source/diagnostic."""
    text = body.decode()
    if stage >= 1:
        text = text.replace('path.is_absolute() and ".." in path.parts', 'path.is_absolute() or ".." in path.parts')
    if stage >= 2:
        text = text.replace('max(1, max(timeout, MAX_COMMAND_TIMEOUT_SECONDS))',
                            'max(1, min(timeout, MAX_COMMAND_TIMEOUT_SECONDS))')
    if stage >= 3:
        text = text.replace('Path, PurePosixPath', 'Path, PurePosixPath, PureWindowsPath')
        text = text.replace('if path.is_absolute() or ".." in path.parts',
                            'if PureWindowsPath(normalized).drive or path.is_absolute() or ".." in path.parts')
        # Only this function's conversion handler is in scope.
        old = '        timeout = int(value)\n    except (TypeError, ValueError):'
        text = text.replace(old, '        timeout = int(value)\n    except (TypeError, ValueError, OverflowError):')
    return text.encode()

def qualify(module, loop, adapter, store, folder):
    preceding = copy.deepcopy(adapter.preceding_feedback)
    try:
        return _qualify(module, loop, adapter, store, folder)
    finally:
        adapter.preceding_feedback[:] = preceding

def _qualify(module, loop, adapter, store, folder):
    branch = Path(folder)/'scripted/verifier'
    session = module.initial_session()
    initial = session.candidate
    module.attach_observations(session, branch, loop.log)
    adapter.preceding_feedback.clear()
    trials, checks = [], []
    bodies = module.imports()[2]
    entries = session.view()['imported_observations']['entries']
    chosen = next(r['handle'] for r in entries if r['observed_candidate_id'] == initial.candidate_id)

    def act(action, basis, accepted=True):
        before = copy.deepcopy(session.view())
        old_receipts = copy.deepcopy(adapter.preceding_feedback)
        request = adapter.request_for(before)
        count = loop.measure(before)
        assert count <= 23808 and not session.delivery_blocked
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion=basis, operation=action)
        outcome = module.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
        assert len(outcome['operations']) == 1
        result = outcome['operations'][0]['result']
        assert result['accepted'] is accepted, outcome
        after = copy.deepcopy(session.view())
        following = loop.measure(after)
        assert following <= 23808 and not session.delivery_blocked
        if action['action'] == 'check':
            checks.append(copy.deepcopy(result))
            observation = session.observations.read(result['observation'])
            assert observation['executed'] and observation['capture_complete']
            assert observation['checker_sha256'] == module.PUBLIC_SHA
        assert all(session.candidate.file_map[p] == raw for p,raw in initial.files if p != module.TARGET)
        if len(session.pairs) >= 1:
            capture_shown(after, chosen, bodies[chosen])
        number = len(trials)+1
        stem = f'scripted/verifier/steps/{number:02d}'
        state = module.snapshot(session)
        candidate = module.candidate_bytes(session.candidate)
        row = dict(before_view=before, preceding_before=old_receipts, before_request=request,
            reply=reply, outcome=outcome, after_view=after,
            preceding_after=copy.deepcopy(adapter.preceding_feedback), input_tokens=count,
            next_input_tokens=following, information_path_justification=basis, classification=CLASSIFICATION)
        artifacts = [store.put(stem+'.json', canonical_json_bytes(row)),
            store.put(stem+'-state.json', canonical_json_bytes(state)),
            store.put(stem+'-candidate.json', candidate)]
        loop.log.append('scripted_information_path_step', dict(step=number, completion_sent=False,
            input_tokens=count, next_input_tokens=following), artifacts)
        restored = module.restore(state, session.candidate, branch, replay=True)
        assert canonical_json_bytes(module.snapshot(restored)) == canonical_json_bytes(state)
        assert restored.view() == session.view()
        for i in range(1,len(session.pairs)+1):
            assert restored.payload(f'RES-{i:04d}') == session.payload(f'RES-{i:04d}')
            assert restored.payload(f'EVT-{i:04d}') == session.payload(f'EVT-{i:04d}')
        trials.append(dict(step=number, action=action['action'], accepted=accepted,
            input_tokens=count, next_input_tokens=following, candidate_id=session.candidate.candidate_id,
            information_path_justification=basis))
        return result

    def check(basis):
        return act(dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id),basis)

    act(dict(action='reopen_observation', handle=chosen),
        'The exact displayed binding identifies the unique observation for the current candidate. Retrieve its body; this does not execute a verifier.')
    capture_handle = f'RES-{session.calls_used:04d}'
    # Complete single-file groups exercise turnover. No whole-file co-presence
    # assumption or inherited audit coverage is used.
    for path in module.REQUIRED_INSPECTION_PATHS:
        act(dict(action='work_on', sources=[dict(path=path,start_line=1,end_line=0)],results=[capture_handle]),
            'The task names this complete file before mutation. Replace the previous source group while retaining the exact incident; prior delivered coverage survives release.')
        row = helpers.shown_complete(session.view(),path)
        assert row['content'].encode() == initial.file_map[path]
    act(dict(action='work_on', sources=[dict(path=module.TARGET,start_line=1,end_line=0)],results=[capture_handle]),
        'The required inspection is complete after this dispatch. Reacquire the exact current target for editing; cumulative exposure does not grant current editing authority.')
    result = check('Execute the declared public check on the inspected original. Its historical failure is evidence of an earlier observation, not this execution.')
    helpers.failed_diagnostic(session.view(),result,'_safe_relative_path("../escape.py")')
    for stage in (1,2,3):
        before = session.candidate.file_map[module.TARGET]
        after = repair(initial.file_map[module.TARGET],stage)
        # Exact full current source is visible here. The atomic specimen uses
        # one whole-file replacement; it never changes another candidate file.
        source = helpers.shown_complete(session.view(),module.TARGET)
        assert source['content'].encode() == before
        if stage == 1:
            basis = 'The visible implementation uses conjunction although the task requires independent path rejection; actual public failure supplies the parent-path counterexample.'
        elif stage == 2:
            basis = 'The delivered public traceback now identifies timeout zero. The visible inner maximum implements a floor rather than the required upper clamp.'
        else:
            basis = ('The delivered expanded-check assertion identifies C:/outside.py as accepted. The complete source uses POSIX-only path classification and catches only TypeError/ValueError during timeout conversion. '
                'The declared native/invalid-input contract and visible code justify adding Windows drive classification and handling integer-conversion overflow; this is evaluator reasoning, not claimed learning from a nonexistent infinity diagnostic.')
        act(dict(action='patch',path=module.TARGET,old=before.decode(),new=after.decode(),
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256(module.TARGET)),basis)
        result = check('Run the declared check on the actual saved successor and consume its real outcome; a saved edit alone is not verification.')
        if stage == 1:
            helpers.failed_diagnostic(session.view(),result,'_bounded_timeout(0)')
        elif stage == 2:
            helpers.failed_diagnostic(session.view(),result,'unsafe path accepted')
        else:
            assert result['passed'] and session.view()['verification']['submission']['eligible']
    act(dict(action='submit',expected_candidate_id=session.candidate.candidate_id),
        'The complete actual public pass applies to the unchanged current candidate. Required source exposure is recorded and other24files remain exact. Submit.')
    assert session.submitted and [r['passed'] for r in checks] == [False,False,False,True]
    assert helpers.public_api(initial.file_map[module.TARGET]) == helpers.public_api(session.candidate.file_map[module.TARGET])
    return dict(classification=CLASSIFICATION,trials=trials,submitted=True,
        completion_requests=0,model_starting_state_untouched=True,checks_executed=4,
        chosen_observation=chosen,final_candidate_id=session.candidate.candidate_id,
        source_prerequisites=module.coverage_state(session),untouched_file_bodies=24)
