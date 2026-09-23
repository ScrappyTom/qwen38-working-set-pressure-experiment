"""Same saved task and consumed allowance, with bounded exact search projection."""
import copy
from pathlib import Path
import bootstrap
import transport_task as previous
from search_navigation import SearchNavigationMixin, REFERENCE_ADDITION
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

ROOT, AREA = previous.ROOT, Path(__file__).resolve().parent
OLD = previous.AREA / 'run-002'
OLD_SEAL = '9a9c8e88615a60383feeb23c58898af67923be8d29808bde8c1ae398f788b1d0'
ACTOR, SEED = previous.ACTOR, previous.SEED
MAX_REQUESTS, MAX_OPERATIONS = 24, 72
OWNER_DIRECTION = previous.OWNER_DIRECTION


class Session(SearchNavigationMixin, previous.Session):
    pass


def restore(folder=None, projected=True, stem='final'):
    assert sha256_file(OLD/'RESPONSE_SEAL.json') == OLD_SEAL
    seal = previous.read(OLD/'RESPONSE_SEAL.json')
    inventory = {r['path']: r for r in seal['files']}
    for name in (stem+'-state.json', stem+'-candidate.json', stem+'-preceding-feedback.json'):
        assert sha256_file(OLD/name) == inventory[name]['sha256']
    state = previous.read(OLD/(stem+'-state.json'))
    session = previous.initial_session((folder or OLD)/'observations', replay=True)
    assert previous.candidate_bytes(session.candidate) == (OLD/(stem+'-candidate.json')).read_bytes()
    for key, value in state.items():
        if key != 'candidate_id': setattr(session, key, copy.deepcopy(value))
    session.diffs = {int(k): v for k, v in session.diffs.items()}
    session.restored_control_fields = tuple(session.restored_control_fields)
    session.parked_source_regions = tuple(tuple(x) for x in session.parked_source_regions)
    assert canonical_json_bytes(previous.snapshot(session)) == canonical_json_bytes(state)
    if projected: session.__class__ = Session
    return session


def implementation_identities():
    assert sha256_file(OLD/'RESPONSE_SEAL.json') == OLD_SEAL
    seal = previous.read(OLD/'RESPONSE_SEAL.json')
    assert seal['disposition'] == 'operator_stopped'
    assert (seal['sent_requests'], seal['actual_operations']) == (13,18)
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    bound = dict(seal['source_sha256'])
    bound[(OLD/'RESPONSE_SEAL.json').relative_to(ROOT).as_posix()] = OLD_SEAL
    for row in seal['files']:
        path = OLD/row['path']; assert path.resolve().is_relative_to(OLD.resolve())
        bound[path.relative_to(ROOT).as_posix()] = row['sha256']
    paths = [*AREA.glob('*.py'), *AREA.glob('TESTS-*.log'), *(AREA/'tests').glob('*.py'),
             *(AREA/n for n in ('TASK.txt','SYSTEM.txt','PLAN.md','SPEC.md')),
             previous.AREA/'review/VERIFICATION.json']
    bound.update({p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths})
    previous.verify_sources(bound)
    return bound


class Task(previous.Task):
    def __init__(self, version='001', replay_folder=None):
        super().__init__(version, replay_folder)
        self.AREA = AREA
        self.PACKAGE, self.RUN = AREA/f'preparation-{version}', AREA/f'run-{version}'
        self.MANIFEST = AREA/f'EXECUTION_MANIFEST-{version}.json'
    def initial_session(self):
        session = restore(self.replay_folder)
        assert (session.requests_used, session.calls_used, session.starting_archive_length) == (13,18,39)
        assert not session.submitted and not session.delivery_blocked
        assert (AREA/'TASK.txt').read_bytes() == (previous.AREA/'TASK.txt').read_bytes()
        assert (AREA/'SYSTEM.txt').read_bytes() == (previous.AREA/'SYSTEM.txt').read_bytes()
        return session
    def initial_preceding_feedback(self): return previous.read(OLD/'final-preceding-feedback.json')
    def operating_reference(self): return super().operating_reference()+'\n\n'+REFERENCE_ADDITION
    def source_identities(self): return implementation_identities()
    def implementation_identities(self): return implementation_identities()


def __getattr__(name): return getattr(previous,name)
