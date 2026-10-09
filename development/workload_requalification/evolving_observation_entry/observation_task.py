"""Original E18 probes and sources over the existing immutable-capture host."""
import copy
import importlib.util
from pathlib import Path

import bootstrap
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent
CORE_PATH = ROOT / 'development/workload_requalification/ecological_observation_entry/ecological_task.py'
spec = importlib.util.spec_from_file_location('evolving_observation_core', CORE_PATH)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
host, capture_bridge = core.host, core.capture_bridge
BANK = ROOT / 'experiments/018_large_world_event_frame_v2/fresh_bank'
CASE = 'E18-OBS-HARBOR'
MODEL_VISIBLE, EXECUTION_ONLY, EVALUATOR_ONLY = (BANK / part / CASE for part in
    ('model_visible', 'execution_only', 'evaluator_only'))
STARTING_ID = 'e331513f6ce44015a22f975c289b0594c11e6a685299c3e4aeabcb331a399a49'
FIXTURE_SHA = 'be45fedf92e15b2bf8592396beae31b6c5b4e2171dcf5b9b9faaf9b3a236e267'
TASK_SHA = '76b8a52bf3ca36e3dd8bed7498e0c57009f198488747beffcfd1460cdb70bf3c'
PUBLIC_SHA = HIDDEN_SHA = '54a1b882e3622c1006cb1c4a2e8d5b3fec0d1ac4dcc494f0feec1448ac00b4db'
FILE_LIMIT = 24000
TARGET, SECONDARY = 'codec/label.py', 'codec/footer.py'
REQUIRED_INSPECTION_PATHS = tuple(f'ledgers/required_{i:02d}.py' for i in range(4))
ACTOR, SEED = dict(host.ACTOR), 173205
MAX_REQUESTS, MAX_OPERATIONS = 32, 96
OWNER_DIRECTION = 'Continue the authorized workload programme with the original E18 observation entry and its declared32-request opportunity.'
DESCRIPTIONS = {'public': 'Execute the original E18 marker behavior acceptance on this candidate. A current pass is required for submission; historical acquisition and task order are separate obligations.'}
TRANSPORT_NORMALIZATION = dict(changed_fields=['action'], original_action='probe', transport_action='capture',
    effect='Transport classification only; no historical or current execution is created.')


def exact(path, digest):
    raw = Path(path).read_bytes()
    if sha256_bytes(raw) != digest:
        raise ValueError('Pinned E18 observation material changed: ' + str(path))
    return raw


def fixture():
    value = load_json_strict(exact(EXECUTION_ONLY / 'FIXTURE.json', FIXTURE_SHA))
    rows = value['observations']
    if (value['fixture_id'] != CASE or value['candidate_id'] != STARTING_ID
            or len(value['candidate_files']) != 130
            or tuple(value['required_reads']) != REQUIRED_INSPECTION_PATHS
            or [row['handle'] for row in rows] != ['OBS-0001', 'OBS-0002']
            or [row['sequence'] for row in rows] != [1, 2]
            or any(row['action'] != 'probe' or row['target'] != 'marker' for row in rows)
            or rows[0]['candidate_id'] == STARTING_ID or rows[1]['candidate_id'] != STARTING_ID):
        raise ValueError('Original E18 observation entry differs')
    return value


def starting_files():
    files = {row['path']: exact(MODEL_VISIBLE / 'candidate' / row['path'], row['sha256'])
        for row in fixture()['candidate_files']}
    if len(files) != 130 or sum(map(len, files.values())) != 1103867:
        raise ValueError('E18 observation source inventory differs')
    if any(len(files[row['path']]) != row['size_bytes'] for row in fixture()['candidate_files']):
        raise ValueError('E18 source extent differs')
    return files


class Session(capture_bridge.Session):
    assessment_api = core.case_reports

    def __init__(self, *args, original_observations, retain_imported_captures=True, **kwargs):
        expected = fixture()['observations']
        transport = {row['handle']: {**row, 'action': 'capture'} for row in expected}
        if (original_observations != expected or kwargs.get('imported_observations') != transport
                or retain_imported_captures is not True):
            raise ValueError('E18 probe provenance or transport differs')
        self._original_observations = tuple(canonical_json_bytes(row) for row in expected)
        super().__init__(*args, retain_imported_captures=True, **kwargs)

    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['episode_annotation'] = (
            'This task begins with the original source files and two stored marker probe records. '
            'The records keep their original candidate bindings. Retrieving one does not run a probe or check. '
            'Repeated task text is the same assignment, not a new observation after an edit. '
            'Current activity records this task; no earlier conversation is supplied.')
        value['imported_observations']['scope'] = (
            'Original marker probe records, bound to their recorded candidates; retrieval is not execution during this task.')
        return value


