"""Opt-in diagnostic presentation over the exact exhausted configparser state."""
import copy
from pathlib import Path

import bootstrap
import operational_task as previous
import diagnostic_reports
import source_verification
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = previous.ROOT, Path(__file__).resolve().parent
OLD = previous.AREA/'run-001'
ACTOR, SEED = previous.ACTOR, previous.SEED
MAX_REQUESTS, MAX_OPERATIONS = 56, 108
INHERITED_REQUESTS, INHERITED_OPERATIONS = 40, 60
OWNER_DIRECTION = previous.OWNER_DIRECTION


class Session(previous.Session):
    assessment_api = diagnostic_reports


def restore(stem='final', *, revised=True, replay_folder=None, extend=False):
    state = previous.read(OLD/f'{stem}-state.json')
    raw = previous.read(OLD/f'{stem}-candidate.json')
    session = previous.Task(replay_folder=OLD).initial_session()
    session.candidate = Candidate.create({r['path']:r['content_utf8'].encode() for r in raw['files']},max_file_bytes=raw['max_file_bytes'])
    for key,value in state.items():
        if key != 'candidate_id':setattr(session,key,copy.deepcopy(value))
    session.diffs = {int(k):v for k,v in session.diffs.items()}
    session.restored_control_fields = tuple(session.restored_control_fields)
    session.parked_source_regions = tuple(tuple(row) for row in session.parked_source_regions)
    # Restore exact historical versions as well as the designated current version.
    for path in sorted((OLD/'after').glob('*-candidate.json')):
        if stem.startswith('after/') and path.stem.removesuffix('-candidate') > Path(stem).name:
            continue
        value=previous.read(path)
        if value['candidate_id'] not in session.versions:
            candidate=Candidate.create({r['path']:r['content_utf8'].encode() for r in value['files']},max_file_bytes=value['max_file_bytes'])
            assert candidate.candidate_id==value['candidate_id']
            session.versions[candidate.candidate_id]=candidate
    session.versions[session.candidate.candidate_id]=session.candidate
    assert canonical_json_bytes(previous.snapshot(session))==canonical_json_bytes(state)
    assert previous.candidate_bytes(session.candidate)==(OLD/f'{stem}-candidate.json').read_bytes()
    if revised:session.__class__=Session
    if extend:
        assert stem=='final' and (session.requests_used,session.calls_used)==(40,60)
        session.request_limit,session.call_limit=MAX_REQUESTS,MAX_OPERATIONS
    if replay_folder:
        session.observations=ObservationStore(Path(replay_folder)/'observations',replay=True)
    return session


def checkpoint_bindings():
    seal=previous.read(OLD/'RESPONSE_SEAL.json')
    assert seal['disposition']=='request_allowance_exhausted' and seal['sent_requests']==40 and seal['actual_operations']==60
    assert seal['actor']==ACTOR and seal['port_free']
    assert sha256_bytes(canonical_json_bytes(seal['files']))==seal['aggregate_sha256']
    bindings={**seal['source_sha256'],(OLD/'RESPONSE_SEAL.json').relative_to(ROOT).as_posix():sha256_file(OLD/'RESPONSE_SEAL.json')}
    for row in seal['files']:
        path=OLD/row['path']
        assert path.resolve().is_relative_to(OLD.resolve())
        bindings[path.relative_to(ROOT).as_posix()]=row['sha256']
    proof=previous.read(previous.AREA/'review/VERIFICATION.json')
    assert proof['status']=='replayed_exactly' and proof['actual_operations']==60 and proof['completed_replies']==40
    path=previous.AREA/'review/VERIFICATION.json'
    bindings[path.relative_to(ROOT).as_posix()]=sha256_file(path)
    verify_sources(bindings)
    return bindings


def verify_sources(values):
    source_verification.verify_sources(ROOT,values,workers=4)


def implementation_identities():
    paths=[*AREA.glob('*.py'),*sorted((AREA/'tests').glob('*.py')),AREA/'PLAN.md',AREA/'SPEC.md',AREA/'SYSTEM.txt',
           *AREA.glob('TESTS-*.log'),AREA/'VERIFICATION_TIMING-001.json']
    return {**checkpoint_bindings(),**{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}


class Task(previous.Task):
    def __init__(self,version='001',replay_folder=None):
        super().__init__(version,replay_folder)
        self.AREA=AREA
        self.PACKAGE,self.RUN=AREA/f'preparation-{version}',AREA/f'run-{version}'
        self.MANIFEST=AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.MAX_REQUESTS,self.MAX_OPERATIONS=MAX_REQUESTS,MAX_OPERATIONS

    def initial_session(self):return restore(replay_folder=self.replay_folder,extend=True)
    def initial_preceding_feedback(self):return previous.read(OLD/'final-preceding-feedback.json')
    def verify_sources(self,values):verify_sources(values)
    def implementation_identities(self):return implementation_identities()
    def source_identities(self):return implementation_identities()
    def operating_reference(self):
        text=super().operating_reference()
        old='Use inspect_check for complete criterion records and inspect_observation for raw captured bytes.'
        assert text.count(old)==1
        text=text.replace(old,'Use inspect_check for exact diagnostic field fragments and inspect_observation for raw captured bytes.')
        old=('Returns up to four complete assessment records, unmet criteria first. offset=0 starts; next_offset continues records, not bytes. '
             'Diagnostic text may be explicitly abbreviated with exact raw observation access. Never reruns a check or changes source selection.')
        assert text.count(old)==1
        text=text.replace(old,('Returns up to two exact diagnostic field fragments. offset=0 starts; next_offset continues fragment records, not criteria or byte offsets. '
            'Entries identify the test or trace field and its UTF-8 byte extent; complete=true means the whole field is shown. '
            'Compact criterion outcomes accompany each page. Never reruns a check or changes source selection.'))
        return text + ('\nCheck reports retain compact outcomes for the independent contract and the current edited tests. '
            'diagnostics lists selected actual failures with direct inspect_check offsets; counts distinguish shown and remaining. '
            'inspect_check offsets index diagnostic field fragments, not criteria. Each entry names the test or trace field, '
            'its exact UTF-8 byte range and whether the entire field is present. Follow next_offset to read remaining records. '
            'The overview returns to the same bounded diagnostics after other operations; detailed observations remain historical, '
            'and applicability still depends on both candidate and checker.')


def __getattr__(name):return getattr(previous,name)
