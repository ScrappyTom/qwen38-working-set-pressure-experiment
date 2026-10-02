"""Fresh original E19 source-reopening entry on the current exact-work host."""
import copy
import importlib.util
import re
from functools import lru_cache
from pathlib import Path

import bootstrap
import repair_task as host
import case_reports
import navigation
import operational_reply
from search_navigation import SearchNavigationMixin, REFERENCE_ADDITION
from working_set_exp.candidate import Candidate
from working_set_exp.coherent_diagnostic_session import CoherentDiagnosticSession
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.thinking_grammar import with_thinking

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent
BANK = ROOT / 'experiments/019_owner_controlled_ecological_pilot/fresh_bank'
CASE = 'E19-SOURCE-REOPEN'
MODEL_VISIBLE = BANK / 'model_visible' / CASE
EXECUTION_ONLY = BANK / 'execution_only' / CASE
EVALUATOR_ONLY = BANK / 'evaluator_only' / CASE
STARTING_ID = 'd2a57a0044458310fbe0b915eb88447b6f76b87dd511d68a0e31c29416342116'
FIXTURE_SHA = '9a8a72b263c91424fb3dd1e87ef560f21e810ec2c1922ad9e2f9523875a10564'
TASK_SHA = '99506c6fbd702cc3362421657e6f79edc52bf4d36f8fe4992e98078d0f46c2d5'
PUBLIC_SHA = '2bcb87dc5d40656dfd1e4a13439e222ba4071dcbb993b877f911f6bcedd32ea5'
HIDDEN_SHA = '962b0e952d545fe10c7033bd0d690cc14bf4da2735ac871f2f0507d2fec4118f'
FILE_LIMIT = 24000
TARGET = 'src/addressable_information_layer/artifact_units.py'
REOPEN = 'src/addressable_information_layer/reopen.py'
REQUIRED_INSPECTION_PATHS = (TARGET, REOPEN,
    'src/addressable_information_layer/records.py', 'src/addressable_information_layer/hashing.py')
ACTOR, SEED = dict(host.ACTOR), 173205
MAX_REQUESTS, MAX_OPERATIONS = 24, 72
OWNER_DIRECTION = 'Continue the authorized workload requalification programme with the original E19 source-reopening entry on the current host.'
DESCRIPTIONS = {'public': 'Execute the unchanged original E19 source-reopening public acceptance check on this candidate; a current pass is required for submission.'}


def read(path):
    return load_json_strict(Path(path).read_bytes())


def exact(path, digest):
    raw = Path(path).read_bytes()
    if sha256_bytes(raw) != digest:
        raise ValueError('Original E19 material changed: ' + Path(path).name)
    return raw


def fixture():
    value = load_json_strict(exact(EXECUTION_ONLY / 'FIXTURE.json', FIXTURE_SHA))
    if (value['fixture_id'] != CASE or value['candidate_id'] != STARTING_ID
            or value['observations'] != [] or len(value['candidate_files']) != 25):
        raise ValueError('Original E19 entry contract differs')
    return value


def starting_files():
    rows = fixture()['candidate_files']
    files = {}
    for row in rows:
        path = row['path']
        if path in files:
            raise ValueError('Original E19 source inventory has duplicate paths')
        raw = exact(MODEL_VISIBLE / 'candidate' / path, row['sha256'])
        if len(raw) != row['size_bytes']:
            raise ValueError('Original E19 source size differs: ' + path)
        files[path] = raw
    if sum(map(len, files.values())) != 128575:
        raise ValueError('Original E19 total source size differs')
    return files


def starting_candidate():
    candidate = Candidate.create(starting_files(), max_file_bytes=FILE_LIMIT)
    if candidate.candidate_id != STARTING_ID:
        raise ValueError('Original E19 candidate identity differs')
    return candidate


def task_text():
    return exact(MODEL_VISIBLE / 'TASK.txt', TASK_SHA).decode('utf-8')


def public_checker():
    return exact(EXECUTION_ONLY / 'public.py', PUBLIC_SHA)


