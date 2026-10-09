"""Explicit new verification job over exact submitted E20 work."""
import copy
import difflib
from pathlib import Path

import bootstrap
import ecological_task as previous
import checker as contract_checker
import successor_reports
import case_reports
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = previous.ROOT, Path(__file__).resolve().parent
OLD = previous.AREA / 'run-003'
OLD_SEAL = 'e097eee7afe3b17b926401d3545b8ee0eed12a4b85cb0f708f1598bb90c17fe1'
SAVED_ID = '36e21200c5213d1621ed91025ce0f8404bd41846d6a42e3d44d90085a6f53c34'
INHERITED_REQUESTS, INHERITED_OPERATIONS = 20, 29
MAX_REQUESTS, MAX_OPERATIONS = 32, 65
ACTOR, SEED, FILE_LIMIT = previous.ACTOR, previous.SEED, previous.FILE_LIMIT
PUBLIC_SHA = sha256_bytes(contract_checker.public_checker())
OWNER_DIRECTION = 'Continue the authorized incomplete E20 boundary contract as an explicitly reopened job; preserve the submitted run and original grades.'
DESCRIPTIONS = {'public': 'Execute the unchanged original and parent verifier checks plus the declared Windows path-component composition contract. The complete current check must pass for this new job.'}
read, snapshot = previous.read, previous.snapshot
candidate_bytes, process_reply = previous.candidate_bytes, previous.process_reply



class Session(previous.Session):
    assessment_api = successor_reports

    def reply_schema(self):
        return reply_schema()

    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['episode_annotation'] = (
            'This is a new containment-contract completion job continuing submitted verifier work. '
            'The previous accepted submission and passes remain historical outcomes. '
            'The new public definition adds path-component normalization and Windows joining checks; '
            'the old pass is not applicable to this job. Original ten-file inspection before '
            'the recorded first mutation remains satisfied. History includes both jobs; '
            'no earlier conversation or private thinking is supplied.')
        return value


def inherited_inventory():
    if sha256_file(OLD / 'RESPONSE_SEAL.json') != OLD_SEAL:
        raise ValueError('Inherited E20 seal changed')
    seal = read(OLD / 'RESPONSE_SEAL.json')
    if (seal['disposition'] != 'checked_submission' or seal['sent_requests'] != 20
            or seal['actual_operations'] != 29 or seal['actor'] != ACTOR
            or sha256_bytes(canonical_json_bytes(seal['files'])) != seal['aggregate_sha256']):
        raise ValueError('Inherited E20 closure differs')
    index = {row['path']: row for row in seal['files']}
    if len(index) != len(seal['files']):
        raise ValueError('Duplicate inherited artifact addresses')
    return seal, index


def inherited_bytes(name):
    _, index = inherited_inventory()
    path = (OLD / name).resolve()
    if not path.is_relative_to(OLD.resolve()) or name not in index:
        raise ValueError('Inherited artifact address differs')
    raw, row = path.read_bytes(), index[name]
    if len(raw) != row['size_bytes'] or sha256_bytes(raw) != row['sha256']:
        raise ValueError('Inherited artifact bytes differ: ' + name)
    return raw


def inherited_state():
    return load_json_strict(inherited_bytes('final-state.json'))


def task_text():
    return (previous.task_text() + '\n\nNEW CONTAINMENT-CONTRACT COMPLETION JOB\n'
        'Continue the saved submitted verifier repair, preserving completed behavior and surrounding code. '
        'Review found that the earlier acceptance definitions did not exhaust path containment: '
        'normalization and joining of path components on Windows must also preserve the intended '
        'workspace-relative destination. The new public checker retains all original and parent '
        'checks and adds initial, dot-prefixed and interior drive forms, rooted/UNC and traversal '
        'forms, plus valid relative paths composed under two Windows workspace roots. '
        'No result of that new check is supplied initially. Obtain applicable evidence, correct '
        'remaining contract mismatches, check the actual successor and submit this new job. '
        'The complete original ten-file inspection obligation remains satisfied; current source '
        'and version guards still apply. Preserve the earlier accepted submission as history. '
        'There are twelve additional model requests and thirty-six operations, absolute limits '
        '32 and 65. Accounts remain optional. Edits do not trigger checks automatically.')


