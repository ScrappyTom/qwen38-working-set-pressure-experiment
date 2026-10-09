"""E18 source data and task clarification over the existing ordinary source host."""
import importlib.util
from pathlib import Path
import re

import bootstrap
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent
CORE_PATH = ROOT / 'development/workload_requalification/ecological_source_entry/ecological_task.py'
spec = importlib.util.spec_from_file_location('evolving_source_core', CORE_PATH)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
host = core.host
BANK = ROOT / 'experiments/018_large_world_event_frame_v2/fresh_bank'
CASE = 'E18-SOURCE-LANTERN'
MODEL_VISIBLE, EXECUTION_ONLY, EVALUATOR_ONLY = (BANK / part / CASE for part in
    ('model_visible', 'execution_only', 'evaluator_only'))
STARTING_ID = '3dfa888955adab1021a75c47f1e1400887a8a16b4fb920c190f60fdbae9fe882'
FIXTURE_SHA = '691fee72e2d33f0c6fcf5c8511213a55a970b35812c6ce5b526d4863d4d9e11c'
ORIGINAL_TASK_SHA = '73f6782b6e36f4901ec5e1d692439e82734123de1d3e5686d29d4c579bd4fb6c'
PUBLIC_SHA = HIDDEN_SHA = 'ab8f5397bf92f6536c67e70343807d4ab7b8be75bc103587f7eccbfbd8ec93f7'
FILE_LIMIT = 24000
TARGET, POLICY, SECONDARY = 'api/primary.py', 'policy/current.py', 'api/secondary.py'
REQUIRED_INSPECTION_PATHS = tuple(f'ledgers/required_{i:02d}.py' for i in range(4))
ACTOR, SEED = dict(host.ACTOR), 173205
MAX_REQUESTS, MAX_OPERATIONS = 24, 72
OWNER_DIRECTION = 'Keep working through the authorized workload programme; qualify E18 source with its declared clarification, then one finite uncoached attempt.'
DESCRIPTIONS = {'public': 'Execute the original E18 source behavioral acceptance in ordinary Python on the current candidate. A current pass is required for submission; source acquisition and task order are separate obligations.'}


def read(path):
    return load_json_strict(Path(path).read_bytes())


def exact(path, digest):
    raw = Path(path).read_bytes()
    if sha256_bytes(raw) != digest:
        raise ValueError('Pinned E18 material changed: ' + str(path))
    return raw


def fixture():
    value = load_json_strict(exact(EXECUTION_ONLY / 'FIXTURE.json', FIXTURE_SHA))
    if (value['fixture_id'] != CASE or value['candidate_id'] != STARTING_ID
            or value['observations'] or len(value['candidate_files']) != 130
            or tuple(value['required_reads']) != REQUIRED_INSPECTION_PATHS):
        raise ValueError('E18 initial fixture contract differs')
    return value


def starting_files():
    files = {row['path']: exact(MODEL_VISIBLE / 'candidate' / row['path'], row['sha256'])
             for row in fixture()['candidate_files']}
    if len(files) != 130 or sum(map(len, files.values())) != 1117043:
        raise ValueError('E18 source inventory differs')
    for row in fixture()['candidate_files']:
        if len(files[row['path']]) != row['size_bytes']:
            raise ValueError('E18 source size differs')
    return files


def task_text():
    original = exact(MODEL_VISIBLE / 'TASK.txt', ORIGINAL_TASK_SHA).decode()
    return original + '\n\n' + (AREA / 'CLARIFICATION.txt').read_text(encoding='utf-8').strip()


TASK_SHA = sha256_bytes(task_text().encode())
for name in ('AREA', 'BANK', 'CASE', 'MODEL_VISIBLE', 'EXECUTION_ONLY', 'EVALUATOR_ONLY',
             'STARTING_ID', 'FIXTURE_SHA', 'TASK_SHA', 'PUBLIC_SHA', 'HIDDEN_SHA', 'FILE_LIMIT',
             'TARGET', 'REQUIRED_INSPECTION_PATHS', 'ACTOR', 'SEED', 'MAX_REQUESTS', 'MAX_OPERATIONS',
             'OWNER_DIRECTION', 'DESCRIPTIONS', 'exact', 'fixture', 'starting_files', 'task_text'):
    setattr(core, name, globals()[name])

initial_session = core.initial_session
snapshot, restore = core.snapshot, core.restore


def source_identities():
    paths = [CORE_PATH, *AREA.glob('*.py'), *(AREA / 'tests').glob('*.py'), *(AREA / 'review').glob('*.py'),
        *(AREA / name for name in ('PLAN.md', 'SPEC.md', 'SYSTEM.txt', 'TASK.txt', 'CLARIFICATION.txt')),
        *AREA.glob('*TESTS*.log'),
        ROOT / 'tests/test_binding_diagnostics.py', ROOT / 'tests/test_feedback_repair.py',
        EXECUTION_ONLY / 'FIXTURE.json', MODEL_VISIBLE / 'TASK.txt', EXECUTION_ONLY / 'public.py',
        EVALUATOR_ONLY / 'hidden.py',
        *(MODEL_VISIBLE / 'candidate' / row['path'] for row in fixture()['candidate_files'])]
    for part in ('ecological_source_entry', 'search_continuity', 'navigation_continuity', 'small_repairs', 'action_lifecycle'):
        paths.extend((ROOT / 'development/workload_requalification' / part).glob('*.py'))
    paths.extend(ROOT / name for name in (
        'development/workload_requalification/ecological_source_entry/review/verify_run.py',
        'development/workload_requalification/ecological_source_entry/review/measure_run.py',
        'development/workload_requalification/url_port_entry/review/verify_run.py',
        'development/workload_requalification/url_port_continuation/review/measure_run.py',
        'development/decision_interface/reference_repair/verify_reference.py',
        'development/bounded_working_set/parser-documentation/grammar-review/native_order_probe_gbnf.py',
        'development/bounded_working_set/parser-documentation/grammar-review/NATIVE_GBNF_ORDER_PROBE.json'))
    return {**host.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}


implementation_identities = source_identities


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
        return []

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(core, name)


def __getattr__(name):
    return getattr(core, name)
