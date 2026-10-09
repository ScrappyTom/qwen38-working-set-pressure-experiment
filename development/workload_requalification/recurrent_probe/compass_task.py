"""Exact original COMPASS material on the existing recurrent/probe host."""
import copy
from functools import lru_cache
import importlib.util
from pathlib import Path
import re

import compass_bootstrap
import recurrent_task as source
import phase_task
import compass_session
import probe_task
from current_facts import operating_reference as current_reference
from working_set_exp import decision_view, working_view
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.thinking_grammar import with_thinking

ROOT, AREA, BANK = source.ROOT, Path(__file__).resolve().parent, source.BANK
CASE = 'E12-OBS-COMPASS'
ORDER = compass_session.Session.order


def reply_schema():
    return compass_session.reply_schema_for(phase_task.DESCRIPTIONS)


def decode_reply(content):
    reply = decision_view.decode_reply(content)
    working_view.validate(reply, reply_schema()['json_schema']['schema'])
    return reply


@lru_cache(maxsize=1)
def response_constraints():
    path = ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    assert sha256_file(path) == 'ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
    spec = importlib.util.spec_from_file_location('compass_schema_converter', path)
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    original = decision_view.reply_schema(phase_task.DESCRIPTIONS)['json_schema']['schema']
    replaced = []
    class Converter(converter.SchemaConverter):
        def visit(self, schema, name):
            if name == 'ordinary-reply':
                assert schema == original and not replaced
                replaced.append(name)
                schema = reply_schema()['json_schema']['schema']
            return super().visit(schema, name)
    grammar = decision_view.reply_grammar(phase_task.DESCRIPTIONS, Converter)
    assert replaced == ['ordinary-reply']
    return dict(grammar=with_thinking(grammar))


def expected_native(request):
    assert request['grammar'] == response_constraints()['grammar'] and request['seed'] == phase_task.SEED
    old = copy.deepcopy(request)
    old['grammar'] = phase_task.response_constraints()['grammar']
    return phase_task.expected_native(old)


class Task(source.Task):
    AREA, CASE = AREA, CASE
    STARTING_ID = 'bfd1a99ee7376657b258b34198a0e7559b2f5fea3939b0926d26aa3a3a8550d2'
    OWNER_DIRECTION = 'Continue original workload qualification: one qualified uncoached four-phase COMPASS attempt.'
    reply_schema = staticmethod(reply_schema)
    decode_reply = staticmethod(decode_reply)
    response_constraints = staticmethod(response_constraints)
    expected_native = staticmethod(expected_native)

    def __init__(self, version='001', replay_folder=None):
        if not re.fullmatch(r'[0-9]{3}', version):
            raise ValueError('version must be three decimal digits')
        self.version, self.replay_folder = version, Path(replay_folder) if replay_folder else None
        self.PACKAGE, self.RUN = AREA / f'preparation-{version}', AREA / f'run-{version}'
        self.MANIFEST = AREA / f'EXECUTION_MANIFEST-{version}.json'
        assert sha256_file(BANK / 'BANK_MANIFEST.json') == source.BANK_SHA256
        self.original_rows = {r['path']: r for r in self.read(BANK / 'BANK_MANIFEST.json')['files']}
        self.fixture = load_json_strict(self.exact(f'execution_only/{CASE}/FIXTURE.json'))
        assert self.fixture['initial_candidate_id'] == self.STARTING_ID
        assert self.fixture['fixture_id'] == CASE and len(self.fixture['candidate_files']) == 160

    def task_text(self):
        return self.exact(f'model_visible/{CASE}/TASK.txt').decode()

    def starting_files(self):
        files = {}
        for row in self.fixture['candidate_files']:
            raw = self.exact(f'model_visible/{CASE}/candidate/' + row['path'])
            assert len(raw) == row['size_bytes'] and sha256_bytes(raw) == row['sha256']
            files[row['path']] = raw
        return files

    def checker(self, phase):
        return self.exact(f'execution_only/{CASE}/checks/{phase}.py')

    def initial_session(self):
        checkers = {p: self.checker(p) for p in ORDER}
        contracts = {p: dict(checker_sha256=sha256_bytes(v)) for p, v in checkers.items()}
        return compass_session.Session(self.starting_candidate(),
            {'prefork': checkers['A'], 'public': checkers['B']}, self.task_text(),
            edit_checks={}, call_limit=self.MAX_OPERATIONS, request_limit=self.MAX_REQUESTS,
            phase_texts={p: self.exact(f'model_visible/{CASE}/PHASE_{p}.txt').decode() for p in ORDER},
            phase_required={p: self.fixture['phases'][p]['required'] for p in ORDER},
            phase_checkers=checkers, phase_contracts=contracts,
            probe_bodies={p: self.exact(f'execution_only/{CASE}/probes/{p}.txt').decode() for p in ('A','B','C')},
            observations=ObservationStore((self.replay_folder or AREA / 'unexecuted') / 'observations',
                replay=self.replay_folder is not None),
            check_contracts={'prefork': contracts['A'], 'public': contracts['B']})

    def operating_reference(self):
        return current_reference(super().operating_reference()) + '\n\n' + compass_session.REFERENCE + (
            '\nRequired argument forms: ' + canonical_json_bytes(compass_session.probe_forms()).decode())

    def restore(self, state, candidate, replay_folder=None, replay=False):
        # Same recurrent snapshot contract; construct this adapter rather than
        # widening the frozen ORBIT class's hard-coded factory.
        if not isinstance(candidate, Candidate):
            candidate = self.candidate_from_snapshot(candidate)
        session = type(self)(self.version, replay_folder if replay else None).initial_session()
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
        session.sync_checkers()
        for row in session.presented_coverage:
            if (set(row) != {'phase', 'path', 'file_sha256', 'ranges'} or row['phase'] not in ORDER
                    or row['path'] not in session.phase_required[row['phase']]):
                raise ValueError('coverage scope differs')
            matching = [v for v in mapped.values() if v.file_sha256(row['path']) == row['file_sha256']]
            if not matching or any(type(a) is not int or type(b) is not int or not 1 <= a <= b <=
                    len(matching[0].file_map[row['path']].decode().splitlines(keepends=True)) for a, b in row['ranges']):
                raise ValueError('coverage extent/version differs')
        session.observation_rows()
        if canonical_json_bytes(self.snapshot(session)) != canonical_json_bytes(state):
            raise ValueError('checkpoint reconstruction differs')
        return session

    def source_identities(self):
        paths = [*AREA.glob('*.py'), *(AREA / 'tests').glob('*.py'), *(AREA / 'review').glob('*.py'),
            *(AREA / n for n in ('PLAN.md', 'SPEC.md', 'SYSTEM.txt')),
            AREA.parent / 'decision_facts/current_facts.py', AREA.parent / 'decision_facts/PLAN.md']
        paths.extend(BANK / name for name in self.original_rows if f'/{CASE}/' in name and '/known_good/' not in name)
        return {**super().source_identities(), **probe_task.Task().source_identities(),
            **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}

    implementation_identities = source_identities


def __getattr__(name):
    return getattr(source, name)
