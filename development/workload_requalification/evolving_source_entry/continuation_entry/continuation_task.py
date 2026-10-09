"""Twelve new requests over the exact unfinished E18 source contribution."""
import copy
from pathlib import Path
import re

import bootstrap
import source_task as previous
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = previous.ROOT, Path(__file__).resolve().parent
OLD = previous.AREA / 'run-001'
OLD_SEAL = '183150d1520d2941691a93de4265fd4a7f78601fca3c8241125eb69bed70c4e7'
OLD_VERIFICATION = '17644a5f45f90b209d5c86eadbd70dc27142d1c4575cdf100adde5b64d6f487a'
SAVED_ID = '99e533ea427f3e45364825e5353a9202d8134a5bf9dca703ce81d52e52819380'
INHERITED_REQUESTS, INHERITED_OPERATIONS = 24, 37
MAX_REQUESTS, MAX_OPERATIONS = 36, 73
ACTOR, SEED, FILE_LIMIT = previous.ACTOR, previous.SEED, previous.FILE_LIMIT
PUBLIC_SHA, DESCRIPTIONS = previous.PUBLIC_SHA, previous.DESCRIPTIONS
OWNER_DIRECTION = 'Continue the authorized source task from exact saved partial work; keep the prior finite outcome and count all lineage cost.'
read, snapshot = previous.read, previous.snapshot
candidate_bytes, process_reply = previous.candidate_bytes, previous.process_reply
task_text, operating_reference = previous.task_text, previous.operating_reference
reply_schema, decode_reply = previous.reply_schema, previous.decode_reply
response_constraints, expected_native = previous.response_constraints, previous.expected_native


class Session(previous.Session):
    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['episode_annotation'] = (
            'This is a declared continuation of the same unfinished source task. '
            'The preceding job ended at its24-request allowance without a check or submission; '
            'its saved edits, acquisitions, account and37operation records remain history. '
            'The task and public checker are unchanged. This job has12new model requests '
            'and36new operations, with cumulative limits36requests and73operations. '
            'Current source and verification describe the actual saved candidate; an older '
            'account remains model-authored. No earlier conversation or private thinking is supplied.')
        return value


def inherited_inventory():
    if sha256_file(OLD / 'RESPONSE_SEAL.json') != OLD_SEAL:
        raise ValueError('Inherited source seal changed')
    seal = read(OLD / 'RESPONSE_SEAL.json')
    if (seal['disposition'] != 'request_allowance_exhausted'
            or (seal['sent_requests'], seal['actual_operations']) != (24, 37)
            or seal['actor'] != ACTOR
            or sha256_bytes(canonical_json_bytes(seal['files'])) != seal['aggregate_sha256']):
        raise ValueError('Inherited source attempt differs')
    index = {row['path']: row for row in seal['files']}
    if len(index) != len(seal['files']):
        raise ValueError('Duplicate inherited addresses')
    return seal, index


def inherited_bytes(name):
    _, index = inherited_inventory()
    path = (OLD / name).resolve()
    if not path.is_relative_to(OLD.resolve()) or name not in index:
        raise ValueError('Inherited address differs')
    raw, row = path.read_bytes(), index[name]
    if len(raw) != row['size_bytes'] or sha256_bytes(raw) != row['sha256']:
        raise ValueError('Inherited bytes differ: ' + name)
    return raw


def inherited_state():
    return load_json_strict(inherited_bytes('final-state.json'))


def _apply_fields(session, state, candidate):
    versions = [previous.core.candidate_from_snapshot(row) for row in state['source_versions']]
    version_map = {value.candidate_id: value for value in versions}
    if (len(version_map) != len(versions) or candidate.candidate_id not in version_map
            or candidate_bytes(version_map[candidate.candidate_id]) != candidate_bytes(candidate)):
        raise ValueError('Continuation versions differ')
    for key, value in state.items():
        if key not in ('candidate_id', 'source_versions'):
            setattr(session, key, copy.deepcopy(value))
    session.candidate, session.versions = candidate, version_map
    session.diffs = previous.core._restore_diffs(state['diffs'], session.pairs)
    session.restored_control_fields = tuple(session.restored_control_fields)
    session.parked_source_regions = tuple(tuple(row) for row in session.parked_source_regions)
    return session


def _new_session(folder=None, replay=False):
    return Session(previous.starting_candidate(), {'public': previous.public_checker()}, task_text(),
        edit_checks={}, call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
        observations=ObservationStore((Path(folder) if folder else OLD) / 'observations',
            replay=replay or folder is None), check_contracts={'public': {'checker_sha256': PUBLIC_SHA}})


