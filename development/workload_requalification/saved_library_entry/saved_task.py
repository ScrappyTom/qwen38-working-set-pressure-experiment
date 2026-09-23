"""Historical saved-library entry, preserving its distinct candidate and archive."""
import copy
from pathlib import Path
import bootstrap
import continuity_task as previous
import bounded_parser as historical
from chronology_priority import RecoveryChronologyMixin
from working_set_exp.candidate import Candidate
from working_set_exp.observations import ObservationStore
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file

ROOT,AREA=previous.ROOT,Path(__file__).resolve().parent
ACTOR,SEED=previous.ACTOR,previous.SEED
MAX_REQUESTS,MAX_OPERATIONS=32,96
OWNER_DIRECTION=previous.OWNER_DIRECTION
TASK_SHA='9d0d23e959b111960eb97ca519388f2edbbe0387b63d6b7b5eed791ea1936df1'
STARTING_ID='8ac73858f45e89ecb2df138e2accfdb105d0325ffc056e0bad7e9bf7e7c89a2d'

class Session(RecoveryChronologyMixin,previous.Session):
    def view(self,**kwargs):
        value=super().view(**kwargs)
        value['episode_annotation']=('This contribution starts from saved library work and32 historical operations. '
            'Rows marked prior_work belong to that earlier attempt; this_contribution rows record the present test/documentation assignment. '
            'The unchanged task is an assignment, not a new report after each action.')
        return value

def initial_session(folder,replay=False):
    candidate,pairs=historical.starting_evidence()
    assert candidate.candidate_id==STARTING_ID
    task=(historical.AREA/'TASK.txt').read_bytes();assert sha256_bytes(task)==TASK_SHA
    assert historical.task.checker()==previous.original.original_checker(),'historical acceptance differs'
    code=previous.original.checker()
    session=Session(candidate,{'public':code},task.decode(),pairs=pairs,edit_checks={},
        call_limit=MAX_OPERATIONS,request_limit=MAX_REQUESTS,
        observations=ObservationStore(folder,replay=replay),
        check_contracts={'public':{'checker_sha256':sha256_bytes(code),
                                  'original_acceptance_checker_sha256':previous.original.CHECKER_SHA}})
    # Preserve all source versions in the32-operation prefix, not an invented
    # alias from historical handles to the final library version.
    original=previous.original.starting_candidate();session.versions[original.candidate_id]=original
    for path in sorted((historical.OLD/'after').glob('C*-candidate.json')):
        if path.name>'C32-candidate.json':continue
        raw=previous.read(path)
        item=Candidate.create({r['path']:r['content_utf8'].encode() for r in raw['files']},max_file_bytes=raw.get('max_file_bytes',historical.task.FILE_LIMIT))
        assert item.candidate_id==raw['candidate_id'];session.versions[item.candidate_id]=item
    assert session.starting_archive_length==32 and session.calls_used==session.requests_used==0
    assert not session.ranges and not session.saved and not session.submitted
    return session

def snapshot(session):
    return dict(previous.snapshot(session),recovery_recent_count=session.recovery_recent_count)


def implementation_identities():
    bound=previous.implementation_identities()
    # Historical custody is reused, not the old host implementation as executable code.
    seal=previous.read(historical.OLD/'RESPONSE_SEAL.json')
    bound[(historical.OLD/'RESPONSE_SEAL.json').relative_to(ROOT).as_posix()]=sha256_file(historical.OLD/'RESPONSE_SEAL.json')
    for row in seal['files']:
        path=historical.OLD/row['path'];assert path.resolve().is_relative_to(historical.OLD.resolve())
        bound[path.relative_to(ROOT).as_posix()]=row['sha256']
    paths=[Path(historical.__file__),historical.AREA/'TASK.txt',*AREA.glob('*.py'),*AREA.glob('TESTS-*.log'),
        AREA/'SYSTEM.txt',AREA/'PLAN.md',AREA/'SPEC.md',*(AREA/'tests').glob('*.py')]
    bound.update({p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths})
    folder=ROOT/'development/workload_requalification/recovery_chronology/qualification-002'
    seal=previous.read(folder/'SEAL.json');assert seal['status']=='qualified_no_model_inference'
    assert sha256_bytes(canonical_json_bytes(seal['files']))==seal['aggregate_sha256']
    result=previous.read(folder/'RESULTS.json')
    assert result['status']=='qualified' and result['model_requests']==result['new_check_executions']==0
    assert result['recorded_check_replays']==1 and len(result['trials'])==4
    bound.update(seal['source_sha256'])
    bound[(folder/'SEAL.json').relative_to(ROOT).as_posix()]=sha256_file(folder/'SEAL.json')
    for row in seal['files']:
        path=folder/row['path'];assert path.resolve().is_relative_to(folder.resolve())
        bound[path.relative_to(ROOT).as_posix()]=row['sha256']
    previous.verify_sources(bound)
    return bound

class Task(previous.Task):
    def __init__(self,version='001',replay_folder=None):
        super().__init__(version,replay_folder)
        self.AREA=AREA;self.PACKAGE,self.RUN=AREA/f'preparation-{version}',AREA/f'run-{version}'
        self.MANIFEST=AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.MAX_REQUESTS,self.MAX_OPERATIONS=MAX_REQUESTS,MAX_OPERATIONS
    def initial_session(self):return initial_session((self.replay_folder or AREA/'unexecuted')/'observations',self.replay_folder is not None)
    def initial_preceding_feedback(self):return []
    snapshot=staticmethod(snapshot)
    def source_identities(self):return implementation_identities()
    def implementation_identities(self):return implementation_identities()

def __getattr__(name):return getattr(previous,name)
