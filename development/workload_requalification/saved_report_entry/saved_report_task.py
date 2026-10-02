"""Declared assisted two-phase continuation; exact historical work stays historical."""
from __future__ import annotations

import copy
from pathlib import Path

import bootstrap
import compiler_task as compiler
from working_set_exp.accounted_contribution import process_reply as host_process_reply
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.working_session import INPUT_LIMIT

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent
PROPOSAL = ROOT / 'development/delivery_dialogue/proposal-check-001'
PROPOSAL_SEAL_SHA = '791eb9c1d709f598e8734987a35d06504b0e366e52390248e4d5d57e7abc0d82'
STARTING_ID = 'f7939c49b60d57f19b88dde8d31c6deb0ea036b6a3746c5d27b61d5ce0b99fd6'
REPORT = 'reports/incident.json'
ACTOR, SEED = dict(compiler.ACTOR), compiler.SEED
MAX_REQUESTS, MAX_OPERATIONS = 16, 41
PHASE_REQUESTS, PHASE_ACTOR_OPERATIONS = 8, 16
INHERITED_OPERATIONS, MAX_ARCHIVED_OPERATIONS = 3, 44
OWNER_DIRECTION = 'Continue the authorized repair/qualify/run programme with the distinct assisted saved-report continuation.'
read = compiler.read


def candidate_from_snapshot(value):
    rows = value['files']
    files = {row['path']: row['content_utf8'].encode() for row in rows}
    if len(files) != len(rows) or any(sha256_bytes(files[row['path']]) != row['sha256']
            or ('size_bytes' in row and len(files[row['path']]) != row['size_bytes']) for row in rows):
        raise ValueError('saved candidate contents differ')
    candidate = Candidate.create(files, max_file_bytes=value.get('max_file_bytes', 24_000))
    if candidate.candidate_id != value['candidate_id']:
        raise ValueError('saved candidate identity differs')
    return candidate


def starting_material():
    if sha256_file(PROPOSAL / 'SEAL.json') != PROPOSAL_SEAL_SHA:
        raise ValueError('saved proposal seal differs')
    seal = read(PROPOSAL / 'SEAL.json')
    if seal['status'] != 'completed_offline_checks':
        raise ValueError('saved proposal is not completed historical work')
    for row in seal['files']:
        path = (PROPOSAL / row['path']).resolve()
        if (not path.is_relative_to(PROPOSAL.resolve()) or path.stat().st_size != row['size_bytes']
                or sha256_file(path) != row['sha256']):
            raise ValueError('saved proposal artifact differs: ' + row['path'])
    original, checker, task, inventory, bodies = compiler.original_material()
    candidate = candidate_from_snapshot(read(PROPOSAL / 'candidate.json'))
    pairs = read(PROPOSAL / 'scripted-pairs.json')
    if (candidate.candidate_id != STARTING_ID or len(pairs) != INHERITED_OPERATIONS
            or candidate.file_map[REPORT] != b'{"builds": []}\n'
            or pairs[-1]['result'] != read(PROPOSAL / 'public-check-result.json')
            or pairs[1]['result'] != read(PROPOSAL / 'patch-result.json')):
        raise ValueError('saved work or prior records differ')
    if (pairs[-1]['response']['action'] != 'check' or pairs[-1]['result']['passed'] is not False
            or pairs[-1]['result']['checked_candidate_id'] != STARTING_ID
            or 'observation' in pairs[-1]['result'] or 'check_definition_sha256' in pairs[-1]['result']):
        raise ValueError('legacy check must remain an unchanged historical receipt')
    return candidate, pairs, original, checker, task, inventory, bodies


