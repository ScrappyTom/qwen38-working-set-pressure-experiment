"""Fresh original URL-port contribution on the current exact-work host."""
import copy
import importlib.util
import re
from functools import lru_cache
from pathlib import Path

import bootstrap
import checkers
import url_reports
import repair_task as host
import navigation
import operational_reply
from search_navigation import SearchNavigationMixin, REFERENCE_ADDITION
from working_set_exp.candidate import Candidate
from working_set_exp.coherent_diagnostic_session import CoherentDiagnosticSession
from working_set_exp.feedback_session import operating_reference as common_reference
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.thinking_grammar import with_thinking

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent
ORIGINAL = ROOT / 'development/working_account/url_ports'
STARTING_ID = '2921cbc8a115c86871a11f8eaea929c3d48a8e4d2bb2ca03bf48971c36cf15cd'
TASK_SHA = '18f90ff54e3703df94aacfeda94e273631fd569eeaf12c951f4a58021f222346'
STARTING_CONTAINER_SHA = '6bdb96b0e4e7409f228dc5f4711f7a12b69e0a1b545a9b0938024db97408e731'
FILE_LIMIT = 1_048_576
TARGET, TEST, DOC = 'Lib/urllib/parse.py', 'Lib/test/test_urlparse.py', 'Doc/library/urllib.parse.rst'
ACTOR, SEED = dict(host.ACTOR), 961219
MAX_REQUESTS, MAX_OPERATIONS = 20, 60
OWNER_DIRECTION = 'Continue the authorized repair/qualify/run programme with the original URL-port entry on the revised host.'
DESCRIPTIONS = {
    'tests': 'Run the original saved and edited test suites, required API/input/case coverage, and seven aggregate fault-detection checks on the current candidate.',
    'examples': 'Execute newly added documentation examples and check preservation on the current candidate. This does not validate every surrounding prose claim.',
    'public': 'Run all original tests, examples and preservation acceptance on the current candidate; a current pass is required for submission. Documentation accuracy also requires direct review.',
}


def read(path):
    return load_json_strict(Path(path).read_bytes())


def task_text():
    raw = (ORIGINAL / 'TASK.txt').read_bytes()
    assert sha256_bytes(raw) == TASK_SHA, 'Original URL task changed'
    return raw.decode('utf-8')


def starting_candidate():
    raw = (ORIGINAL / 'preparation-complete-003/starting-candidate.json').read_bytes()
    assert sha256_bytes(raw) == STARTING_CONTAINER_SHA, 'Original starting container changed'
    saved = load_json_strict(raw)
    files = checkers.starting_files()
    rows = saved['files']
    assert len(rows) == len(files) == 6
    assert {r['path']: r['content_utf8'].encode() for r in rows} == files
    assert all(sha256_bytes(files[r['path']]) == r['sha256'] for r in rows)
    candidate = Candidate.create(files, max_file_bytes=FILE_LIMIT)
    assert candidate.candidate_id == saved['candidate_id'] == STARTING_ID
    return candidate


class Session(SearchNavigationMixin, navigation.NavigationMixin, CoherentDiagnosticSession):
    assessment_api = url_reports

    def reply_schema(self):
        return operational_reply.reply_schema(DESCRIPTIONS)

    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['episode_annotation'] = (
            'Task-author context: this contribution begins with the supplied original files and no prior work history. '
            'The task is the present tests/documentation assignment, not a new incident after each operation. '
            'recent_activity and retrievable operation history record this contribution; no earlier conversation is supplied.')
        return value


def initial_session(folder=None, replay=False):
    session = Session(starting_candidate(), {s: checkers.checker(s) for s in DESCRIPTIONS}, task_text(),
        edit_checks={TEST: 'tests', DOC: 'public'}, call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
        observations=ObservationStore((Path(folder) if folder is not None else AREA / 'unexecuted') / 'observations', replay=replay),
        check_contracts=checkers.contracts())
    assert session.requests_used == session.calls_used == session.starting_archive_length == 0
    assert not session.pairs and not session.ranges and not session.saved and session.working_account() is None
    assert not session.submitted and session.check_state() is None
    return session


