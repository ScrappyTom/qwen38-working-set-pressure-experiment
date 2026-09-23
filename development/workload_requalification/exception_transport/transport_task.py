"""Distinct saved-work coverage entry with truthful full-observation projection."""
import copy
from pathlib import Path
import bootstrap
import parser_roundtrip as historical
import saved_task as previous
import transport_capture
import transport_reports
from working_set_exp.candidate import Candidate
from working_set_exp.observations import ObservationStore
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file

ROOT,AREA=previous.ROOT,Path(__file__).resolve().parent
ACTOR,SEED=previous.ACTOR,previous.SEED
MAX_REQUESTS,MAX_OPERATIONS=24,72
OWNER_DIRECTION=previous.OWNER_DIRECTION
TASK_SHA='00b8d4e25a21157107461e140553b6195566c1c604912a438f975004bc113224'
STARTING_ID=historical.STARTING_ID

class Session(previous.Session):
    assessment_api=transport_reports
    def view(self,**kwargs):
        value=super().view(**kwargs)
        value['episode_annotation']=('This coverage contribution starts from saved library, tests and documentation and39 historical operations. '
            'Rows marked prior_work belong to the earlier saved contribution; this_contribution rows record this new coverage assignment. '
            'The task is not a new failure report after each action. Only the test file is assigned for editing.')
        return value

def checker():
    candidate,_=historical.starting_work()
    return transport_capture.preserve_observations(candidate.file_map,historical.base.task.checker(),
                                                   (historical.AREA/'PUBLIC_CHECK.py').read_bytes())

def history_folders():
    base=ROOT/'development/bounded_working_set'
    return [base/name/f'turn-{i:02d}' for name in ('assisted-regression','parser-documentation') for i in range(1,5)]

def initial_session(folder,replay=False):
    candidate,state=historical.starting_work()
    assert candidate.candidate_id==STARTING_ID
    raw=(AREA/'TASK.txt').read_bytes();assert sha256_bytes(raw)==TASK_SHA
    assert raw==(historical.AREA/'TASK.txt').read_bytes()
    code=checker()
    session=Session(candidate,{'public':code},raw.decode(),pairs=copy.deepcopy(state['pairs']),edit_checks={},
        call_limit=MAX_OPERATIONS,request_limit=MAX_REQUESTS,
        observations=ObservationStore(folder,replay=replay),
        check_contracts={'public':{'checker_sha256':sha256_bytes(code),
                                  'original_acceptance_checker_sha256':sha256_bytes(historical.checker())}})
    session.diffs={int(k):v for k,v in state['diffs'].items()}
    # Keep the earlier source versions behind historical addresses, rather than
    # rebinding every old result to the currently saved version.
    session.versions.update(previous.initial_session(folder,replay).versions)
    for directory in history_folders():
        for name in ('starting-candidate.json','final-candidate.json'):
            path=directory/name
            value=previous.read(path)
            item=Candidate.create({r['path']:r['content_utf8'].encode() for r in value['files']},max_file_bytes=value['max_file_bytes'])
            assert item.candidate_id==value['candidate_id'];session.versions[item.candidate_id]=item
    session.versions[candidate.candidate_id]=candidate
    assert session.starting_archive_length==39 and session.requests_used==session.calls_used==0
    assert not session.ranges and not session.saved and session.working_account() is None
    return session

def implementation_identities():
    bound=previous.implementation_identities()
    for directory in history_folders():
        seal=previous.read(directory/'RESPONSE_SEAL.json')
        assert sha256_bytes(canonical_json_bytes(seal['files']))==seal['aggregate_sha256']
        bound[(directory/'RESPONSE_SEAL.json').relative_to(ROOT).as_posix()]=sha256_file(directory/'RESPONSE_SEAL.json')
        for row in seal['files']:
            path=directory/row['path'];assert path.resolve().is_relative_to(directory.resolve())
            bound[path.relative_to(ROOT).as_posix()]=row['sha256']
    paths=[Path(historical.__file__),historical.AREA/'TASK.txt',historical.AREA/'PUBLIC_CHECK.py',
           *AREA.glob('*.py'),*AREA.glob('TESTS-*.log'),*(AREA/'tests').glob('*.py'),
           AREA/'TASK.txt',AREA/'SYSTEM.txt',AREA/'PLAN.md',AREA/'SPEC.md']
    bound.update({p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths})
    # CPU qualification evidence is frozen independently before native exposure.
    for directory in sorted(AREA.glob('capture-qualification-*')):
        for path in directory.rglob('*'):
            if path.is_file():bound[path.relative_to(ROOT).as_posix()]=sha256_file(path)
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
    def source_identities(self):return implementation_identities()
    def implementation_identities(self):return implementation_identities()
    def operating_reference(self):
        text=super().operating_reference()
        old=('The frozen upstream suite, independent backport contract and current edited tests must pass. '
             'The separate run of current added tests against the original parser must fail or error to detect the original defect. '
             'That expected failure is successful regression detection, not a failure of the current library. '
             'There are no injected fault targets in this public check. The documentation declaration check does not establish accurate prose.')
        new=('The saved suite, edited suite, independent continuation contract and observed transport suite must succeed on the current library. '
             'Added tests must exercise copy, deepcopy and every supported pickle protocol on real parser-raised errors with and without final newline. '
             'Each of the four named isolated restoration faults must make the added suite execute and be unsuccessful: this is successful fault detection, '
             'not a current-library failure or a demand to change the library. Prior work must remain preserved. '
             'Observed transport modes and detected faults do not prove every requested attribute was asserted; direct review remains necessary.')
        assert text.count(old)==1;text=text.replace(old,new)
        return text

def __getattr__(name):return getattr(previous,name)
