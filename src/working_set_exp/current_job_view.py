"""Opt-in derived presentation; never changes records, guards or account meaning."""
import copy


def render(view, *, title, pairs, boundary, submitted):
    if not 0 <= boundary <= len(pairs):
        raise ValueError('job boundary is outside the operation archive')
    result = copy.deepcopy(view)
    verification = result['verification']
    current, historical = {}, {}
    for scope, state in verification['checks'].items():
        if state is None:
            current[scope] = dict(status='not_executed', applicable_observation=None)
            continue
        sequence = int(state['handle'].split('-')[1])
        origin = 'prior_work' if sequence <= boundary else 'current_job'
        if state['applies_to_current']:
            current[scope] = dict(status='passed' if state['passed'] else 'failed',
                evidence_origin=origin, **state)
        else:
            current[scope] = dict(status='not_executed_for_current_candidate_and_checker',
                applicable_observation=None)
            historical[scope] = {k: v for k, v in state.items() if k != 'assessment'}
            historical[scope]['evidence_origin'] = origin
            historical[scope]['meaning'] = 'This recorded outcome is unchanged; it does not verify the current candidate under the current checker.'
            if state.get('assessment'):
                historical[scope]['observation'] = state['assessment'].get('observation')
    verification['checks'] = current
    verification['historical_checks'] = historical
    verification['recorded_current_failures'] = verification.pop('outstanding')
    verification['recorded_current_failures_meaning'] = 'Executed applicable failures only; an empty list does not establish a pass or task completion.'
    result['current_job'] = dict(title=title,
        submission='accepted' if submitted else 'open',
        starting_archive_operations=boundary,
        verification_meaning='Applicability concerns the current candidate and registered checker. Historical acceptance remains unchanged.')
    accepted = [(i, p) for i, p in enumerate(pairs[:boundary], 1)
                if p['response']['action'] == 'submit' and p['result'].get('accepted')]
    if accepted:
        sequence, pair = accepted[-1]
        result['prior_work'] = dict(latest_accepted_submission=dict(
            action_handle=f'EVT-{sequence:04d}', result_handle=f'RES-{sequence:04d}',
            candidate_id=pair['result']['submitted_candidate_id'], outcome='accepted'),
            meaning='Historical acceptance is not the current job submission or an endorsement of its new requirements.')
    else:
        result['prior_work'] = dict(latest_accepted_submission=None)
    account = result.get('working_account')
    if account:
        sequence = int(account['action_handle'].split('-')[1])
        account['authored_in'] = 'prior_work' if sequence <= boundary else 'current_job'
    return result
