"""Continue from the public read accepted by the corrected inspection host."""
import copy
import subprocess
from pathlib import Path

import cycle_task as prior
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.recovery_context_session import RecoveryContextSession

ROOT, AREA = prior.ROOT, Path(__file__).resolve().parent
ACTOR, SEED = prior.ACTOR, prior.SEED
MAX_REQUESTS, MAX_OPERATIONS = 24, 72
OWNER_DIRECTION = prior.OWNER_DIRECTION
QUALIFIED = AREA/'qualification-001'
OLD = prior.AREA/'run-001'


def snapshot(session):
    return {**prior.snapshot(session), 'parked_source_regions':list(session.parked_source_regions)}


def verify_qualification_sources():
    sources=prior.read(QUALIFIED/'SEAL.json')['source_sha256']
    for name,digest in sources.items():
        if name==(AREA/'PLAN.md').relative_to(ROOT).as_posix():
            # Qualification preceded the separately declared C02 context repair.
            data=subprocess.check_output(['git','show','a9b274aa:'+name],cwd=ROOT)
            assert sha256_bytes(data)==digest
        else:
            assert sha256_file(ROOT/name)==digest,name


def operating_reference():
    return prior.operating_reference()+(
        '\nrecent_edit_rejection is historical host feedback for unchanged file bytes, '
        'retained through intervening acquisition. It records that no edit occurred. '
        'It does not make the old action current or authorize editing; current source '
        'visibility and candidate guards still apply.')


def source_identities():
    paths=[*AREA.glob('*.py'),AREA/'PLAN.md',AREA/'SPEC.md',AREA/'SYSTEM.txt',
           QUALIFIED/'SEAL.json',OLD/'RESPONSE_SEAL.json',
           *[ROOT/'src/working_set_exp'/name for name in ('recovery_inspection_session.py','recovery_context_session.py')],
           *[ROOT/'tests'/name for name in ('test_recovery_inspection.py','test_recovery_context.py')]]
    return {**prior.source_identities(),**{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}


class Task:
    def __init__(self,version='001',replay_folder=None):
        self.PACKAGE,self.RUN=AREA/f'preparation-{version}',AREA/'run-001'
        self.MANIFEST=AREA/'EXECUTION_MANIFEST.json'
        self.replay_folder=replay_folder

    def initial_session(self):
        seal=prior.read(QUALIFIED/'SEAL.json')
        for row in seal['files']:
            assert sha256_file(QUALIFIED/row['path'])==row['sha256'],row['path']
        state=prior.read(QUALIFIED/'corrected-state.json')
        session=prior.Task().initial_session()
        session.__class__=RecoveryContextSession
        for key,value in state.items():
            if key!='candidate_id':setattr(session,key,copy.deepcopy(value))
        session.restored_control_fields=tuple(session.restored_control_fields)
        session.parked_source_regions=tuple(tuple(row) for row in session.parked_source_regions)
        session.diffs={int(key):value for key,value in session.diffs.items()}
        assert canonical_json_bytes(snapshot(session))==canonical_json_bytes(state)
        assert session.candidate.candidate_id==state['candidate_id']
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
