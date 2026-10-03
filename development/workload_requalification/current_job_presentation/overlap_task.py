"""Matched actual saved entry; only normal model-facing status composition varies."""
import ast
import base64
import copy
from pathlib import Path
import sys

import bootstrap
import dispatch_task as study
from working_set_exp.current_job_view import render
from working_set_exp.observations import ObservationStore
from working_set_exp.jsonutil import sha256_bytes, sha256_file

HERE = Path(__file__).resolve().parent
INHERITED = study.AREA / 'documentation_continuation/run-001'
TITLE = 'Overlapping virtual-membership coverage'
ACTOR, SEED = study.ACTOR, study.SEED
DOC, TEST = 'Doc/howto/union-dispatch.rst', 'tests/test_virtual_registration.py'


def checker(candidate):
    original, body = study.checker('dynamic', candidate).split(b'\n', 1)
    config = ast.literal_eval(original.removeprefix(b'CONFIG = ').decode())
    config['unchanged'] = {p: sha256_bytes(v) for p, v in candidate.file_map.items()
                           if p not in (DOC, TEST)}
    config['saved_doc'] = base64.b64encode(candidate.file_map[DOC]).decode()
    config['saved_tests'] = base64.b64encode(candidate.file_map[TEST]).decode()
    # The registered original runner remains exact. Correct the same qualified
    # namespace boundary, then append independent execution criteria.
    old = b"doc, {'functools': library},"
    assert body.count(old) == 1
    body = body.replace(old, b"doc, {'functools': library, '__name__': '__main__'},", 1)
    old = b'    failures = [row[\'case\'] for row in rows if not row[\'passed\']]'
    assert body.count(old) == 1
    body = body.replace(old, b'    qualify_overlap(library, report)\n' + old, 1)
    marker = b"if __name__ == '__main__':\n    main()"
    assert body.count(marker) == 1
    extension = (HERE / 'checker_extension.py').read_bytes()
    body = body.replace(marker, extension + b'\n\n' + marker, 1)
    return b'CONFIG = ' + repr(config).encode() + b'\n' + body


class Session(study.Session):
    @property
    def calls_used(self): return len(self.pairs)

    def view(self, **kwargs):
        value = super().view(**kwargs)
        if self.condition == 'current_job':
            return render(value, title=TITLE, pairs=self.pairs,
                boundary=self.starting_archive_length, submitted=self.submitted)
        return value


class Task(study.Task):
    def __init__(self, condition='control', version='001'):
        assert condition in ('control', 'current_job')
        super().__init__('dynamic', version, INHERITED)
        self.condition, self.phase, self.AREA = condition, 'overlap', HERE
        self.PACKAGE = HERE / condition / f'preparation-{version}'
        self.RUN = HERE / condition / f'run-{version}'
        self.MANIFEST = HERE / condition / f'EXECUTION_MANIFEST-{version}.json'
        self.OWNER_DIRECTION = 'Proceed with one matched current-job presentation comparison on new saved-work coverage.'

    def initial_session(self, folder=None, replay=False):
        check = checker(self.inherited_candidate)
        session = Session(self.inherited_candidate, {'public': check},
            (HERE / 'TASK.txt').read_text(encoding='utf-8'), edit_checks={},
            call_limit=self.MAX_OPERATIONS, request_limit=self.MAX_REQUESTS,
            observations=ObservationStore((Path(folder) if folder else INHERITED) / 'observations',
                replay=replay or folder is None),
            check_contracts={'public': {'checker_sha256': sha256_bytes(check)}})
        session.condition = self.condition
        study.restore_fields(session, self.inherited_state, self.inherited_candidate)
        session.request_limit, session.call_limit = self.MAX_REQUESTS, self.MAX_OPERATIONS
        session.starting_archive_length = self.INHERITED_OPERATIONS
        session.submitted = False
        session.ranges, session.saved, session.delivered_sources = [], {}, []
        session.last = None
        session.recovery = False
        session.parked_source_regions = ()
        return session

    def implementation_identities(self):
        bound = study.read(INHERITED / 'RESPONSE_SEAL.json')['source_sha256']
        for name, digest in bound.items():
            assert sha256_file(study.ROOT / name) == digest, name
        paths = [*HERE.glob('*.py'), *HERE.glob('*.txt'), HERE/'PLAN.md', HERE/'SPEC.md',
                 *sorted((HERE/'tests').glob('*.py')),
                 study.ROOT/'src/working_set_exp/current_job_view.py',
                 INHERITED/'RESPONSE_SEAL.json']
        paths += [INHERITED/row['path'] for row in study.read(INHERITED/'RESPONSE_SEAL.json')['files']]
        return {**bound, **{p.relative_to(study.ROOT).as_posix(): sha256_file(p) for p in paths}}

    source_identities = implementation_identities
    def __getattr__(self, name):
        if name in globals(): return globals()[name]
        return super().__getattr__(name)


snapshot = study.snapshot
read = study.read
candidate_bytes = study.candidate_bytes
process_reply = study.process_reply
present_receipts = study.present_receipts
