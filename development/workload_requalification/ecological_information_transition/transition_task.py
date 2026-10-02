"""A declared selection transition over the exact, pre-submission C16 checkpoint."""
import copy
import difflib
import importlib.util
import re
from pathlib import Path

import bootstrap
import ecological_task as original
import contract_checker
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = original.ROOT, Path(__file__).resolve().parent
OLD = original.AREA / 'run-001'
OLD_SEAL = '6550a09cdadf7369e6151bcf39ec8baef11c855df08b10bfb5fa022ceaf1182b'
CHECKPOINT = 'after/C16-O01-state.json'
CHECKPOINT_SHA = '80a98f182060145b6b5c17fba221f89939c11a02875bee5af235124cd2eb65df'
SAVED_ID = '8009375d715d85c91b329ec12e58df9c091c95c521cd2b56f1e5b725ad05c60e'
INHERITED_REQUESTS, INHERITED_OPERATIONS = 16, 24
MAX_REQUESTS, MAX_OPERATIONS = 24, 72
CONDITIONS = ('unchanged', 'released')
ACTOR, SEED, FILE_LIMIT = original.ACTOR, original.SEED, original.FILE_LIMIT
TARGET, SAVED_RUNS = original.TARGET, original.SAVED_RUNS
PUBLIC_SHA = contract_checker.checker_sha256()
OWNER_DIRECTION = 'Execute the authorized, controlled C16 information-transition diagnostic; preserve all completed E20 work.'
DESCRIPTIONS = {'public': 'Execute the original E20 public program and the unchanged twelve-case byte/count boundary probe on this candidate. Both must pass before submission.'}
read, candidate_bytes, process_reply = original.read, original.candidate_bytes, original.process_reply
_spec = importlib.util.spec_from_file_location('transition_contract_helpers',
    ROOT / 'development/workload_requalification/ecological_contract_continuation/continuation_task.py')
contract_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contract_core)
inherited_inventory, inherited_bytes = contract_core.inherited_inventory, contract_core.inherited_bytes
_replacement_matches = contract_core._replacement_matches

def inherited_state():
    raw = inherited_bytes(CHECKPOINT)
    if sha256_bytes(raw) != CHECKPOINT_SHA:
        raise ValueError('C16 checkpoint changed')
    return load_json_strict(raw)

def task_text():
    return original.task_text() + (
        '\n\nCHECKPOINT CONTINUATION\nContinue the saved work after sixteen model requests '
        'and twenty-four operations, before any submission. Preserve the completed changes '
        'and satisfy the original task contract. The registered public checker now executes '
        'the original acceptance program and twelve byte/count boundary cases with '
        'max_file_bytes=0,1,5 and max_files=0,1,2,10. No result of this check is supplied '
        'initially. Original eleven-file inspection remains historical and satisfied; '
        'current exact source and version guards govern new edits. Eight model requests '
        'and 48 operations remain within unchanged absolute limits of 24 and 72. '
        'Checks are actor-requested; edits do not automatically trigger them.')

class Session(original.Session):
    assessment_api = contract_checker

    def __init__(self, *args, condition='unchanged', **kwargs):
        if condition not in CONDITIONS:
            raise ValueError('Unknown transition condition')
        self.transition_condition = condition
        super().__init__(*args, **kwargs)

    def reply_schema(self):
        return reply_schema()

    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['episode_annotation'] = (
            'This continues the recorded repair at its checkpoint after sixteen requests '
            'and twenty-four operations, before submission. Task text is the same original '
            'assignment, not a new failure observation. Saved changes, accounts and operation '
            'history belong to this repair. The selected sources are the material currently '
            'designated and shown; released content remains exactly recoverable. Historical '
            'inspection does not supply current editing authority. No earlier conversation '
            'or private thinking is supplied. The public checker uses the declared full scope.')
        return value

def _new_session(condition, folder=None, replay=False):
    return Session(original.starting_candidate(), {'public': contract_checker.public_checker()},
        task_text(), condition=condition, edit_checks={}, call_limit=MAX_OPERATIONS,
        request_limit=MAX_REQUESTS,
        observations=ObservationStore((Path(folder) if folder else AREA / 'unexecuted' / condition)
            / 'observations', replay=replay or folder is None),
        check_contracts=contract_checker.contracts())

