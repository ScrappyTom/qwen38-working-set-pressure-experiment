"""Fresh original E19 observation entry; retrieval does not execute a verifier."""
import copy
import importlib.util
import re
from functools import lru_cache
from pathlib import Path

import bootstrap
import capture_bridge
import repair_task as host
import case_reports
import navigation
from search_navigation import REFERENCE_ADDITION
from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.thinking_grammar import with_thinking

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent
BANK = ROOT / 'experiments/019_owner_controlled_ecological_pilot/fresh_bank'
CASE = 'E19-OBS-SUMMARY-GRAPH'
MODEL_VISIBLE = BANK / 'model_visible' / CASE
EXECUTION_ONLY = BANK / 'execution_only' / CASE
EVALUATOR_ONLY = BANK / 'evaluator_only' / CASE
STARTING_ID = '476f83a90c40b0897e1ab5d6bc00bbb52cf3a4fe60cc11c1dd47ab3da85d0172'
FIXTURE_SHA = 'b82e4c5a6853f127770a72ce737e359d17a8ae841297470155c58e1698889bac'
TASK_SHA = '8c79408f30136165061cd4f97bc36103a3a0672709156775edb8db5d66126267'
PUBLIC_SHA = '2ef1e2251d125e85664b09653c9957a0f9eb0f4f23105a22e99feaa7c9f50530'
HIDDEN_SHA = '54bcbe9f2619c8892914ba446e80e1bfb7e2a12d24c862712e336473a50330a6'
FILE_LIMIT = 24000
TARGET = 'src/addressable_information_layer/summary_graph.py'
SUMMARIES = 'src/addressable_information_layer/summaries.py'
REQUIRED_INSPECTION_PATHS = (TARGET, SUMMARIES,
    'src/addressable_information_layer/records.py', 'src/addressable_information_layer/policy.py')
ACTOR, SEED = dict(host.ACTOR), 173205
MAX_REQUESTS, MAX_OPERATIONS = 24, 72
OWNER_DIRECTION = 'Continue the authorized workload requalification programme with the original E19 summary-graph observation entry on the current host.'
DESCRIPTIONS = {'public': 'Execute the unchanged original E19 summary-graph public acceptance check on this candidate; a current pass is required for submission.'}
TRANSPORT_NORMALIZATION = {
    'changed_fields': ['action'], 'original_action': 'verifier', 'transport_action': 'capture',
    'effect': 'Transport classification only; no historical or current execution is created.'}


def read(path):
    return load_json_strict(Path(path).read_bytes())


def exact(path, digest):
    raw = Path(path).read_bytes()
    if sha256_bytes(raw) != digest:
        raise ValueError('Original E19 material changed: ' + Path(path).name)
    return raw


def fixture():
    value = load_json_strict(exact(EXECUTION_ONLY / 'FIXTURE.json', FIXTURE_SHA))
    rows = value['observations']
    if (value['fixture_id'] != CASE or value['candidate_id'] != STARTING_ID
            or len(value['candidate_files']) != 25 or len(rows) != 2
            or [row['handle'] for row in rows] != ['OBS-0001', 'OBS-0002']
            or [row['sequence'] for row in rows] != [1, 2]
            or any(row['action'] != 'verifier' for row in rows)
            or rows[0]['candidate_id'] == STARTING_ID or rows[1]['candidate_id'] != STARTING_ID):
        raise ValueError('Original E19 observation entry contract differs')
    return value


def starting_files():
    files = {}
    for row in fixture()['candidate_files']:
        path = row['path']
        if path in files:
            raise ValueError('Original E19 source inventory has duplicate paths')
        raw = exact(MODEL_VISIBLE / 'candidate' / path, row['sha256'])
        if len(raw) != row['size_bytes']:
            raise ValueError('Original E19 source size differs: ' + path)
        files[path] = raw
    if sum(map(len, files.values())) != 128545:
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


