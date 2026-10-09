"""Fresh coding task on saved work; existing execution and recovery machinery."""
import copy
from functools import lru_cache
import importlib.util
from pathlib import Path

import bootstrap
import write_task as previous
import operational_reply
import recovery_navigation
import unnamed_cpu
import unnamed_material as material
import unnamed_reports
from working_set_exp.candidate import Candidate
from working_set_exp.current_job_view import render
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.thinking_grammar import with_thinking

ROOT, AREA = material.ROOT, material.AREA
ACTOR, SEED = dict(previous.ACTOR), previous.SEED
MAX_REQUESTS, MAX_OPERATIONS, FILE_LIMIT = 40, 120, previous.FILE_LIMIT
STARTING_ID = Candidate.create(material.starting_files(), max_file_bytes=FILE_LIMIT).candidate_id
OWNER_DIRECTION = 'Continue substantive coding: add unnamed sections to saved parser work; no live coaching, reset or retry.'
DESCRIPTIONS = {'public': 'Run preserved parser/write-safety suites, independent unnamed-section integration, current authored tests and missing-feature baseline comparison. Required for submission; prose/examples need independent review.'}
REQUIRED_INSPECTION_PATHS = (material.LIBRARY, material.NEW_TESTS, material.DOC)


class Session(recovery_navigation.RecoveryNavigationMixin, previous.common.Session):
    assessment_api = unnamed_reports

    def reply_schema(self):
        return reply_schema()

    def view(self, **kwargs):
        return render(super().view(**kwargs), title='Configparser unnamed sections',
            pairs=self.pairs, boundary=0, submitted=self.submitted)


def reply_schema():
    return operational_reply.reply_schema(DESCRIPTIONS)


def decode_reply(content):
    return operational_reply.decode_reply(content, DESCRIPTIONS)


def operating_reference():
    text = previous.operating_reference()
    old = 'Older-implementation failure satisfies the sensitivity criterion; it is not a current-candidate failure.'
    assert text.count(old) == 1
    return text.replace(old, 'Failure or error on the saved library without this feature is expected comparison detection, '
        'not current-candidate failure. Missing-API errors alone do not establish assertion quality; '
        'test semantics and behavioral sensitivity receive separate review.')


@lru_cache(maxsize=1)
def response_constraints():
    path = ROOT/'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    assert sha256_file(path) == 'ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
    spec = importlib.util.spec_from_file_location('unnamed_schema_converter', path)
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    return {'grammar': with_thinking(operational_reply.reply_grammar(DESCRIPTIONS, converter.SchemaConverter))}


def expected_native(request):
    assert request['grammar'] == response_constraints()['grammar'] and request['seed'] == SEED
    value = copy.deepcopy(request)
    value['grammar'] = previous.response_constraints()['grammar']
    return previous.expected_native(value)


snapshot = previous.snapshot


def candidate_from_snapshot(value):
    candidate = Candidate.create({row['path']: row['content_utf8'].encode() for row in value['files']},
                                 max_file_bytes=FILE_LIMIT)
    assert previous.candidate_bytes(candidate) == canonical_json_bytes(value)
    assert set(candidate.file_map) == set(material.starting_files())
    return candidate


class Task:
    INHERITED_REQUESTS = INHERITED_OPERATIONS = 0
    phase = 'unnamed_sections'

    def __init__(self, version='001', replay_folder=None):
        assert len(version) == 3 and version.isdecimal()
        self.AREA = AREA
        self.PACKAGE, self.RUN = AREA/f'preparation-{version}', AREA/f'run-{version}'
        self.MANIFEST = AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.replay_folder = Path(replay_folder) if replay_folder else None

    def initial_session(self, folder=None, replay=False):
        candidate = Candidate.create(material.starting_files(), max_file_bytes=FILE_LIMIT)
        assert candidate.candidate_id == STARTING_ID
        code = unnamed_cpu.checker()
        return Session(candidate, {'public': code}, (AREA/'TASK.txt').read_text(encoding='utf-8'),
            edit_checks={}, call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
            observations=ObservationStore((Path(folder) if folder else self.replay_folder or
                self.PACKAGE/'unexecuted')/'observations', replay=replay or self.replay_folder is not None),
            check_contracts={'public': {'checker_sha256': sha256_bytes(code)}})

    def restore(self, state, candidate, replay_folder=None, replay=False):
        if not isinstance(candidate, Candidate):
            candidate = candidate_from_snapshot(candidate)
        session = self.initial_session(replay_folder, replay)
        assert set(state) == set(snapshot(session)) and state['candidate_id'] == candidate.candidate_id
        assert (state['request_limit'], state['call_limit']) == (MAX_REQUESTS, MAX_OPERATIONS)
        versions = [candidate_from_snapshot(value) for value in state['source_versions']]
        assert len({value.candidate_id for value in versions}) == len(versions)
        assert STARTING_ID in {value.candidate_id for value in versions}
        for key, value in state.items():
            if key not in ('candidate_id', 'source_versions'):
                setattr(session, key, copy.deepcopy(value))
        session.candidate = candidate
        session.versions = {value.candidate_id: value for value in versions}
        assert candidate.candidate_id in session.versions
        expected = {str(i): pair['result']['applied_diff'] for i, pair in enumerate(session.pairs, 1)
                    if pair['response']['action'] in ('patch', 'replace_region') and pair['result'].get('accepted')}
        assert session.diffs == expected
        session.diffs = {int(k): v for k, v in expected.items()}
        session.restored_control_fields = tuple(session.restored_control_fields)
        session.parked_source_regions = tuple(tuple(row) for row in session.parked_source_regions)
        assert canonical_json_bytes(snapshot(session)) == canonical_json_bytes(state)
        return session

    def implementation_identities(self):
        proof = read(AREA/'cpu-qualification-001/RESULTS.json')
        assert proof['status'] == 'qualified_cpu_only'
        for name, digest in proof['sources'].items():
            assert sha256_file(AREA/name) == digest, name
        recovered = AREA.parent/'recovery_navigation'
        assert read(recovered/'VERIFICATION-001.json')['status'] == 'replayed_exactly'
        paths = [*AREA.glob('*.py'), *AREA.glob('*.txt'), AREA/'PLAN.md', AREA/'SPEC.md',
            *sorted((AREA/'tests').glob('*.py')), material.BASELINE,
            material.PARENT/'run-001/RESPONSE_SEAL.json', material.PARENT/'review/001/SAVED-WORK.json',
            AREA/'cpu-qualification-001/RESULTS.json',
            recovered/'recovery_navigation.py', recovered/'VERIFICATION-001.json',
            recovered/'native-qualification-001/SEAL.json',
            Path(unnamed_cpu.corrected_checker.__file__)]
        return {**previous.Task('002').source_identities(),
                **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}

    source_identities = implementation_identities
    attach_observations = staticmethod(previous.attach_observations)

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(previous, name)


process_reply, candidate_bytes, present_receipts, read = (
    previous.process_reply, previous.candidate_bytes, previous.present_receipts, previous.read)


def __getattr__(name):
    return getattr(previous, name)
