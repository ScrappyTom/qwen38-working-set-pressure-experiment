"""Read-only restoration of the completed coding run for offline qualification."""
import copy
import json
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
sys.path[:0] = [str(AREA), str(AREA.parent/'configparser_write_safety_continuation')]
import continuation_task as previous
import recovery_navigation
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file

RUN = previous.AREA/'run-001'
SEAL_SHA256 = '060fd2261e8d87b8c684c68d72a8ce2085df1aaf6023402292321d765d7a70b7'


class Session(recovery_navigation.RecoveryNavigationMixin, previous.previous.Session):
    pass


def read(path):
    return json.loads(path.read_bytes())


def restored(stem='C23-O01', *, projected=True):
    assert sha256_file(RUN/'RESPONSE_SEAL.json') == SEAL_SHA256
    seal = read(RUN/'RESPONSE_SEAL.json')
    inventory = {row['path']: row for row in seal['files']}
    paths = [f'after/{stem}-state.json', f'after/{stem}-candidate.json']
    for path in paths:
        assert sha256_file(RUN/path) == inventory[path]['sha256']
    state, candidate = (read(RUN/path) for path in paths)
    session = previous.Task('001').restore(state, candidate, RUN, replay=True)
    before = canonical_json_bytes(previous.snapshot(session))
    if projected:
        session.__class__ = Session  # Explicit prospective presentation, never an old-run replay.
    assert canonical_json_bytes(previous.snapshot(session)) == before
    return session


def snapshot(session):
    return copy.deepcopy(previous.snapshot(session))