class Session(compiler.Session):
    def __init__(self, *args, **kwargs):
        self.phase = 1
        self.phase_start_requests = 0
        self.phase_start_actor_operations = 0
        self.phase_start_archive_length = INHERITED_OPERATIONS
        self.setup_sequences = ()
        self._setup_in_progress = False
        self.early_phase_one_submit = False
        super().__init__(*args, **kwargs)

    def actor_operations_used(self):
        return self.calls_used - len(self.setup_sequences)

    def phase_counters(self):
        requests = self.requests_used - self.phase_start_requests
        operations = self.actor_operations_used() - self.phase_start_actor_operations
        current_setup = [seq for seq in self.setup_sequences if seq > self.phase_start_archive_length]
        ranges = [[1, INHERITED_OPERATIONS]]
        for sequence in self.setup_sequences:
            if len(ranges) > 1 and sequence == ranges[-1][1] + 1:
                ranges[-1][1] = sequence
            else:
                ranges.append([sequence, sequence])
        return dict(phase=self.phase, phase_requests_limit=PHASE_REQUESTS,
            phase_requests_used=requests, phase_requests_remaining=PHASE_REQUESTS-requests,
            phase_actor_operation_limit=PHASE_ACTOR_OPERATIONS,
            phase_actor_operations_used=operations,
            phase_actor_operations_remaining=PHASE_ACTOR_OPERATIONS-operations,
            cumulative_requests_used=self.requests_used, actor_operations_used=self.actor_operations_used(),
            assisted_operations_new=len(self.setup_sequences), inherited_operations=INHERITED_OPERATIONS,
            assisted_operations_total=INHERITED_OPERATIONS+len(self.setup_sequences),
            archived_operations=len(self.pairs), backend_new_operations=self.calls_used,
            backend_new_operation_limit=MAX_OPERATIONS, setup_sequence_ranges=ranges,
            phase_setup_complete=(len(current_setup) == (4 if self.phase == 1 else 5)
                and all(self.pairs[seq-1]['result'].get('accepted') is True for seq in current_setup)))

    def phase_budget_available(self):
        value = self.phase_counters()
        return (not self.submitted and not self.delivery_blocked and not self.early_phase_one_submit
            and value['phase_setup_complete'] and value['phase_requests_remaining'] > 0
            and value['phase_actor_operations_remaining'] > 0)

    def begin_request(self):
        if not self.phase_budget_available():
            raise ValueError('saved-report phase request allowance is terminal or insufficient')
        return super().begin_request()

    def transition_ready(self):
        if self.phase != 1 or not self.pairs or self.early_phase_one_submit or self.submitted:
            return False
        pair = self.pairs[-1]
        action, result = pair['response'], pair['result']
        if not (action.get('action') == 'check' and action.get('check_id') == 'public'
                and result.get('accepted') is True and result.get('executed') is True):
            return False
        return any(pair['result'].get('accepted') is True
            and pair['result'].get('path') == REPORT
            and pair['result'].get('previous_candidate_id') != pair['result'].get('candidate_id')
            and 'previous_candidate_id' in pair['result']
            for sequence, pair in enumerate(self.pairs, 1)
            if sequence > self.phase_start_archive_length and sequence not in self.setup_sequences)

    def _record(self, action, result):
        super()._record(action, result)
        if self._setup_in_progress:
            self.setup_sequences = (*self.setup_sequences, len(self.pairs))
        elif self.phase == 1 and action['action'] == 'submit':
            self.early_phase_one_submit = True

    def view(self, **kwargs):
        value = super().view(**kwargs)
        counters = self.phase_counters()
        value['saved_report_phase'] = counters
        value['active_user_authored_step'] = dict(id=f'SAVED-REPORT-{self.phase}', host_inference=False,
            text=(AREA / f'PHASE_{self.phase}.txt').read_text(encoding='utf-8').strip())
        value['episode_annotation'] = (
            'Task-author context: OBS-0001/0002/0003 are historical captures made before the saved optimizer repair. '
            'Operations 1-3 are preserved reviewer-executed acquisition, application of Qwen\'s D2 proposal, '
            'and its historical check; these are not this actor\'s repair or new CHK executions. '
            'The historical check passed 25 optimizer cases and failed the empty-report obligation. '
            'setup_sequence_ranges identifies the prescribed assisted acquisitions; other later operations '
            'are model work. The deliberate phase transition supplies a new selected arrangement, not '
            'a natural context-pressure event. Private earlier thinking is not supplied. Captures remain '
            'bound to the original incident; checks concern their named candidate and definition.')
        value['allowance'].update(actions_used=counters['phase_actor_operations_used'],
            actions_remaining=counters['phase_actor_operations_remaining'],
            request_limit=PHASE_REQUESTS, requests_used=counters['phase_requests_used'],
            requests_remaining=counters['phase_requests_remaining'],
            request_counting='Each phase permits eight requests and sixteen actor operations. Unused phase-one opportunity expires. Cumulative dispatch and archival totals never reset; setup is separate.')
        return value


