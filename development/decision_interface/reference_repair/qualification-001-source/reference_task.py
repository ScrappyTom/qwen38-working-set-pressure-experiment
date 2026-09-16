"""Separately bounded continuation of a verified public prefix, without coaching."""
import copy
from pathlib import Path

import feedback_task as prior
from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.reference_session import ReferenceSession

ROOT, AREA = prior.ROOT, Path(__file__).resolve().parent
ACTOR, SEED = prior.ACTOR, prior.SEED
MAX_REQUESTS, MAX_OPERATIONS = 6, 18
OWNER_DIRECTION = prior.OWNER_DIRECTION
OLD = prior.AREA/'run-001'
QUALIFIED = AREA/'qualification-001'


def restore(folder, stem='corrected'):
    state, raw = prior.read(folder/(stem+'-state.json')), prior.read(folder/(stem+'-candidate.json'))
    session = prior.from_checkpoint()
    session.__class__ = ReferenceSession  # No additional state; opt-in resolver only.
    session.candidate = Candidate.create({r['path']:r['content_utf8'].encode() for r in raw['files']},
                                         max_file_bytes=raw['max_file_bytes'])
    for key, value in state.items():
        if key != 'candidate_id':
            setattr(session,key,copy.deepcopy(value))
    session.versions[session.candidate.candidate_id] = session.candidate
    session.observations = ObservationStore(folder/'observations',replay=True)
    assert session.candidate.candidate_id == state['candidate_id']
    return session


def copy_observations(source, folder, log):
    store = ArtifactStore(folder)
    artifacts=[]
    for path in sorted(source.rglob('*')):
        if path.is_file():
            artifacts.append(store.put('observations/'+path.relative_to(source).as_posix(),path.read_bytes()))
    log.append('inherited_observations_copied',dict(source=source.relative_to(ROOT).as_posix(),
        observations_not_reexecuted=True),artifacts)


def attach_observations(session,folder,log):
    copy_observations(session.observations.root,folder,log)
    prior.attach_observations(session,folder,log)


def source_identities():
    paths=[*AREA.glob('*.py'),AREA/'PLAN.md',AREA/'SPEC.md',AREA/'SYSTEM.txt',
           ROOT/'src/working_set_exp/reference_session.py',ROOT/'tests/test_reference_repair.py',
           OLD/'RESPONSE_SEAL.json']
    if (QUALIFIED/'SEAL.json').exists():
        paths.append(QUALIFIED/'SEAL.json')
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
        session=restore(QUALIFIED)
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
