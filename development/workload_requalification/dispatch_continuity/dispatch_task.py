"""Thin fresh-task adapter; phase change uses exact saved work, never a donor patch."""
import base64
import copy
import importlib.util
from functools import lru_cache
from pathlib import Path

import bootstrap
import dispatch_reports
import navigation
import operational_reply
import repair_task as host
from search_navigation import SearchNavigationMixin, REFERENCE_ADDITION
from working_set_exp.candidate import Candidate
from working_set_exp.coherent_diagnostic_session import CoherentDiagnosticSession
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.thinking_grammar import with_thinking

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent
ACTOR, SEED, FILE_LIMIT = dict(host.ACTOR), 314159, 1_048_576
OWNER_DIRECTION = 'Proceed with fresh information-dependent work, preserving exact work and uncoached task execution.'
DESCRIPTIONS = {'public': 'Execute the current job acceptance: original dispatch behavior, independent contract, authored regression sensitivity, and dynamic-job executable docs when applicable. Required for submission; prose needs direct review.'}
REQUIRED_INSPECTION_PATHS = ('Lib/functools.py', 'tests/test_union_registration.py',
    'tests/test_virtual_registration.py', 'Doc/howto/union-dispatch.rst')  # native synthetic forms only
PARENT_FILES = ('Lib/functools.py', 'Lib/test/test_functools.py', 'Doc/library/functools.rst', 'LICENSE')
SOURCE_HASHES = {'Lib/functools.py': '30509cf5490ae644a7b200756e0de9eb66435bde019eb940a463aa05528867de',
    'Lib/test/test_functools.py': '02b9cb594671af7b98c06cf67b848668ae03c080b3d6ba49881a8190bbd5de13',
    'Doc/library/functools.rst': '9304b59b50b3722cf0c26ade6aa1af325205fcfd465b0b2f1d33cd8600fd2878',
    'LICENSE': 'd0285b61e1a8e420c7deb95836738a5d4a0d26463138b17601f5971212684c4b'}
SKELETON = 'import functools\nimport unittest\n\n\n# Add regression TestCase classes here.\n'
DOC_SKELETON = 'Union dispatch and virtual registration\n======================================\n\n'


def read(path): return load_json_strict(Path(path).read_bytes())
def save(folder, name, value):
    path = Path(folder) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else canonical_json_bytes(value))
    return path


def starting_files():
    files = {}
    for name, digest in SOURCE_HASHES.items():
        raw = (AREA / 'upstream/parent' / name).read_bytes()
        assert sha256_bytes(raw) == digest, name
        files[name] = raw
    files.update({'tests/test_union_registration.py': SKELETON.encode(),
                  'tests/test_virtual_registration.py': SKELETON.encode(),
                  'Doc/howto/union-dispatch.rst': DOC_SKELETON.encode(),
                  'README.md': ('Historical functools maintenance on Python 3.11. The checker loads '
                    'Lib/functools.py as functools for the new tests. Original TestSingleDispatch '
                    'runs unchanged with installed test.support; other upstream tests are outside '
                    'this scope. New regression files use unittest. The library, upstream tests, '
                    'documentation and license came from the pinned original parent.\n').encode()})
    return files


def checker(phase, first_candidate=None):
    files = first_candidate.file_map if phase == 'dynamic' else starting_files()
    editable = {'Lib/functools.py', 'tests/test_union_registration.py'} if phase == 'union' else {
        'Lib/functools.py', 'tests/test_virtual_registration.py', 'Doc/howto/union-dispatch.rst'}
    config = dict(phase=phase, unchanged={p: sha256_bytes(v) for p,v in files.items() if p not in editable},
        original_library=base64.b64encode((AREA/'upstream/parent/Lib/functools.py').read_bytes()).decode(),
        original_tests=base64.b64encode((AREA/'upstream/parent/Lib/test/test_functools.py').read_bytes()).decode(),
        merged_library=base64.b64encode((AREA/'upstream/merged/functools.py').read_bytes()).decode())
    return b'CONFIG = ' + repr(config).encode() + b'\n' + (AREA/'checker_program.py').read_bytes()


class Session(SearchNavigationMixin, navigation.NavigationMixin, CoherentDiagnosticSession):
    assessment_api = dispatch_reports
    def reply_schema(self): return reply_schema()


