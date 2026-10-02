"""Task-local continuous source delivery, independent of editing authority."""
import copy
import re

from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes

REQUIRED_PATHS = tuple('src/addressable_information_layer/' + name for name in
    ('saved_runs.py', 'importers.py', 'fixture_packs.py', 'records.py', 'content_log.py',
     'artifact_units.py', 'hashing.py', 'storage.py', 'renderer.py', 'policy.py', 'readiness.py'))
POLICY_ID = 'e20-first-mutation-continuous-source-coverage-v1'
SCHEMA = 'task-continuous-source-coverage-v1'
WITNESS_KEYS = frozenset(('path', 'candidate_id', 'file_sha256', 'start_line',
    'end_line', 'content_sha256', 'size_bytes', 'region_ref', 'request_number',
    'archive_actions_before_request', 'source_result_handle', 'source_index', 'presentation_sha256'))
BOUNDARY_KEYS = frozenset(('action_handle', 'request_number', 'path',
    'previous_candidate_id', 'candidate_id', 'coverage_sha256'))
REFERENCE_ADDITION = (
    'task_prerequisites is a declared task-local barrier before the first accepted file mutation. '
    'For each of its eleven required paths, exact current source must actually reach dispatched '
    'decision inputs continuously from line 1 through the true file end. Adjacent and overlapping '
    'delivered ranges accumulate; all files need not be shown together. A beginning and an EOF '
    'with an unread middle do not complete coverage. The compact coverage rows identify file '
    'identity, covered/missing line counts and the first missing interval. '
    'Status covers previous dispatches; exact current source shown in this input gains coverage '
    'on dispatch and need not be reread solely for the barrier. Acquisition, rendering or sizing '
    'without dispatch, accounts, outlines, addresses and partially recovered serialized history '
    'do not count. Complete recovered source qualifies only under the ordinary exact current-source '
    'rules. Coverage survives releasing unchanged source; changed file identity invalidates '
    'pre-boundary coverage. Use read or work_on/work_on_exact to select missing source; none is '
    'acquired automatically. Both mutation forms reject missing coverage, preserving the proposal '
    'and current files. Coverage establishes exposure, not comprehension or a semantic audit. '
    'It grants no editing authority: exact target text must still be visible in the current input. '
    'The first accepted mutation freezes its historical boundary and proof identity; ordinary '
    'source/version/check guards remain. Accounts, public checks and operation charging are unchanged.')


def coverage_policy():
    return dict(policy_id=POLICY_ID, required_paths=list(REQUIRED_PATHS),
        before='first_accepted_file_mutation',
        criterion='continuous_exact_current_source_in_dispatched_inputs_from_1_through_EOF',
        exposure_is_not_inspection=True, complete_file_required=True)


def coverage_state(session=None):
    return dict(schema=SCHEMA, policy=coverage_policy(),
        coverage=copy.deepcopy(session._source_coverage) if session is not None else {},
        first_mutation=copy.deepcopy(session._first_source_mutation) if session is not None else None)


def initialize(session):
    session._source_coverage = {}
    session._first_source_mutation = None


def _lines(version, path):
    return version.file_map[path].decode('utf-8').splitlines(keepends=True)


def union(intervals):
    merged = []
    for first, last in sorted(intervals):
        if merged and first <= merged[-1][1] + 1:
            merged[-1][1] = max(last, merged[-1][1])
        else:
            merged.append([first, last])
    return merged


def missing(intervals, first, last):
    result, cursor = [], first
    for a, b in intervals:
        if b < cursor:
            continue
        if a > last:
            break
        if a > cursor:
            result.append([cursor, min(last, a - 1)])
        cursor = max(cursor, b + 1)
        if cursor > last:
            break
    if cursor <= last:
        result.append([cursor, last])
    return result


def _applicable_intervals(session, path):
    row = session._source_coverage.get(path)
    return row['intervals'] if row and row['file_sha256'] == session.candidate.file_sha256(path) else []


def missing_extents(session):
    return {path: gaps for path in REQUIRED_PATHS
        if (gaps := missing(_applicable_intervals(session, path), 1,
                            len(_lines(session.candidate, path))))}