def initial_session(folder=None, replay=False):
    state = inherited_state()
    candidate = previous.core.candidate_from_snapshot(load_json_strict(inherited_bytes('final-candidate.json')))
    original = previous.restore(state, candidate, OLD, replay=True)
    if (canonical_json_bytes(snapshot(original)) != inherited_bytes('final-state.json')
            or candidate.candidate_id != SAVED_ID or original.submitted or original.delivery_blocked
            or (original.requests_used, original.calls_used) != (24, 37)
            or original.check_state() is not None):
        raise ValueError('Original partial source reconstruction differs')
    session = _apply_fields(_new_session(folder, replay), state, candidate)
    session.request_limit, session.call_limit = MAX_REQUESTS, MAX_OPERATIONS
    return session


def initial_preceding_feedback():
    return load_json_strict(inherited_bytes('final-preceding-feedback.json'))


def restore(state, candidate, replay_folder=None, replay=False):
    if not isinstance(candidate, Candidate):
        candidate = previous.core.candidate_from_snapshot(candidate)
    inherited = inherited_state()
    session = _new_session(replay_folder, replay)
    if (not isinstance(state, dict) or set(state) != set(snapshot(session))
            or state['candidate_id'] != candidate.candidate_id or state['starting_archive_length'] != 0
            or (state['request_limit'], state['call_limit']) != (36, 73)
            or type(state['requests_used']) is not int or not 24 <= state['requests_used'] <= 36
            or not 37 <= len(state['pairs']) <= 73 or state['pairs'][:37] != inherited['pairs']):
        raise ValueError('Continuation checkpoint ancestry, shape or opportunity differs')
    session = _apply_fields(session, state, candidate)
    for row in inherited['source_versions']:
        if (row['candidate_id'] not in session.versions
                or candidate_bytes(session.versions[row['candidate_id']]) != canonical_json_bytes(row)):
            raise ValueError('Inherited source version changed')
    if canonical_json_bytes(snapshot(session)) != canonical_json_bytes({**state, 'diffs': session.diffs}):
        raise ValueError('Continuation checkpoint reconstruction differs')
    return session


def attach_observations(session, folder, log):
    # The parent executed no checks; never synthesize inherited observations.
    _, index = inherited_inventory()
    if any(name.startswith('observations/') for name in index):
        raise ValueError('Unexpected parent check observation')
    return previous.attach_observations(session, folder, log)


def implementation_identities():
    inherited_inventory()
    proof = previous.AREA / 'review/VERIFICATION-001.json'
    if sha256_file(proof) != OLD_VERIFICATION or read(proof)['status'] != 'replayed_exactly':
        raise ValueError('Inherited exact replay proof changed')
    paths = [*AREA.glob('*.py'), *(AREA / 'tests').glob('*.py'), *(AREA / 'review').glob('*.py'),
        *(AREA / name for name in ('PLAN.md', 'SPEC.md', 'SYSTEM.txt', 'TASK.txt')),
        *AREA.glob('*TESTS*.log'), proof, OLD / 'RESPONSE_SEAL.json',
        *(OLD / name for name in ('final-state.json', 'final-candidate.json', 'final-preceding-feedback.json')),
        ROOT / 'development/workload_requalification/action_lifecycle/run_continuation.py',
        ROOT / 'development/workload_requalification/acquisition_feedback/PLAN.md',
        ROOT / 'tests/test_acquisition_feedback.py']
    for name in ('SEAL.json', 'QUALIFICATION.json'):
        paths.append(ROOT / 'development/workload_requalification/acquisition_feedback/qualification-002' / name)
    return {**previous.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}


source_identities = implementation_identities


class Task:
    def __init__(self, version='001', replay_folder=None):
        if not re.fullmatch('[0-9]{3}', version):
            raise ValueError('version must be three digits')
        self.version, self.AREA = version, AREA
        self.PACKAGE, self.RUN = AREA / f'preparation-{version}', AREA / f'run-{version}'
        self.MANIFEST = AREA / f'EXECUTION_MANIFEST-{version}.json'
        self.replay_folder = replay_folder

    def initial_session(self):
        return initial_session(self.replay_folder, self.replay_folder is not None)

    def initial_preceding_feedback(self):
        return initial_preceding_feedback()

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(previous, name)


def __getattr__(name):
    return getattr(previous, name)
