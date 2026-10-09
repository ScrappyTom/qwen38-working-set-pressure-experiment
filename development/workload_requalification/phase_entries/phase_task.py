"""Original E13 source task over the qualified single-contribution machinery."""
import copy
from functools import lru_cache
import importlib.util
from pathlib import Path
import re

import bootstrap
import repair_task as host
import navigation
import operational_reply
import search_navigation
from phase_session import Session, fork_rule, reply_schema_for
from working_set_exp import decision_view, working_view
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.thinking_grammar import with_thinking

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent
BANK = ROOT / 'experiments/013_active_phase_receipts/fresh_bank'
BANK_SHA256 = '2bcbfe7702e9194da1dabeb4cf56a91806e47aa2e2d92d30a608d9a0e7be04ef'
CASE = 'E13-SOURCE-LUMEN'
STARTING_ID = 'de6c9c58d53bfdfbf5b1fc821a7fb53d6465a70d7fdb5080fe77b51f429cadd5'
ACTOR, SEED, FILE_LIMIT = dict(host.ACTOR), 173205, 24000
MAX_REQUESTS, MAX_OPERATIONS = 32, 96
DESCRIPTIONS = {'prefork': 'Original Phase A progress behavior check; required for fork_ready.',
                'public': 'Original Phase B policy/name behavior check; required for submission.'}


def action_rule():
    rule = decision_view.action_rule(DESCRIPTIONS)
    rule['oneOf'].append(fork_rule())
    return rule


def reply_schema():
    return reply_schema_for(DESCRIPTIONS)


def decode_reply(content):
    reply = decision_view.decode_reply(content)
    working_view.validate(reply, reply_schema()['json_schema']['schema'])
    return reply


@lru_cache(maxsize=1)
def response_constraints():
    path = ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    assert sha256_file(path) == 'ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
    spec = importlib.util.spec_from_file_location('phase_schema_converter', path)
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    original = decision_view.reply_schema(DESCRIPTIONS)['json_schema']['schema']
    replacements = []
    class PhaseConverter(converter.SchemaConverter):
        def visit(self, schema, name):
            if name == 'ordinary-reply':
                assert schema == original and not replacements
                replacements.append(name)
                schema = reply_schema()['json_schema']['schema']
            return super().visit(schema, name)
    grammar = decision_view.reply_grammar(DESCRIPTIONS, PhaseConverter)
    assert replacements == ['ordinary-reply']
    return dict(grammar=with_thinking(grammar))


def expected_native(request):
    assert request['grammar'] == response_constraints()['grammar'] and request['seed'] == SEED
    old = copy.deepcopy(request)
    old['grammar'], old['seed'] = host.response_constraints()['grammar'], host.SEED
    return host.expected_native(old)


def operating_reference():
    text = operational_reply.operating_reference(host.Task('artifact_map').operating_reference())
    # Rebuild the existing check argument line with the actual named scopes.
    old_rule = decision_view.action_rule({'public': DESCRIPTIONS['public']})
    old_check, = [f for f in old_rule['oneOf'] if f['properties']['action'].get('const') == 'check']
    new_check, = [f for f in action_rule()['oneOf'] if f['properties']['action'].get('const') == 'check']
    before, after = canonical_json_bytes(old_check).decode(), canonical_json_bytes(new_check).decode()
    assert text.count(before) == 1
    text = text.replace(before, after)
    label = 'The original public checker must pass; there are no injected fault tests in this task.'
    assert text.count(label) == 1
    text = text.replace(label, 'The selected original checker reports its own named scope; there are no injected fault tests in this task.')
    text = text.replace('request check public in a later reply', 'request the active phase check in a later reply')
    return text + '\n\n' + navigation.REFERENCE_ADDITION + '\n\n' + search_navigation.REFERENCE_ADDITION + (
        '\n\nPhase A uses check prefork; Phase B uses check public. Checks of the inactive scope are rejected. '
        'The original task and current phase are separate from the archive. A prior phase pass remains '
        'historical and does not qualify submission. Source coverage in phase records prior exact '
        'presentation on unchanged file bytes, not present visibility or understanding. The submission '
        'guard checks Phase B and the current public pass; other task obligations still require your work.\n\n'
        'fork_ready: Completes Phase A only after its required files were fully presented and the '
        'current candidate passed prefork. It changes no file and runs no check. On acceptance it '
        'releases selected source/results, preserves the archive and account, and begins Phase B in '
        'the next input. The overall request/operation allowance is not reset. A rejected boundary '
        'preserves the current phase and selection.\nRequired argument forms: ' + canonical_json_bytes(fork_rule()).decode())