def imports():
    """Return original verifier rows, labeled transport copies and exact bodies.

    The shared bridge accepts capture-classified manifests. Its transport copies
    change only that field; original fixture provenance is bound separately.
    Neither row classification is a new actor action or executed observation.
    """
    original = fixture()['observations']
    transport, bodies = {}, {}
    for row in original:
        handle = row['handle']
        raw = exact(EXECUTION_ONLY / 'observations' / (handle + '.json'), row['sha256'])
        value = load_json_strict(raw)
        if (len(raw) != row['size_bytes'] or canonical_json_bytes(value) != raw
                or value['candidate_id'] != row['candidate_id']):
            raise ValueError('Original E19 observation body or candidate binding differs')
        transport[handle] = {**copy.deepcopy(row), 'action': 'capture'}
        bodies[handle] = raw
    return copy.deepcopy(original), transport, bodies


class Session(capture_bridge.Session):
    # The inherited bridge MRO already contains search, navigation and the
    # coherent diagnostic host. No previous compiler Task/world is imported.
    assessment_api = case_reports

    def __init__(self, *args, original_observations, retain_imported_captures=True, **kwargs):
        expected = fixture()['observations']
        expected_transport = {row['handle']: {**row, 'action': 'capture'} for row in expected}
        if (original_observations != expected or kwargs.get('imported_observations') != expected_transport
                or retain_imported_captures is not True):
            raise ValueError('Original E19 verifier provenance or capture transport policy differs')
        self._original_observations = tuple(canonical_json_bytes(row) for row in expected)
        super().__init__(*args, retain_imported_captures=True, **kwargs)

    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['episode_annotation'] = (
            'Task-author context: this repair begins with the supplied original files and two stored verifier records. '
            'The imported records retain their recorded candidate bindings; retrieving them is not a new verifier run. '
            'Repeated task text is the same assignment, not a new observation after an operation. '
            'recent_activity and retrievable operation history record this repair; no earlier conversation is supplied.')
        value['imported_observations']['scope'] = (
            'Original fixture verifier records, bound to their recorded candidates; retrieval is not execution during this repair.')
        return value


def original_observation_state(session=None):
    rows = (fixture()['observations'] if session is None else
        [load_json_strict(raw) for raw in session._original_observations])
    return {'schema': 'ecological-original-verifier-observations-v1',
        'fixture_sha256': FIXTURE_SHA,
        'rows': rows,
        'transport_normalization': copy.deepcopy(TRANSPORT_NORMALIZATION)}


original_observation_snapshot = original_observation_state


def initial_session(folder=None, replay=False):
    original, transport, bodies = imports()
    session = Session(starting_candidate(), {'public': public_checker()}, task_text(),
        edit_checks={}, call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
        observations=ObservationStore((Path(folder) if folder is not None else AREA / 'unexecuted') / 'observations', replay=replay),
        check_contracts={'public': {'checker_sha256': PUBLIC_SHA}},
        original_observations=original, imported_observations=transport,
        imported_bodies=bodies, retain_imported_captures=True)
    assert session.requests_used == session.calls_used == session.starting_archive_length == 0
    assert not session.pairs and not session.ranges and not session.saved and not session.delivered_sources
    assert session.working_account() is None and not session.submitted and session.check_state() is None
    return session


def attach_observations(session, folder, log):
    """Preserve imported provenance separately from future executed checks."""
    target, custody = Path(folder).resolve(), Path(log.path).parent.resolve()
    assert target.is_relative_to(custody)
    prefix = target.relative_to(custody).as_posix()
    prefix = '' if prefix == '.' else prefix + '/'
    original, transport, bodies = imports()
    if (original_observation_snapshot(session)['rows'] != original
            or capture_bridge.capture_snapshot(session)['inventory'] != list(transport.values())):
        raise ValueError('Session imported provenance differs before custody attachment')
    store = ArtifactStore(custody)
    artifacts = [store.put(prefix + 'imported-captures/original-fixture.json',
        exact(EXECUTION_ONLY / 'FIXTURE.json', FIXTURE_SHA)),
        store.put(prefix + 'imported-captures/original-verifier-rows.json', canonical_json_bytes(original)),
        store.put(prefix + 'imported-captures/transport-inventory.json', canonical_json_bytes(transport)),
        store.put(prefix + 'imported-captures/transport-normalization.json', canonical_json_bytes(TRANSPORT_NORMALIZATION))]
    artifacts.extend(store.put(prefix + 'imported-captures/' + handle + '.json', raw)
        for handle, raw in bodies.items())
    log.append('imported_capture_custody', {'records': len(bodies), 'actor_acquisitions': 0,
        'fixture_sha256': FIXTURE_SHA, 'original_action': 'verifier', 'transport_action': 'capture',
        'observed_candidates': {row['handle']: row['candidate_id'] for row in original},
        'retrieval_only': True, 'source_edit_authority': False, 'applicable_check_authority': False}, artifacts)
    def preserved(record, artifacts):
        log.append('check_observation_preserved', record,
            [{**row, 'path': prefix + 'observations/' + row['path']} for row in artifacts])
    session.observations = ObservationStore(target / 'observations', on_preserved=preserved)


