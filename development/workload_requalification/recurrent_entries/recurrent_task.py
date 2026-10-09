"""Exact original ORBIT entry; the current host remains the execution core."""
import copy
from pathlib import Path
import re

import recurrent_bootstrap
import phase_task as source
import recurrent_session
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = source.ROOT, Path(__file__).resolve().parent
BANK = ROOT / 'experiments/012_large_world_recurrent_continuity/fresh_bank'
BANK_SHA256 = '6f83c4c8f524ebe6d04bc3d646df250e588cfd3d81e3a7dd0a33ba1332118b4e'
CASE = 'E12-SOURCE-ORBIT'
ORDER = recurrent_session.Session.order


class Task(source.Task):
    AREA, CASE = AREA, CASE
    STARTING_ID = '02b29a62f2e074df1b942e0e59664f54403e6ad342f9faab17f3ec963afc4c62'
    MAX_REQUESTS, MAX_OPERATIONS = 64, 192
    OWNER_DIRECTION = 'Continue original workload qualification: one qualified uncoached four-phase ORBIT attempt.'

    def __init__(self, version='001', replay_folder=None):
        if not re.fullmatch(r'[0-9]{3}', version):
            raise ValueError('version must be three decimal digits')
        self.version, self.replay_folder = version, Path(replay_folder) if replay_folder else None
        self.PACKAGE, self.RUN = AREA / f'preparation-{version}', AREA / f'run-{version}'
        self.MANIFEST = AREA / f'EXECUTION_MANIFEST-{version}.json'
        assert sha256_file(BANK / 'BANK_MANIFEST.json') == BANK_SHA256
        self.original_rows = {r['path']: r for r in self.read(BANK / 'BANK_MANIFEST.json')['files']}
        self.fixture = load_json_strict(self.exact(f'execution_only/{CASE}/FIXTURE.json'))
        assert self.fixture['initial_candidate_id'] == self.STARTING_ID
        assert self.fixture['fixture_id'] == CASE and len(self.fixture['candidate_files']) == 160

    def exact(self, name):
        path = (BANK / name).resolve()
        if not path.is_relative_to(BANK.resolve()) or name not in self.original_rows:
            raise ValueError('unlisted original bank path')
        raw, row = path.read_bytes(), self.original_rows[name]
        if len(raw) != row['size_bytes'] or sha256_bytes(raw) != row['sha256']:
            raise ValueError('original bank bytes differ: ' + name)
        return raw

    def task_text(self):
        return self.exact(f'model_visible/{CASE}/TASK.txt').decode()

    def starting_files(self):
        files = {}
        for row in self.fixture['candidate_files']:
            raw = self.exact(f'model_visible/{CASE}/candidate/' + row['path'])
            assert len(raw) == row['size_bytes'] and sha256_bytes(raw) == row['sha256']
            files[row['path']] = raw
        return files

    def starting_candidate(self):
        candidate = Candidate.create(self.starting_files(), max_file_bytes=self.FILE_LIMIT)
        assert candidate.candidate_id == self.STARTING_ID
        return candidate

    def checker(self, phase):
        return self.exact(f'execution_only/{CASE}/checks/{phase}.py')

    def initial_session(self):
        checkers = {p: self.checker(p) for p in ORDER}
        contracts = {p: dict(checker_sha256=sha256_bytes(v)) for p, v in checkers.items()}
        return recurrent_session.Session(self.starting_candidate(),
            {'prefork': checkers['A'], 'public': checkers['B']}, self.task_text(),
            edit_checks={}, call_limit=self.MAX_OPERATIONS, request_limit=self.MAX_REQUESTS,
            phase_texts={p: self.exact(f'model_visible/{CASE}/PHASE_{p}.txt').decode() for p in ORDER},
            phase_required={p: self.fixture['phases'][p]['required'] for p in ORDER},
            phase_checkers=checkers, phase_contracts=contracts,
            observations=ObservationStore((self.replay_folder or AREA / 'unexecuted') / 'observations',
                                          replay=self.replay_folder is not None),
            check_contracts={'prefork': contracts['A'], 'public': contracts['B']})

    def operating_reference(self):
        text = source.operating_reference()
        marker = '\n\nPhase A uses check prefork; Phase B uses check public.'
        assert text.count(marker) == 1
        return text.split(marker)[0] + (
            '\n\nThis original task has four ordered phases. A uses prefork; B, C and D '
            'each use public with their own original checker definition. Inactive checks are rejected. '
            'The current definition is shown in phase; historical passes do not acquire a new scope. '
            'Coverage records previously delivered exact source on unchanged file bytes, not current '
            'visibility or understanding. Other original task obligations remain your work.\n\n'
            'fork_ready completes the current nonterminal phase only after its required files were '
            'fully presented and the candidate passed its active checker. It edits no file and runs '
            'no check. On acceptance it releases selected source/results, preserves archive/account '
            'and starts the next phase with that phase\'s original checker. No request/operation '
            'allowance resets. Rejection preserves phase and selection. Only D permits submit, '
            'and submission requires its current public pass.\nRequired argument forms: '
            + canonical_json_bytes(source.fork_rule()).decode())

    def snapshot(self, session):
        value = super().snapshot(session)
        value['diffs'] = {str(k): v for k, v in value['diffs'].items()}
        return value

    def restore(self, state, candidate, replay_folder=None, replay=False):
        if not isinstance(candidate, Candidate):
            candidate = self.candidate_from_snapshot(candidate)
        session = Task(self.version, replay_folder if replay else None).initial_session()
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
        session.sync_checkers()  # Validates accepted boundary order; no competing phase flag.
        for row in session.presented_coverage:
            if (set(row) != {'phase', 'path', 'file_sha256', 'ranges'} or row['phase'] not in ORDER
                    or row['path'] not in session.phase_required[row['phase']]):
                raise ValueError('coverage scope differs')
            matching = [v for v in mapped.values() if v.file_sha256(row['path']) == row['file_sha256']]
            if not matching or any(type(a) is not int or type(b) is not int or not 1 <= a <= b <=
                    len(matching[0].file_map[row['path']].decode().splitlines(keepends=True)) for a, b in row['ranges']):
                raise ValueError('coverage extent/version differs')
        if canonical_json_bytes(self.snapshot(session)) != canonical_json_bytes(state):
            raise ValueError('checkpoint reconstruction differs')
        return session

    def source_identities(self):
        paths = [*AREA.glob('*.py'), *(AREA / 'tests').glob('*.py'), *(AREA / 'review').glob('*.py'),
                 *(AREA / n for n in ('PLAN.md', 'SPEC.md', 'SYSTEM.txt')), BANK / 'BANK_MANIFEST.json']
        paths.extend(BANK / name for name in self.original_rows if f'/{CASE}/' in name and '/known_good/' not in name)
        return {**super().source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}

    implementation_identities = source_identities


def __getattr__(name):
    return getattr(source, name)
