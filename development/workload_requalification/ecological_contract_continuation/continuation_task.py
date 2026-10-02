"""Explicit new verification job over exact submitted E20 work."""
import copy
import difflib
from pathlib import Path

import bootstrap
import ecological_task as previous
import contract_checker
import case_reports
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = previous.ROOT, Path(__file__).resolve().parent
OLD = previous.AREA / 'run-001'
OLD_SEAL = '6550a09cdadf7369e6151bcf39ec8baef11c855df08b10bfb5fa022ceaf1182b'
SAVED_ID = '23b5c17999963faf7453c68a6b537ae6c447555f77eb0a835bfa659ad47e89aa'
INHERITED_REQUESTS, INHERITED_OPERATIONS = 19, 28
MAX_REQUESTS, MAX_OPERATIONS = 32, 72
ACTOR, SEED, FILE_LIMIT = previous.ACTOR, previous.SEED, previous.FILE_LIMIT
PUBLIC_SHA = contract_checker.checker_sha256()
OWNER_DIRECTION = 'Continue the authorized incomplete E20 boundary contract as an explicitly reopened job; preserve the submitted run and original grades.'
DESCRIPTIONS = {'public': 'Execute the original E20 public program and the twelve-case directory byte/count boundary probe, including zero counts, on this current candidate. Both must pass before this job can be submitted.'}
read, snapshot = previous.read, previous.snapshot
candidate_bytes, process_reply = previous.candidate_bytes, previous.process_reply



class Session(previous.Session):
    assessment_api = contract_checker

    def reply_schema(self):
        return reply_schema()

    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['episode_annotation'] = (
            'This is a new contract-completion job continuing the previously submitted E20 work. '
            'The earlier submission and original public pass remain historical recorded effects. '
            'The current submitted designation is reopened; the new public checker also includes '
            'twelve byte/count boundary cases, so the old checker pass is inapplicable. '
            'Original full-source inspection before the recorded first mutation remains satisfied. '
            'Operation history includes both jobs; no earlier conversation or private thinking is supplied.')
        return value