def initial_session(condition='unchanged', folder=None, replay=False):
    state = inherited_state()
    candidate = original.candidate_from_snapshot(load_json_strict(
        inherited_bytes('after/C16-O01-candidate.json')))
    prior = original.restore(state, candidate, OLD, replay=True)
    if (canonical_json_bytes(original.snapshot(prior)) != inherited_bytes(CHECKPOINT)
            or candidate.candidate_id != SAVED_ID or prior.submitted
            or (prior.requests_used, prior.calls_used) != (16, 24)
            or len(prior.ranges) != 7 or any(p['response']['action'] in ('check', 'submit')
                for p in prior.pairs)):
        raise ValueError('Exact pre-submission C16 entry differs')
    session = contract_core._restore_fields(_new_session(condition, folder, replay), state, candidate)
    # The saved preceding dispatch is history, not authority for the new branch.
    # Both conditions establish authority afresh only when their actual input is sent.
    session.delivered_sources = []
    if condition == 'released':
        session.ranges = [copy.deepcopy(row) for row in state['ranges'] if row['path'] == SAVED_RUNS]
        if len(session.ranges) != 1:
            raise ValueError('Actual saved-runs designation missing')
    return session

def initial_preceding_feedback():
    return load_json_strict(inherited_bytes('after/C16-O01-preceding-feedback.json'))

def snapshot(session):
    return {**original.snapshot(session), 'transition_condition': session.transition_condition}

def restore(state, candidate, replay_folder=None, replay=False):
    if not isinstance(candidate, original.Candidate):
        candidate = original.candidate_from_snapshot(candidate)
    inherited = inherited_state()
    condition = state.get('transition_condition')
    session = _new_session(condition, replay_folder, replay)
    if (set(state) != set(snapshot(session)) or state['candidate_id'] != candidate.candidate_id
            or state['starting_archive_length'] != 0
            or (state['request_limit'], state['call_limit']) != (24, 72)
            or type(state['requests_used']) is not int or not 16 <= state['requests_used'] <= 24
            or not 24 <= len(state['pairs']) <= 72 or state['pairs'][:24] != inherited['pairs']
            or state['source_prerequisites'] != inherited['source_prerequisites']):
        raise ValueError('Checkpoint condition, ancestry, coverage or opportunity differs')
    session = contract_core._restore_fields(session, state, candidate)
    for row in inherited['source_versions']:
        if (row['candidate_id'] not in session.versions
                or candidate_bytes(session.versions[row['candidate_id']]) != canonical_json_bytes(row)):
            raise ValueError('Inherited source version changed')
    _validate_effects(session, inherited)
    if canonical_json_bytes(snapshot(session)) != canonical_json_bytes({**state, 'diffs': session.diffs}):
        raise ValueError('Exact transition checkpoint reconstruction differs')
    return session

def attach_observations(session, folder, log):
    # C16 has no executed checks. Never import the later CHK-0027 observation.
    original.attach_observations(session, folder, log)

def reply_schema():
    return original.previous.operational_reply.reply_schema(DESCRIPTIONS)

def decode_reply(content):
    return original.previous.operational_reply.decode_reply(content, DESCRIPTIONS)

def implementation_identities():
    bound = dict(contract_core.implementation_identities())
    paths = [*AREA.glob('*.py'), *(AREA / 'tests').glob('*.py'),
        *(AREA / 'apparatus_qualification').glob('*.py'),
        *(AREA / 'apparatus_qualification').glob('*.ps1'),
        *(AREA / name for name in ('PLAN.md', 'SPEC.md', 'SYSTEM.txt')),
        AREA / 'apparatus_qualification/PLAN.md', AREA / 'review/APPARATUS-DECISION-001.json']
    bound.update({p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths})
    original.verify_sources(bound)
    return bound

source_identities = implementation_identities

