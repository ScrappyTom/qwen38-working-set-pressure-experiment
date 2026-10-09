"""E20 OBS task: compose existing custody and delivered-source policies."""
import copy
import importlib.util
from pathlib import Path
import re

import bootstrap
import reports
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent

def load_private(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Isolated module instances: configure task data, never alter the donor files or
# an existing task instance. Their generic custody/restore implementations stay exact.
CORE_PATH = ROOT / 'development/workload_requalification/ecological_observation_entry/ecological_task.py'
POLICY_PATH = ROOT / 'development/workload_requalification/ecological_import_entry/coverage_policy.py'
core = load_private('verifier_observation_core', CORE_PATH)
policy = load_private('verifier_coverage_core', POLICY_PATH)
host = core.host
BANK = ROOT / 'experiments/020_owner_controlled_ecological_pilot_v2/fresh_bank'
CASE = 'E20-OBS-VERIFIER-SAFETY'
MODEL_VISIBLE, EXECUTION_ONLY, EVALUATOR_ONLY = (BANK / part / CASE for part in
    ('model_visible', 'execution_only', 'evaluator_only'))
STARTING_ID = 'a8ccf6bcf04177b0199148e6a91dad4ac9f1818c0898403b0fc91cceb43dcadd'
FIXTURE_SHA = 'f0b17ae01e7c58f763161e2b2b0b045de0f5fbd2529079c5879911fb02631343'
TASK_SHA = '618cfe2169ed68b1ca6aebc53dd880b98c2822bb215ff12ce412d53636544fa9'
ORIGINAL_PUBLIC_SHA = 'e484244a0eb144c0fbb1673e429dc8882a1976807374c0922785fee03eeb1951'
HIDDEN_SHA = '6b17208c9beddc918b2ac39af8e4d6764b63c473bbd8db20fbee702dbb95434f'
FILE_LIMIT = 24000
TARGET = 'src/addressable_information_layer/verifiers.py'
REQUIRED_INSPECTION_PATHS = tuple('src/addressable_information_layer/'+name for name in
    ('verifiers.py','records.py','hashing.py','readiness.py','policy.py','routing.py',
     'reducers.py','verifier_logs.py','storage.py','artifact_units.py'))
ACTOR, SEED = dict(host.ACTOR), 173205
MAX_REQUESTS, MAX_OPERATIONS = 32, 96
OWNER_DIRECTION = 'Continue the authorized workload programme with the original E20 verifier world and prospectively qualified full-contract public check.'
DESCRIPTIONS = {'public': ('Execute the original verifier assertions plus the declared native path, '
    'invalid-timeout and preservation contract checks in ordinary Python on this host. '
    'This expanded checker has its own identity; a current overall pass is required for submission.')}

def public_checker():
    original = core.exact(EXECUTION_ONLY / 'public.py', ORIGINAL_PUBLIC_SHA)
    return original + b'\n# Declared contract extension follows the unchanged original.\n' + (AREA/'contract_checks.py').read_bytes()

PUBLIC_SHA = sha256_bytes(public_checker())
for name in ('AREA','BANK','CASE','MODEL_VISIBLE','EXECUTION_ONLY','EVALUATOR_ONLY',
             'STARTING_ID','FIXTURE_SHA','TASK_SHA','PUBLIC_SHA','HIDDEN_SHA','FILE_LIMIT',
             'TARGET','REQUIRED_INSPECTION_PATHS','ACTOR','SEED','MAX_REQUESTS','MAX_OPERATIONS',
             'OWNER_DIRECTION','DESCRIPTIONS','public_checker'):
    setattr(core, name, globals()[name])
policy.REQUIRED_PATHS = REQUIRED_INSPECTION_PATHS
policy.POLICY_ID = 'e20-verifier-first-mutation-continuous-source-coverage-v1'
policy.REFERENCE_ADDITION = policy.REFERENCE_ADDITION.replace('eleven required paths', 'ten required paths')
_fixture = core.fixture
def fixture():
    value = _fixture()
    if tuple(value['required_inspection_paths']) != REQUIRED_INSPECTION_PATHS:
        raise ValueError('E20 complete inspection paths differ')
    return value
core.fixture = fixture

class Session(core.Session):
    assessment_api = reports

    def __init__(self, *args, **kwargs):
        policy.initialize(self)
        super().__init__(*args, **kwargs)

    def clone(self):
        other = super().clone()
        other._source_coverage = copy.deepcopy(self._source_coverage)
        other._first_source_mutation = copy.deepcopy(self._first_source_mutation)
        return other

    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['task_prerequisites'] = policy.view(self)
        return value

    def mark_delivered(self, view):
        if view.get('task_prerequisites') != policy.view(self):
            raise ValueError('delivered coverage view differs')
        super().mark_delivered(view)
        policy.credit_delivered(self, view)

    def _patch(self, action):
        rejected = policy.mutation_rejection(self)
        if rejected is not None:
            return rejected
        result = super()._patch(action)
        policy.record_first_mutation(self, result)
        return result

    def prerequisite_state(self):
        return policy.coverage_state(self)

    coverage_state = prerequisite_state

core.Session = Session
coverage_policy, coverage_state = policy.coverage_policy, policy.coverage_state
prerequisite_state = coverage_state
initial_session = core.initial_session

def snapshot(session):
    return {**core.snapshot(session), 'source_prerequisites': policy.coverage_state(session)}

def restore(state, candidate, replay_folder=None, replay=False):
    plain = copy.deepcopy(state)
    prerequisite = plain.pop('source_prerequisites')
    session = core.restore(plain, candidate, replay_folder, replay)
    policy.restore_state(session, prerequisite)
    if canonical_json_bytes(snapshot(session)) != canonical_json_bytes(state):
        raise ValueError('E20 exact combined checkpoint reconstruction differs')
    return session

def operating_reference():
    text = core.operating_reference().replace('The original public checker must pass;',
        'The declared expanded public checker must pass;')
    return (text + '\n\n' + policy.REFERENCE_ADDITION + '\n\n'
        'Current public check: ' + DESCRIPTIONS['public'] +
        ' Execution environment: ordinary Python on Windows, candidate root as cwd, '
        'candidate src import path. It includes Windows path spellings and invalid nonfinite '
        'numeric timeouts. Original acceptance scripts remain historical definitions; '
        'their earlier pass text does not establish an overall expanded-check pass.')

def source_identities():
    paths = [CORE_PATH, POLICY_PATH, *AREA.glob('*.py'), *(AREA/'tests').glob('*.py'),
        *(AREA/'review').glob('*.py'), AREA/'PLAN.md', AREA/'SPEC.md', AREA/'SYSTEM.txt', AREA/'TASK.txt',
        EXECUTION_ONLY/'FIXTURE.json', MODEL_VISIBLE/'TASK.txt', EXECUTION_ONLY/'public.py',
        EVALUATOR_ONLY/'hidden.py',
        *(MODEL_VISIBLE/'candidate'/row['path'] for row in fixture()['candidate_files']),
        *(EXECUTION_ONLY/'observations'/(row['handle']+'.json') for row in fixture()['observations'])]
    for part in ('ecological_observation_entry','compiler_entry','ecological_import_entry',
                 'search_continuity','navigation_continuity','small_repairs','action_lifecycle'):
        paths.extend((ROOT/'development/workload_requalification'/part).glob('*.py'))
    paths.extend(ROOT/path for path in (
        'development/workload_requalification/ecological_observation_entry/review/verify_run.py',
        'development/workload_requalification/ecological_import_entry/review/verify_run.py',
        'development/workload_requalification/compiler_entry/review/verify_run.py',
        'development/workload_requalification/url_port_entry/review/verify_run.py',
        'development/workload_requalification/url_port_continuation/review/measure_run.py',
        'development/decision_interface/reference_repair/verify_reference.py',
        'development/bounded_working_set/parser-documentation/grammar-review/native_order_probe_gbnf.py',
        'development/bounded_working_set/parser-documentation/grammar-review/NATIVE_GBNF_ORDER_PROBE.json'))
    return {**host.source_identities(), **{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}

class Task:
    def __init__(self, version='001', replay_folder=None):
        if not re.fullmatch('[0-9]{3}', version):
            raise ValueError('version must be three digits')
        self.version, self.AREA = version, AREA
        self.PACKAGE, self.RUN = AREA/f'preparation-{version}', AREA/f'run-{version}'
        self.MANIFEST = AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.replay_folder = replay_folder

    def initial_session(self):
        return initial_session(self.replay_folder, self.replay_folder is not None)

    def initial_preceding_feedback(self):
        return []

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(core, name)

def __getattr__(name):
    return getattr(core, name)