def contracts():
    return {'public': {'checker_sha256': PUBLIC_SHA}}


def operating_reference():
    return previous.operating_reference() + '\n\nSuccessor public definition: ' + DESCRIPTIONS['public']


def _restore_fields(session, state, candidate):
    versions = [previous.candidate_from_snapshot(value) for value in state['source_versions']]
    version_map = {value.candidate_id: value for value in versions}
    if (len(version_map) != len(versions) or candidate.candidate_id not in version_map
            or candidate_bytes(version_map[candidate.candidate_id]) != candidate_bytes(candidate)):
        raise ValueError('Continuation checkpoint source versions differ')
    previous.core.capture_bridge.restore_capture_state(session, state['imported_capture_state'])
    if previous.original_observation_snapshot(session) != state['original_observation_state']:
        raise ValueError('Original observation provenance differs')
    for key, value in state.items():
        if key not in ('candidate_id', 'source_versions', 'source_prerequisites', 'imported_capture_state', 'original_observation_state'):
            setattr(session, key, copy.deepcopy(value))
    session.candidate, session.versions = candidate, version_map
    session.diffs = previous.core._restore_diffs(state['diffs'], session.pairs)
    session.restored_control_fields = tuple(session.restored_control_fields)
    session.parked_source_regions = tuple(tuple(row) for row in session.parked_source_regions)
    previous.policy.restore_state(session, state['source_prerequisites'])
    return session


def _new_session(folder=None, replay=False):
    original, transport, bodies = previous.imports()
    return Session(previous.starting_candidate(), {'public': contract_checker.public_checker()},
        task_text(), edit_checks={}, call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
        observations=ObservationStore((Path(folder) if folder else OLD) / 'observations',
            replay=replay or folder is None), check_contracts=contracts(), original_observations=original, imported_observations=transport,
        imported_bodies=bodies, retain_imported_captures=True)


def initial_session(folder=None, replay=False):
    state = inherited_state()
    candidate = previous.candidate_from_snapshot(load_json_strict(inherited_bytes('final-candidate.json')))
    original = previous.restore(state, candidate, OLD, replay=True)
    if (canonical_json_bytes(snapshot(original)) != inherited_bytes('final-state.json')
            or candidate.candidate_id != SAVED_ID or not original.submitted
            or original.delivery_blocked or (original.requests_used, original.calls_used) != (20, 29)):
        raise ValueError('Original submitted E20 reconstruction differs')
    session = _restore_fields(_new_session(folder, replay), state, candidate)
    session.request_limit, session.call_limit, session.submitted = MAX_REQUESTS, MAX_OPERATIONS, False
    return session


def initial_preceding_feedback():
    return load_json_strict(inherited_bytes('final-preceding-feedback.json'))


def restore(state, candidate, replay_folder=None, replay=False):
    if not isinstance(candidate, previous.Candidate):
        candidate = previous.candidate_from_snapshot(candidate)
    inherited = inherited_state()
    session = _new_session(replay_folder, replay)
    if (not isinstance(state, dict) or set(state) != set(snapshot(session))
            or state['candidate_id'] != candidate.candidate_id or state['starting_archive_length'] != 0
            or (state['request_limit'], state['call_limit']) != (32, 65)
            or type(state['requests_used']) is not int or not 20 <= state['requests_used'] <= 32
            or not 29 <= len(state['pairs']) <= 65 or state['pairs'][:29] != inherited['pairs']
            or state['source_prerequisites']['first_mutation'] != inherited['source_prerequisites']['first_mutation']):
        raise ValueError('Continuation checkpoint shape, ancestry, coverage or opportunity differs')
    session = _restore_fields(session, state, candidate)
    if any(row['candidate_id'] not in session.versions
            or candidate_bytes(session.versions[row['candidate_id']]) != canonical_json_bytes(row)
            for row in inherited['source_versions']):
        raise ValueError('Inherited source versions changed')
    _validate_effects(session, inherited)
    if canonical_json_bytes(snapshot(session)) != canonical_json_bytes({**state, 'diffs': session.diffs}):
        raise ValueError('Continuation checkpoint reconstruction differs')
    return session


