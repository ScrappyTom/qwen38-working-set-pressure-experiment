"""Engineering successor configuration; no live attempt is authorized here."""
import copy
from functools import lru_cache
import importlib.util
from pathlib import Path

import operable_task as prior
from working_set_exp import decision_view
from working_set_exp.accounted_contribution import process_reply
from working_set_exp.candidate import Candidate
from working_set_exp.decision_session import DecisionSession
from working_set_exp.jsonutil import sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = prior.ROOT, Path(__file__).resolve().parent
ACTOR, SEED = prior.ACTOR, prior.SEED
DESCRIPTIONS, TEST, DOC = prior.DESCRIPTIONS, prior.TEST, prior.DOC
MAX_REQUESTS, MAX_OPERATIONS = 16, 48  # Scripted qualification envelope only.
OLD = prior.AREA/'run-001'
decode_reply, present_receipts = decision_view.decode_reply, decision_view.present_receipts
FAULTS = dict(error_class='Replace ValueError with a subclass while keeping its arguments.',
             error_arguments='Add an unexpected second exception argument.',
             error_message='Replace the exception diagnostic text.',
             eager_validation='Validate the port during result construction instead of property access.',
             empty_port='Return zero for an empty port.',zero_port='Return None for port zero.',
             maximum_port='Return 65534 for port 65535.')


def reply_schema():
    return decision_view.reply_schema(DESCRIPTIONS)


def operating_reference():
    return decision_view.operating_reference(DESCRIPTIONS)


@lru_cache(maxsize=1)
def response_constraints():
    path=ROOT/'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    assert sha256_file(path)=='ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
    spec=importlib.util.spec_from_file_location('decision_schema_converter',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict(grammar=decision_view.reply_grammar(DESCRIPTIONS,module.SchemaConverter))


def expected_native(request):
    assert 'response_format' not in request and request['grammar']==response_constraints()['grammar']
    # The pinned message template does not render decoder constraints. Reuse the
    # historical message-envelope verifier with its expected constraint key; the
    # actual saved wire keeps grammar and is separately tested by the native decoder.
    envelope=copy.deepcopy(request)
    envelope.pop('grammar')
    envelope['response_format']=reply_schema()
    return prior.expected_native(envelope)


def from_checkpoint(stem='after/C12-O01', observation_root=None):
    state=prior.read(OLD/(stem+'-state.json'))
    raw=prior.read(OLD/(stem+'-candidate.json'))
    candidate=Candidate.create({f['path']:f['content_utf8'].encode() for f in raw['files']},max_file_bytes=raw['max_file_bytes'])
    assert candidate.candidate_id==state['candidate_id']
    seal=prior.read(OLD/'RESPONSE_SEAL.json')
    for suffix in ('-state.json','-candidate.json'):
        row,=[v for v in seal['files'] if v['path']==stem+suffix]
        assert sha256_file(OLD/row['path'])==row['sha256']
    checkers={s:prior.checker(s) for s in DESCRIPTIONS}
    session=DecisionSession(candidate,checkers,(ROOT/'development/working_account/url_ports/TASK.txt').read_text(encoding='utf-8'),
        edit_checks={TEST:'tests',DOC:'public'},observations=ObservationStore(observation_root or OLD/'observations',replay=observation_root is None),
        pairs=state['pairs'],call_limit=MAX_OPERATIONS,request_limit=MAX_REQUESTS,
        check_contracts={s:dict(checker_sha256=sha256_bytes(c),fault_changes=FAULTS) for s,c in checkers.items()})
    for key in ('ranges','saved','last','recovery','recovery_obstacle','control_tier','starting_archive_length'):
        setattr(session,key,copy.deepcopy(state[key]))
    # The last acquired recovery page remains the only reconstructed focus. Do not
    # retroactively pretend earlier removed pages were retained by the old host.
    if session.recovery:
        for s in session.feedback_sources(session.last):
            session.recovery_focus.append(dict(path=s['path'],start_line=s['returned_start_line'],end_line=s['returned_end_line']))
    session.delivered_sources=[]
    session.requests_used=0
    session.starting_archive_length=len(session.pairs)
    return session


def initial_session():
    return from_checkpoint()


def snapshot(session):
    return {**prior.snapshot(session),'recovery_focus':copy.deepcopy(session.recovery_focus)}


def source_identities():
    own=[*AREA.glob('*.py'),AREA/'SYSTEM.txt',AREA/'PLAN.md',ROOT/'tests/test_decision_interface.py',
         *[ROOT/'src/working_set_exp'/name for name in ('check_assessment.py','decision_session.py','decision_view.py')]]
    return {**prior.source_identities(),**{p.relative_to(ROOT).as_posix():sha256_file(p) for p in own}}


class Task:
    def __getattr__(self,name):
        if name in globals():
            return globals()[name]
        return getattr(prior,name)


def __getattr__(name):
    return getattr(prior,name)