def view(session):
    active = session._first_source_mutation is None
    rows = []
    for path in REQUIRED_PATHS:
        total = len(_lines(session.candidate, path))
        row = session._source_coverage.get(path)
        matches = row is not None and row['file_sha256'] == session.candidate.file_sha256(path)
        intervals = row['intervals'] if matches else []
        gaps = missing(intervals, 1, total)
        covered = sum(b - a + 1 for a, b in intervals)
        rows.append(dict(path=path, file_sha256=session.candidate.file_sha256(path),
            total_lines=total, covered_lines=covered, missing_lines=total-covered,
            complete=not gaps, first_missing_interval=gaps[0] if gaps else None,
            current_file_matches=matches))
    return dict(policy_id=POLICY_ID, active=active, required_paths=list(REQUIRED_PATHS),
        status_as_of='previous dispatches; exact source shown here gains coverage on dispatch without another read',
        coverage=rows, missing_paths=list(missing_extents(session)) if active else [],
        first_mutation=copy.deepcopy(session._first_source_mutation),
        exposure_is_not_inspection=True, complete_file_required=True)


def _acquired_sources(pair):
    if (not isinstance(pair, dict) or not isinstance(pair.get('response'), dict)
            or not isinstance(pair.get('result'), dict)
            or pair['result'].get('accepted') is not True
            or pair['response'].get('action') not in ('read', 'work_on', 'work_on_exact')):
        return []
    result = pair['result']
    return [result['source']] if 'source' in result else result.get('sources', [])


def _carrier(session, number, source_index, path, fingerprint, before):
    """Validate preserved acquisition bytes without mistaking them for delivery."""
    if not 1 <= number <= before <= len(session.pairs):
        return None
    sources = _acquired_sources(session.pairs[number-1])
    if not isinstance(sources, list) or not 0 <= source_index < len(sources):
        return None
    source = sources[source_index]
    if (not isinstance(source, dict) or source.get('kind') != 'current_source'
            or source.get('path') != path or source.get('file_sha256') != fingerprint):
        return None
    a, b, raw = source.get('returned_start_line'), source.get('returned_end_line'), source.get('content')
    version = session.versions.get(source.get('candidate_id'))
    if (type(a) is not int or type(b) is not int or type(raw) is not str
            or version is None or path not in version.file_map
            or version.file_sha256(path) != fingerprint):
        return None
    lines = _lines(version, path)
    if not 1 <= a <= b <= len(lines) or raw != ''.join(lines[a-1:b]):
        return None
    action = session.pairs[number-1]['response']
    if action['action'] == 'work_on_exact':
        requested = action.get('regions')
        if (not isinstance(requested, list) or source_index >= len(requested)
                or requested[source_index] != session.region(path, fingerprint, a, b)['region_ref']):
            return None
    else:
        if action['action'] == 'read':
            requested = action if source_index == 0 else None
        else:
            group = action.get('sources')
            requested = group[source_index] if isinstance(group, list) and source_index < len(group) else None
        if (not isinstance(requested, dict) or requested.get('path') != path
                or type(requested.get('start_line')) is not int
                or type(requested.get('end_line')) is not int
                or requested['start_line'] != a
                or requested['end_line'] != 0 and requested['end_line'] < b):
            return None
    return dict(start=a, end=b, number=number, source_index=source_index)


def _carriers(session, path, fingerprint, before):
    carriers = []
    for number, pair in enumerate(session.pairs[:before], 1):
        for source_index, _ in enumerate(_acquired_sources(pair)):
            carrier = _carrier(session, number, source_index, path, fingerprint, before)
            if carrier is not None:
                carriers.append(carrier)
    return carriers


def _supported_subspans(carriers, first, last):
    """A displayed union may have several independent custody carriers."""
    cursor = first
    while cursor <= last:
        usable = [row for row in carriers if row['start'] <= cursor <= row['end']]
        if not usable:
            later = [row['start'] for row in carriers if cursor < row['start'] <= last]
            if not later:
                return
            cursor = min(later)
            continue
        carrier = min(usable, key=lambda row: (-row['end'], row['number'], row['source_index']))
        end = min(last, carrier['end'])
        yield cursor, end, carrier
        cursor = end + 1