def hidden_checker():
    """Evaluator-only original bytes; never registered as an actor check."""
    return exact(EVALUATOR_ONLY / 'hidden.py', HIDDEN_SHA)


class Session(SearchNavigationMixin, navigation.NavigationMixin, CoherentDiagnosticSession):
    assessment_api = case_reports

    def reply_schema(self):
        return operational_reply.reply_schema(DESCRIPTIONS)

    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['episode_annotation'] = (
            'Task-author context: this repair begins with the supplied original files and no prior work history. '
            'Repeated task text is the same assignment, not a new observation after an operation. '
            'recent_activity and retrievable operation history record this repair; no earlier conversation is supplied.')
        return value


def initial_session(folder=None, replay=False):
    session = Session(starting_candidate(), {'public': public_checker()}, task_text(),
        edit_checks={}, call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
        observations=ObservationStore((Path(folder) if folder is not None else AREA / 'unexecuted') / 'observations', replay=replay),
        check_contracts={'public': {'checker_sha256': PUBLIC_SHA}})
    assert session.requests_used == session.calls_used == session.starting_archive_length == 0
    assert not session.pairs and not session.ranges and not session.saved and session.working_account() is None
    assert not session.submitted and session.check_state() is None
    return session


def attach_observations(session, folder, log):
    target, custody = Path(folder).resolve(), Path(log.path).parent.resolve()
    assert target.is_relative_to(custody)
    prefix = target.relative_to(custody).as_posix()
    prefix = '' if prefix == '.' else prefix + '/'
    def preserved(record, artifacts):
        log.append('check_observation_preserved', record,
            [{**row, 'path': prefix + 'observations/' + row['path']} for row in artifacts])
    session.observations = ObservationStore(target / 'observations', on_preserved=preserved)


def reply_schema():
    return operational_reply.reply_schema(DESCRIPTIONS)


def decode_reply(content):
    return operational_reply.decode_reply(content, DESCRIPTIONS)


def operating_reference():
    # Reuse the qualified public-only/no-automatic-check policy. No fixture or
    # oracle state is constructed by this reference-only Task instance.
    text = host.Task('artifact_map').operating_reference()
    return operational_reply.operating_reference(text) + '\n\n' + navigation.REFERENCE_ADDITION + '\n\n' + REFERENCE_ADDITION


@lru_cache(maxsize=1)
def response_constraints():
    path = ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    if sha256_file(path) != 'ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3':
        raise ValueError('Pinned grammar converter changed')
    spec = importlib.util.spec_from_file_location('ecological_source_converter', path)
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    return {'grammar': with_thinking(operational_reply.reply_grammar(DESCRIPTIONS, converter.SchemaConverter))}


def expected_native(request):
    assert (request['grammar'] == response_constraints()['grammar'] and 'response_format' not in request
            and request['seed'] == SEED)
    envelope = copy.deepcopy(request)
    envelope['grammar'], envelope['seed'] = host.response_constraints()['grammar'], host.SEED
    return host.expected_native(envelope)


def snapshot(session):
    return {**host.snapshot(session), 'source_versions': [read_bytes(host.candidate_bytes(value))
        for _, value in sorted(session.versions.items())]}


def read_bytes(raw):
    return load_json_strict(raw)


def candidate_from_snapshot(value):
    if (not isinstance(value, dict) or set(value) != {'candidate_id', 'max_file_bytes', 'files'}
            or value['max_file_bytes'] != FILE_LIMIT):
        raise ValueError('checkpoint candidate shape or admission differs')
    rows = value['files']
    files = {row['path']: row['content_utf8'].encode() for row in rows}
    if len(files) != len(rows) or set(files) != set(starting_files()):
        raise ValueError('checkpoint file inventory differs')
    candidate = Candidate.create(files, max_file_bytes=FILE_LIMIT)
    if (candidate.candidate_id != value['candidate_id']
            or host.candidate_bytes(candidate) != canonical_json_bytes(value)):
        raise ValueError('checkpoint candidate bytes differ')
    return candidate


