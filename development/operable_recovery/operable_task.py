"""One declared successor: actual broad checkpoint, no supplied replacement group."""
import copy
from functools import lru_cache
from pathlib import Path

import task as prior
from working_set_exp.accounted_contribution import process_reply
from working_set_exp.jsonutil import sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.operable_session import OperableSession
from working_set_exp import operable_view

ROOT, AREA = prior.ROOT, Path(__file__).resolve().parent
ACTOR, SEED = dict(prior.ACTOR), 961221
MAX_REQUESTS, MAX_OPERATIONS = 16, 48
DESCRIPTIONS, TEST, DOC = prior.DESCRIPTIONS, prior.TEST, prior.DOC
SOURCE_RUN = prior.PARENT / 'url_continuation/run-001'
SOURCE_STATE = SOURCE_RUN / 'after/C01-O01-state.json'
present_receipts = operable_view.present_receipts


def reply_schema():
    return operable_view.reply_schema(DESCRIPTIONS)


def operating_reference():
    return operable_view.operating_reference(DESCRIPTIONS)


def expected_native(request):
    prior.require(request['seed'] == SEED, 'declared successor seed differs')
    normalized = copy.deepcopy(request)
    normalized['seed'] = prior.SEED
    return prior.expected_native(normalized)


@lru_cache(maxsize=3)
def checker(scope='public'):
    prior.require(scope in DESCRIPTIONS, 'unknown scope')
    values = dict(_BASELINE_FILES={p:b.decode() for p,b in prior.starting_candidate().files},
                  _SCOPE=scope, _EXAMPLES_HELPER=(AREA/'examples.py').read_text(encoding='utf-8'))
    return ''.join(k+' = '+repr(v)+'\n' for k,v in values.items()).encode() + (AREA/'CHECK.py').read_bytes()


def initial_session(observation_root=None, replay=False):
    state = prior.read(SOURCE_STATE)
    seal = prior.read(SOURCE_RUN/'RESPONSE_SEAL.json')
    row, = [r for r in seal['files'] if r['path']=='after/C01-O01-state.json']
    prior.require(sha256_file(SOURCE_STATE)==row['sha256'], 'historical broad checkpoint differs')
    session = OperableSession(prior.starting_candidate(), {s:checker(s) for s in DESCRIPTIONS},
        (prior.AREA/'TASK.txt').read_text(encoding='utf-8'), edit_checks={TEST:'tests', DOC:'public'},
        pairs=state['pairs'], call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
        observations=ObservationStore(observation_root or AREA/'.unbound-observations', replay=replay))
    for key in ('ranges', 'saved', 'last'):
        setattr(session, key, copy.deepcopy(state[key]))
    prior.require(session.candidate.candidate_id==state['candidate_id'] and len(session.pairs)==5
        and session.working_account() is None and not session.last['result']['accepted'], 'starting state differs')
    # Historical visibility is not delivery of the new recovery input.
    session.delivered_sources = []
    session.enter_recovery('recorded capacity rejection; selected source remains designated but its bodies are omitted for this recovery decision')
    return session


def snapshot(session):
    return {**prior.snapshot(session), 'recovery':session.recovery,
            'recovery_obstacle':copy.deepcopy(session.recovery_obstacle), 'control_tier':session.control_tier}


def attach_observations(session, folder, log):
    def preserved(record, artifacts):
        log.append('check_observation_preserved', record,
            [{**r, 'path':'observations/'+r['path']} for r in artifacts])
    session.observations = ObservationStore(folder/'observations', on_preserved=preserved)


def source_identities():
    paths = [*AREA.glob('*.py'), AREA/'PLAN.md', AREA/'SPEC.md', AREA/'SYSTEM.txt',
             ROOT/'tests/test_operable_recovery.py', SOURCE_STATE, SOURCE_RUN/'RESPONSE_SEAL.json']
    return {**prior.source_identities(), **{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}


class Task:
    def __init__(self, scenario='complete', version='001', replay_folder=None):
        self.scenario, self.condition = scenario, 'operable_recovery'
        self.PACKAGE = AREA / f'preparation-{scenario}-{version}'
        self.RUN, self.MANIFEST = AREA/'run-001', AREA/'EXECUTION_MANIFEST.json'
        self.replay_folder = replay_folder

    def initial_session(self):
        return initial_session(self.replay_folder/'observations' if self.replay_folder else None,
                               replay=self.replay_folder is not None)

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(prior, name)


def __getattr__(name):
    return getattr(prior, name)
