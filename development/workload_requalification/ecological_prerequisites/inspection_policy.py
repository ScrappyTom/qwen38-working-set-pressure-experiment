"""Exact exposure is a mechanical prerequisite, not a claim of inspection."""
import copy
import re

from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes

REQUIRED_PATHS = tuple('src/addressable_information_layer/' + name for name in
    ('summary_graph.py', 'summaries.py', 'records.py', 'policy.py'))
POLICY_ID = 'e19-first-mutation-exact-exposure-v1'
SCHEMA = 'task-source-exposure-v1'
WITNESS_KEYS = frozenset(('path', 'candidate_id', 'file_sha256', 'start_line',
    'end_line', 'content_sha256', 'size_bytes', 'region_ref', 'request_number',
    'archive_actions_before_request', 'source_result_handle', 'presentation_sha256'))
BOUNDARY_KEYS = frozenset(('action_handle', 'request_number', 'path',
    'previous_candidate_id', 'candidate_id', 'exposures_sha256'))
REFERENCE_ADDITION = (
    'task_prerequisites is a declared task-local barrier before the first accepted file mutation. '
    'Each required path needs some nonempty exact current source actually shown in an earlier '
    'decision input. Acquisition without delivery, an outline, address, account, imported '
    'observation or partial serialized history cannot supply this credit. '
    'Displayed exposure status covers previous dispatches. Exact current source visible in '
    'this input gains exposure credit on dispatch and need not be reread solely for this barrier. '
    'missing_paths names paths without previously recorded applicable exposure; request their source '
    'through read or work_on/work_on_exact. No source is acquired automatically. '
    'Exposure survives releasing unchanged source from selection, but does not grant current '
    'editing authority. Exact target text must still be visible for an edit. '
    'The host records request, source identity and extent; it does not establish comprehension '
    'or substantive inspection, and this E19 policy does not require every line. '
    'A missing prerequisite rejects the mutation and preserves its public proposal in the '
    'archive. Accounts and operation charging remain unchanged. Once the first mutation is '
    'accepted, its historical boundary remains recorded and ordinary source/version/check '
    'guards continue. Exposure is separate from checker applicability and model-authored accounts.')


def exposure_policy():
    return dict(policy_id=POLICY_ID, required_paths=list(REQUIRED_PATHS),
        before='first_accepted_file_mutation',
        criterion='some_nonempty_exact_current_source_in_dispatched_input',
        exposure_is_not_inspection=True, complete_file_required=False)


def exposure_state(session=None):
    return dict(schema=SCHEMA, policy=exposure_policy(),
        exposures=copy.deepcopy(session._source_exposures) if session is not None else {},
        first_mutation=copy.deepcopy(session._first_source_mutation) if session is not None else None)


def initialize(session):
    session._source_exposures = {}
    session._first_source_mutation = None


def missing_paths(session):
    return [path for path in REQUIRED_PATHS if path not in session._source_exposures
        or session._source_exposures[path]['file_sha256'] != session.candidate.file_sha256(path)]


def view(session):
    active = session._first_source_mutation is None
    return dict(policy_id=POLICY_ID, active=active, required_paths=list(REQUIRED_PATHS),
        status_as_of='previous dispatches; exact source shown here gains credit on dispatch without another read',
        missing_paths=missing_paths(session) if active else [],
        exposures=[dict(path=path, witness=copy.deepcopy(session._source_exposures.get(path)),
            current_file_matches=(path in session._source_exposures and
                session._source_exposures[path]['file_sha256'] == session.candidate.file_sha256(path)))
            for path in REQUIRED_PATHS],
        first_mutation=copy.deepcopy(session._first_source_mutation),
        exposure_is_not_inspection=True)


def _acquired_sources(pair):
    if (pair['result'].get('accepted') is not True or
            pair['response'].get('action') not in ('read', 'work_on', 'work_on_exact')):
        return []
    result = pair['result']
    return [result['source']] if 'source' in result else result.get('sources', [])


def _origin(session, path, fingerprint, first, last, content, before=None):
    """Bind to exact acquisition custody; this does not itself prove delivery."""
    for number, pair in enumerate(session.pairs[:before], 1):
        for source in _acquired_sources(pair):
            if (not isinstance(source, dict) or source.get('kind') != 'current_source'
                    or source.get('path') != path or source.get('file_sha256') != fingerprint):
                continue
            a, b = source.get('returned_start_line'), source.get('returned_end_line')
            raw = source.get('content')
            if (type(a) is not int or type(b) is not int or type(raw) is not str
                    or not a <= first <= last <= b):
                continue
            version = session.versions.get(source.get('candidate_id'))
            if version is None or path not in version.file_map or version.file_sha256(path) != fingerprint:
                continue
            lines = version.file_map[path].decode().splitlines(keepends=True)
            if (not 1 <= a <= b <= len(lines) or raw != ''.join(lines[a-1:b])
                    or content != ''.join(lines[first-1:last])):
                continue
            return f'RES-{number:04d}'
    return None


