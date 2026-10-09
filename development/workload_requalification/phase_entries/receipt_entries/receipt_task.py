"""Case configuration for the remaining original E14 full-phase entries."""
import copy
from functools import lru_cache
import importlib.util
from pathlib import Path
import re
from types import SimpleNamespace

import receipt_bootstrap
import phase_task as source
import phase_session
import probe_task
import probe_session
import receipt_reports
from working_set_exp import decision_view, working_view
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.thinking_grammar import with_thinking

ROOT, AREA = source.ROOT, Path(__file__).resolve().parent
BANK = ROOT / 'experiments/014_unified_active_phase_receipts/fresh_bank'
BANK_SHA256 = 'e4c209df334b6ef7d8e4ed901f0097f58e5026a8d7ad43943311d6e67932618a'
CASES = {
    'E14-CLOSURE-MINT': dict(folder='mint', files=157, probe=True,
        initial='9f74185e02bca6767e806d67d8885a472add9d32027f2df504739fd8f6e47fbe',
        public='Original Phase B label behavior check; it does not establish the required acquisition history.'),
    'E14-STALE-SABLE': dict(folder='sable', files=158, probe=False,
        initial='e82fdef3ee93d361bce884e8e1cfcfdd9548a25581dc24892e0007d72250459c',
        public='Original public check executes invariants.stable.invariant_ok(). It does not test normalized-name behavior or acquisition history.'),
}


class ProbeSession(probe_session.Session):
    assessment_api = receipt_reports


class SourceSession(phase_session.Session):
    assessment_api = receipt_reports