def credit_delivered(session, delivered_view):
    if session._first_source_mutation is not None:
        return
    coverage = copy.deepcopy(session._source_coverage)
    before = len(session.pairs)
    presentation_sha = sha256_bytes(canonical_json_bytes(delivered_view))
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
            row = coverage.get(path)
            if row is None or row['file_sha256'] != fingerprint:
                row = dict(file_sha256=fingerprint, intervals=[], witnesses=[])
            carriers = _carriers(session, path, fingerprint, before)
            for first, last in missing(row['intervals'], span['start_line'], span['end_line']):
                for a, b, carrier in _supported_subspans(carriers, first, last):
                    exact = session.source(dict(path=path, start_line=a, end_line=b))
                    raw = exact['content'].encode('utf-8')
                    if not raw:
                        continue
                    row['witnesses'].append(dict(path=path, candidate_id=session.candidate.candidate_id,
                        file_sha256=fingerprint, start_line=a, end_line=b,
                        content_sha256=sha256_bytes(raw), size_bytes=len(raw),
                        region_ref=exact['region_ref'], request_number=session.requests_used+1,
                        archive_actions_before_request=before,
                        source_result_handle=f"RES-{carrier['number']:04d}",
                        source_index=carrier['source_index'], presentation_sha256=presentation_sha))
                    row['intervals'] = union([*row['intervals'], [a, b]])
            if row['witnesses']:
                coverage[path] = row
    session._source_coverage = coverage


def mutation_rejection(session):
    if session._first_source_mutation is not None:
        return None
    gaps = missing_extents(session)
    if not gaps:
        return None
    return dict(accepted=False, rejection_code='missing_source_coverage', policy_id=POLICY_ID,
        missing_paths=list(gaps), missing_extents=gaps,
        error=('No edit committed: the task requires complete exact delivered source before '
            'the first mutation. Missing current-file line intervals are listed in missing_extents. '
            'Select them through read or work_on/work_on_exact and then resubmit with current '
            'guards. Files need not be visible together; stored/acquired but undelivered source '
            'does not count. Exposure does not establish comprehension or current edit eligibility.'),
        candidate_id=session.candidate.candidate_id,
        exact_action_handle=f'EVT-{len(session.pairs)+1:04d}')


def record_first_mutation(session, result):
    if result.get('accepted') is not True or session._first_source_mutation is not None:
        return
    boundary = dict(action_handle=result['exact_action_handle'], request_number=session.requests_used,
        path=result['path'], previous_candidate_id=result['previous_candidate_id'],
        candidate_id=result['candidate_id'],
        coverage_sha256=sha256_bytes(canonical_json_bytes(session._source_coverage)))
    session._first_source_mutation = boundary
    result['source_prerequisite_boundary'] = copy.deepcopy(boundary)