def reply_schema(): return operational_reply.reply_schema(DESCRIPTIONS)
def decode_reply(content): return operational_reply.decode_reply(content, DESCRIPTIONS)
def operating_reference():
    text = host.Task('artifact_map').operating_reference()
    text = operational_reply.operating_reference(text)
    inherited = 'The original public checker must pass; there are no injected fault tests in this task.'
    assert text.count(inherited) == 1
    text = text.replace(inherited, 'This job\'s registered public checker must pass. Its report distinguishes '
        'current-candidate behavior from regression sensitivity on the specified older implementation. '
        'Older-implementation failure satisfies the sensitivity criterion; it is not a current-candidate failure. '
        'There are no injected faults in this task.')
    return text + '\n\n' + navigation.REFERENCE_ADDITION + '\n\n' + REFERENCE_ADDITION


@lru_cache(maxsize=1)
def response_constraints():
    path = ROOT/'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    assert sha256_file(path) == 'ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
    spec = importlib.util.spec_from_file_location('dispatch_schema_converter', path)
    converter = importlib.util.module_from_spec(spec); spec.loader.exec_module(converter)
    return {'grammar': with_thinking(operational_reply.reply_grammar(DESCRIPTIONS, converter.SchemaConverter))}


def expected_native(request):
    assert request['grammar'] == response_constraints()['grammar'] and request['seed'] == SEED
    envelope = copy.deepcopy(request)
    envelope['grammar'], envelope['seed'] = host.response_constraints()['grammar'], host.SEED
    return host.expected_native(envelope)


def snapshot(session):
    return {**host.snapshot(session), 'source_versions': [read_bytes(host.candidate_bytes(value))
        for _,value in sorted(session.versions.items())]}


def read_bytes(raw): return load_json_strict(raw)
def candidate_from_snapshot(value):
    files = {row['path']: row['content_utf8'].encode() for row in value['files']}
    candidate = Candidate.create(files, max_file_bytes=FILE_LIMIT)
    assert host.candidate_bytes(candidate) == canonical_json_bytes(value)
    assert set(files) == set(starting_files())
    return candidate


def restore_fields(session, state, candidate):
    versions = [candidate_from_snapshot(value) for value in state['source_versions']]
    assert len({v.candidate_id for v in versions}) == len(versions), 'Duplicate source versions'
    assert Candidate.create(starting_files(), max_file_bytes=FILE_LIMIT).candidate_id in {v.candidate_id for v in versions}
    for key,value in state.items():
        if key not in ('candidate_id', 'source_versions'):
            setattr(session, key, copy.deepcopy(value))
    session.candidate = candidate
    session.versions = {value.candidate_id:value for value in versions}
    assert candidate.candidate_id in session.versions
    diffs = {int(k):v for k,v in session.diffs.items()}
    expected = {i:p['result']['applied_diff'] for i,p in enumerate(session.pairs,1)
        if p['response']['action'] in ('patch','replace_region') and p['result'].get('accepted')}
    assert diffs == expected, 'Diffs differ from recorded accepted edits'
    session.diffs = diffs
    session.restored_control_fields = tuple(session.restored_control_fields)
    session.parked_source_regions = tuple(tuple(row) for row in session.parked_source_regions)
    assert canonical_json_bytes(snapshot(session)) == canonical_json_bytes(state)
    return session


def inherited_material(folder):
    folder = Path(folder)
    seal = read(folder/'RESPONSE_SEAL.json')
    assert seal['disposition'] == 'checked_submission' and seal['actor'] == ACTOR
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    for row in seal['files']:
        raw = (folder/row['path']).read_bytes()
        assert len(raw) == row['size_bytes'] and sha256_bytes(raw) == row['sha256'], row['path']
    return read(folder/'final-state.json'), candidate_from_snapshot(read(folder/'final-candidate.json'))


def attach_observations(session, folder, log):
    target, custody = Path(folder).resolve(), Path(log.path).parent.resolve()
    assert target.is_relative_to(custody)
    prefix = target.relative_to(custody).as_posix()
    prefix = '' if prefix == '.' else prefix+'/'
    def preserved(record, artifacts):
        log.append('check_observation_preserved', record,
            [{**row,'path':prefix+'observations/'+row['path']} for row in artifacts])
    session.observations = ObservationStore(target/'observations', on_preserved=preserved)


