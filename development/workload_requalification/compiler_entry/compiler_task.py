"""Original compiler incident on the current host; capture records stay historical."""
import copy
import importlib.util
from functools import lru_cache
from pathlib import Path
import bootstrap
import repair_task as host
import capture_bridge
import navigation
from search_navigation import REFERENCE_ADDITION
from working_set_exp.candidate import Candidate
from working_set_exp.observations import ObservationStore
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.thinking_grammar import with_thinking

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent
ORIGINAL = ROOT/'development/compiler_incident/preparation-001'
ORIGINAL_SEAL_SHA = '35a53de9d8ca5a1811d842378d309f291035d11172791ead0d59b3ee99fe9480'
STARTING_ID = '28441db41e7ca5385feb03c96574fed32acfc4d67e7e608c93572fe06ed8033d'
ACTOR, SEED = dict(host.ACTOR), host.SEED
MAX_REQUESTS, MAX_OPERATIONS = 40, 100
DESCRIPTIONS = {'public': 'Run the original 26-case compiler and captured-comparison acceptance check on this candidate; required for submission.'}
OWNER_DIRECTION = 'Continue the authorized repair/qualify/run programme across the previously tested workloads; qualify capture access then run the original compiler entry uncoached.'
Session = capture_bridge.Session

def read(path):
    return load_json_strict(Path(path).read_bytes())

def original_material():
    # Read sealed artifacts only. Never import the oracle-generating fixture builder.
    assert sha256_file(ORIGINAL/'PREPARATION_SEAL.json') == ORIGINAL_SEAL_SHA
    seal = read(ORIGINAL/'PREPARATION_SEAL.json')
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    index = {r['path']: r for r in seal['files']}
    def exact(name):
        raw = (ORIGINAL/name).read_bytes()
        assert len(raw) == index[name]['size_bytes'] and sha256_bytes(raw) == index[name]['sha256'], name
        return raw
    snapshot = load_json_strict(exact('candidate.json'))
    files = {r['path']: r['content_utf8'].encode() for r in snapshot['files']}
    assert len(files) == len(snapshot['files'])
    assert all(sha256_bytes(files[r['path']]) == r['sha256'] for r in snapshot['files'])
    candidate = Candidate.create(files)
    assert candidate.candidate_id == snapshot['candidate_id'] == STARTING_ID
    rows = load_json_strict(exact('observations.json'))
    captures = load_json_strict(exact('captures.json'))
    bodies = {f'OBS-{i:04d}': canonical_json_bytes(r) for i,r in enumerate(captures,1)}
    assert len(rows) == len(bodies) == 3
    inventory = {}
    for r in rows:
        raw = bodies[r['handle']]
        assert r['candidate_id'] == STARTING_ID and r['size_bytes'] == len(raw) and r['sha256'] == sha256_bytes(raw)
        inventory[r['handle']] = copy.deepcopy(r)
    return candidate, exact('PUBLIC_CHECK.py'), exact('TASK.txt').decode(), inventory, bodies

def initial_session(folder=None, replay=False):
    candidate, checker, task, inventory, bodies = original_material()
    return Session(candidate, {'public': checker}, task, edit_checks={},
        call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
        observations=ObservationStore((folder or AREA/'unexecuted')/'observations', replay=replay),
        check_contracts={'public': {'checker_sha256': sha256_bytes(checker)}},
        imported_observations=inventory, imported_bodies=bodies)

@lru_cache(maxsize=1)
def response_constraints():
    path = ROOT/'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    assert sha256_file(path) == 'ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
    spec = importlib.util.spec_from_file_location('compiler_capture_converter', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return {'grammar': with_thinking(capture_bridge.reply_grammar(DESCRIPTIONS, module.SchemaConverter))}

def expected_native(request):
    assert request['grammar'] == response_constraints()['grammar'] and 'response_format' not in request
    envelope = copy.deepcopy(request)
    envelope['grammar'] = host.response_constraints()['grammar']
    return host.expected_native(envelope)

def snapshot(session):
    return {**host.snapshot(session), 'imported_capture_state': capture_bridge.capture_snapshot(session)}

def attach_observations(session, folder, log):
    # This is a fresh original entry. Do not inherit the earlier parser task's
    # attach hook or fabricate acquisition actions for historical captures.
    from working_set_exp.custody import ArtifactStore
    session.observations = ObservationStore(Path(folder)/'observations')
    _, _, _, inventory, bodies = original_material()
    custody_root = Path(log.path).parent.resolve()
    target = Path(folder).resolve()
    assert target.is_relative_to(custody_root)
    prefix = target.relative_to(custody_root).as_posix()
    prefix = '' if prefix == '.' else prefix+'/'
    store = ArtifactStore(custody_root)
    artifacts = [store.put(prefix+'imported-captures/inventory.json', canonical_json_bytes(inventory))]
    artifacts += [store.put(prefix+f'imported-captures/{handle}.json', raw) for handle, raw in bodies.items()]
    log.append('imported_capture_custody', {'historical_candidate_id': STARTING_ID,
        'records':len(bodies), 'actor_acquisitions':0, 'source_edit_authority':False}, artifacts)

def implementation_identities():
    paths = [*AREA.glob('*.py'), *(AREA/'tests').glob('*.py'),
             *(AREA/n for n in ('SPEC.md','SYSTEM.txt','PLAN.md','TASK.txt')),
             ROOT/'development/workload_requalification/search_continuity/search_navigation.py',
             ROOT/'development/workload_requalification/action_lifecycle/operational_reply.py',
             ROOT/'development/bounded_working_set/parser-documentation/grammar-review/native_order_probe_gbnf.py',
             ROOT/'development/bounded_working_set/parser-documentation/grammar-review/NATIVE_GBNF_ORDER_PROBE.json',
             ORIGINAL/'PREPARATION_SEAL.json',
             *(ORIGINAL/n for n in ('candidate.json','PUBLIC_CHECK.py','TASK.txt','captures.json','observations.json'))]
    return {**host.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}

class Task:
    def __init__(self, version='001', replay_folder=None):
        assert len(version)==3 and version.isdecimal()
        self.AREA=AREA; self.PACKAGE=AREA/f'preparation-{version}'; self.RUN=AREA/f'run-{version}'
        self.MANIFEST=AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.replay_folder=Path(replay_folder) if replay_folder else None
    def initial_session(self): return initial_session(self.replay_folder, self.replay_folder is not None)
    def reply_schema(self): return capture_bridge.reply_schema(DESCRIPTIONS)
    def operating_reference(self):
        text = host.Task('artifact_map').operating_reference() + '\n\n' + navigation.REFERENCE_ADDITION + '\n\n' + REFERENCE_ADDITION
        return capture_bridge.operating_reference(text)
    def response_constraints(self): return response_constraints()
    def decode_reply(self, content): return capture_bridge.decode_reply(content, DESCRIPTIONS)
    def source_identities(self): return implementation_identities()
    def implementation_identities(self): return implementation_identities()
    def initial_preceding_feedback(self): return []
    def snapshot(self, session): return snapshot(session)
    def attach_observations(self, session, folder, log): return attach_observations(session,folder,log)
    def __getattr__(self, name): return globals()[name] if name in globals() else getattr(host,name)

def __getattr__(name): return getattr(host,name)
