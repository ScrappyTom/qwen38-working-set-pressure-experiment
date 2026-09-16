"""Declared host/checker repair package on the same original task checkpoint."""
import copy
from functools import lru_cache
from pathlib import Path

import channel_task as prior
from working_set_exp.candidate import Candidate
from working_set_exp.feedback_session import FeedbackSession, operating_reference as reference
from working_set_exp.jsonutil import sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = prior.ROOT, Path(__file__).resolve().parent
ACTOR, SEED = prior.ACTOR, prior.SEED
MAX_REQUESTS, MAX_OPERATIONS = 16, 48
OWNER_DIRECTION = 'Fix the issues and rerun.'
DESCRIPTIONS, TEST, DOC = prior.DESCRIPTIONS, prior.TEST, prior.DOC
OLD = prior.AREA/'run-001'
FAULTS = {**prior.FAULTS, 'absent_port':'Return zero for an absent port.'}
FAULTS = {k:v+' Independently targeted at each declared API/input/case.' for k,v in FAULTS.items()}


@lru_cache(maxsize=3)
def checker(scope='public'):
    assert scope in DESCRIPTIONS
    candidate = prior.Task().initial_session().candidate
    values = dict(_BASELINE_FILES={p:b.decode() for p,b in candidate.files}, _SCOPE=scope,
                  _EXAMPLES_HELPER=(ROOT/'development/operable_recovery/examples.py').read_text(encoding='utf-8'))
    return ''.join(k+' = '+repr(v)+'\n' for k,v in values.items()).encode()+(AREA/'CHECK.py').read_bytes()


def operating_reference():
    return reference(DESCRIPTIONS)


def from_checkpoint(stem='starting', observation_root=None, legacy_checks=False):
    state, raw = prior.read(OLD/(stem+'-state.json')), prior.read(OLD/(stem+'-candidate.json'))
    seal=prior.read(OLD/'RESPONSE_SEAL.json')
    for suffix in ('-state.json','-candidate.json'):
        row,=[r for r in seal['files'] if r['path']==stem+suffix]
        assert sha256_file(OLD/row['path'])==row['sha256']
    candidate=Candidate.create({f['path']:f['content_utf8'].encode() for f in raw['files']},max_file_bytes=raw['max_file_bytes'])
    checkers={s:prior.checker(s) if legacy_checks else checker(s) for s in DESCRIPTIONS}
    session=FeedbackSession(candidate,checkers,(AREA/'TASK.txt').read_text(encoding='utf-8'),
        edit_checks={TEST:'tests',DOC:'public'},observations=ObservationStore(observation_root or OLD/'observations',replay=observation_root is None),
        pairs=state['pairs'],call_limit=MAX_OPERATIONS,request_limit=MAX_REQUESTS,
        check_contracts={s:dict(checker_sha256=sha256_bytes(c),fault_changes=FAULTS) for s,c in checkers.items()})
    for key in ('ranges','saved','last','recovery','recovery_obstacle','control_tier','recovery_focus'):
        setattr(session,key,copy.deepcopy(state[key]))
    session.delivered_sources=[]
    session.starting_archive_length=len(session.pairs)
    assert session.candidate.candidate_id==state['candidate_id']
    return session


def source_identities():
    paths=[*AREA.glob('*.py'),AREA/'PLAN.md',AREA/'SPEC.md',AREA/'SYSTEM.txt',AREA/'TASK.txt',
        ROOT/'src/working_set_exp/feedback_session.py',ROOT/'src/working_set_exp/feedback_assessment.py',
        ROOT/'tests/test_feedback_repair.py',OLD/'RESPONSE_SEAL.json']
    return {**prior.source_identities(),**{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}


class Task:
    def __init__(self,version='001',replay_folder=None):
        self.PACKAGE,self.RUN=AREA/f'preparation-{version}',AREA/'run-001'
        self.MANIFEST=AREA/'EXECUTION_MANIFEST.json'
        self.replay_folder=replay_folder

    def initial_session(self):
        s=from_checkpoint()
        if self.replay_folder:
            s.observations=ObservationStore(self.replay_folder/'observations',replay=True)
        assert len(s.pairs)==5 and s.working_account() is None and s.recovery
        return s

    def __getattr__(self,name):
        return globals()[name] if name in globals() else getattr(prior,name)


def __getattr__(name):
    return getattr(prior,name)
