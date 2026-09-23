"""Restore actual closed decision states for offline projection qualification."""
import copy
from pathlib import Path
import bootstrap
import followup_task as previous
from chronology import RecoveryChronologyMixin
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file

ROOT,AREA=previous.ROOT,Path(__file__).resolve().parent
class Session(RecoveryChronologyMixin,previous.previous.Session):
    pass

def restore(case):
    if case=='documentation-C52':
        module,run,stem=previous,previous.AREA/'run-001','after/C51-O02'
        session=previous.restore()
        session.observations=previous.ObservationStore(run/'observations',replay=True)
        wire=previous.read(run/'calls/C52-wire-request.json')
    elif case=='diagnostic-C48':
        module,run,stem=previous.previous,previous.previous.AREA/'run-002','after/C47-O01'
        session=previous.previous.restore(extend=True)
        session.observations=previous.ObservationStore(run/'observations',replay=True)
        wire=previous.read(run/'calls/C48-wire-request.json')
    else:raise ValueError(case)
    state=previous.read(run/(stem+'-state.json'))
    for key,value in state.items():
        if key!='candidate_id':setattr(session,key,copy.deepcopy(value))
    session.diffs={int(k):v for k,v in session.diffs.items()}
    session.restored_control_fields=tuple(session.restored_control_fields)
    session.parked_source_regions=tuple(tuple(x) for x in session.parked_source_regions)
    raw=previous.read(run/(stem+'-candidate.json'))
    session.candidate=Candidate.create({x['path']:x['content_utf8'].encode() for x in raw['files']},max_file_bytes=raw['max_file_bytes'])
    session.versions[session.candidate.candidate_id]=session.candidate
    assert canonical_json_bytes(previous.snapshot(session))==canonical_json_bytes(state)
    assert session.recovery and not session.view()['recent_activity']
    return session,wire,run

def snapshot(session):
    return dict(previous.snapshot(session),recovery_recent_count=session.recovery_recent_count)

def bindings():
    bound=previous.implementation_identities()
    run=previous.AREA/'run-001'
    seal=previous.read(run/'RESPONSE_SEAL.json')
    bound.update(seal['source_sha256'])
    bound[(run/'RESPONSE_SEAL.json').relative_to(ROOT).as_posix()]=sha256_file(run/'RESPONSE_SEAL.json')
    for row in seal['files']:
        path=run/row['path'];assert path.resolve().is_relative_to(run.resolve())
        bound[path.relative_to(ROOT).as_posix()]=row['sha256']
    for path in [*AREA.glob('*.py'),AREA/'PLAN.md',*AREA.glob('TESTS-*.log'),*(AREA/'tests').glob('*.py')]:
        bound[path.relative_to(ROOT).as_posix()]=sha256_file(path)
    previous.verify_sources(bound)
    return bound
