"""One declared review-directed closure on actual saved work; no ancestor changes."""
import ast
import base64
from pathlib import Path
import bootstrap
import overlap_task as parent
import scoped_reports
from working_set_exp.current_job_view import render
from working_set_exp.jsonutil import sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

study = parent.study
ROOT = study.ROOT
HERE = Path(__file__).resolve().parent
INHERITED = parent.HERE / 'control/run-003'
TEST, DOC = parent.TEST, parent.DOC
TITLE = 'Exact overlap-assertion contract completion'
ACTOR, SEED = study.ACTOR, study.SEED


def checker(candidate):
    original, body = parent.checker(parent.Task('control', '003').inherited_candidate).split(b'\n', 1)
    config = ast.literal_eval(original.removeprefix(b'CONFIG = ').decode())
    config['unchanged'] = {p: sha256_bytes(v) for p, v in candidate.file_map.items() if p != TEST}
    # Preserve the actual saved document/library. New methods are still identified
    # against the original two late-registration methods, not the six incomplete ones.
    old = (parent.HERE / 'checker_extension.py').read_bytes()
    assert body.count(old) == 1
    independent = old.split(b'def new_actor_suite(', 1)[0]
    body = body.replace(old, independent + (HERE / 'coverage_extension.py').read_bytes(), 1)
    return b'CONFIG = ' + repr(config).encode() + b'\n' + body


def operating_reference():
    text = study.operating_reference()
    old = 'There are no injected faults in this task.'
    assert text.count(old) == 1
    return text.replace(old,
        'This checker also executes separate intentional resolver, exception-subclass and diagnostic faults. '
        'Failing those mutated executions is expected sensitivity evidence, not failure of the real candidate. '
        'Coverage is assessed at each observed raising site; a successful test run does not establish assertion strength.')


class Session(study.Session):
    assessment_api = scoped_reports

    @property
    def calls_used(self):
        return len(self.pairs)

    def view(self, **kwargs):
        return render(super().view(**kwargs), title=TITLE, pairs=self.pairs,
            boundary=self.starting_archive_length, submitted=self.submitted)


class Task(study.Task):
    def __init__(self, version='001'):
        super().__init__('dynamic', version, INHERITED)
        self.phase, self.AREA = 'contract_completion', HERE
        self.PACKAGE, self.RUN = HERE / f'preparation-{version}', HERE / f'run-{version}'
        self.MANIFEST = HERE / f'EXECUTION_MANIFEST-{version}.json'
        self.MAX_REQUESTS, self.MAX_OPERATIONS = self.INHERITED_REQUESTS + 12, self.INHERITED_OPERATIONS + 36
        self.OWNER_DIRECTION = 'Complete the verified assertion gaps on actual saved control work after prospective checker qualification.'

    def initial_session(self, folder=None, replay=False):
        candidate = self.inherited_candidate
        check = checker(candidate)
        session = Session(candidate, {'public': check}, (HERE / 'TASK.txt').read_text(encoding='utf-8'),
            edit_checks={}, call_limit=self.MAX_OPERATIONS, request_limit=self.MAX_REQUESTS,
            observations=ObservationStore((Path(folder) if folder else INHERITED) / 'observations', replay=replay or folder is None),
            check_contracts={'public': {'checker_sha256': sha256_bytes(check)}})
        study.restore_fields(session, self.inherited_state, candidate)
        session.request_limit, session.call_limit = self.MAX_REQUESTS, self.MAX_OPERATIONS
        session.starting_archive_length, session.submitted = self.INHERITED_OPERATIONS, False
        session.ranges, session.saved, session.delivered_sources = [], {}, []
        session.last, session.recovery, session.parked_source_regions = None, False, ()
        return session

    def implementation_identities(self):
        bound = study.read(INHERITED / 'RESPONSE_SEAL.json')['source_sha256']
        for name, digest in bound.items():
            assert sha256_file(ROOT / name) == digest, name
        paths = [*HERE.glob('*.py'), HERE/'SYSTEM.txt', HERE/'TASK.txt', HERE/'PLAN.md', HERE/'SPEC.md',
                 *sorted((HERE/'tests').glob('*.py')), INHERITED/'RESPONSE_SEAL.json']
        paths += [INHERITED/r['path'] for r in study.read(INHERITED/'RESPONSE_SEAL.json')['files']]
        for route in ('cpu-route-001', 'cpu-route-002'):
            paths += sorted(p for p in (HERE/route).rglob('*') if p.is_file())
        return {**bound, **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}

    source_identities = implementation_identities

    def __getattr__(self, name):
        if name in globals():
            return globals()[name]
        return super().__getattr__(name)


snapshot, read, candidate_bytes = study.snapshot, study.read, study.candidate_bytes
process_reply, present_receipts = study.process_reply, study.present_receipts
