"""Original constructed E17 boundary, using the existing prior-work archive API."""
import copy
import re
from pathlib import Path

import bootstrap
import ecological_task as template
from working_set_exp.candidate import Candidate
from working_set_exp.event_frame_v2 import event_from_pair_v2
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent
STARTING_ID = '376ce4da59fb6ee1c4e0967110767e0fb7b51a87e959b1c8c3c60ac1e4fc726c'
PAIR_SHA = '4bb61d8308e188463461aad05658324772ff2b8d7be34ac5276ceae9cdb2e644'
FILE_LIMIT = 24000
MAX_REQUESTS, MAX_OPERATIONS = 8, 24
ACTOR, SEED = template.ACTOR, 173205
OWNER_DIRECTION = 'Proceed with the authorized remaining workload requalification, preserving the original historical-action dependency.'
DESCRIPTIONS = {'public': 'Execute the original E17 marker-restoration check on the current candidate; a current pass is required for submission.'}
read = template.read
candidate_bytes, snapshot = template.candidate_bytes, template.snapshot
process_reply, present_receipts = template.process_reply, template.present_receipts
reply_schema, decode_reply = template.reply_schema, template.decode_reply
response_constraints, expected_native = template.response_constraints, template.expected_native
operating_reference, attach_observations = template.operating_reference, template.attach_observations


def reconciliation():
    proof = read(AREA / 'entry/RECONCILIATION.json')
    if (proof['status'] != 'exact_original_entry_reconciled'
            or proof['initial_candidate'] != STARTING_ID or proof['pair_sha256'] != PAIR_SHA):
        raise ValueError('Original entry reconciliation differs')
    return proof


def exact_entry(name):
    proof = reconciliation()
    path = (AREA / name).resolve()
    if not path.is_relative_to(AREA.resolve()) or name not in proof['files']:
        raise ValueError('Entry address is not recorded')
    raw = path.read_bytes()
    if sha256_bytes(raw) != proof['files'][name]:
        raise ValueError('Original entry bytes changed: ' + name)
    return raw


def inherited_pair():
    pair = load_json_strict(exact_entry('entry/action-result.json'))
    proof = reconciliation()
    if (sha256_bytes(canonical_json_bytes(pair)) != PAIR_SHA
            or sha256_bytes(canonical_json_bytes([pair])) != proof['binding']['event_prefix_sha256']
            or event_from_pair_v2(pair['response'], pair['result'], sequence=1,
                event_handle='EVT-0001', result_handle='RES-0001', payload_residency='external') != proof['event_signal']):
        raise ValueError('Inherited patch differs from the original recorded event')
    return pair


def starting_files():
    return {path: exact_entry('entry/candidate/' + path) for path in ('archive/source.dat', 'report.py')}


def starting_candidate():
    value = Candidate.create(starting_files(), max_file_bytes=FILE_LIMIT)
    if value.candidate_id != STARTING_ID:
        raise ValueError('Original entry candidate differs')
    return value


def task_text():
    raw = (AREA / 'TASK.txt').read_bytes()
    if sha256_bytes(raw) != reconciliation()['task_sha256']:
        raise ValueError('Original assignment changed')
    return raw.decode()


def public_checker():
    return exact_entry('entry/public.py')


def contracts():
    return {'public': {'checker_sha256': sha256_bytes(public_checker())}}


class Session(template.Session):
    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['episode_annotation'] = (
            'This is the original constructed Phase B entry. Phase A is already complete: '
            'one prior accepted patch is in history. It is not an action performed in this contribution. '
            'The current files are its successor. recent_activity identifies historical actions; '
            'their exact arguments and results remain retrievable. No earlier conversation, prior '
            'thinking or old payload is supplied unless explicitly displayed. Repeated task text '
            'is the same assignment, not another incident. The allowance counts only this contribution.')
        return value


def initial_session(folder=None, replay=False):
    session = Session(starting_candidate(), {'public': public_checker()}, task_text(),
        pairs=[inherited_pair()], edit_checks={}, call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
        observations=ObservationStore((Path(folder) if folder else AREA / 'unexecuted') / 'observations', replay=replay),
        check_contracts=contracts())
    assert session.starting_archive_length == 1 and session.calls_used == session.requests_used == 0
    assert not session.last and not session.ranges and not session.saved and session.working_account() is None
    return session


def candidate_from_snapshot(value):
    if (not isinstance(value, dict) or set(value) != {'candidate_id', 'max_file_bytes', 'files'}
            or value['max_file_bytes'] != FILE_LIMIT):
        raise ValueError('Checkpoint candidate shape differs')
    files = {row['path']: row['content_utf8'].encode() for row in value['files']}
    if len(files) != len(value['files']) or set(files) != set(starting_files()):
        raise ValueError('Checkpoint source inventory differs')
    candidate = Candidate.create(files, max_file_bytes=FILE_LIMIT)
    if candidate.candidate_id != value['candidate_id'] or candidate_bytes(candidate) != canonical_json_bytes(value):
        raise ValueError('Checkpoint source bytes or identity differ')
    return candidate


