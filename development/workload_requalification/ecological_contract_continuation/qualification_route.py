"""Evaluator-only full-contract failure/correction route, zero completions."""
import copy
from pathlib import Path

from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes

CLASSIFICATION = 'evaluator-scripted native information path; not model selection or recovery'


def shown(view, path):
    rows = [row for row in view['working_set']['sources'] if row['path'] == path]
    if len(rows) != 1 or not rows[0]['whole_file_shown']:
        raise ValueError('Required exact current source is not wholly displayed')
    return rows[0]


def qualify(module, loop, adapter, store, folder):
    previous = copy.deepcopy(adapter.preceding_feedback)
    try:
        return _qualify(module, loop, adapter, store, folder)
    finally:
        adapter.preceding_feedback[:] = previous


def _qualify(module, loop, adapter, store, folder):
    branch = Path(folder) / 'scripted/contract_completion'
    session = module.initial_session()
    module.attach_observations(session, branch, loop.log)
    adapter.preceding_feedback[:] = module.initial_preceding_feedback()
    initial = session.candidate
    trials, checks = [], []

    def checkpoint(stem):
        state = canonical_json_bytes(module.snapshot(session))
        candidate = module.candidate_bytes(session.candidate)
        artifacts = [store.put(stem+'-state.json', state),
            store.put(stem+'-candidate.json', candidate),
            store.put(stem+'-preceding-feedback.json', canonical_json_bytes(adapter.preceding_feedback))]
        loop.log.append('scripted_state_saved', dict(stem=stem, completion_sent=False), artifacts)
        restored = module.restore(load_json_strict(state), session.candidate, branch, replay=True)
        if canonical_json_bytes(module.snapshot(restored)) != state or restored.view() != session.view():
            raise ValueError('Actual scripted checkpoint reconstruction differs')
        for number in range(1, len(session.pairs)+1):
            for kind in ('EVT', 'RES'):
                if restored.payload(f'{kind}-{number:04d}') != session.payload(f'{kind}-{number:04d}'):
                    raise ValueError('Actual historical payload restoration differs')
        return state

    def act(action, basis, account=None):
        before = copy.deepcopy(session.view())
        preceding = copy.deepcopy(adapter.preceding_feedback)
        request, count = adapter.request_for(before), loop.measure(before)
        if count > 23808 or session.delivery_blocked:
            raise ValueError('Scripted actual decision input does not fit')
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion=basis, operation=action)
        if account is not None:
            reply['account'] = account
        outcome = module.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
        if any(not row['result'].get('accepted') for row in outcome['operations']):
            raise ValueError('Scripted proposed operation rejected: '+repr(outcome))
        result = outcome['operations'][-1]['result']
        after, following = copy.deepcopy(session.view()), loop.measure(session.view())
        if following > 23808 or session.delivery_blocked:
            raise ValueError('Complete actual immediate feedback does not fit')
        if any(session.candidate.file_map[p] != raw for p, raw in initial.files if p != module.TARGET):
            raise ValueError('Non-target source changed')
        if action['action'] == 'check':
            observed = session.observations.read(result['observation'])
            if (not observed['capture_complete'] or not observed['executed']
                    or observed['checker_sha256'] != module.PUBLIC_SHA
                    or observed['candidate_id'] != session.candidate.candidate_id
                    or observed['streams'] != result['streams']):
                raise ValueError('Real check observation/candidate/capture differs')
            checks.append(copy.deepcopy(result))
        stem = 'scripted/contract_completion/steps/'+f'{len(trials)+1:02d}'
        artifact = store.put(stem+'.json', canonical_json_bytes(dict(before_view=before,
            preceding_before=preceding, before_request=request, reply=reply,
            outcome=outcome, after_view=after, preceding_after=adapter.preceding_feedback,
            input_tokens=count, next_input_tokens=following,
            information_path_justification=basis, classification=CLASSIFICATION)))
        loop.log.append('scripted_information_path_step', dict(step=len(trials)+1,
            input_tokens=count, next_input_tokens=following, completion_sent=False), [artifact])
        state = checkpoint(stem)
        trials.append(dict(step=len(trials)+1, action=action['action'], input_tokens=count,
            next_input_tokens=following, requests_used=session.requests_used,
            operations_used=session.calls_used, candidate_id=session.candidate.candidate_id,
            snapshot_sha256=sha256_bytes(state), information_path_justification=basis))
        return result

    checkpoint('scripted/contract_completion/starting')
    first = act(dict(action='check', check_id='public', expected_candidate_id=initial.candidate_id),
        'The new job requires the combined public definition. The displayed old pass has a different checker identity and is inapplicable; request the actual new observation without assuming a failure or importing post-seal results.')
    if first['passed']:
        raise ValueError('Known submitted candidate unexpectedly meets the complete boundary contract')
    assessment = session.view()['verification']['checks']['public']['assessment']
    failed = [row for row in assessment['criteria']
              if row.get('observation', {}).get('criterion_kind') == 'behavioral_case' and not row['met']]
    # The bounded overview shows two of three primary cases; their independent
    # observed values suffice to identify the zero-count disagreement.
    if (assessment['probe_cases_failed'] != 3 or not failed
            or any(row['observation']['max_files'] != 0
                or row['observation']['expected'] != []
                or row['observation']['actual'] != [{'path': 'a.txt'}] for row in failed)):
        raise ValueError('Actual initial failure lacks the useful zero-count diagnostic')
    act(dict(action='work_on', sources=[dict(path=module.TARGET, start_line=1, end_line=0),
        dict(path=module.SAVED_RUNS, start_line=1, end_line=0)], results=[]),
        'Actual new case feedback says zero allowed files returned a.txt rather than an empty list. The task names the directory importer; retain its exact implementation and the already-repaired JSONL implementation together for a focused correction. This is evaluator selection, not actor behavior.',
        account='The new boundary check contradicts the saved directory-count repair at zero. Preserve the completed byte and JSONL changes; inspect the count guard before revising it. No corrected successor has been checked yet.')
    source = shown(session.view(), module.TARGET)
    old = '        rel = path.relative_to(root).as_posix()\n        artifacts.append({"path": rel})\n        if len(artifacts) >= max_files:\n            break\n'
    new = '        if len(artifacts) >= max_files:\n            break\n        rel = path.relative_to(root).as_posix()\n        artifacts.append({"path": rel})\n'
    if source['content'].count(old) != 1:
        raise ValueError('The visible current guard/anchor is not unique')
    act(dict(action='patch', path=module.TARGET, expected_candidate_id=session.candidate.candidate_id,
        expected_file_sha256=source['file_sha256'], old=old, new=new),
        'The current exact source appends before testing the allowance; the actual failed cases require an empty list at zero. Check the count before append, retaining eligibility/order/size filtering and the prior inclusive byte change. This basis is visible code plus delivered case evidence, not an evaluator-only diagnostic.')
    last = act(dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id),
        'The correction is saved and its complete diff/current source is displayed. Check the actual successor under the combined public definition; the prior failed observation cannot establish this version.')
    if not last['passed'] or not session.view()['verification']['submission']['eligible']:
        raise ValueError('Corrected successor did not obtain its own complete applicable pass')
    act(dict(action='submit', expected_candidate_id=session.candidate.candidate_id),
        'Actual combined public execution passed on the unchanged current successor. Submit this new job; preserve the previous submit, old grades and model-authored account timing separately.')
    if not session.submitted or [row['passed'] for row in checks] != [False, True]:
        raise ValueError('Complete failure/correction/check/submission route is absent')
    value = dict(classification=CLASSIFICATION, completion_requests=0, submitted=True,
        inherited_requests=19, inherited_operations=28, scripted_decisions=len(trials),
        checks_executed=len(checks), steps=trials, candidate_id=session.candidate.candidate_id,
        requests_used=session.requests_used, operations_used=session.calls_used,
        all_checkpoint_restorations_exact=True, no_reference_work_in_prospective_entry=True,
        primary_behavioral_failure_delivered=True, non_target_source_preserved=True)
    store.put('scripted/contract_completion/RESULT.json', canonical_json_bytes(value))
    return value