def reply_schema():
    return capture_bridge.reply_schema(DESCRIPTIONS)


def decode_reply(content):
    return capture_bridge.decode_reply(content, DESCRIPTIONS)


def operating_reference():
    text = host.Task('artifact_map').operating_reference()
    text += '\n\n' + navigation.REFERENCE_ADDITION + '\n\n' + REFERENCE_ADDITION
    return capture_bridge.operating_reference(text, retain_imported_captures=True)


@lru_cache(maxsize=1)
def response_constraints():
    path = ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    if sha256_file(path) != 'ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3':
        raise ValueError('Pinned grammar converter changed')
    spec = importlib.util.spec_from_file_location('ecological_observation_converter', path)
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    return {'grammar': with_thinking(capture_bridge.reply_grammar(DESCRIPTIONS, converter.SchemaConverter))}


def expected_native(request):
    assert (request['grammar'] == response_constraints()['grammar'] and 'response_format' not in request
            and request['seed'] == SEED)
    envelope = copy.deepcopy(request)
    envelope['grammar'], envelope['seed'] = host.response_constraints()['grammar'], host.SEED
    return host.expected_native(envelope)


def snapshot(session):
    return {**host.snapshot(session), 'source_versions': [load_json_strict(host.candidate_bytes(value))
        for _, value in sorted(session.versions.items())],
        'imported_capture_state': capture_bridge.capture_snapshot(session),
        'original_observation_state': original_observation_snapshot(session)}


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
    capture_bridge.restore_capture_state(session, state['imported_capture_state'])
    if original_observation_snapshot(session) != state['original_observation_state']:
        raise ValueError('checkpoint original verifier provenance or transport normalization differs')
    versions = [candidate_from_snapshot(value) for value in state['source_versions']]
    version_map = {value.candidate_id: value for value in versions}
    if (len(version_map) != len(versions) or STARTING_ID not in version_map
            or host.candidate_bytes(version_map[STARTING_ID]) != host.candidate_bytes(starting_candidate())
            or candidate.candidate_id not in version_map
            or host.candidate_bytes(version_map[candidate.candidate_id]) != host.candidate_bytes(candidate)):
        raise ValueError('checkpoint source versions differ')
    for key, value in state.items():
        if key not in ('candidate_id', 'source_versions', 'imported_capture_state', 'original_observation_state'):
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
        *(AREA / name for name in ('PLAN.md', 'PLAN_REVIEW.md', 'SPEC.md', 'SYSTEM.txt', 'TASK.txt')),
        *AREA.glob('*TESTS*.log'),
        AREA / 'review/verify_run.py', AREA / 'review/measure_run.py',
        ROOT / 'development/decision_interface/reference_repair/verify_reference.py',
        ROOT / 'development/workload_requalification/url_port_entry/review/verify_run.py',
        ROOT / 'development/workload_requalification/url_port_continuation/review/measure_run.py',
        ROOT / 'development/workload_requalification/compiler_entry/capture_bridge.py',
        ROOT / 'development/workload_requalification/compiler_entry/native_forms.py',
        ROOT / 'development/workload_requalification/compiler_entry/review/verify_run.py',
        ROOT / 'development/workload_requalification/review/NEXT_OBSERVATION_ENTRY_NOTES.md',
        ROOT / 'development/workload_requalification/ecological/ENTRY_MAP.md',
        ROOT / 'experiments/019_owner_controlled_ecological_pilot/execution_package/cell-03/initial-coding-request.json',
        EXECUTION_ONLY / 'FIXTURE.json',
        MODEL_VISIBLE / 'TASK.txt', EXECUTION_ONLY / 'public.py', EVALUATOR_ONLY / 'hidden.py',
        *(EXECUTION_ONLY / 'observations' / (row['handle'] + '.json') for row in fixture()['observations']),
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