class Task:
    def __init__(self, phase='union', version='001', inherited=None):
        assert phase in ('union', 'dynamic') and len(version) == 3 and version.isdecimal()
        self.phase, self.version = phase, version
        self.AREA = AREA
        self.PACKAGE, self.RUN = AREA/phase/f'preparation-{version}', AREA/phase/f'run-{version}'
        self.MANIFEST = AREA/phase/f'EXECUTION_MANIFEST-{version}.json'
        self.inherited = Path(inherited).resolve() if inherited else None
        self.inherited_state, self.inherited_candidate = inherited_material(self.inherited) if self.inherited else (None,None)
        assert (phase == 'dynamic') == (self.inherited is not None)
        self.INHERITED_REQUESTS = self.inherited_state['requests_used'] if self.inherited else 0
        self.INHERITED_OPERATIONS = len(self.inherited_state['pairs']) if self.inherited else 0
        self.MAX_REQUESTS = self.INHERITED_REQUESTS + 24
        self.MAX_OPERATIONS = self.INHERITED_OPERATIONS + 72

    def initial_session(self, folder=None, replay=False):
        candidate = self.inherited_candidate or Candidate.create(starting_files(), max_file_bytes=FILE_LIMIT)
        check = checker(self.phase, self.inherited_candidate)
        task = (AREA/('TASK-UNION.txt' if self.phase == 'union' else 'TASK-DYNAMIC.txt')).read_text(encoding='utf-8')
        session = Session(candidate, {'public':check}, task, edit_checks={},
            call_limit=self.MAX_OPERATIONS, request_limit=self.MAX_REQUESTS,
            observations=ObservationStore((Path(folder) if folder else self.inherited if self.inherited else
                self.PACKAGE/'unexecuted')/'observations', replay=replay or (self.inherited is not None and folder is None)),
            check_contracts={'public':{'checker_sha256':sha256_bytes(check)}})
        if self.inherited:
            session = restore_fields(session, self.inherited_state, candidate)
            session.request_limit, session.call_limit = self.MAX_REQUESTS, self.MAX_OPERATIONS
            session.submitted = False
            session.ranges, session.saved, session.delivered_sources = [], {}, []
            session.last = None
            session.recovery = False
            session.parked_source_regions = ()
        return session

    def implementation_identities(self):
        helpers = ('development/workload_requalification/ecological_import_entry/native_forms.py',
                   'development/workload_requalification/action_lifecycle/native_forms.py',
                   'development/workload_requalification/search_continuity/search_navigation.py',
                   'development/workload_requalification/navigation_continuity/navigation.py',
                   'development/workload_requalification/action_lifecycle/operational_reply.py')
        paths = [*AREA.glob('*.py'),*AREA.glob('*.txt'),AREA/'PLAN.md',AREA/'SPEC.md',
                 *sorted((AREA/'tests').glob('*.py')),*sorted(p for p in (AREA/'upstream').rglob('*') if p.is_file()),
                 *sorted(p for p in (AREA/'cpu-route-002').rglob('*') if p.is_file()),
                 *(ROOT/p for p in helpers)]
        if self.inherited:
            paths += [self.inherited/'RESPONSE_SEAL.json']
            paths += [self.inherited/row['path'] for row in read(self.inherited/'RESPONSE_SEAL.json')['files']]
        return {**host.source_identities(), **{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}

    source_identities = implementation_identities
    def restore(self,state,candidate,replay_folder=None,replay=False):
        if not isinstance(candidate,Candidate): candidate = candidate_from_snapshot(candidate)
        session = self.initial_session(replay_folder,replay)
        assert set(state) == set(snapshot(session)), 'Checkpoint shape differs'
        assert state['candidate_id'] == candidate.candidate_id
        assert (state['request_limit'],state['call_limit']) == (self.MAX_REQUESTS,self.MAX_OPERATIONS)
        assert self.INHERITED_REQUESTS <= state['requests_used'] <= self.MAX_REQUESTS
        assert self.INHERITED_OPERATIONS <= len(state['pairs']) <= self.MAX_OPERATIONS
        if self.inherited:
            assert state['pairs'][:self.INHERITED_OPERATIONS] == self.inherited_state['pairs']
        return restore_fields(session,state,candidate)

    def attach_observations(self,session,folder,log):
        if self.inherited:
            from working_set_exp.custody import ArtifactStore
            target,custody = Path(folder).resolve(),Path(log.path).parent.resolve()
            assert target.is_relative_to(custody)
            store = ArtifactStore(custody)
            artifacts = []
            for path in sorted((self.inherited/'observations').rglob('*')):
                if path.is_file():
                    dest = target/'observations'/path.relative_to(self.inherited/'observations')
                    assert dest.resolve().is_relative_to(target)
                    artifacts.append(store.put(dest.relative_to(custody).as_posix(),path.read_bytes()))
            log.append('inherited_observation_custody',dict(source_seal_sha256=sha256_file(self.inherited/'RESPONSE_SEAL.json'),
                original_meaning_preserved=True,actor_acquisitions=0),artifacts)
        attach_observations(session,folder,log)

    def __getattr__(self, name): return globals()[name] if name in globals() else getattr(host,name)


process_reply = host.process_reply
candidate_bytes = host.candidate_bytes
present_receipts = navigation.present_receipts
def __getattr__(name): return getattr(host,name)
