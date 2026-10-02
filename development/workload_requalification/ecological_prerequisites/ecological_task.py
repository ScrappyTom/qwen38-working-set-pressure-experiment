"""Prospective E19 entry with a declared first-mutation exposure prerequisite."""
import copy
import importlib.util
import re
from pathlib import Path

import bootstrap
import inspection_policy as policy
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('ecological_observation_prerequisite_base',
    ROOT / 'development/workload_requalification/ecological_observation_entry/ecological_task.py')
previous = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(previous)
REQUIRED_INSPECTION_PATHS = previous.REQUIRED_INSPECTION_PATHS
if REQUIRED_INSPECTION_PATHS != policy.REQUIRED_PATHS:
    raise ValueError('Explicit task paths and prerequisite policy differ')
MAX_REQUESTS, MAX_OPERATIONS = previous.MAX_REQUESTS, previous.MAX_OPERATIONS
OWNER_DIRECTION = ('Continue the authorized original E19 observation task with a prospectively '
    'declared first-mutation exact-source exposure prerequisite.')

exposure_policy, exposure_state = policy.exposure_policy, policy.exposure_state


class Session(previous.Session):
    def __init__(self, *args, **kwargs):
        policy.initialize(self)
        super().__init__(*args, **kwargs)

    def clone(self):
        other = super().clone()
        other._source_exposures = copy.deepcopy(self._source_exposures)
        other._first_source_mutation = copy.deepcopy(self._first_source_mutation)
        return other

    def prerequisite_state(self):
        return exposure_state(self)

    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['task_prerequisites'] = policy.view(self)
        return value

    def mark_delivered(self, view):
        if view.get('task_prerequisites') != policy.view(self):
            raise ValueError('delivered source prerequisite view differs')
        super().mark_delivered(view)
        policy.credit_delivered(self, view)

    def _patch(self, action):
        rejected = policy.mutation_rejection(self)
        if rejected is not None:
            return rejected
        result = super()._patch(action)
        policy.record_first_mutation(self, result)
        return result


def initial_session(folder=None, replay=False):
    original, transport, bodies = previous.imports()
    return Session(previous.starting_candidate(), {'public': previous.public_checker()},
        previous.task_text(), edit_checks={}, call_limit=MAX_OPERATIONS,
        request_limit=MAX_REQUESTS,
        observations=ObservationStore((Path(folder) if folder is not None else AREA / 'unexecuted')
            / 'observations', replay=replay),
        check_contracts={'public': {'checker_sha256': previous.PUBLIC_SHA}},
        original_observations=original, imported_observations=transport,
        imported_bodies=bodies, retain_imported_captures=True)


def operating_reference():
    return previous.operating_reference() + '\n\n' + policy.REFERENCE_ADDITION


def snapshot(session):
    return {**previous.snapshot(session), 'source_prerequisites': exposure_state(session)}


def restore(state, candidate, replay_folder=None, replay=False):
    if not isinstance(state, dict) or 'source_prerequisites' not in state:
        raise ValueError('checkpoint lacks declared source prerequisite state')
    core = {key: copy.deepcopy(value) for key, value in state.items()
        if key != 'source_prerequisites'}
    validated = previous.restore(core, candidate, replay_folder, replay)
    session = initial_session(replay_folder, replay)
    session.__dict__.update(validated.__dict__)
    policy.restore_state(session, state['source_prerequisites'])
    normalized = {**state, 'diffs': session.diffs}
    if canonical_json_bytes(snapshot(session)) != canonical_json_bytes(normalized):
        raise ValueError('checkpoint exact prerequisite reconstruction differs')
    return session


def implementation_identities():
    paths = [*AREA.glob('*.py'), *(AREA / 'tests').glob('*.py'),
        *(AREA / name for name in ('PLAN.md', 'PLAN_REVIEW.md', 'SPEC.md', 'SYSTEM.txt', 'TASK.txt')),
        AREA / 'review/verify_run.py', AREA / 'review/measure_run.py',
        ROOT / 'development/workload_requalification/ecological_observation_entry/review/PREREQUISITE_DESIGN-002.md',
        ROOT / 'development/workload_requalification/ecological_observation_entry/run-002/RESPONSE_SEAL.json',
        ROOT / 'development/workload_requalification/ecological_observation_entry/run-002/calls/C03-reply.json']
    return {**previous.source_identities(),
        **{path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths}}


source_identities = implementation_identities
attach_observations = previous.attach_observations
process_reply = previous.process_reply
present_receipts = previous.present_receipts
candidate_bytes = previous.candidate_bytes


class Task:
    def __init__(self, version='001', replay_folder=None):
        if not re.fullmatch('[0-9]{3}', version):
            raise ValueError('version must be exactly three decimal digits')
        self.version, self.AREA = version, AREA
        self.PACKAGE, self.RUN = AREA / f'preparation-{version}', AREA / f'run-{version}'
        self.MANIFEST = AREA / f'EXECUTION_MANIFEST-{version}.json'
        self.replay_folder = Path(replay_folder) if replay_folder is not None else None

    def initial_session(self):
        return initial_session(self.replay_folder, self.replay_folder is not None)

    def initial_preceding_feedback(self):
        return []

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(previous, name)


def __getattr__(name):
    return globals()[name] if name in globals() else getattr(previous, name)
