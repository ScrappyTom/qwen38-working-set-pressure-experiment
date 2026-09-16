"""Standing-authorized continuation from the corrected public rejection."""
import copy
from pathlib import Path

import reference_task as prior
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.recovery_detail_session import RecoveryDetailSession

ROOT, AREA = prior.ROOT, Path(__file__).resolve().parent
ACTOR, SEED = prior.ACTOR, prior.SEED
MAX_REQUESTS, MAX_OPERATIONS = 24, 72
OWNER_DIRECTION = 'We keep repeating until all host and your run apparatus features are fixed and things are successful'
QUALIFIED = AREA.parent / 'recovery_detail/qualification-001'
OLD = prior.AREA / 'run-001'


def snapshot(session):
    return {**prior.snapshot(session), 'restored_control_fields': list(session.restored_control_fields)}


def source_identities():
    paths = [*AREA.glob('*.py'), AREA/'PLAN.md', AREA/'SPEC.md', AREA/'SYSTEM.txt',
             QUALIFIED/'SEAL.json', ROOT/'src/working_set_exp/recovery_detail_session.py',
             ROOT/'tests/test_recovery_detail.py', OLD/'RESPONSE_SEAL.json']
    return {**prior.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}


class Task:
    def __init__(self, version='001', replay_folder=None):
        self.PACKAGE, self.RUN = AREA/f'preparation-{version}', AREA/'run-001'
        self.MANIFEST = AREA/'EXECUTION_MANIFEST.json'
        self.replay_folder = replay_folder

    def initial_session(self):
        seal = prior.read(QUALIFIED/'SEAL.json')
        for row in seal['files']:
            assert sha256_file(QUALIFIED/row['path']) == row['sha256'], row['path']
        state = prior.read(QUALIFIED/'corrected-state.json')
        session = prior.restore(OLD, 'after/C05-O02')
        session.__class__ = RecoveryDetailSession
        session.restored_control_fields = tuple(state['restored_control_fields'])
        assert canonical_json_bytes(snapshot(session)) == canonical_json_bytes(state)
        session.requests_used = 0
        session.request_limit = MAX_REQUESTS
        session.call_limit = MAX_OPERATIONS
        session.starting_archive_length = len(session.pairs)
        session.delivered_sources = []
        if self.replay_folder:
            session.observations = ObservationStore(self.replay_folder/'observations', replay=True)
        return session

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(prior, name)


def __getattr__(name):
    return getattr(prior, name)