def inherited_inventory():
    if sha256_file(OLD / 'RESPONSE_SEAL.json') != OLD_SEAL:
        raise ValueError('Inherited E20 seal changed')
    seal = read(OLD / 'RESPONSE_SEAL.json')
    if (seal['disposition'] != 'checked_submission' or seal['sent_requests'] != 19
            or seal['actual_operations'] != 28 or seal['actor'] != ACTOR
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
    return (previous.task_text() + '\n\nNEW CONTRACT-COMPLETION JOB\n'
        'Continue the saved submitted work, preserving the completed repairs and surrounding behavior. '
        'The original public and hidden acceptance programs passed, but their coverage does not '
        'exhaust the original at-most-first-N file contract. The newly registered public check '
        'executes the unchanged original public program and twelve byte/count boundary cases '
        'with max_file_bytes=0,1,5 and max_files=0,1,2,10. No result of this new check is supplied '
        'initially. Obtain applicable evidence, correct any remaining contract mismatch, '
        'check the actual current successor with this public definition, and submit this new job. '
        'The earlier complete eleven-file inspection remains satisfied; current exact source '
        'and version guards still govern edits. The previous submit event remains in history. '
        'You have thirteen new model requests, within an absolute limit of 32, and 44 operations '
        'within the unchanged limit of 72. Edits do not trigger checks automatically.')


def _restore_fields(session, state, candidate):
    versions = [previous.candidate_from_snapshot(value) for value in state['source_versions']]
    version_map = {value.candidate_id: value for value in versions}
    if (len(version_map) != len(versions) or candidate.candidate_id not in version_map
            or candidate_bytes(version_map[candidate.candidate_id]) != candidate_bytes(candidate)):
        raise ValueError('Continuation checkpoint source versions differ')
    for key, value in state.items():
        if key not in ('candidate_id', 'source_versions', 'source_prerequisites'):
            setattr(session, key, copy.deepcopy(value))
    session.candidate, session.versions = candidate, version_map
    session.diffs = previous.previous._restore_diffs(state['diffs'], session.pairs)
    session.restored_control_fields = tuple(session.restored_control_fields)
    session.parked_source_regions = tuple(tuple(row) for row in session.parked_source_regions)
    previous.policy.restore_state(session, state['source_prerequisites'])
    return session


def _new_session(folder=None, replay=False):
    return Session(previous.starting_candidate(), {'public': contract_checker.public_checker()},
        task_text(), edit_checks={}, call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
        observations=ObservationStore((Path(folder) if folder else OLD) / 'observations',
            replay=replay or folder is None), check_contracts=contract_checker.contracts())


def initial_session(folder=None, replay=False):
    state = inherited_state()
    candidate = previous.candidate_from_snapshot(load_json_strict(inherited_bytes('final-candidate.json')))
    original = previous.restore(state, candidate, OLD, replay=True)
    if (canonical_json_bytes(snapshot(original)) != inherited_bytes('final-state.json')
            or candidate.candidate_id != SAVED_ID or not original.submitted
            or original.delivery_blocked or (original.requests_used, original.calls_used) != (19, 28)):
        raise ValueError('Original submitted E20 reconstruction differs')
    session = _restore_fields(_new_session(folder, replay), state, candidate)
    session.request_limit, session.submitted = MAX_REQUESTS, False
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
            or (state['request_limit'], state['call_limit']) != (32, 72)
            or type(state['requests_used']) is not int or not 19 <= state['requests_used'] <= 32
            or not 28 <= len(state['pairs']) <= 72 or state['pairs'][:28] != inherited['pairs']
            or state['source_prerequisites'] != inherited['source_prerequisites']):
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
    if names != ['observations/CHK-0027/' + name for name in
            ('outcome.json', 'started.json', 'stderr.bin', 'stdout.bin')]:
        raise ValueError('Inherited observation inventory differs')
    store = ArtifactStore(custody)
    artifacts = [store.put(prefix + name, inherited_bytes(name)) for name in names]
    log.append('inherited_observations_copied', dict(source=OLD.relative_to(ROOT).as_posix(),
        observations=['CHK-0027'], observations_not_reexecuted=True,
        inherited_requests=19, inherited_operations=28), artifacts)
    previous.attach_observations(session, target, log)
    if session.observations.read('CHK-0027')['candidate_id'] != SAVED_ID:
        raise ValueError('Copied observation candidate differs')


def reply_schema():
    return previous.previous.operational_reply.reply_schema(DESCRIPTIONS)


def decode_reply(content):
    return previous.previous.operational_reply.decode_reply(content, DESCRIPTIONS)


def implementation_identities():
    seal, index = inherited_inventory()
    bound = dict(seal['source_sha256'])
    bound[(OLD / 'RESPONSE_SEAL.json').relative_to(ROOT).as_posix()] = OLD_SEAL
    bound.update({(OLD / name).relative_to(ROOT).as_posix(): row['sha256'] for name, row in index.items()})
    proof = previous.AREA / 'review/VERIFICATION-001.json'
    if sha256_file(proof) != '8f060fc5d62dbb2fc75dd7a99935eb8e88c64783741133e5a3f8317398d712a0':
        raise ValueError('Inherited exact replay proof changed')
    paths = [proof, *AREA.glob('*.py'), *(AREA / 'tests').glob('*.py'),
        *(AREA / name for name in ('PLAN.md', 'SPEC.md', 'SYSTEM.txt')),
        *AREA.glob('*TESTS-*.log'), *(AREA / 'review').glob('*TESTS-*.log'),
        *(AREA / 'review').glob('*.py'), AREA / 'review/IMPLEMENTATION_NOTES.md',
        *(path for directory in (AREA / 'review').glob('checker-cpu-observations-*')
          for path in directory.rglob('*') if path.is_file()),
        ROOT / 'development/workload_requalification/action_lifecycle/run_continuation.py',
        ROOT / 'development/workload_requalification/url_port_continuation/review/verify_run.py',
        ROOT / 'maintenance/resume_after_020/import_boundary_probe.py']
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

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(previous, name)


def __getattr__(name):
    return getattr(previous, name)
