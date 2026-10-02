"""Exact saved URL work, with only an explicit finite request extension."""
import copy
import difflib
from pathlib import Path

import bootstrap
import url_task as previous
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = previous.ROOT, Path(__file__).resolve().parent
OLD = previous.AREA / 'run-002'
OLD_SEAL = '22261c75844433e47dd3f65f71cdc4b40801085bcd3f95e1ee42003e20607645'
SAVED_ID = '83d8704c0a98ca6b201c991c56951d2e95bc060af33523531aa0b7789bf304ef'
DECODER = previous.AREA / 'preparation-002/native-forms'
DECODER_SEAL_SHA = '0f42ebb13c9857baa47ab488e9eb0015771545049ca520e25ab72af249713afb'
PREPARATION_SEAL_SHA = 'e866c441e2c4fde59033ad780eda75e96e44ba27e17e8594c116015ae4905d2d'
INHERITED_REQUESTS, INHERITED_OPERATIONS = 20, 30
MAX_REQUESTS, MAX_OPERATIONS = 36, 60
ACTOR, SEED, FILE_LIMIT = previous.ACTOR, previous.SEED, previous.FILE_LIMIT
OWNER_DIRECTION = 'Continue the authorized URL-port contribution from its exact saved failure, with 16 explicit additional requests and no reset or coaching.'
Session, checkers = previous.Session, previous.checkers
read, snapshot = previous.read, previous.snapshot
candidate_bytes, process_reply = previous.candidate_bytes, previous.process_reply


def inherited_inventory():
    if sha256_file(OLD / 'RESPONSE_SEAL.json') != OLD_SEAL:
        raise ValueError('Inherited URL seal changed')
    seal = read(OLD / 'RESPONSE_SEAL.json')
    if (seal['disposition'] != 'request_allowance_exhausted' or seal['sent_requests'] != 20
            or seal['actual_operations'] != 30 or seal['actor'] != ACTOR
            or sha256_bytes(canonical_json_bytes(seal['files'])) != seal['aggregate_sha256']):
        raise ValueError('Inherited URL closure differs')
    index = {row['path']: row for row in seal['files']}
    if len(index) != len(seal['files']):
        raise ValueError('Duplicate inherited artifact addresses')
    return seal, index


def inherited_bytes(name):
    _, index = inherited_inventory()
    path = (OLD / name).resolve()
    if not path.is_relative_to(OLD.resolve()) or name not in index:
        raise ValueError('Inherited artifact address differs')
    raw = path.read_bytes()
    row = index[name]
    if len(raw) != row['size_bytes'] or sha256_bytes(raw) != row['sha256']:
        raise ValueError('Inherited artifact bytes differ: ' + name)
    return raw


def inherited_state():
    return previous.read_bytes(inherited_bytes('final-state.json'))


def initial_session(folder=None, replay=False):
    state = inherited_state()
    saved = previous.read_bytes(inherited_bytes('final-candidate.json'))
    session = previous.restore(state, saved, folder or OLD, replay=True)
    if (session.candidate.candidate_id != SAVED_ID
            or (session.requests_used, session.calls_used, session.starting_archive_length) != (20, 30, 0)
            or session.submitted or session.delivery_blocked):
        raise ValueError('Inherited URL entry differs')
    if canonical_json_bytes(snapshot(session)) != inherited_bytes('final-state.json'):
        raise ValueError('Original URL reconstruction differs')
    # Establish the old checkpoint first; this is the sole changed control.
    session.request_limit = MAX_REQUESTS
    # An unattached entry may inspect inherited bytes, but must never execute
    # a new check into the frozen old run. The custody hook enables new capture.
    session.observations = ObservationStore((Path(folder) if folder else OLD) / 'observations',
        replay=replay or folder is None)
    return session


def initial_preceding_feedback():
    return previous.read_bytes(inherited_bytes('final-preceding-feedback.json'))


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
    for sequence, pair in enumerate(session.pairs[INHERITED_OPERATIONS:], INHERITED_OPERATIONS + 1):
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
    if current.candidate_id != session.candidate.candidate_id or set(session.versions) != reached:
        raise ValueError('Checkpoint current or historical candidate ancestry differs')


def restore(state, candidate, replay_folder=None, replay=False):
    if not isinstance(candidate, previous.Candidate):
        candidate = previous.candidate_from_snapshot(candidate)
    inherited = inherited_state()
    session = previous.initial_session(replay_folder, replay)
    if (set(state) != set(snapshot(session)) or state['candidate_id'] != candidate.candidate_id
            or state['starting_archive_length'] != 0
            or (state['request_limit'], state['call_limit']) != (MAX_REQUESTS, MAX_OPERATIONS)
            or type(state['requests_used']) is not int or not 20 <= state['requests_used'] <= 36
            or not 30 <= len(state['pairs']) <= 60
            or state['pairs'][:30] != inherited['pairs']):
        raise ValueError('Continuation checkpoint shape, ancestry or opportunity differs')
    versions = [previous.candidate_from_snapshot(value) for value in state['source_versions']]
    version_map = {value.candidate_id: value for value in versions}
    if (len(version_map) != len(versions) or candidate.candidate_id not in version_map
            or candidate_bytes(version_map[candidate.candidate_id]) != candidate_bytes(candidate)
            or any(row['candidate_id'] not in version_map
                or candidate_bytes(version_map[row['candidate_id']]) != canonical_json_bytes(row)
                for row in inherited['source_versions'])):
        raise ValueError('Continuation checkpoint historical versions differ')
    for key, value in state.items():
        if key not in ('candidate_id', 'source_versions'):
            setattr(session, key, copy.deepcopy(value))
    session.candidate, session.versions = candidate, version_map
    session.diffs = previous._restore_diffs(state['diffs'], session.pairs)
    session.restored_control_fields = tuple(session.restored_control_fields)
    session.parked_source_regions = tuple(tuple(row) for row in session.parked_source_regions)
    _validate_effects(session, inherited)
    if canonical_json_bytes(snapshot(session)) != canonical_json_bytes({**state, 'diffs': session.diffs}):
        raise ValueError('Continuation checkpoint exact reconstruction differs')
    return session