class Task(original.Task):
    def __init__(self, condition='unchanged', version='001', replay_folder=None):
        if condition not in CONDITIONS:
            raise ValueError('Unknown transition condition')
        super().__init__(version, replay_folder)
        self.condition, self.AREA = condition, AREA
        branch = AREA / condition
        self.PACKAGE, self.RUN = branch / f'preparation-{version}', branch / f'run-{version}'
        self.MANIFEST = branch / f'EXECUTION_MANIFEST-{version}.json'
        self.MAX_REQUESTS, self.MAX_OPERATIONS = MAX_REQUESTS, MAX_OPERATIONS
        self.OWNER_DIRECTION = OWNER_DIRECTION

    def initial_session(self):
        return initial_session(self.condition, self.replay_folder, self.replay_folder is not None)

    def initial_preceding_feedback(self):
        return initial_preceding_feedback()

    def restore(self, state, candidate, replay_folder=None, replay=False):
        if state.get('transition_condition') != self.condition:
            raise ValueError('Checkpoint belongs to a different branch')
        return restore(state, candidate, replay_folder, replay)

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(original, name)

def __getattr__(name):
    return getattr(original, name)


def _validate_effects(session, inherited):
    current = session.versions[SAVED_ID]
    reached = {row['candidate_id'] for row in inherited['source_versions']}
    new_job_submitted, latest_new_check = False, None
    for sequence, pair in enumerate(session.pairs[INHERITED_OPERATIONS:], INHERITED_OPERATIONS + 1):
        if new_job_submitted:
            raise ValueError('New job archive continues after its accepted submission')
        action, receipt = pair['response'], pair['result']
        name = action['action']
        if name in ('patch', 'replace_region') and receipt.get('accepted'):
            path = receipt['path']
            successor = session.versions.get(receipt['candidate_id'])
            if (successor is None or action['expected_candidate_id'] != current.candidate_id
                    or receipt['previous_candidate_id'] != current.candidate_id
                    or receipt['file_sha256'] != successor.file_sha256(path)
                    or receipt['exact_action_handle'] != f'EVT-{sequence:04d}'
                    or any(successor.file_map[p] != data for p, data in current.files if p != path)):
                raise ValueError('Checkpoint edit receipt or candidate lineage differs')
            before, after = current.file_map[path].decode(), successor.file_map[path].decode()
            expected = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                fromfile='a/' + path, tofile='b/' + path))
            if receipt['applied_diff'] != expected or current.candidate_id == successor.candidate_id:
                raise ValueError('Checkpoint edit diff differs from exact versions')
            if name == 'patch':
                if (action['path'] != path or action['expected_file_sha256'] != current.file_sha256(path)
                        or not action['old'] or before.count(action['old']) != 1
                        or before.replace(action['old'], action['new'], 1) != after):
                    raise ValueError('Checkpoint patch differs from its recorded proposal')
            elif not _replacement_matches(before, after, action, receipt):
                raise ValueError('Checkpoint source replacement differs from its recorded proposal')
            current = successor
            reached.add(current.candidate_id)
        elif name == 'check' and (receipt.get('accepted') or receipt.get('observation') or receipt.get('executed')):
            if not receipt.get('executed') or not receipt.get('observation'):
                raise ValueError('Checkpoint check receipt lacks its executed observation')
            observed = session.observations.read(receipt['observation'])
            if (action['expected_candidate_id'] != current.candidate_id
                    or receipt['checked_candidate_id'] != current.candidate_id
                    or observed['candidate_id'] != current.candidate_id
                    or observed['check_id'] != action['check_id']):
                raise ValueError('Checkpoint check candidate or scope differs')
            if (receipt['check_id'] != action['check_id']
                    or receipt['check_definition_sha256'] != sha256_bytes(session.checkers[action['check_id']])
                    or observed['checker_sha256'] != receipt['check_definition_sha256']
                    or any(receipt[key] != observed[key] for key in
                        ('accepted', 'executed', 'passed', 'returncode', 'termination', 'capture_complete', 'streams'))):
                raise ValueError('Checkpoint check receipt differs from preserved observation')
            latest_new_check = (current.candidate_id, observed['passed'])
        elif name == 'submit' and receipt.get('accepted'):
            if (action['expected_candidate_id'] != current.candidate_id
                    or receipt.get('submitted_candidate_id') != current.candidate_id
                    or not receipt.get('public_check_passed_for_candidate')
                    or latest_new_check != (current.candidate_id, True)):
                raise ValueError('New job submission lacks its own current registered pass')
            new_job_submitted = True
    if current.candidate_id != session.candidate.candidate_id or set(session.versions) != reached:
        raise ValueError('Checkpoint current or historical candidate ancestry differs')
    if session.submitted is not new_job_submitted:
        raise ValueError('Current submission designation differs from the reopened job archive')