def initial_session(folder=None, replay=False):
    candidate, pairs, original, checker, task, inventory, bodies = starting_material()
    session = Session(candidate, {'public': checker}, task, pairs=pairs, edit_checks={},
        call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
        observations=ObservationStore((Path(folder) if folder else AREA/'unexecuted')/'observations', replay=replay),
        check_contracts={'public': {'checker_sha256': sha256_bytes(checker)}},
        imported_observations=inventory, imported_bodies=bodies, retain_imported_captures=True)
    session.versions = {original.candidate_id: original, candidate.candidate_id: candidate}
    session.diffs = {2: pairs[1]['result']['diff']}
    return session


def start_phase_two(session, preceding):
    if not session.transition_ready():
        raise ValueError('restart requires an accepted executed public check after an accepted report edit')
    check_handle = f'RES-{len(session.pairs):04d}'
    session.phase_start_requests = session.requests_used
    session.phase_start_actor_operations = session.actor_operations_used()
    session.phase_start_archive_length = len(session.pairs)
    session.phase = 2
    session.ranges, session.saved, session.delivered_sources = [], {}, []
    session.last = None
    session.recovery, session.recovery_obstacle, session.recovery_focus = False, None, []
    session.control_tier, session.restored_control_fields, session._inspect_only = 0, (), False
    preceding.clear()
    return check_handle


def setup(session, phase, measure, preceding, record=None):
    if phase == 1:
        if (session.phase != 1 or session.requests_used or session.calls_used
                or session.setup_sequences or len(session.pairs) != INHERITED_OPERATIONS):
            raise ValueError('phase-one setup must occur exactly once before actor work')
        actions = []
    elif phase == 2:
        actions = [dict(action='reopen_result', handle=start_phase_two(session, preceding), offset=0)]
    else:
        raise ValueError('unknown saved-report phase')
    actions += [dict(action='read', path=name, start_line=1, end_line=0)
                for name in ('README.md', REPORT)]
    actions += [dict(action='reopen_observation', handle=handle)
                for handle in ('OBS-0001', 'OBS-0002' if phase == 1 else 'OBS-0003')]
    sequences = []
    preceding.clear()
    for action in actions:
        session._setup_in_progress = True
        try:
            result = session.execute(action, measure)
        finally:
            session._setup_in_progress = False
        sequence = len(session.pairs)
        sequences.append(sequence)
        if record:
            record(sequence, copy.deepcopy(action), copy.deepcopy(result))
        if result.get('accepted') is not True:
            raise ValueError('prescribed assisted acquisition rejected')
        if action['action'] == 'read':
            source = result['source']
            if (source['content'].encode() != session.candidate.file_map[action['path']]
                    or source['next_start_line'] is not None):
                raise ValueError('prescribed assisted source is incomplete')
        elif action['action'] == 'reopen_result':
            body = session.payload(action['handle'])
            if (result.get('offset') != 0 or result.get('next_offset') is not None
                    or result.get('exact_utf8', '').encode() != body
                    or result.get('total_bytes') != len(body) or result.get('sha256') != sha256_bytes(body)):
                raise ValueError('prescribed preceding check is incomplete')
    view = session.view()
    _validate_setup_view(session, phase, view, actions[0]['handle'] if phase == 2 else None)
    if measure(view) > INPUT_LIMIT or session.delivery_blocked:
        raise ValueError('complete prescribed setup cannot be delivered')
    return sequences