def attach_observations(session, folder, log):
    # Fresh entry: no inherited observation copies or fabricated acquisitions.
    target = Path(folder).resolve()
    custody = Path(log.path).parent.resolve()
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
    text = common_reference(DESCRIPTIONS)
    previous = ('Ordinary tests must pass before mutation failures count as detection. '
        'Each declared fault target must be detected by the new tests; normal failure blocks that assessment. '
        'Mutation-run missing paths are not additional requirements.')
    replacement = ('The saved and edited ordinary test suites must pass before injected-fault failures count as detection. '
        'The original seven faults are assessed in aggregate: each fault must execute at least one added test and not succeed. '
        'That unsuccessful injected run is successful fault detection, not a failure of the fault-detection criterion. '
        'Required API/input/case coverage belongs to normal execution; coverage missing only during an injected fault is not an additional requirement.')
    assert text.count(previous) == 1, 'Shared check interpretation changed'
    text = text.replace(previous, replacement)
    marker = '\nrecent_edit_rejection is historical host feedback'
    inherited = host.host.operating_reference()
    assert inherited.count(marker) == 1, 'Shared recovery reference changed'
    text += marker + inherited.split(marker, 1)[1]
    return operational_reply.operating_reference(text) + '\n\n' + navigation.REFERENCE_ADDITION + '\n\n' + REFERENCE_ADDITION


@lru_cache(maxsize=1)
def response_constraints():
    path = ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    assert sha256_file(path) == 'ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
    spec = importlib.util.spec_from_file_location('url_operational_converter', path)
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    return {'grammar': with_thinking(operational_reply.reply_grammar(DESCRIPTIONS, converter.SchemaConverter))}


def expected_native(request):
    assert (request['grammar'] == response_constraints()['grammar'] and 'response_format' not in request
            and request['seed'] == SEED)
    envelope = copy.deepcopy(request)
    envelope['grammar'] = host.response_constraints()['grammar']
    # The message template renders neither grammar nor seed. Verify the actual
    # URL seed above, then reuse the pinned host's message-only envelope proof.
    # The saved wire and native form qualification retain the actual URL fields.
    envelope['seed'] = host.SEED
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
    if len(files) != len(rows) or set(files) != set(checkers.starting_files()):
        raise ValueError('checkpoint file inventory differs')
    candidate = Candidate.create(files, max_file_bytes=FILE_LIMIT)
    if (candidate.candidate_id != value['candidate_id']
            or host.candidate_bytes(candidate) != canonical_json_bytes(value)):
        raise ValueError('checkpoint candidate bytes differ')
    return candidate


def _restore_diffs(value, pairs):
    """Bind canonical numeric addresses to accepted edit receipts, without rewriting custody."""
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
        *(AREA / name for name in ('PLAN.md', 'SPEC.md', 'SYSTEM.txt')),
        *(AREA.glob('*TESTS*.log')),
        ROOT / 'development/workload_requalification/action_lifecycle/operational_reply.py',
        ROOT / 'development/workload_requalification/action_lifecycle/native_forms.py',
        ROOT / 'development/workload_requalification/search_continuity/search_navigation.py',
        ROOT / 'development/workload_requalification/navigation_continuity/navigation.py',
        ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/native_order_probe_gbnf.py',
        ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/NATIVE_GBNF_ORDER_PROBE.json',
        ROOT / 'development/workload_requalification/navigation_continuity/receipts/run-001/RESPONSE_SEAL.json',
        ROOT / 'development/workload_requalification/navigation_continuity/receipts/run-001/calls/C05-assistant-content.txt',
        ORIGINAL / 'TASK.txt', ORIGINAL / 'SOURCE.json',
        ORIGINAL / 'preparation-complete-003/starting-candidate.json']
    return {**host.source_identities(), **checkers.source_identities(),
        **{path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths}}


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
