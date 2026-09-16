"""Same stopped contribution, with coherent projection of actual check failures."""
from pathlib import Path

import inspection_task as prior
from working_set_exp.coherent_diagnostic_session import CoherentDiagnosticSession
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.recovery_context_session import RecoveryContextSession

ROOT, AREA = prior.ROOT, Path(__file__).resolve().parent
OLD = prior.AREA/'run-001'
QUALIFIED = AREA/'qualification-002'
ACTOR, SEED = prior.ACTOR, prior.SEED
MAX_REQUESTS, MAX_OPERATIONS = 16, 48
OWNER_DIRECTION = prior.OWNER_DIRECTION
snapshot = prior.snapshot


def restore(stem='final', corrected=True):
    seal = prior.read(OLD/'RESPONSE_SEAL.json')
    for suffix in ('-state.json','-candidate.json','-preceding-feedback.json'):
        row, = [r for r in seal['files'] if r['path']==stem+suffix]
        assert sha256_file(OLD/row['path'])==row['sha256'],row['path']
    state = prior.read(OLD/(stem+'-state.json'))
    session = prior.restore(OLD,stem)
    session.__class__ = CoherentDiagnosticSession if corrected else RecoveryContextSession
    session.restored_control_fields=tuple(session.restored_control_fields)
    session.parked_source_regions=tuple(tuple(row) for row in session.parked_source_regions)
    assert canonical_json_bytes(snapshot(session))==canonical_json_bytes(state)
    return session


def source_identities():
    paths=[*AREA.glob('*.py'),AREA/'PLAN.md',AREA/'SPEC.md',AREA/'SYSTEM.txt',
           ROOT/'src/working_set_exp/coherent_diagnostics.py',
           ROOT/'src/working_set_exp/coherent_diagnostic_session.py',
           ROOT/'tests/test_coherent_diagnostics.py',OLD/'RESPONSE_SEAL.json']
    if (QUALIFIED/'SEAL.json').exists():
        paths.append(QUALIFIED/'SEAL.json')
    return {**prior.source_identities(),**{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}


class Task:
    def __init__(self,version='001',replay_folder=None):
        self.PACKAGE,self.RUN=AREA/f'preparation-{version}',AREA/'run-001'
        self.MANIFEST=AREA/'EXECUTION_MANIFEST.json'
        self.replay_folder=replay_folder

    def initial_session(self):
        session=restore()
        session.requests_used=0
        session.request_limit=MAX_REQUESTS
        session.call_limit=MAX_OPERATIONS
        session.starting_archive_length=len(session.pairs)
        session.delivered_sources=[]
        if self.replay_folder:
            session.observations=ObservationStore(self.replay_folder/'observations',replay=True)
        return session

    def __getattr__(self,name):
        return globals()[name] if name in globals() else getattr(prior,name)


def __getattr__(name):
    return getattr(prior,name)
