"""Corrected reporting over an exact interrupted contribution checkpoint."""
import copy
from pathlib import Path

import interpolation_task as previous
import operable_task
from session import Session
from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = previous.ROOT, Path(__file__).resolve().parent
OLD = previous.AREA / 'run-002'
AUDIT = previous.AREA / 'review' / 'INTERRUPTION_SEAL.json'
ACTOR, SEED = previous.ACTOR, previous.SEED
MAX_REQUESTS, MAX_OPERATIONS = 10, 96
OWNER_DIRECTION = 'Proceed with the corrected-report continuation and the authorized workload requalification programme.'
ENTRY = 'after/C21-O01'
ACCOUNTING = dict(previous_requests_dispatched=22, previous_responses_completed=21,
    previous_request_without_saved_response='interpolation/run-002 C22',
    original_request_limit=32, remaining_requests_allocated_here=10,
    previous_contribution_operations=34, original_operation_limit=96,
    explanation='The ten-request counter is local to this continuation. Earlier dispatches remain charged; operations retain their original cumulative counter.')


def restore(stem=ENTRY, corrected=False):
    inventory = {r['path']:r for r in previous.read(AUDIT)['files']}
    for suffix in ('-state.json', '-candidate.json'):
        name = stem + suffix
        assert sha256_file(OLD/name) == inventory[name]['sha256'], name
    state = previous.read(OLD / (stem + '-state.json'))
    raw = previous.read(OLD / (stem + '-candidate.json'))
    session = previous.Task().initial_session()
    session.candidate = Candidate.create({r['path']:r['content_utf8'].encode() for r in raw['files']},
                                         max_file_bytes=raw['max_file_bytes'])
    for key, value in state.items():
        if key != 'candidate_id':
            setattr(session, key, copy.deepcopy(value))
    session.diffs = {int(k):v for k,v in session.diffs.items()}
    session.restored_control_fields = tuple(session.restored_control_fields)
    session.parked_source_regions = tuple(tuple(r) for r in session.parked_source_regions)
    session.versions[session.candidate.candidate_id] = session.candidate
    session.observations = ObservationStore(OLD / 'observations', replay=True)
    assert canonical_json_bytes(previous.snapshot(session)) == canonical_json_bytes(state)
    assert session.candidate.candidate_id == state['candidate_id']
    if corrected:
        session.__class__ = Session
    return session


def snapshot(session):
    value = previous.snapshot(session)
    if getattr(session, 'continuation_accounting', None):
        value['continuation_accounting'] = dict(session.continuation_accounting)
    return value


def verified_observation_files(root):
    expected = {r['path'][len('observations/'):]:r
                for r in previous.read(AUDIT)['files'] if r['path'].startswith('observations/')}
    actual = {p.relative_to(root).as_posix():p for p in root.rglob('*') if p.is_file()}
    assert set(actual) == set(expected), 'Inherited observation inventory differs from the interruption audit'
    result = []
    for name, path in sorted(actual.items()):
        raw = path.read_bytes()
        assert len(raw) == expected[name]['size_bytes'] and sha256_bytes(raw) == expected[name]['sha256'], name
        result.append((name, raw))
    return result


def attach_observations(session, folder, log):
    # Verify the exact bytes being copied, even when a shortened display is unchanged.
    inherited = verified_observation_files(session.observations.root)
    store = ArtifactStore(folder)
    artifacts = [store.put('observations/' + name, raw) for name, raw in inherited]
    log.append('inherited_observations_copied', dict(source=session.observations.root.relative_to(ROOT).as_posix(),
        observations_not_reexecuted=True), artifacts)
    operable_task.attach_observations(session, folder, log)


def source_identities():
    paths = [*AREA.glob('*.py'), AREA/'PLAN.md', AREA/'SPEC.md', AREA/'SYSTEM.txt', AUDIT,
             OLD/(ENTRY+'-state.json'), OLD/(ENTRY+'-candidate.json'),
             OLD/'calls/C22-wire-request.json', AREA/'cpu-qualification-001/SEAL.json',
             AREA/'tests/test_inherited.py',
             *[p for p in (OLD/'observations').rglob('*') if p.is_file()]]
    return {**previous.source_identities(), **{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}


class Task:
    def __init__(self, version='001', replay_folder=None):
        self.PACKAGE, self.RUN = AREA/f'preparation-{version}', AREA/f'run-{version}'
        self.MANIFEST = AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.replay_folder = replay_folder

    def initial_session(self):
        session = restore(corrected=True)
        assert session.requests_used == 21 and session.calls_used == 34 and not session.submitted
        # This is the remaining local allowance, not a grant of another 32 calls.
        session.requests_used, session.request_limit = 0, MAX_REQUESTS
        session.call_limit = MAX_OPERATIONS
        session.continuation_accounting = dict(ACCOUNTING)
        session.delivered_sources = []
        if self.replay_folder:
            session.observations = ObservationStore(self.replay_folder/'observations', replay=True)
        return session

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(previous, name)


def __getattr__(name):
    return getattr(previous, name)