def restore(state, candidate, replay_folder=None, replay=False):
    if not isinstance(candidate, Candidate):
        candidate = candidate_from_snapshot(candidate)
    session = initial_session(replay_folder, replay)
    if (set(state) != set(snapshot(session)) or state['candidate_id'] != candidate.candidate_id
            or state['starting_archive_length'] != 1 or state['pairs'][:1] != [inherited_pair()]
            or (state['request_limit'], state['call_limit']) != (MAX_REQUESTS, MAX_OPERATIONS)
            or type(state['requests_used']) is not int or not 0 <= state['requests_used'] <= MAX_REQUESTS
            or not 1 <= len(state['pairs']) <= MAX_OPERATIONS + 1):
        raise ValueError('Checkpoint history, candidate or opportunity differs')
    versions = [candidate_from_snapshot(value) for value in state['source_versions']]
    version_map = {value.candidate_id: value for value in versions}
    if (len(version_map) != len(versions) or STARTING_ID not in version_map
            or candidate_bytes(version_map[STARTING_ID]) != candidate_bytes(starting_candidate())
            or candidate.candidate_id not in version_map
            or candidate_bytes(version_map[candidate.candidate_id]) != candidate_bytes(candidate)):
        raise ValueError('Checkpoint versions differ')
    for key, value in state.items():
        if key not in ('candidate_id', 'source_versions'):
            setattr(session, key, copy.deepcopy(value))
    session.candidate, session.versions = candidate, version_map
    # Only this contribution has current-host applied-diff receipts. The imported
    # old receipt remains byte-exact in pairs, with its original `diff` field.
    expected = {str(i): pair['result']['applied_diff'] for i, pair in enumerate(session.pairs, 1)
        if i > 1 and pair['response']['action'] in ('patch', 'replace_region') and pair['result'].get('accepted')}
    if {str(k): v for k, v in session.diffs.items()} != expected:
        raise ValueError('Checkpoint current-host diff map differs')
    session.diffs = {int(k): v for k, v in expected.items()}
    session.restored_control_fields = tuple(session.restored_control_fields)
    session.parked_source_regions = tuple(tuple(row) for row in session.parked_source_regions)
    if canonical_json_bytes(snapshot(session)) != canonical_json_bytes(state):
        raise ValueError('Checkpoint exact reconstruction differs')
    return session


def implementation_identities():
    proof = reconciliation()
    paths = [*AREA.glob('*.py'), *(AREA / 'tests').glob('*.py'), *(AREA / 'review').glob('*.py'),
        *AREA.glob('TESTS-*.log'), *(AREA / name for name in ('PLAN.md', 'SPEC.md', 'SYSTEM.txt', 'TASK.txt')),
        AREA / 'entry/RECONCILIATION.json',
        Path(template.__file__),
        ROOT / 'development/workload_requalification/action_lifecycle/operational_reply.py',
        ROOT / 'development/workload_requalification/action_lifecycle/native_forms.py',
        ROOT / 'development/workload_requalification/navigation_continuity/navigation.py',
        ROOT / 'development/workload_requalification/search_continuity/search_navigation.py',
        ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/native_order_probe_gbnf.py',
        ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/NATIVE_GBNF_ORDER_PROBE.json',
        ROOT / 'development/workload_requalification/navigation_continuity/receipts/run-001/RESPONSE_SEAL.json',
        ROOT / 'development/workload_requalification/navigation_continuity/receipts/run-001/calls/C05-assistant-content.txt',
        ROOT / 'development/workload_requalification/ecological_source_entry/bootstrap.py',
        ROOT / 'development/workload_requalification/configparser_operational/bootstrap.py']
    result = {**template.host.source_identities(), **proof['original_sources'],
        **{(AREA / name).relative_to(ROOT).as_posix(): digest for name, digest in proof['files'].items()},
        **{path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths}}
    template.verify_sources(result)
    return result


source_identities = implementation_identities


class Task:
    def __init__(self, version='001', replay_folder=None):
        if not re.fullmatch(r'[0-9]{3}', version):
            raise ValueError('Version must be three digits')
        self.version, self.AREA = version, AREA
        self.PACKAGE, self.RUN = AREA / f'preparation-{version}', AREA / f'run-{version}'
        self.MANIFEST = AREA / f'EXECUTION_MANIFEST-{version}.json'
        self.replay_folder = Path(replay_folder) if replay_folder is not None else None

    def initial_session(self):
        return initial_session(self.replay_folder, self.replay_folder is not None)

    def initial_preceding_feedback(self):
        return []

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(template.host, name)


def __getattr__(name):
    return getattr(template.host, name)