def _validate_setup_view(session, phase, view, check_handle):
    """Check actual presentation bytes, not only acquisition or inventory flags."""
    shown_sources = {source['path']: source for source in
        view['working_set']['sources'] + session.feedback_sources(view.get('latest_feedback'))}
    for path in ('README.md', REPORT):
        source = shown_sources.get(path, {})
        if (source.get('content', '').encode() != session.candidate.file_map[path]
                or source.get('next_start_line') is not None or source.get('returned_start_line') != 1
                or source.get('file_sha256') != session.candidate.file_sha256(path)):
            raise ValueError('prescribed source bytes are absent from final setup input')
    pages = list(view['working_set']['saved_results'])
    latest = view.get('latest_feedback')
    shown_results = []
    if latest:
        result = latest['result']
        shown_results.append(result)
        pages.extend(result.get('saved_results', []))
        if result.get('kind') == 'saved_bytes':
            pages.append(result)
    complete_pages = {}
    for page in pages:
        body = page.get('exact_utf8', '').encode()
        if (page.get('kind') == 'saved_bytes' and page.get('offset') == 0
                and page.get('next_offset') is None and page.get('total_bytes') == len(body)
                and page.get('sha256') == sha256_bytes(body)):
            complete_pages[page['handle']] = body
            shown_results.append(read_bytes(body))
    expected = {'OBS-0001', 'OBS-0002' if phase == 1 else 'OBS-0003'}
    captures = {result['handle']: result['content_utf8'].encode() for result in shown_results
        if session._capture_identity(result) is not None}
    if captures != {handle: session.imported_record(handle)[1] for handle in expected}:
        raise ValueError('prescribed capture bytes are absent or extra in final setup input')
    if check_handle is not None and complete_pages.get(check_handle) != session.payload(check_handle):
        raise ValueError('actual preceding check bytes are absent from final setup input')


def process_reply(session, reply, measure, preceding, record_operation=None):
    counters = session.phase_counters()
    needed = int('account' in reply) + int('operation' in reply)
    if (not counters['phase_setup_complete'] or not 0 < counters['phase_requests_used'] <= PHASE_REQUESTS
            or session.early_phase_one_submit or needed > counters['phase_actor_operations_remaining']):
        raise ValueError('saved-report phase reply allowance is terminal or insufficient')
    return host_process_reply(session, reply, measure, preceding, record_operation)


def snapshot(session):
    return {**compiler.snapshot(session),
        'saved_report_state': dict(schema='saved-report-phase-v1', proposal_seal_sha256=PROPOSAL_SEAL_SHA,
            starting_candidate_id=STARTING_ID, phase=session.phase,
            phase_start_requests=session.phase_start_requests,
            phase_start_actor_operations=session.phase_start_actor_operations,
            phase_start_archive_length=session.phase_start_archive_length,
            setup_sequences=list(session.setup_sequences), early_phase_one_submit=session.early_phase_one_submit),
        'source_versions': [read_bytes(compiler.candidate_bytes(candidate))
            for _, candidate in sorted(session.versions.items())]}


def read_bytes(raw):
    from working_set_exp.jsonutil import load_json_strict
    return load_json_strict(raw)