def _hash(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def restore_state(session, state):
    """Restore byte/extent/origin proof; the saved-wire replayer proves dispatch."""
    if (not isinstance(state, dict) or set(state) != {'schema', 'policy', 'coverage', 'first_mutation'}
            or state['schema'] != SCHEMA or state['policy'] != coverage_policy()
            or not isinstance(state['coverage'], dict)
            or not set(state['coverage']) <= set(REQUIRED_PATHS)):
        raise ValueError('checkpoint continuous source coverage policy or shape differs')
    coverage, boundary = state['coverage'], state['first_mutation']
    for path, row in coverage.items():
        if (not isinstance(row, dict) or set(row) != {'file_sha256', 'intervals', 'witnesses'}
                or not _hash(row['file_sha256']) or not isinstance(row['witnesses'], list)
                or not row['witnesses'] or not isinstance(row['intervals'], list)):
            raise ValueError('checkpoint source coverage row differs')
        derived, total = [], None
        for witness in row['witnesses']:
            if (not isinstance(witness, dict) or set(witness) != WITNESS_KEYS or witness['path'] != path
                    or witness['file_sha256'] != row['file_sha256']
                    or not all(_hash(witness[key]) for key in ('candidate_id', 'file_sha256',
                        'content_sha256', 'presentation_sha256'))
                    or any(type(witness[key]) is not int for key in ('start_line', 'end_line',
                        'size_bytes', 'request_number', 'archive_actions_before_request', 'source_index'))
                    or not 2 <= witness['request_number'] <= session.requests_used
                    or not 1 <= witness['archive_actions_before_request'] <= len(session.pairs)
                    or witness['source_index'] < 0 or witness['size_bytes'] <= 0):
                raise ValueError('checkpoint continuous source witness differs')
            version = session.versions.get(witness['candidate_id'])
            if (version is None or path not in version.file_map
                    or version.file_sha256(path) != row['file_sha256']):
                raise ValueError('checkpoint source coverage version differs')
            lines = _lines(version, path)
            total = len(lines)
            first, last = witness['start_line'], witness['end_line']
            if not 1 <= first <= last <= total or missing(derived, first, last) != [[first, last]]:
                raise ValueError('checkpoint source coverage extent or new contribution differs')
            raw = ''.join(lines[first-1:last]).encode('utf-8')
            handle = witness['source_result_handle']
            if type(handle) is not str or re.fullmatch('RES-[0-9]{4,}', handle) is None:
                raise ValueError('checkpoint source coverage origin handle differs')
            number = int(handle[4:])
            if handle != f'RES-{number:04d}':
                raise ValueError('checkpoint source coverage origin is not canonical')
            carrier = _carrier(session, number, witness['source_index'], path,
                row['file_sha256'], witness['archive_actions_before_request'])
            if (carrier is None or not carrier['start'] <= first <= last <= carrier['end']
                    or not raw or witness['size_bytes'] != len(raw)
                    or witness['content_sha256'] != sha256_bytes(raw)
                    or witness['region_ref'] != session.region(path, row['file_sha256'], first, last)['region_ref']):
                raise ValueError('checkpoint source coverage bytes or acquisition differs')
            derived = union([*derived, [first, last]])
        if (len(row['witnesses']) > total
                or any(not isinstance(interval, list) or len(interval) != 2
                    or any(type(value) is not int for value in interval) for interval in row['intervals'])
                or row['intervals'] != derived):
            raise ValueError('checkpoint coverage union or bounded proof differs')
    edits = [(number, pair) for number, pair in enumerate(session.pairs, 1)
        if pair['response'].get('action') in session.mutation_actions
        and pair['result'].get('accepted') is True]
    if bool(edits) != (boundary is not None):
        raise ValueError('checkpoint first mutation presence differs')
    if boundary is not None:
        if (not isinstance(boundary, dict) or set(boundary) != BOUNDARY_KEYS
                or type(boundary['request_number']) is not int
                or not 1 <= boundary['request_number'] <= session.requests_used
                or set(coverage) != set(REQUIRED_PATHS)):
            raise ValueError('checkpoint first mutation shape or complete coverage differs')
        number, pair = edits[0]
        result = pair['result']
        expected = dict(action_handle=f'EVT-{number:04d}', request_number=boundary['request_number'],
            path=result['path'], previous_candidate_id=result['previous_candidate_id'],
            candidate_id=result['candidate_id'], coverage_sha256=sha256_bytes(canonical_json_bytes(coverage)))
        before = session.versions.get(result['previous_candidate_id'])
        if (boundary != expected or result.get('source_prerequisite_boundary') != expected or before is None):
            raise ValueError('checkpoint first mutation receipt differs')
        for path, row in coverage.items():
            if (before.file_sha256(path) != row['file_sha256']
                    or row['intervals'] != [[1, len(_lines(before, path))]]
                    or any(w['archive_actions_before_request'] >= number
                        or w['request_number'] > boundary['request_number'] for w in row['witnesses'])):
                raise ValueError('checkpoint first mutation temporal or continuous coverage differs')
    session._source_coverage = copy.deepcopy(coverage)
    session._first_source_mutation = copy.deepcopy(boundary)
    return session