def _restore_diffs(value, pairs):
    """Decode canonical numeric addresses and bind accepted edit receipts."""
    if not isinstance(value, dict):
        raise ValueError('checkpoint diffs are not an address map')
    restored = {}
    for key, diff in value.items():
        if type(key) is int:
            number = key
        elif type(key) is str and key.isascii() and key.isdecimal() and str(int(key)) == key:
            number = int(key)
        else:
            raise ValueError('checkpoint diff address is not canonical')
        if number <= 0 or number in restored or type(diff) is not str:
            raise ValueError('checkpoint diff address or value differs')
        restored[number] = diff
    expected = {}
    for number, pair in enumerate(pairs, 1):
        if pair['response'].get('action') in ('patch', 'replace_region') and pair['result'].get('accepted'):
            diff = pair['result'].get('applied_diff')
            if type(diff) is not str:
                raise ValueError('checkpoint accepted edit lacks exact diff receipt')
            expected[number] = diff
    if restored != expected:
        raise ValueError('checkpoint diff map differs from accepted edit receipts')
    return restored


def restore(state, candidate, replay_folder=None, replay=False):
    if not isinstance(candidate, Candidate):
        candidate = candidate_from_snapshot(candidate)
    session = initial_session(replay_folder, replay)
    if (set(state) != set(snapshot(session)) or state['candidate_id'] != candidate.candidate_id
            or state['starting_archive_length'] != 0
            or (state['request_limit'], state['call_limit']) != (MAX_REQUESTS, MAX_OPERATIONS)
            or type(state['requests_used']) is not int or not 0 <= state['requests_used'] <= MAX_REQUESTS
            or len(state['pairs']) > MAX_OPERATIONS):
        raise ValueError('checkpoint shape, candidate, ancestry or opportunity differs')
    versions = [candidate_from_snapshot(value) for value in state['source_versions']]
    version_map = {value.candidate_id: value for value in versions}
    if (len(version_map) != len(versions) or STARTING_ID not in version_map
            or host.candidate_bytes(version_map[STARTING_ID]) != host.candidate_bytes(starting_candidate())
            or candidate.candidate_id not in version_map
            or host.candidate_bytes(version_map[candidate.candidate_id]) != host.candidate_bytes(candidate)):
        raise ValueError('checkpoint source versions differ')
    for key, value in state.items():
        if key not in ('candidate_id', 'source_versions'):
            setattr(session, key, copy.deepcopy(value))
    session.candidate, session.versions = candidate, version_map
    session.diffs = _restore_diffs(state['diffs'], session.pairs)
    session.restored_control_fields = tuple(session.restored_control_fields)
    session.parked_source_regions = tuple(tuple(row) for row in session.parked_source_regions)
    if canonical_json_bytes(snapshot(session)) != canonical_json_bytes({**state, 'diffs': session.diffs}):
        raise ValueError('checkpoint exact reconstruction differs')
    return session


def implementation_identities():
    paths = [*AREA.glob('*.py'), *(AREA / 'tests').glob('*.py'),
        *(AREA / name for name in ('PLAN.md', 'SPEC.md', 'SYSTEM.txt', 'TASK.txt')),
        *AREA.glob('*TESTS*.log'),
        AREA / 'review/verify_run.py', AREA / 'review/measure_run.py',
        ROOT / 'development/decision_interface/reference_repair/verify_reference.py',
        ROOT / 'development/workload_requalification/url_port_entry/review/verify_run.py',
        ROOT / 'development/workload_requalification/url_port_continuation/review/measure_run.py',
        EXECUTION_ONLY / 'FIXTURE.json',
        MODEL_VISIBLE / 'TASK.txt', EXECUTION_ONLY / 'public.py', EVALUATOR_ONLY / 'hidden.py',
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
    return {**host.source_identities(), **{path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths}}


source_identities = implementation_identities
candidate_bytes = host.candidate_bytes
process_reply = host.process_reply
present_receipts = navigation.present_receipts


class Task:
    def __init__(self, version='001', replay_folder=None):
        if not re.fullmatch(r'[0-9]{3}', version):
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
        return globals()[name] if name in globals() else getattr(host, name)


def __getattr__(name):
    return globals()[name] if name in globals() else getattr(host, name)
