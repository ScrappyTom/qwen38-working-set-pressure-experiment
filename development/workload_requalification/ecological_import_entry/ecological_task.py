"""Fresh E20 source-import entry with continuous actual-delivery coverage."""
import copy
import importlib.util
import re
from pathlib import Path

import bootstrap
import coverage_policy as policy
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('ecological_import_source_core',
    ROOT / 'development/workload_requalification/ecological_source_entry/ecological_task.py')
previous = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(previous)
host = previous.host
BANK = ROOT / 'experiments/020_owner_controlled_ecological_pilot_v2/fresh_bank'
CASE = 'E20-SOURCE-IMPORT-BOUNDARIES'
MODEL_VISIBLE = BANK / 'model_visible' / CASE
EXECUTION_ONLY = BANK / 'execution_only' / CASE
EVALUATOR_ONLY = BANK / 'evaluator_only' / CASE
STARTING_ID = '2355c3eaa32dcf8db2659a75feb3a93309255fbff60e14b7f154dc34c47675c0'
FIXTURE_SHA = 'eeaa1d0e7a97a5e1491ba2c9406782f3529a477a7dfac65e266cbc2b5314cb44'
TASK_SHA = '32b39bfdaf4e0ad7270f5ca926a33104266f7cd189d881b14968b776492f3d27'
PUBLIC_SHA = 'e9a407cd0d0ddbafc7267dcf34fabb689afde8fc0bc49f8077a85e4d5fe59d59'
HIDDEN_SHA = '1ca34b6fc7b4c89bd42310a577fa176eab40f1ad30268984acd5b57f1b8ffe9d'
FILE_LIMIT = 24000
TARGET = 'src/addressable_information_layer/importers.py'
SAVED_RUNS = 'src/addressable_information_layer/saved_runs.py'
REQUIRED_INSPECTION_PATHS = policy.REQUIRED_PATHS
ACTOR, SEED = dict(host.ACTOR), 173205
MAX_REQUESTS, MAX_OPERATIONS = 24, 72
OWNER_DIRECTION = ('Continue the authorized original E20 source-import workload with '
    'a prospectively declared complete continuous delivered-source coverage barrier.')
DESCRIPTIONS = {'public': 'Execute the unchanged original E20 import-boundary public acceptance check on this candidate; a current pass is required for submission.'}
coverage_policy, coverage_state = policy.coverage_policy, policy.coverage_state
prerequisite_state = coverage_state


def read(path):
    return load_json_strict(Path(path).read_bytes())


def exact(path, digest):
    raw = Path(path).read_bytes()
    if sha256_bytes(raw) != digest:
        raise ValueError('Original E20 material changed: ' + Path(path).name)
    return raw


def fixture():
    value = load_json_strict(exact(EXECUTION_ONLY / 'FIXTURE.json', FIXTURE_SHA))
    if (value['fixture_id'] != CASE or value['candidate_id'] != STARTING_ID
            or value['observations'] != [] or len(value['candidate_files']) != 25
            or tuple(value['required_inspection_paths']) != REQUIRED_INSPECTION_PATHS):
        raise ValueError('Original E20 entry contract differs')
    return value


def starting_files():
    files = {}
    for row in fixture()['candidate_files']:
        path = row['path']
        if path in files:
            raise ValueError('Original E20 source inventory has duplicate paths')
        raw = exact(MODEL_VISIBLE / 'candidate' / path, row['sha256'])
        if len(raw) != row['size_bytes']:
            raise ValueError('Original E20 source size differs: ' + path)
        files[path] = raw
    if sum(map(len, files.values())) != 128546:
        raise ValueError('Original E20 total source size differs')
    return files


def starting_candidate():
    candidate = Candidate.create(starting_files(), max_file_bytes=FILE_LIMIT)
    if candidate.candidate_id != STARTING_ID:
        raise ValueError('Original E20 candidate identity differs')
    return candidate


def task_text():
    return exact(MODEL_VISIBLE / 'TASK.txt', TASK_SHA).decode('utf-8')


def public_checker():
    return exact(EXECUTION_ONLY / 'public.py', PUBLIC_SHA)


def hidden_checker():
    """Evaluator-only original bytes; never registered as an actor check."""
    return exact(EVALUATOR_ONLY / 'hidden.py', HIDDEN_SHA)


class Session(previous.Session):
    def __init__(self, *args, **kwargs):
        policy.initialize(self)
        super().__init__(*args, **kwargs)

    def reply_schema(self):
        return reply_schema()

    def clone(self):
        other = super().clone()
        other._source_coverage = copy.deepcopy(self._source_coverage)
        other._first_source_mutation = copy.deepcopy(self._first_source_mutation)
        return other

    def prerequisite_state(self):
        return coverage_state(self)

    def coverage_state(self):
        return coverage_state(self)

    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['task_prerequisites'] = policy.view(self)
        return value

    def mark_delivered(self, view):
        if view.get('task_prerequisites') != policy.view(self):
            raise ValueError('delivered continuous coverage view differs')
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
    session = Session(starting_candidate(), {'public': public_checker()}, task_text(),
        edit_checks={}, call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
        observations=ObservationStore((Path(folder) if folder is not None else AREA / 'unexecuted')
            / 'observations', replay=replay),
        check_contracts={'public': {'checker_sha256': PUBLIC_SHA}})
    assert session.requests_used == session.calls_used == session.starting_archive_length == 0
    assert not session.pairs and not session.ranges and not session.saved and session.working_account() is None
    assert not session.submitted and session.check_state() is None
    assert session.prerequisite_state() == coverage_state()
    return session


def reply_schema():
    return previous.operational_reply.reply_schema(DESCRIPTIONS)