# Exact recorded-effect validation reused from URL continuation; globals are task-local.
def _replacement_matches(before, after, action, receipt):
    """Validate a recorded literal replacement from exact version bytes, not inference."""
    new = action['new']
    width = len(before) - len(after) + len(new)
    offsets, offset = [0], 0
    for line in after.splitlines(keepends=True):
        offset += len(line)
        offsets.append(offset)
    for start in offsets:
        end = start + width
        if (width <= 0 or end > len(before) or not after.startswith(new, start)
                or before[:start] != after[:start] or before[end:] != after[start + len(new):]):
            continue
        old = before[start:end]
        first, last = before[:start].count('\n') + 1, before[:end - 1].count('\n') + 1
        region = Session.region(receipt['path'], action['expected_file_sha256']
            if 'expected_file_sha256' in action else sha256_bytes(before.encode()), first, last)
        if (region['region_ref'] == action['region'] == receipt['replaced_region']
                and sha256_bytes(old.encode()) == receipt['old_source_sha256']):
            return True
    return False

def _validate_effects(session, inherited):
    current = session.versions[SAVED_ID]
    reached = {row['candidate_id'] for row in inherited['source_versions']}
    new_job_submitted, latest_new_check = False, None
    for sequence, pair in enumerate(session.pairs[INHERITED_OPERATIONS:], INHERITED_OPERATIONS + 1):
        if new_job_submitted:
            raise ValueError('New job archive continues after its accepted submission')
        action, receipt = pair['response'], pair['result']
        name = action['action']
        if name in ('patch', 'replace_region') and receipt.get('accepted'):
            path = receipt['path']
            successor = session.versions.get(receipt['candidate_id'])
            if (successor is None or action['expected_candidate_id'] != current.candidate_id
                    or receipt['previous_candidate_id'] != current.candidate_id
                    or receipt['file_sha256'] != successor.file_sha256(path)
                    or receipt['exact_action_handle'] != f'EVT-{sequence:04d}'
                    or any(successor.file_map[p] != data for p, data in current.files if p != path)):
                raise ValueError('Checkpoint edit receipt or candidate lineage differs')
            before, after = current.file_map[path].decode(), successor.file_map[path].decode()
            expected = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                fromfile='a/' + path, tofile='b/' + path))
            if receipt['applied_diff'] != expected or current.candidate_id == successor.candidate_id:
                raise ValueError('Checkpoint edit diff differs from exact versions')
            if name == 'patch':
                if (action['path'] != path or action['expected_file_sha256'] != current.file_sha256(path)
                        or not action['old'] or before.count(action['old']) != 1
                        or before.replace(action['old'], action['new'], 1) != after):
                    raise ValueError('Checkpoint patch differs from its recorded proposal')
            elif not _replacement_matches(before, after, action, receipt):
                raise ValueError('Checkpoint source replacement differs from its recorded proposal')
            current = successor
            reached.add(current.candidate_id)
        elif name == 'check' and (receipt.get('accepted') or receipt.get('observation') or receipt.get('executed')):
            if not receipt.get('executed') or not receipt.get('observation'):
                raise ValueError('Checkpoint check receipt lacks its executed observation')
            observed = session.observations.read(receipt['observation'])
            if (action['expected_candidate_id'] != current.candidate_id
                    or receipt['checked_candidate_id'] != current.candidate_id
                    or observed['candidate_id'] != current.candidate_id
                    or observed['check_id'] != action['check_id']):
                raise ValueError('Checkpoint check candidate or scope differs')
            if (receipt['check_id'] != action['check_id']
                    or receipt['check_definition_sha256'] != sha256_bytes(session.checkers[action['check_id']])
                    or observed['checker_sha256'] != receipt['check_definition_sha256']
                    or any(receipt[key] != observed[key] for key in
                        ('accepted', 'executed', 'passed', 'returncode', 'termination', 'capture_complete', 'streams'))):
                raise ValueError('Checkpoint check receipt differs from preserved observation')
            latest_new_check = (current.candidate_id, observed['passed'])
        elif name == 'submit' and receipt.get('accepted'):
            if (action['expected_candidate_id'] != current.candidate_id
                    or receipt.get('submitted_candidate_id') != current.candidate_id
                    or not receipt.get('public_check_passed_for_candidate')
                    or latest_new_check != (current.candidate_id, True)):
                raise ValueError('New job submission lacks its own current registered pass')
            new_job_submitted = True
    if current.candidate_id != session.candidate.candidate_id or set(session.versions) != reached:
        raise ValueError('Checkpoint current or historical candidate ancestry differs')
    if session.submitted is not new_job_submitted:
        raise ValueError('Current submission designation differs from the reopened job archive')