def restore(state, candidate, replay_folder=None, replay=False):
    if not isinstance(candidate, Candidate):
        candidate = candidate_from_snapshot(candidate)
    session = initial_session(replay_folder, replay)
    expected = set(snapshot(session))
    if set(state) != expected or state['candidate_id'] != candidate.candidate_id:
        raise ValueError('checkpoint shape or candidate differs')
    phase = state['saved_report_state']
    if (set(phase) != set(snapshot(session)['saved_report_state'])
            or phase['schema'] != 'saved-report-phase-v1'
            or phase['proposal_seal_sha256'] != PROPOSAL_SEAL_SHA
            or phase['starting_candidate_id'] != STARTING_ID
            or type(phase['phase']) is not int or phase['phase'] not in (1, 2)
            or state['pairs'][:INHERITED_OPERATIONS] != session.pairs
            or state['starting_archive_length'] != INHERITED_OPERATIONS
            or (state['request_limit'], state['call_limit']) != (MAX_REQUESTS, MAX_OPERATIONS)):
        raise ValueError('checkpoint immutable configuration or prior archive differs')
    compiler.capture_bridge.restore_capture_state(session, state['imported_capture_state'])
    versions = [candidate_from_snapshot(value) for value in state['source_versions']]
    version_map = {value.candidate_id: value for value in versions}
    if (len(version_map) != len(versions) or candidate.candidate_id not in version_map
            or compiler.candidate_bytes(version_map[candidate.candidate_id]) != compiler.candidate_bytes(candidate)
            or any(key not in version_map or compiler.candidate_bytes(value) != compiler.candidate_bytes(version_map[key])
                   for key, value in session.versions.items())):
        raise ValueError('checkpoint source versions differ')
    for key, value in state.items():
        if key not in ('candidate_id', 'saved_report_state', 'source_versions', 'imported_capture_state'):
            setattr(session, key, copy.deepcopy(value))
    session.candidate, session.versions = candidate, version_map
    session.diffs = {int(key): value for key, value in session.diffs.items()}
    session.restored_control_fields = tuple(session.restored_control_fields)
    session.parked_source_regions = tuple(tuple(row) for row in session.parked_source_regions)
    for key in ('phase', 'phase_start_requests', 'phase_start_actor_operations', 'phase_start_archive_length',
                'early_phase_one_submit'):
        setattr(session, key, phase[key])
    session.setup_sequences = tuple(phase['setup_sequences'])
    if (session.setup_sequences != tuple(sorted(set(session.setup_sequences)))
            or any(type(seq) is not int or not INHERITED_OPERATIONS < seq <= len(session.pairs)
                   for seq in session.setup_sequences)
            or not 0 <= session.requests_used <= MAX_REQUESTS or not 0 <= session.calls_used <= MAX_OPERATIONS):
        raise ValueError('checkpoint operation/request accounting differs')
    _validate_phase_ledger(session)
    counters = session.phase_counters()
    if (not 0 <= counters['phase_requests_used'] <= PHASE_REQUESTS
            or not 0 <= counters['phase_actor_operations_used'] <= PHASE_ACTOR_OPERATIONS
            or len(session.setup_sequences) > 9
            or canonical_json_bytes(snapshot(session)) != canonical_json_bytes(state)):
        raise ValueError('checkpoint phase accounting or exact reconstruction differs')
    return session


