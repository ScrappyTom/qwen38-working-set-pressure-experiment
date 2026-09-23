"""Reviewer-directed assignment over exact submitted work; no new host semantics."""
import copy
from pathlib import Path
import bootstrap
import continuity_task as previous
from working_set_exp.candidate import Candidate
from working_set_exp.observations import ObservationStore
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file
ROOT,AREA=previous.ROOT,Path(__file__).resolve().parent
OLD=previous.AREA/'run-002'
ACTOR,SEED=previous.ACTOR,previous.SEED
MAX_REQUESTS,MAX_OPERATIONS=57,97
OWNER_DIRECTION=previous.OWNER_DIRECTION


def restore(replay_folder=None,amend=True):
    session=previous.restore()
    state=previous.read(OLD/'final-state.json')
    for key,value in state.items():
        if key!='candidate_id':setattr(session,key,copy.deepcopy(value))
    session.diffs={int(k):v for k,v in session.diffs.items()}
    session.restored_control_fields=tuple(session.restored_control_fields)
    session.parked_source_regions=tuple(tuple(x) for x in session.parked_source_regions)
    for path in [*sorted((OLD/'after').glob('*-candidate.json')),OLD/'final-candidate.json']:
        raw=previous.read(path)
        candidate=Candidate.create({r['path']:r['content_utf8'].encode() for r in raw['files']},max_file_bytes=raw['max_file_bytes'])
        assert candidate.candidate_id==raw['candidate_id']
        session.versions[candidate.candidate_id]=candidate
        session.candidate=candidate
    assert canonical_json_bytes(previous.snapshot(session))==canonical_json_bytes(state)
    assert previous.candidate_bytes(session.candidate)==(OLD/'final-candidate.json').read_bytes()
    assert session.submitted and (session.requests_used,session.calls_used)==(49,73)
    session.observations=ObservationStore((Path(replay_folder) if replay_folder else OLD)/'observations',replay=True)
    if amend:
        session.task=(AREA/'TASK.txt').read_text(encoding='utf-8')
        session.submitted=False
        session.request_limit,session.call_limit=MAX_REQUESTS,MAX_OPERATIONS
    return session


def implementation_identities():
    seal=previous.read(OLD/'RESPONSE_SEAL.json')
    assert seal['disposition']=='checked_submission' and seal['sent_requests']==9 and seal['actual_operations']==73
    assert sha256_bytes(canonical_json_bytes(seal['files']))==seal['aggregate_sha256']
    bindings={**seal['source_sha256'],(OLD/'RESPONSE_SEAL.json').relative_to(ROOT).as_posix():sha256_file(OLD/'RESPONSE_SEAL.json')}
    for row in seal['files']:
        path=OLD/row['path'];assert path.resolve().is_relative_to(OLD.resolve())
        bindings[path.relative_to(ROOT).as_posix()]=row['sha256']
    proof=previous.AREA/'review/VERIFICATION.json';value=previous.read(proof)
    assert value['status']=='replayed_exactly' and value['submitted'] and value['requests_used']==49 and value['actual_operations']==73
    paths=[*AREA.glob('*.py'),*AREA.glob('TESTS-*.log'),AREA/'TASK.txt',AREA/'SYSTEM.txt',AREA/'PLAN.md',AREA/'SPEC.md',proof,*sorted((AREA/'tests').glob('*.py'))]
    bindings.update({p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths})
    previous.verify_sources(bindings)
    return bindings


class Task(previous.Task):
    def __init__(self,version='001',replay_folder=None):
        super().__init__(version,replay_folder)
        self.AREA=AREA;self.PACKAGE,self.RUN=AREA/f'preparation-{version}',AREA/f'run-{version}'
        self.MANIFEST=AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.MAX_REQUESTS,self.MAX_OPERATIONS=MAX_REQUESTS,MAX_OPERATIONS
    def initial_session(self):return restore(self.replay_folder)
    def initial_preceding_feedback(self):return previous.read(OLD/'final-preceding-feedback.json')
    def source_identities(self):return implementation_identities()
    def implementation_identities(self):return implementation_identities()


def __getattr__(name):return getattr(previous,name)