def attach_observations(session, folder, log):
    target, custody = Path(folder).resolve(), Path(log.path).parent.resolve()
    if not target.is_relative_to(custody):
        raise ValueError('Inherited observation custody differs')
    prefix = target.relative_to(custody).as_posix()
    prefix = '' if prefix == '.' else prefix + '/'
    _, index = inherited_inventory()
    names = sorted(name for name in index if name.startswith('observations/'))
    expected = sorted('observations/' + handle + '/' + name
        for handle in ('CHK-0025', 'CHK-0028')
        for name in ('outcome.json', 'started.json', 'stderr.bin', 'stdout.bin'))
    if names != expected:
        raise ValueError('Inherited observation inventory differs')
    store = ArtifactStore(custody)
    artifacts = [store.put(prefix + name, inherited_bytes(name)) for name in names]
    log.append('inherited_observations_copied', dict(source=OLD.relative_to(ROOT).as_posix(),
        observations=['CHK-0025', 'CHK-0028'], observations_not_reexecuted=True,
        inherited_requests=20, inherited_operations=29), artifacts)
    previous.attach_observations(session, target, log)
    if session.observations.read('CHK-0028')['candidate_id'] != SAVED_ID:
        raise ValueError('Copied observation candidate differs')


def reply_schema():
    return previous.core.capture_bridge.reply_schema(DESCRIPTIONS)


def decode_reply(content):
    return previous.core.capture_bridge.decode_reply(content, DESCRIPTIONS)


def implementation_identities():
    seal, index = inherited_inventory()
    bound = dict(seal['source_sha256'])
    bound[(OLD / 'RESPONSE_SEAL.json').relative_to(ROOT).as_posix()] = OLD_SEAL
    bound.update({(OLD / name).relative_to(ROOT).as_posix(): row['sha256'] for name, row in index.items()})
    proof = previous.AREA / 'review/VERIFICATION-003.json'
    if sha256_file(proof) != '9d5a4e4da8a691b0cccecfea644fa2beb22c4ffb7f3e9cabcde80e9be6232f48':
        raise ValueError('Inherited replay proof changed')
    paths = [proof, *AREA.glob('*.py'), *(AREA/'tests').glob('*.py'),
        *(AREA/'review').glob('*.py'), *(AREA/name for name in
        ('PLAN.md','SPEC.md','SYSTEM.txt','CHECKER_REVIEW.md','CHECKER-CPU-001.log')),
        *(AREA/'checker-cpu-001').rglob('*'), *AREA.glob('CPU-TESTS-*.log'),
        ROOT/'development/workload_requalification/action_lifecycle/run_continuation.py',
        ROOT/'development/workload_requalification/ecological_contract_continuation/continuation_task.py',
        ROOT/'development/workload_requalification/ecological_contract_continuation/run_continuation.py',
        ROOT/'development/workload_requalification/ecological_contract_continuation/qualification_route.py',
        ROOT/'development/workload_requalification/ecological_contract_continuation/review/verify_run.py']
    bound.update({path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths if path.is_file()})
    previous.verify_sources(bound)
    return bound


source_identities = implementation_identities


class Task(previous.Task):
    def __init__(self, version='001', replay_folder=None):
        super().__init__(version, replay_folder)
        self.AREA = AREA
        self.PACKAGE, self.RUN = AREA / f'preparation-{version}', AREA / f'run-{version}'
        self.MANIFEST = AREA / f'EXECUTION_MANIFEST-{version}.json'
        self.MAX_REQUESTS, self.MAX_OPERATIONS = MAX_REQUESTS, MAX_OPERATIONS
        self.OWNER_DIRECTION = OWNER_DIRECTION

    def initial_session(self):
        return initial_session(self.replay_folder, self.replay_folder is not None)

    def initial_preceding_feedback(self):
        return initial_preceding_feedback()

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(previous, name)


def __getattr__(name):
    return getattr(previous, name)
