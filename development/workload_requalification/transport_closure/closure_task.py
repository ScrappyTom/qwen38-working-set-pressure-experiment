"""Expose the terminal actual pass with an explicitly increased finite allowance."""
import copy
from pathlib import Path
import bootstrap
import search_task as previous
from working_set_exp.candidate import Candidate
from working_set_exp.observations import ObservationStore
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file
ROOT,AREA=previous.ROOT,Path(__file__).resolve().parent
OLD=previous.AREA/'run-002'
OLD_SEAL='0d35a4fae3ea65cda3cadb6c2ce74ef9422929fcfaec8fd716d85b17538cbf1c'
ACTOR,SEED=previous.ACTOR,previous.SEED
MAX_REQUESTS,MAX_OPERATIONS=26,38
OWNER_DIRECTION=previous.OWNER_DIRECTION

def restore(replay_folder=None,extend=True):
    assert sha256_file(OLD/'RESPONSE_SEAL.json')==OLD_SEAL
    seal=previous.read(OLD/'RESPONSE_SEAL.json');index={r['path']:r for r in seal['files']}
    def checked(path):
        assert sha256_file(path)==index[path.relative_to(OLD).as_posix()]['sha256']
        return previous.read(path)
    state=checked(OLD/'final-state.json')
    session=previous.restore()
    for key,value in state.items():
        if key!='candidate_id':setattr(session,key,copy.deepcopy(value))
    session.diffs={int(k):v for k,v in session.diffs.items()}
    session.restored_control_fields=tuple(session.restored_control_fields)
    session.parked_source_regions=tuple(tuple(x) for x in session.parked_source_regions)
    for path in [*sorted((OLD/'after').glob('*-candidate.json')),OLD/'final-candidate.json']:
        raw=checked(path)
        item=Candidate.create({r['path']:r['content_utf8'].encode() for r in raw['files']},max_file_bytes=raw['max_file_bytes'])
        assert item.candidate_id==raw['candidate_id'];session.versions[item.candidate_id]=item;session.candidate=item
    session.observations=ObservationStore((Path(replay_folder) if replay_folder else OLD)/'observations',replay=True)
    assert canonical_json_bytes(previous.snapshot(session))==canonical_json_bytes(state)
    assert previous.candidate_bytes(session.candidate)==(OLD/'final-candidate.json').read_bytes()
    assert (session.requests_used,session.calls_used,session.starting_archive_length)==(24,34,39)
    assert not session.submitted and not session.delivery_blocked
    if extend:session.request_limit,session.call_limit=MAX_REQUESTS,MAX_OPERATIONS
    return session

def implementation_identities():
    assert sha256_file(OLD/'RESPONSE_SEAL.json')==OLD_SEAL
    seal=previous.read(OLD/'RESPONSE_SEAL.json')
    assert seal['disposition']=='request_allowance_exhausted' and seal['sent_requests']==11 and seal['actual_operations']==34
    assert sha256_bytes(canonical_json_bytes(seal['files']))==seal['aggregate_sha256']
    bound=dict(seal['source_sha256']);bound[(OLD/'RESPONSE_SEAL.json').relative_to(ROOT).as_posix()]=OLD_SEAL
    for row in seal['files']:
        path=OLD/row['path'];assert path.resolve().is_relative_to(OLD.resolve());bound[path.relative_to(ROOT).as_posix()]=row['sha256']
    proof=previous.AREA/'review/VERIFICATION.json';v=previous.read(proof)
    assert v['status']=='replayed_exactly' and v['requests_used']==24 and v['actual_operations']==34 and not v['submitted']
    paths=[*AREA.glob('*.py'),*AREA.glob('TESTS-*.log'),*(AREA/'tests').glob('*.py'),*(AREA/n for n in ('TASK.txt','SYSTEM.txt','PLAN.md','SPEC.md')),proof]
    bound.update({p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths});previous.verify_sources(bound)
    return bound

class Task(previous.Task):
    def __init__(self,version='001',replay_folder=None):
        super().__init__(version,replay_folder);self.AREA=AREA
        self.PACKAGE,self.RUN=AREA/f'preparation-{version}',AREA/f'run-{version}'
        self.MANIFEST=AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.MAX_REQUESTS,self.MAX_OPERATIONS=MAX_REQUESTS,MAX_OPERATIONS
    def initial_session(self):return restore(self.replay_folder)
    def initial_preceding_feedback(self):return previous.read(OLD/'final-preceding-feedback.json')
    def source_identities(self):return implementation_identities()
    def implementation_identities(self):return implementation_identities()

def __getattr__(name):return getattr(previous,name)
