"""Scoped review-directed documentation job; preserve both frozen ancestors."""
import argparse
import ast
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap
import dispatch_task as study
import run_dispatch as execution
sys.path.insert(0, str(study.AREA / 'dynamic'))
from run_saved_dispatch import Session
import qualification_documentation
from working_set_exp.jsonutil import sha256_bytes, sha256_file

HERE = Path(__file__).resolve().parent
DOC = 'Doc/howto/union-dispatch.rst'


def checker(candidate):
    # Derive a successor without changing a byte of either bound checker.
    config_line, body = study.checker('dynamic', candidate).split(b'\n', 1)
    config = ast.literal_eval(config_line.removeprefix(b'CONFIG = ').decode())
    config['unchanged'] = {p: sha256_bytes(v) for p, v in candidate.file_map.items()
                           if p != DOC}
    old = b"doc, {'functools': library},"
    new = b"doc, {'functools': library, '__name__': '__main__'},"
    assert body.count(old) == 1, 'Expected namespace boundary changed'
    body = body.replace(old, new, 1)
    old = b"'Added interactive examples execute; prose still requires direct review.',"
    new = b"'Added interactive examples execute in __main__; prose still requires direct review.',"
    assert body.count(old) == 1, 'Expected observation description changed'
    body = body.replace(old, new, 1)
    old = b"failed=result.failed, attempted=result.attempted, runner_output=stream.getvalue())"
    new = b"namespace='__main__', failed=result.failed, attempted=result.attempted, runner_output=stream.getvalue())"
    assert body.count(old) == 1, 'Expected observation context changed'
    return b'CONFIG = ' + repr(config).encode() + b'\n' + body.replace(old, new, 1)


class Task(study.Task):
    def __init__(self, version='001'):
        super().__init__('dynamic', version, study.AREA / 'dynamic/run-001')
        self.phase = 'documentation'
        self.PACKAGE, self.RUN = HERE / f'preparation-{version}', HERE / f'run-{version}'
        self.MANIFEST = HERE / f'EXECUTION_MANIFEST-{version}.json'
        self.MAX_REQUESTS = self.INHERITED_REQUESTS + 12
        self.MAX_OPERATIONS = self.INHERITED_OPERATIONS + 36
        self.OWNER_DIRECTION = ('Proceed with the published, review-directed documentation '
                                'correction; preserve code/tests and both original studies.')

    def initial_session(self, folder=None, replay=False):
        candidate = self.inherited_candidate
        check = checker(candidate)
        session = Session(candidate, {'public': check},
            (HERE / 'TASK.txt').read_text(encoding='utf-8'), edit_checks={},
            call_limit=self.MAX_OPERATIONS, request_limit=self.MAX_REQUESTS,
            observations=study.ObservationStore(
                (Path(folder) if folder else self.inherited) / 'observations',
                replay=replay or folder is None),
            check_contracts={'public': {'checker_sha256': sha256_bytes(check)}})
        study.restore_fields(session, self.inherited_state, candidate)
        session.request_limit, session.call_limit = self.MAX_REQUESTS, self.MAX_OPERATIONS
        session.starting_archive_length = self.INHERITED_OPERATIONS
        session.submitted = False
        session.ranges, session.saved, session.delivered_sources = [], {}, []
        session.last = None
        session.recovery = False
        session.parked_source_regions = ()
        return session

    def implementation_identities(self):
        inherited = study.read(self.inherited / 'RESPONSE_SEAL.json')['source_sha256']
        for name, digest in inherited.items():
            assert sha256_file(study.ROOT / name) == digest, name
        extra = [HERE / n for n in ('run_documentation.py', 'qualification_documentation.py',
                                    'reference_documentation.py', 'TASK.txt', 'PLAN.md',
                                    'tests/test_documentation_transition.py')]
        extra += sorted(p for p in (HERE / 'cpu-route-001').rglob('*') if p.is_file())
        return {**inherited, **super().implementation_identities(),
                **{p.relative_to(study.ROOT).as_posix(): sha256_file(p) for p in extra}}

    source_identities = implementation_identities


class Loop(execution.Loop):
    def execute(self, session):
        assert self.sent == session.requests_used == self.task.INHERITED_REQUESTS
        assert session.calls_used == self.task.INHERITED_OPERATIONS
        self.log.append('job_accounting', dict(phase=self.task.phase,
            inherited_requests=self.sent, inherited_operations=session.calls_used,
            additional_request_limit=self.task.MAX_REQUESTS - self.sent,
            additional_operation_limit=self.task.MAX_OPERATIONS - session.calls_used), [])
        return execution.OriginalLoop.execute(self, session)


def cpu_qualification(module):
    folder = HERE / 'cpu-route-001'
    folder.mkdir(exist_ok=False)
    store = execution.ArtifactStore(folder)
    log = execution.legacy.QualificationLog(folder / 'records.jsonl',
                                           'documentation-cpu-route', task_module=module)
    result = qualification_documentation.qualify(module,
        SimpleNamespace(measure=lambda view: 0, log=log),
        SimpleNamespace(preceding_feedback=[]), store, folder)
    result.update(token_callback='zero; not input-fit qualification', completion_requests=0)
    study.save(folder, 'QUALIFICATION.json', result)
    print(json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('cpu', 'prepare', 'run'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    module = Task(args.version)
    if args.mode == 'cpu':
        cpu_qualification(module)
        return
    execution.Loop = execution.runner.Loop = Loop
    execution.qualification_route = qualification_documentation
    (execution.prepare if args.mode == 'prepare' else execution.run_once)(module)


if __name__ == '__main__': main()