def original_observation_state(session=None):
    rows = fixture()['observations'] if session is None else [load_json_strict(raw) for raw in session._original_observations]
    return dict(schema='evolving-original-probe-observations-v1', fixture_sha256=FIXTURE_SHA,
        rows=rows, transport_normalization=copy.deepcopy(TRANSPORT_NORMALIZATION))


original_observation_snapshot = original_observation_state


def attach_observations(session, folder, log):
    target, custody = Path(folder).resolve(), Path(log.path).parent.resolve()
    assert target.is_relative_to(custody)
    prefix = target.relative_to(custody).as_posix()
    prefix = '' if prefix == '.' else prefix + '/'
    original, transport, bodies = core.imports()
    assert original_observation_state(session)['rows'] == original
    assert capture_bridge.capture_snapshot(session)['inventory'] == list(transport.values())
    store = core.ArtifactStore(custody)
    artifacts = [store.put(prefix + 'imported-captures/' + name, raw) for name, raw in (
        ('original-fixture.json', exact(EXECUTION_ONLY / 'FIXTURE.json', FIXTURE_SHA)),
        ('original-probe-rows.json', canonical_json_bytes(original)),
        ('transport-inventory.json', canonical_json_bytes(transport)),
        ('transport-normalization.json', canonical_json_bytes(TRANSPORT_NORMALIZATION)))]
    artifacts.extend(store.put(prefix + 'imported-captures/' + handle + '.json', raw) for handle, raw in bodies.items())
    log.append('imported_capture_custody', dict(records=len(bodies), actor_acquisitions=0,
        fixture_sha256=FIXTURE_SHA, original_action='probe', transport_action='capture',
        observed_candidates={r['handle']: r['candidate_id'] for r in original},
        retrieval_only=True, source_edit_authority=False, applicable_check_authority=False), artifacts)

    def preserved(record, artifacts):
        log.append('check_observation_preserved', record,
            [{**row, 'path': prefix + 'observations/' + row['path']} for row in artifacts])
    session.observations = core.ObservationStore(target / 'observations', on_preserved=preserved)


def source_identities():
    paths = [CORE_PATH, *AREA.glob('*.py'), *(AREA / 'tests').glob('*.py'), *(AREA / 'review').glob('*.py'),
        *(AREA / name for name in ('PLAN.md', 'SPEC.md', 'SYSTEM.txt', 'TASK.txt')),
        *AREA.glob('*TESTS*.log'), EXECUTION_ONLY / 'FIXTURE.json', MODEL_VISIBLE / 'TASK.txt',
        EXECUTION_ONLY / 'public.py', EVALUATOR_ONLY / 'hidden.py',
        *(MODEL_VISIBLE / 'candidate' / row['path'] for row in fixture()['candidate_files']),
        *(EXECUTION_ONLY / 'observations' / (row['handle'] + '.json') for row in fixture()['observations']),
        ROOT / 'development/workload_requalification/review/NEXT_E18_OBSERVATION_NOTES.md',
        ROOT / 'development/workload_requalification/evolving_source_entry/temporal_audit.py',
        ROOT / 'development/workload_requalification/url_port_entry/review/verify_run.py',
        ROOT / 'development/decision_interface/reference_repair/verify_reference.py',
        ROOT / 'development/workload_requalification/compiler_entry/review/verify_run.py']
    for part in ('ecological_observation_entry', 'compiler_entry', 'search_continuity', 'navigation_continuity', 'small_repairs', 'action_lifecycle'):
        paths.extend((ROOT / 'development/workload_requalification' / part).glob('*.py'))
    return {**host.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}


implementation_identities = source_identities
for name in ('AREA', 'BANK', 'CASE', 'MODEL_VISIBLE', 'EXECUTION_ONLY', 'EVALUATOR_ONLY',
        'STARTING_ID', 'FIXTURE_SHA', 'TASK_SHA', 'PUBLIC_SHA', 'HIDDEN_SHA', 'FILE_LIMIT',
        'TARGET', 'SECONDARY', 'REQUIRED_INSPECTION_PATHS', 'ACTOR', 'SEED', 'MAX_REQUESTS', 'MAX_OPERATIONS',
        'OWNER_DIRECTION', 'DESCRIPTIONS', 'TRANSPORT_NORMALIZATION', 'exact', 'fixture', 'starting_files',
        'Session', 'original_observation_state', 'original_observation_snapshot', 'attach_observations',
        'implementation_identities', 'source_identities'):
    setattr(core, name, globals()[name])

Task = core.Task


def __getattr__(name):
    return getattr(core, name)
