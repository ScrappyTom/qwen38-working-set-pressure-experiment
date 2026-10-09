"""New implementation work on exact saved code using the existing coding host."""
import copy
from functools import lru_cache
import importlib.util
from pathlib import Path

import bootstrap
import dispatch_task as common
import material
import operational_reply
import qualify_cpu
import write_reports
from working_set_exp.candidate import Candidate
from working_set_exp.current_job_view import render
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.thinking_grammar import with_thinking

ROOT, AREA = material.ROOT, material.AREA
ACTOR, SEED = dict(common.ACTOR), 314159
MAX_REQUESTS, MAX_OPERATIONS, FILE_LIMIT = 40, 120, 1_048_576
STARTING_ID = '4be95d88223269e05bbb366cad6169872d74b8a82a14f2622bf8a4cffd8e96da'
DESCRIPTIONS = {'public': 'Run preserved parser tests, independent write-safety cases, current new tests and unsafe-baseline sensitivity. Required for submission; prose needs direct review.'}
REQUIRED_INSPECTION_PATHS = (material.LIBRARY, material.NEW_TESTS, material.DOC)
OWNER_DIRECTION = 'Prioritize substantive coding: extend the saved parser, add meaningful regressions, preserve earlier work, and report the complete contribution.'


class Session(common.Session):
    assessment_api = write_reports

    def reply_schema(self):
        return reply_schema()

    def view(self, **kwargs):
        return render(super().view(**kwargs), title='Configparser write safety',
                      pairs=self.pairs, boundary=0, submitted=self.submitted)


def reply_schema():
    return operational_reply.reply_schema(DESCRIPTIONS)


def decode_reply(content):
    return operational_reply.decode_reply(content, DESCRIPTIONS)


def operating_reference():
    return common.operating_reference()


@lru_cache(maxsize=1)
def response_constraints():
    path = ROOT/'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    assert sha256_file(path) == 'ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
    spec = importlib.util.spec_from_file_location('write_safety_schema_converter', path)
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    return {'grammar': with_thinking(operational_reply.reply_grammar(DESCRIPTIONS, converter.SchemaConverter))}


def expected_native(request):
    assert request['grammar'] == response_constraints()['grammar'] and request['seed'] == SEED
    old = copy.deepcopy(request)
    old['grammar'] = common.response_constraints()['grammar']
    return common.expected_native(old)


def snapshot(session):
    value = common.snapshot(session)
    # JSON object addresses must sort identically before and after restoration.
    value['diffs'] = {str(k): v for k, v in value['diffs'].items()}
    return value


def candidate_from_snapshot(value):
    candidate = Candidate.create({r['path']: r['content_utf8'].encode() for r in value['files']},
                                 max_file_bytes=FILE_LIMIT)
    assert common.candidate_bytes(candidate) == canonical_json_bytes(value)
    assert set(candidate.file_map) == set(material.starting_files())
    return candidate


class Task:
    INHERITED_REQUESTS = INHERITED_OPERATIONS = 0
    phase = 'write_safety'

    def __init__(self, version='001', replay_folder=None):
        assert len(version) == 3 and version.isdecimal()
        self.AREA = AREA
        self.PACKAGE, self.RUN = AREA/f'preparation-{version}', AREA/f'run-{version}'
        self.MANIFEST = AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.replay_folder = Path(replay_folder) if replay_folder else None

    def initial_session(self, folder=None, replay=False):
        baseline = Candidate.create(material.baseline_files(), max_file_bytes=FILE_LIMIT)
        assert baseline.candidate_id == material.BASELINE_ID
        candidate = Candidate.create(material.starting_files(), max_file_bytes=FILE_LIMIT)
        assert candidate.candidate_id == STARTING_ID
        code = qualify_cpu.checker()
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
        assert len({v.candidate_id for v in versions}) == len(versions)
        assert session.candidate.candidate_id in {v.candidate_id for v in versions}
        for key, value in state.items():
            if key not in ('candidate_id', 'source_versions'):
                setattr(session, key, copy.deepcopy(value))
        session.candidate = candidate
        session.versions = {v.candidate_id: v for v in versions}
        assert candidate.candidate_id in session.versions
        expected = {str(i): p['result']['applied_diff'] for i, p in enumerate(session.pairs, 1)
                    if p['response']['action'] in ('patch', 'replace_region') and p['result'].get('accepted')}
        assert session.diffs == expected
        session.diffs = {int(k): v for k, v in expected.items()}
        session.restored_control_fields = tuple(session.restored_control_fields)
        session.parked_source_regions = tuple(tuple(row) for row in session.parked_source_regions)
        assert canonical_json_bytes(snapshot(session)) == canonical_json_bytes(state)
        return session

    def implementation_identities(self):
        proof = read(AREA/'cpu-qualification-002/RESULTS.json')
        assert proof['status'] == 'qualified_cpu_only' and proof['completion_requests'] == 0
        for name, digest in proof['sources'].items():
            assert sha256_file(AREA/name) == digest, name
        helpers = ('dispatch_continuity/run_dispatch.py',
            'dispatch_continuity/bootstrap.py', 'configparser_operational/bootstrap.py',
            'navigation_continuity/navigation.py', 'search_continuity/search_navigation.py',
            'ecological_import_entry/native_forms.py', 'action_lifecycle/native_forms.py')
        paths = [*AREA.glob('*.py'), *AREA.glob('*.txt'), AREA/'PLAN.md', AREA/'SPEC.md',
            *sorted((AREA/'tests').glob('*.py')), material.BASELINE,
            AREA.parent/'documentation_followup/run-001/RESPONSE_SEAL.json',
            Path(common.__file__), Path(operational_reply.__file__), Path(write_reports.previous.__file__),
            *sorted(p for p in (AREA/'upstream').rglob('*') if p.is_file()),
            AREA/'cpu-qualification-002/RESULTS.json',
            *sorted(p for p in (AREA/'cpu-route-002').rglob('*') if p.is_file()),
            *(AREA.parent / name for name in helpers)]
        return {**common.host.source_identities(),
                **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}

    source_identities = implementation_identities
    attach_observations = staticmethod(common.attach_observations)

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(common, name)


process_reply, candidate_bytes = common.process_reply, common.candidate_bytes
present_receipts, read = common.present_receipts, common.read


def __getattr__(name):
    return getattr(common, name)