class Task(source.Task):
    ACTOR, SEED, FILE_LIMIT = dict(source.ACTOR), source.SEED, source.FILE_LIMIT
    MAX_REQUESTS, MAX_OPERATIONS = 32, 96

    def __init__(self, version='001', replay_folder=None, case='E14-CLOSURE-MINT'):
        if case not in CASES or not re.fullmatch(r'[0-9]{3}', version):
            raise ValueError('unknown original case or invalid version')
        self.CASE, self.config = case, CASES[case]
        self.AREA, self.STARTING_ID = AREA / self.config['folder'], self.config['initial']
        self.version, self.replay_folder = version, Path(replay_folder) if replay_folder else None
        self.PACKAGE, self.RUN = self.AREA / f'preparation-{version}', self.AREA / f'run-{version}'
        self.MANIFEST = self.AREA / f'EXECUTION_MANIFEST-{version}.json'
        self.OWNER_DIRECTION = f'Continue original workload requalification: one qualified uncoached full {case} attempt.'
        self.descriptions = {'prefork': 'Original Phase A check: completed_phases() must return 1.',
                             'public': self.config['public']}
        assert sha256_file(BANK / 'BANK_MANIFEST.json') == BANK_SHA256
        self.original_rows = {r['path']: r for r in self.read(BANK / 'BANK_MANIFEST.json')['files']}
        self.fixture = load_json_strict(self.exact(f'execution_only/{case}/FIXTURE.json'))
        assert self.fixture['initial_candidate_id'] == self.STARTING_ID
        assert self.fixture['fixture_id'] == case and len(self.fixture['candidate_files']) == self.config['files']

    def exact(self, name):
        path = (BANK / name).resolve()
        if not path.is_relative_to(BANK.resolve()) or name not in self.original_rows:
            raise ValueError('unlisted original bank path')
        raw, row = path.read_bytes(), self.original_rows[name]
        if len(raw) != row['size_bytes'] or sha256_bytes(raw) != row['sha256']:
            raise ValueError('original bank bytes differ: ' + name)
        return raw

    def task_text(self):
        return self.exact(f'model_visible/{self.CASE}/TASK.txt').decode()

    def starting_files(self):
        files = {}
        for row in self.fixture['candidate_files']:
            raw = self.exact(f'model_visible/{self.CASE}/candidate/' + row['path'])
            assert len(raw) == row['size_bytes'] and sha256_bytes(raw) == row['sha256']
            files[row['path']] = raw
        return files

    def starting_candidate(self):
        candidate = Candidate.create(self.starting_files(), max_file_bytes=self.FILE_LIMIT)
        assert candidate.candidate_id == self.STARTING_ID
        return candidate

    def checker(self, phase):
        return self.exact(f'execution_only/{self.CASE}/checks/{phase}.py')

    def initial_session(self):
        checkers = {'prefork': self.checker('A'), 'public': self.checker('B')}
        factory = ProbeSession if self.config['probe'] else SourceSession
        extra = dict(probe_body=self.exact(f'execution_only/{self.CASE}/probes/A.txt').decode()) if self.config['probe'] else {}
        return factory(self.starting_candidate(), checkers, self.task_text(),
            edit_checks={}, call_limit=self.MAX_OPERATIONS, request_limit=self.MAX_REQUESTS,
            phase_texts={p: self.exact(f'model_visible/{self.CASE}/PHASE_{p}.txt').decode() for p in ('A', 'B')},
            phase_required={p: self.fixture['phases'][p]['required'] for p in ('A', 'B')},
            observations=ObservationStore((self.replay_folder or self.AREA / 'unexecuted') / 'observations',
                                          replay=self.replay_folder is not None),
            check_contracts={k: dict(checker_sha256=sha256_bytes(v), scope_description=self.descriptions[k])
                             for k, v in checkers.items()}, **extra)

    def reply_schema(self):
        factory = probe_session.reply_schema_for if self.config['probe'] else phase_session.reply_schema_for
        return factory(self.descriptions)

    def decode_reply(self, content):
        reply = decision_view.decode_reply(content)
        working_view.validate(reply, self.reply_schema()['json_schema']['schema'])
        return reply

    @lru_cache(maxsize=2)
    def response_constraints(self):
        path = ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
        assert sha256_file(path) == 'ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
        spec = importlib.util.spec_from_file_location('receipt_schema_converter', path)
        converter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(converter)
        original = decision_view.reply_schema(self.descriptions)['json_schema']['schema']
        target, replaced = self.reply_schema()['json_schema']['schema'], []
        class Converter(converter.SchemaConverter):
            def visit(self, schema, name):
                if name == 'ordinary-reply':
                    assert schema == original and not replaced
                    replaced.append(name)
                    schema = target
                return super().visit(schema, name)
        grammar = decision_view.reply_grammar(self.descriptions, Converter)
        assert replaced == ['ordinary-reply']
        return dict(grammar=with_thinking(grammar))

    def expected_native(self, request):
        assert request['grammar'] == self.response_constraints()['grammar'] and request['seed'] == self.SEED
        prior = copy.deepcopy(request)
        prior['grammar'], prior['seed'] = source.response_constraints()['grammar'], source.SEED
        return source.expected_native(prior)

    def operating_reference(self):
        text = probe_task.operating_reference() if self.config['probe'] else source.operating_reference()
        return text + '\n\nRegistered check scope for this original task:\n' + '\n'.join(
            f'{scope}: {description}' for scope, description in self.descriptions.items())

    def snapshot(self, session):
        value = super().snapshot(session)
        value['diffs'] = {str(k): v for k, v in value['diffs'].items()}
        return value

    def restore(self, state, candidate, replay_folder=None, replay=False):
        if not isinstance(candidate, Candidate):
            candidate = self.candidate_from_snapshot(candidate)
        session = Task(self.version, replay_folder if replay else None, self.CASE).initial_session()
        if (set(state) != set(self.snapshot(session)) or state['candidate_id'] != candidate.candidate_id
                or state['starting_archive_length'] != 0 or len(state['pairs']) > self.MAX_OPERATIONS
                or (state['request_limit'], state['call_limit']) != (self.MAX_REQUESTS, self.MAX_OPERATIONS)
                or type(state['requests_used']) is not int or not 0 <= state['requests_used'] <= self.MAX_REQUESTS):
            raise ValueError('checkpoint shape/opportunity differs')
        versions = [self.candidate_from_snapshot(v) for v in state['source_versions']]
        mapped = {v.candidate_id: v for v in versions}
        if (len(mapped) != len(versions) or self.STARTING_ID not in mapped or candidate.candidate_id not in mapped
                or self.candidate_bytes(mapped[candidate.candidate_id]) != self.candidate_bytes(candidate)):
            raise ValueError('checkpoint source versions differ')
        for key, value in state.items():
            if key not in ('candidate_id', 'source_versions'):
                setattr(session, key, copy.deepcopy(value))
        session.candidate, session.versions = candidate, mapped
        expected = {str(i): p['result']['applied_diff'] for i, p in enumerate(session.pairs, 1)
                    if p['response']['action'] in ('patch', 'replace_region') and p['result'].get('accepted')}
        if session.diffs != expected:
            raise ValueError('checkpoint diff history differs')
        session.diffs = {int(k): v for k, v in expected.items()}
        session.restored_control_fields = tuple(session.restored_control_fields)
        session.parked_source_regions = tuple(tuple(r) for r in session.parked_source_regions)
        if len([p for p in session.pairs if p['response']['action'] == 'fork_ready' and p['result'].get('accepted')]) > 1:
            raise ValueError('duplicate accepted phase boundary')
        for row in session.presented_coverage:
            if (set(row) != {'phase', 'path', 'file_sha256', 'ranges'} or row['phase'] not in ('A', 'B')
                    or row['path'] not in session.phase_required[row['phase']]):
                raise ValueError('coverage scope differs')
            matching = [v for v in mapped.values() if v.file_sha256(row['path']) == row['file_sha256']]
            if not matching or any(type(a) is not int or type(b) is not int or not 1 <= a <= b <=
                    len(matching[0].file_map[row['path']].decode().splitlines(keepends=True)) for a, b in row['ranges']):
                raise ValueError('coverage extent/version differs')
        if self.config['probe']:
            session.observation_rows()
        if canonical_json_bytes(self.snapshot(session)) != canonical_json_bytes(state):
            raise ValueError('checkpoint reconstruction differs')
        return session

    def source_identities(self):
        paths = [*AREA.glob('*.py'), *(AREA / 'tests').glob('*.py'), *(AREA / 'review').glob('*.py'),
                 AREA / 'PLAN.md', *(self.AREA / n for n in ('SPEC.md', 'SYSTEM.txt')),
                 *probe_task.AREA.glob('*.py'), BANK / 'BANK_MANIFEST.json']
        paths.extend(BANK / name for name in self.original_rows if f'/{self.CASE}/' in name and '/known_good/' not in name)
        return {**super().source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}

    implementation_identities = source_identities


def case_api(case):
    """The existing replay core accepts a module-shaped case factory."""
    def factory(version='001', replay_folder=None):
        return Task(version, replay_folder, case)
    return SimpleNamespace(ROOT=ROOT, read=source.read, Task=factory)


def __getattr__(name):
    return getattr(source, name)