class Task:
    ROOT, AREA, CASE, STARTING_ID = ROOT, AREA, CASE, STARTING_ID
    ACTOR, SEED, FILE_LIMIT = ACTOR, SEED, FILE_LIMIT
    MAX_REQUESTS, MAX_OPERATIONS = MAX_REQUESTS, MAX_OPERATIONS
    OWNER_DIRECTION = 'Keep working through original full-phase workloads; one qualified uncoached LUMEN attempt.'
    read = staticmethod(host.read)
    save = staticmethod(host.save)
    reply_schema = staticmethod(reply_schema)
    decode_reply = staticmethod(decode_reply)
    response_constraints = staticmethod(response_constraints)
    expected_native = staticmethod(expected_native)
    operating_reference = staticmethod(operating_reference)
    candidate_bytes = staticmethod(host.candidate_bytes)
    process_reply = staticmethod(host.process_reply)
    present_receipts = staticmethod(navigation.present_receipts)

    def __init__(self, version='001', replay_folder=None):
        if not re.fullmatch(r'[0-9]{3}', version):
            raise ValueError('version must be three decimal digits')
        self.version, self.replay_folder = version, Path(replay_folder) if replay_folder else None
        self.PACKAGE, self.RUN = AREA / f'preparation-{version}', AREA / f'run-{version}'
        self.MANIFEST = AREA / f'EXECUTION_MANIFEST-{version}.json'
        assert sha256_file(BANK / 'BANK_MANIFEST.json') == BANK_SHA256
        manifest = self.read(BANK / 'BANK_MANIFEST.json')
        self.original_rows = {r['path']: r for r in manifest['files']}
        self.fixture = load_json_strict(self.exact(f'execution_only/{CASE}/FIXTURE.json'))
        assert self.fixture['initial_candidate_id'] == STARTING_ID and self.fixture['fixture_id'] == CASE
        assert len(self.fixture['candidate_files']) == 160

    def exact(self, name):
        path = (BANK / name).resolve()
        if not path.is_relative_to(BANK.resolve()) or name not in self.original_rows:
            raise ValueError('unlisted bank path')
        raw, row = path.read_bytes(), self.original_rows[name]
        if len(raw) != row['size_bytes'] or sha256_bytes(raw) != row['sha256']:
            raise ValueError('original bank bytes differ: ' + name)
        return raw

    def task_text(self):
        return self.exact(f'model_visible/{CASE}/TASK.txt').decode()

    def starting_files(self):
        result = {}
        for row in self.fixture['candidate_files']:
            raw = self.exact(f'model_visible/{CASE}/candidate/' + row['path'])
            assert sha256_bytes(raw) == row['sha256'] and len(raw) == row['size_bytes']
            result[row['path']] = raw
        return result

    def starting_candidate(self):
        value = Candidate.create(self.starting_files(), max_file_bytes=FILE_LIMIT)
        assert value.candidate_id == STARTING_ID
        return value

    def checker(self, phase):
        return self.exact(f'execution_only/{CASE}/checks/{phase}.py')

    def initial_session(self):
        checkers = {'prefork': self.checker('A'), 'public': self.checker('B')}
        return Session(self.starting_candidate(), checkers, self.task_text(),
            edit_checks={}, call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
            phase_texts={p: self.exact(f'model_visible/{CASE}/PHASE_{p}.txt').decode() for p in ('A', 'B')},
            phase_required={p: self.fixture['phases'][p]['required'] for p in ('A', 'B')},
            observations=ObservationStore((self.replay_folder or AREA / 'unexecuted') / 'observations',
                                          replay=self.replay_folder is not None),
            check_contracts={k: dict(checker_sha256=sha256_bytes(v)) for k, v in checkers.items()})

    def initial_preceding_feedback(self):
        return []

    def snapshot(self, session):
        return {**host.snapshot(session), 'presented_coverage': copy.deepcopy(session.presented_coverage),
            'source_versions': [load_json_strict(self.candidate_bytes(v)) for _, v in sorted(session.versions.items())]}

    def candidate_from_snapshot(self, value):
        if set(value) != {'candidate_id', 'max_file_bytes', 'files'} or value['max_file_bytes'] != FILE_LIMIT:
            raise ValueError('candidate snapshot contract differs')
        files = {r['path']: r['content_utf8'].encode() for r in value['files']}
        candidate = Candidate.create(files, max_file_bytes=FILE_LIMIT)
        if (len(files) != len(value['files']) or set(files) != set(self.starting_files())
                or candidate.candidate_id != value['candidate_id']
                or self.candidate_bytes(candidate) != canonical_json_bytes(value)):
            raise ValueError('candidate snapshot identity differs')
        return candidate

    def restore(self, state, candidate, replay_folder=None, replay=False):
        if not isinstance(candidate, Candidate):
            candidate = self.candidate_from_snapshot(candidate)
        session = Task(self.version, replay_folder if replay else None).initial_session()
        if (set(state) != set(self.snapshot(session)) or state['candidate_id'] != candidate.candidate_id
                or state['starting_archive_length'] != 0 or len(state['pairs']) > MAX_OPERATIONS
                or (state['request_limit'], state['call_limit']) != (MAX_REQUESTS, MAX_OPERATIONS)
                or type(state['requests_used']) is not int or not 0 <= state['requests_used'] <= MAX_REQUESTS):
            raise ValueError('checkpoint shape/opportunity differs')
        versions = [self.candidate_from_snapshot(v) for v in state['source_versions']]
        mapped = {v.candidate_id: v for v in versions}
        if (len(mapped) != len(versions) or STARTING_ID not in mapped or candidate.candidate_id not in mapped
                or self.candidate_bytes(mapped[candidate.candidate_id]) != self.candidate_bytes(candidate)):
            raise ValueError('checkpoint source versions differ')
        for key, value in state.items():
            if key not in ('candidate_id', 'source_versions'):
                setattr(session, key, copy.deepcopy(value))
        session.candidate, session.versions = candidate, mapped
        expected = {str(i): p['result']['applied_diff'] for i, p in enumerate(session.pairs, 1)
                    if p['response']['action'] in ('patch', 'replace_region') and p['result'].get('accepted')}
        if {str(k): v for k, v in session.diffs.items()} != expected:
            raise ValueError('checkpoint diff history differs')
        session.diffs = {int(k): v for k, v in expected.items()}
        session.restored_control_fields = tuple(session.restored_control_fields)
        session.parked_source_regions = tuple(tuple(r) for r in session.parked_source_regions)
        forks = [p for p in session.pairs if p['response']['action'] == 'fork_ready' and p['result'].get('accepted')]
        if len(forks) > 1:
            raise ValueError('duplicate accepted phase boundary')
        for row in session.presented_coverage:
            if (set(row) != {'phase', 'path', 'file_sha256', 'ranges'} or row['phase'] not in ('A', 'B')
                    or row['path'] not in session.phase_required[row['phase']]):
                raise ValueError('coverage scope differs')
            matching = [v for v in mapped.values() if v.file_sha256(row['path']) == row['file_sha256']]
            if not matching or any(type(a) is not int or type(b) is not int or not 1 <= a <= b <=
                    len(matching[0].file_map[row['path']].decode().splitlines(keepends=True)) for a, b in row['ranges']):
                raise ValueError('coverage extent/version differs')
        if canonical_json_bytes(self.snapshot(session)) != canonical_json_bytes(state):
            raise ValueError('checkpoint reconstruction differs')
        return session

    def attach_observations(self, session, folder, log):
        prefix = Path(folder).resolve().relative_to(Path(log.path).parent.resolve()).as_posix()
        prefix = '' if prefix == '.' else prefix + '/'
        def preserved(record, artifacts):
            log.append('check_observation_preserved', record,
                [{**r, 'path': prefix + 'observations/' + r['path']} for r in artifacts])
        session.observations = ObservationStore(Path(folder) / 'observations', on_preserved=preserved)

    def source_identities(self):
        paths = [*AREA.glob('*.py'), *(AREA / 'tests').glob('*.py'),
            *(AREA / 'review').glob('*.py'),
            *(AREA / name for name in ('PLAN.md', 'SPEC.md', 'SYSTEM.txt')),
            BANK / 'BANK_MANIFEST.json',
            ROOT / 'development/workload_requalification/compiler_entry/native_forms.py',
            ROOT / 'development/workload_requalification/url_port_entry/review/verify_run.py']
        for name in ('action_lifecycle', 'navigation_continuity', 'search_continuity', 'small_repairs'):
            paths.extend((ROOT / 'development/workload_requalification' / name).glob('*.py'))
        paths.extend(BANK / name for name in self.original_rows if f'/{CASE}/' in name and '/known_good/' not in name)
        return {**host.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}

    implementation_identities = source_identities

    def __getattr__(self, name):
        return getattr(host, name)


def __getattr__(name):
    return getattr(host, name)