def credit_delivered(session, delivered_view):
    # After the first mutation preserve the original temporal witnesses, not a
    # later replacement of the evidence that authorized that boundary.
    if session._first_source_mutation is not None:
        return
    exposures = copy.deepcopy(session._source_exposures)
    for source in session.delivered_sources:
        if not isinstance(source, dict):
            continue
        try:
            spans = session._verified_source_ranges([source])
        except (KeyError, TypeError, ValueError, UnicodeError):
            continue
        for span in spans:
            path = span['path']
            if path not in REQUIRED_PATHS:
                continue
            fingerprint = session.candidate.file_sha256(path)
            if path in exposures and exposures[path]['file_sha256'] == fingerprint:
                continue
            exact = session.source(span)
            content = exact['content']
            if not content.encode():
                continue
            origin = _origin(session, path, fingerprint, span['start_line'],
                span['end_line'], content)
            if origin is None:
                continue
            exposures[path] = dict(path=path, candidate_id=session.candidate.candidate_id,
                file_sha256=fingerprint, start_line=span['start_line'], end_line=span['end_line'],
                content_sha256=sha256_bytes(content.encode()), size_bytes=len(content.encode()),
                region_ref=exact['region_ref'], request_number=session.requests_used+1,
                archive_actions_before_request=len(session.pairs), source_result_handle=origin,
                presentation_sha256=sha256_bytes(canonical_json_bytes(delivered_view)))
    session._source_exposures = exposures


def mutation_rejection(session):
    missing = missing_paths(session)
    if session._first_source_mutation is not None or not missing:
        return None
    return dict(accepted=False, rejection_code='missing_source_prerequisites',
        policy_id=POLICY_ID, missing_paths=missing,
        error=('No edit committed: before the first file mutation, exact current source '
            'must actually reach a decision input for these required paths: ' + ', '.join(missing)
            + '. Request their source using read or work_on/work_on_exact, then resubmit '
            'the proposal with current guards. Exposure is not substantive inspection.'),
        candidate_id=session.candidate.candidate_id,
        exact_action_handle=f'EVT-{len(session.pairs)+1:04d}')


def record_first_mutation(session, result):
    if result.get('accepted') is not True or session._first_source_mutation is not None:
        return
    boundary = dict(action_handle=result['exact_action_handle'],
        request_number=session.requests_used, path=result['path'],
        previous_candidate_id=result['previous_candidate_id'], candidate_id=result['candidate_id'],
        exposures_sha256=sha256_bytes(canonical_json_bytes(session._source_exposures)))
    session._first_source_mutation = boundary
    result['source_prerequisite_boundary'] = copy.deepcopy(boundary)


def _hash(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def restore_state(session, state):
    """Validate exact custody/version/temporal bindings; replay verifies wires."""
    if (not isinstance(state, dict) or set(state) != {'schema', 'policy', 'exposures', 'first_mutation'}
            or state['schema'] != SCHEMA or state['policy'] != exposure_policy()
            or not isinstance(state['exposures'], dict)
            or not set(state['exposures']) <= set(REQUIRED_PATHS)):
        raise ValueError('checkpoint source prerequisite policy or shape differs')
    exposures, boundary = state['exposures'], state['first_mutation']
    for path, witness in exposures.items():
        if (not isinstance(witness, dict) or set(witness) != WITNESS_KEYS or witness['path'] != path
                or not all(_hash(witness[k]) for k in ('candidate_id', 'file_sha256',
                    'content_sha256', 'presentation_sha256'))
                or any(type(witness[k]) is not int for k in ('start_line', 'end_line',
                    'size_bytes', 'request_number', 'archive_actions_before_request'))
                or not 2 <= witness['request_number'] <= session.requests_used
                or not 1 <= witness['archive_actions_before_request'] <= len(session.pairs)
                or witness['size_bytes'] <= 0):
            raise ValueError('checkpoint exact source exposure witness differs')
        version = session.versions.get(witness['candidate_id'])
        if version is None or version.file_sha256(path) != witness['file_sha256']:
            raise ValueError('checkpoint source exposure version differs')
        first, last = witness['start_line'], witness['end_line']
        lines = version.file_map[path].decode().splitlines(keepends=True)
        if not 1 <= first <= last <= len(lines):
            raise ValueError('checkpoint source exposure extent differs')
        content = ''.join(lines[first-1:last])
        region = session.region(path, witness['file_sha256'], first, last)
        if (not content.encode() or witness['size_bytes'] != len(content.encode())
                or witness['content_sha256'] != sha256_bytes(content.encode())
                or witness['region_ref'] != region['region_ref']
                or witness['source_result_handle'] != _origin(session, path,
                    witness['file_sha256'], first, last, content,
                    witness['archive_actions_before_request'])):
            raise ValueError('checkpoint source exposure bytes or acquisition differs')
    edits = [(number, pair) for number, pair in enumerate(session.pairs, 1)
        if pair['response'].get('action') in session.mutation_actions
        and pair['result'].get('accepted') is True]
    if bool(edits) != (boundary is not None):
        raise ValueError('checkpoint first mutation presence differs')
    if boundary is not None:
        if (not isinstance(boundary, dict) or set(boundary) != BOUNDARY_KEYS
                or type(boundary['request_number']) is not int
                or not 1 <= boundary['request_number'] <= session.requests_used
                or set(exposures) != set(REQUIRED_PATHS)):
            raise ValueError('checkpoint first mutation shape or prerequisites differ')
        number, pair = edits[0]
        result = pair['result']
        expected = dict(action_handle=f'EVT-{number:04d}', request_number=boundary['request_number'],
            path=result['path'], previous_candidate_id=result['previous_candidate_id'],
            candidate_id=result['candidate_id'],
            exposures_sha256=sha256_bytes(canonical_json_bytes(exposures)))
        before = session.versions.get(result['previous_candidate_id'])
        if (boundary != expected or result.get('source_prerequisite_boundary') != expected
                or before is None or any(w['archive_actions_before_request'] >= number
                    or w['request_number'] > boundary['request_number']
                    or before.file_sha256(path) != w['file_sha256']
                    for path, w in exposures.items())):
            raise ValueError('checkpoint first mutation receipt or temporal exposure differs')
    session._source_exposures = copy.deepcopy(exposures)
    session._first_source_mutation = copy.deepcopy(boundary)
    return session