def _validate_phase_ledger(session):
    """Assistance labels and baselines must match the actual archived operations."""
    numbers = (session.requests_used, session.phase_start_requests,
        session.phase_start_actor_operations, session.phase_start_archive_length)
    if (any(type(value) is not int for value in numbers)
            or type(session.early_phase_one_submit) is not bool
            or session.actor_operations_used() > 2 * session.requests_used):
        raise ValueError('checkpoint phase ledger types or actor/request relation differ')
    phase_one_actions = [dict(action='read', path=path, start_line=1, end_line=0)
        for path in ('README.md', REPORT)] + [dict(action='reopen_observation', handle=handle)
        for handle in ('OBS-0001', 'OBS-0002')]
    if session.phase == 1:
        if (session.phase_start_requests, session.phase_start_actor_operations,
                session.phase_start_archive_length) != (0, 0, INHERITED_OPERATIONS):
            raise ValueError('phase-one checkpoint baselines differ')
        expected_sequences = tuple(range(4, 8))[:len(session.setup_sequences)]
        expected_actions = phase_one_actions[:len(session.setup_sequences)]
    else:
        boundary = session.phase_start_archive_length
        if (not 2 <= session.phase_start_requests <= PHASE_REQUESTS
                or not 9 <= boundary <= INHERITED_OPERATIONS + 4 + PHASE_ACTOR_OPERATIONS
                or session.phase_start_actor_operations != boundary-INHERITED_OPERATIONS-4
                or len(session.setup_sequences) < 4):
            raise ValueError('phase-two checkpoint baselines differ')
        prefix = session.pairs[:boundary]
        ending = prefix[-1]
        if not (ending['response'].get('action') == 'check'
                and ending['response'].get('check_id') == 'public'
                and ending['result'].get('accepted') is True and ending['result'].get('executed') is True
                and any(pair['result'].get('accepted') is True and pair['result'].get('path') == REPORT
                    and 'previous_candidate_id' in pair['result']
                    and pair['result']['previous_candidate_id'] != pair['result'].get('candidate_id')
                    for pair in prefix[7:])):
            raise ValueError('phase-two checkpoint lacks the actual transition observation')
        remaining = len(session.setup_sequences)-4
        if not 0 <= remaining <= 5:
            raise ValueError('phase-two checkpoint setup count differs')
        expected_sequences = (*range(4, 8), *range(boundary+1, boundary+remaining+1))
        expected_actions = phase_one_actions + [dict(action='reopen_result', handle=f'RES-{boundary:04d}', offset=0),
            *[dict(action='read', path=path, start_line=1, end_line=0) for path in ('README.md', REPORT)],
            *[dict(action='reopen_observation', handle=handle) for handle in ('OBS-0001', 'OBS-0003')]][:remaining]
    if (session.setup_sequences != expected_sequences
            or any(session.pairs[sequence-1]['response'] != action
                   for sequence, action in zip(expected_sequences, expected_actions))):
        raise ValueError('checkpoint prescribed assistance attribution differs')
    phase_one_end = len(session.pairs) if session.phase == 1 else session.phase_start_archive_length
    requested_submit = any(pair['response'].get('action') == 'submit'
        for pair in session.pairs[7:phase_one_end])
    if (requested_submit != session.early_phase_one_submit
            or (session.phase == 2 and requested_submit)):
        raise ValueError('checkpoint phase-one terminal attribution differs')


def source_identities():
    paths = [*AREA.glob('*.py'), *(AREA/'tests').glob('*.py'),
        *(AREA/name for name in ('PLAN.md', 'SPEC.md', 'SYSTEM.txt', 'PHASE_1.txt', 'PHASE_2.txt')),
        PROPOSAL/'SEAL.json', PROPOSAL/'candidate.json', PROPOSAL/'scripted-pairs.json',
        PROPOSAL/'patch-result.json', PROPOSAL/'public-check-result.json',
        compiler.AREA/'preparation-003/SEAL.json', compiler.AREA/'preparation-003/QUALIFICATION.json',
        compiler.AREA/'preparation-003/native-forms/SEAL.json',
        compiler.AREA/'preparation-003/native-forms/RESULTS.json',
        ROOT/'development/saved_work_continuation/PHASE_1.txt',
        ROOT/'development/saved_work_continuation/PHASE_2.txt']
    return {**compiler.implementation_identities(retain_imported_captures=True),
            **{path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths}}


class Task(compiler.Task):
    def __init__(self, version='001', replay_folder=None):
        if len(version) != 3 or not version.isdecimal():
            raise ValueError('version must be three decimal digits')
        self.version, self.retain_imported_captures = version, True
        self.AREA = AREA
        self.PACKAGE, self.RUN = AREA/f'preparation-{version}', AREA/f'run-{version}'
        self.MANIFEST = AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.replay_folder = Path(replay_folder) if replay_folder else None
        self.MAX_REQUESTS, self.MAX_OPERATIONS = MAX_REQUESTS, MAX_OPERATIONS

    def initial_session(self):
        return initial_session(self.replay_folder, self.replay_folder is not None)

    def source_identities(self):
        return source_identities()

    def implementation_identities(self):
        return source_identities()

    def snapshot(self, session):
        return snapshot(session)

    def process_reply(self, *args, **kwargs):
        return process_reply(*args, **kwargs)

    def setup(self, *args, **kwargs):
        return setup(*args, **kwargs)

    def restore(self, state, candidate, replay_folder=None, replay=False):
        return restore(state, candidate, replay_folder, replay)

    def __getattr__(self, name):
        return globals()[name] if name in globals() else super().__getattr__(name)


def __getattr__(name):
    return globals()[name] if name in globals() else getattr(compiler, name)