def decode_reply(content):
    return previous.operational_reply.decode_reply(content, DESCRIPTIONS)


def operating_reference():
    return previous.operating_reference() + '\n\n' + policy.REFERENCE_ADDITION


# The public-only reply grammar is unchanged: descriptions affect the schema
# documentation, not allowed action/check names or source-text transport.
response_constraints = previous.response_constraints
expected_native = previous.expected_native
attach_observations = previous.attach_observations
process_reply = previous.process_reply
present_receipts = previous.present_receipts
candidate_bytes = previous.candidate_bytes


def snapshot(session):
    return {**previous.snapshot(session), 'source_prerequisites': coverage_state(session)}


def candidate_from_snapshot(value):
    if (not isinstance(value, dict) or set(value) != {'candidate_id', 'max_file_bytes', 'files'}
            or value['max_file_bytes'] != FILE_LIMIT or not isinstance(value['files'], list)):
        raise ValueError('checkpoint candidate shape or admission differs')
    rows = value['files']
    if any(not isinstance(row, dict) or not isinstance(row.get('content_utf8'), str)
            or not isinstance(row.get('path'), str) for row in rows):
        raise ValueError('checkpoint candidate file shape differs')
    files = {row['path']: row['content_utf8'].encode('utf-8') for row in rows}
    if len(files) != len(rows) or set(files) != set(starting_files()):
        raise ValueError('checkpoint file inventory differs')
    candidate = Candidate.create(files, max_file_bytes=FILE_LIMIT)
    if (candidate.candidate_id != value['candidate_id']
            or candidate_bytes(candidate) != canonical_json_bytes(value)):
        raise ValueError('checkpoint candidate bytes differ')
    return candidate


def restore(state, candidate, replay_folder=None, replay=False):
    if not isinstance(candidate, Candidate):
        candidate = candidate_from_snapshot(candidate)
    session = initial_session(replay_folder, replay)
    if (not isinstance(state, dict) or set(state) != set(snapshot(session))
            or state['candidate_id'] != candidate.candidate_id
            or state['starting_archive_length'] != 0
            or (state['request_limit'], state['call_limit']) != (MAX_REQUESTS, MAX_OPERATIONS)
            or type(state['requests_used']) is not int or not 0 <= state['requests_used'] <= MAX_REQUESTS
            or not isinstance(state['pairs'], list) or len(state['pairs']) > MAX_OPERATIONS):
        raise ValueError('checkpoint shape, candidate, ancestry or opportunity differs')
    versions = [candidate_from_snapshot(value) for value in state['source_versions']]
    version_map = {value.candidate_id: value for value in versions}
    if (len(version_map) != len(versions) or STARTING_ID not in version_map
            or candidate_bytes(version_map[STARTING_ID]) != candidate_bytes(starting_candidate())
            or candidate.candidate_id not in version_map
            or candidate_bytes(version_map[candidate.candidate_id]) != candidate_bytes(candidate)):
        raise ValueError('checkpoint source versions differ')
    for key, value in state.items():
        if key not in ('candidate_id', 'source_versions', 'source_prerequisites'):
            setattr(session, key, copy.deepcopy(value))
    session.candidate, session.versions = candidate, version_map
    session.diffs = previous._restore_diffs(state['diffs'], session.pairs)
    session.restored_control_fields = tuple(session.restored_control_fields)
    session.parked_source_regions = tuple(tuple(row) for row in session.parked_source_regions)
    policy.restore_state(session, state['source_prerequisites'])
    if canonical_json_bytes(snapshot(session)) != canonical_json_bytes({**state, 'diffs': session.diffs}):
        raise ValueError('checkpoint exact continuous coverage reconstruction differs')
    return session


def implementation_identities():
    paths = [*AREA.glob('*.py'), *(AREA / 'tests').glob('*.py'),
        *(AREA / name for name in ('SPEC.md', 'SYSTEM.txt', 'TASK.txt')),
        AREA / 'review/verify_run.py', AREA / 'review/measure_run.py',
        ROOT / 'development/workload_requalification/ecological_next/PLAN.md',
        ROOT / 'development/workload_requalification/ecological_next/REVIEW_DRAFT.md',
        ROOT / 'development/workload_requalification/ecological_source_entry/ecological_task.py',
        ROOT / 'development/workload_requalification/ecological_source_entry/bootstrap.py',
        ROOT / 'development/decision_interface/reference_repair/verify_reference.py',
        ROOT / 'development/workload_requalification/url_port_entry/review/verify_run.py',
        ROOT / 'development/workload_requalification/url_port_continuation/review/measure_run.py',
        EXECUTION_ONLY / 'FIXTURE.json', MODEL_VISIBLE / 'TASK.txt', EXECUTION_ONLY / 'public.py',
        EVALUATOR_ONLY / 'hidden.py',
        *(MODEL_VISIBLE / 'candidate' / row['path'] for row in fixture()['candidate_files']),
        ROOT / 'development/workload_requalification/small_repairs/case_reports.py',
        ROOT / 'development/workload_requalification/action_lifecycle/operational_reply.py',
        ROOT / 'development/workload_requalification/action_lifecycle/native_forms.py',
        ROOT / 'development/workload_requalification/search_continuity/search_navigation.py',
        ROOT / 'development/workload_requalification/navigation_continuity/navigation.py',
        ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/native_order_probe_gbnf.py',
        ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/NATIVE_GBNF_ORDER_PROBE.json',
        ROOT / 'development/workload_requalification/navigation_continuity/receipts/run-001/RESPONSE_SEAL.json',
        ROOT / 'development/workload_requalification/navigation_continuity/receipts/run-001/calls/C05-assistant-content.txt']
    return {**host.source_identities(),
        **{path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths}}


source_identities = implementation_identities


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
