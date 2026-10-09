"""Resume the exact partial code contribution with one corrected checker."""
from functools import lru_cache
from pathlib import Path

import bootstrap
import write_task as previous
import corrected_checker
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.custody import verify_records

ROOT, AREA = previous.ROOT, Path(__file__).resolve().parent
OLD = previous.AREA/'run-002'
ACTOR, SEED = dict(previous.ACTOR), previous.SEED
MAX_REQUESTS, MAX_OPERATIONS = previous.MAX_REQUESTS, previous.MAX_OPERATIONS
INHERITED_REQUESTS, INHERITED_OPERATIONS = 9, 12
STARTING_ID = 'f8c299f79fa9b605b5b0540de3f16adf67b54b784fcececab94f21744d1d9cc3'
OWNER_DIRECTION = 'Continue substantive coding from the saved partial edit, with the corrected checker and original remaining allowance; no live coaching.'
INHERITED_HASHES = {
    'RESPONSE_SEAL.json': 'a535e1b3f6beaad94d4d3e83a24642eddc9ca301b51183e24e0b62281cc7e3ee',
    'final-state.json': 'e2214357b29702de1749416a515eff28b90235654b6de08af8c9e5d1085e3445',
    'final-candidate.json': '3b33d41c8d88657ea2d076880915a9db3450edd0956e5299a3bbd8106ef83e6c',
    'final-preceding-feedback.json': '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945',
}


@lru_cache(maxsize=1)
def validate_inherited():
    for name, digest in INHERITED_HASHES.items():
        assert sha256_file(OLD/name) == digest, name
    seal = previous.read(OLD/'RESPONSE_SEAL.json')
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    for row in seal['files']:
        path = (OLD/row['path']).resolve()
        assert path.is_relative_to(OLD.resolve())
        assert path.stat().st_size == row['size_bytes'] and sha256_file(path) == row['sha256']
    for name, digest in seal['private_runtime_files_local_only'].items():
        assert sha256_file(OLD/'private-runtime'/name) == digest
    assert len(verify_records(OLD/'records.jsonl', OLD)) == seal['record_count']
    assert seal['disposition'] == 'operator_stopped' and seal['port_free']
    assert (seal['cumulative_requests'], seal['cumulative_operations']) == (9, 12)
    previous.verify_sources(seal['source_sha256'])
    assert previous.read(OLD/'final-preceding-feedback.json') == []
    proof = previous.read(previous.AREA/'review/VERIFICATION-002.json')
    assert proof['status'] == 'replayed_exactly' and proof['final_candidate_id'] == STARTING_ID
    return seal


class Task:
    phase = 'write_safety_corrected_checker_continuation'

    def __init__(self, version='001', replay_folder=None):
        assert len(version) == 3 and version.isdecimal()
        self.AREA = AREA
        self.PACKAGE, self.RUN = AREA/f'preparation-{version}', AREA/f'run-{version}'
        self.MANIFEST = AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.replay_folder = Path(replay_folder) if replay_folder else None

    def restore(self, state, candidate, replay_folder=None, replay=False):
        folder = replay_folder or self.replay_folder or self.PACKAGE/'unexecuted'
        session = previous.Task('002').restore(state, candidate, folder,
            replay=replay or self.replay_folder is not None)
        code = corrected_checker.checker()
        session.checkers = {'public': code}
        session.checker = code
        session.check_contracts = {'public': {'checker_sha256': sha256_bytes(code)}}
        assert canonical_json_bytes(previous.snapshot(session)) == canonical_json_bytes(state)
        return session

    def initial_session(self, folder=None, replay=False):
        validate_inherited()
        state = previous.read(OLD/'final-state.json')
        session = self.restore(state, previous.read(OLD/'final-candidate.json'), folder, replay)
        assert session.candidate.candidate_id == STARTING_ID
        assert (session.requests_used, session.calls_used) == (9, 12)
        assert not session.submitted
        assert not any(p['response']['action'] == 'check' for p in session.pairs)
        return session

    def implementation_identities(self):
        validate_inherited()
        paths = [*AREA.glob('*.py'), *AREA.glob('*.txt'), AREA/'PLAN.md', AREA/'SPEC.md',
                 *sorted((AREA/'tests').glob('*.py')),
                 *(OLD/name for name in INHERITED_HASHES),
                 previous.AREA/'review/VERIFICATION-002.json',
                 AREA/'cpu-qualification-001/RESULTS.json']
        return {**previous.Task('002').source_identities(),
                **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}

    source_identities = implementation_identities
    attach_observations = staticmethod(previous.attach_observations)

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(previous, name)


def __getattr__(name):
    return getattr(previous, name)