def attach_observations(session, folder, log):
    target, custody = Path(folder).resolve(), Path(log.path).parent.resolve()
    if not target.is_relative_to(custody):
        raise ValueError('Inherited observation custody differs')
    prefix = target.relative_to(custody).as_posix()
    prefix = '' if prefix == '.' else prefix + '/'
    _, index = inherited_inventory()
    names = sorted(name for name in index if name.startswith('observations/'))
    if names != ['observations/CHK-0030/' + name for name in
            ('outcome.json', 'started.json', 'stderr.bin', 'stdout.bin')]:
        raise ValueError('Inherited observation inventory differs')
    store = ArtifactStore(custody)
    artifacts = [store.put(prefix + name, inherited_bytes(name)) for name in names]
    log.append('inherited_observations_copied', dict(source=OLD.relative_to(ROOT).as_posix(),
        observations=['CHK-0030'], observations_not_reexecuted=True, inherited_requests=20,
        inherited_operations=30), artifacts)
    previous.attach_observations(session, target, log)
    if session.observations.read('CHK-0030')['candidate_id'] != SAVED_ID:
        raise ValueError('Copied observation candidate differs')


def decoder_reuse_bindings():
    preparation = DECODER.parent / 'SEAL.json'
    if (sha256_file(preparation) != PREPARATION_SEAL_SHA
            or sha256_file(DECODER / 'SEAL.json') != DECODER_SEAL_SHA):
        raise ValueError('Inherited native qualification seal changed')
    native = read(DECODER / 'SEAL.json')
    result = read(DECODER / 'RESULTS.json')
    if (native['status'] != 'qualified_no_model_inference' or native['completion_requests'] != 0
            or sha256_bytes(canonical_json_bytes(native['files'])) != native['aggregate_sha256']
            or result['status'] != 'passed' or result['completion_requests'] != 0
            or result['model_inference_calls'] != 0 or result['checker_executions'] != 0
            or result['grammar_sha256'] != sha256_bytes(previous.response_constraints()['grammar'].encode())
            or not result['cases']
            or any(row['accepted_including_eos'] != row['expected'] for row in result['cases'])):
        raise ValueError('Inherited native reply proof differs')
    bound = dict(native['source_sha256'])
    bound[preparation.relative_to(ROOT).as_posix()] = PREPARATION_SEAL_SHA
    bound[(DECODER / 'SEAL.json').relative_to(ROOT).as_posix()] = DECODER_SEAL_SHA
    for row in native['files']:
        path = (DECODER / row['path']).resolve()
        if not path.is_relative_to(DECODER.resolve()):
            raise ValueError('Native proof address escapes its closure')
        bound[path.relative_to(ROOT).as_posix()] = row['sha256']
    previous.verify_sources(bound)
    return bound


def implementation_identities():
    seal, index = inherited_inventory()
    bound = dict(seal['source_sha256'])
    bound[(OLD / 'RESPONSE_SEAL.json').relative_to(ROOT).as_posix()] = OLD_SEAL
    for name, row in index.items():
        path = (OLD / name).resolve()
        if not path.is_relative_to(OLD.resolve()):
            raise ValueError('Inherited inventory escapes its closure')
        bound[path.relative_to(ROOT).as_posix()] = row['sha256']
    proof = previous.AREA / 'review/VERIFICATION-002.json'
    value = read(proof)
    if (value['status'] != 'replayed_exactly' or value['requests_used'] != 20
            or value['actual_operations'] != 30 or value['submitted']
            or value['final_candidate_id'] != SAVED_ID):
        raise ValueError('Inherited exact replay proof differs')
    paths = [*AREA.glob('*.py'), *(AREA / 'tests').glob('*.py'), proof,
        *(AREA / name for name in ('PLAN.md', 'SPEC.md', 'SYSTEM.txt')), *AREA.glob('TESTS-*.log')]
    paths.extend(path for path in (AREA / 'review/verify_run.py', AREA / 'review/measure_run.py',
        AREA / 'review/IMPLEMENTATION_REPLAY_NOTES.md') if path.is_file())
    bound.update(decoder_reuse_bindings())
    bound.update({path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths})
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

    def source_identities(self):
        return implementation_identities()

    def implementation_identities(self):
        return implementation_identities()

    def restore(self, *args, **kwargs):
        return restore(*args, **kwargs)

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(previous, name)


def __getattr__(name):
    return getattr(previous, name)
