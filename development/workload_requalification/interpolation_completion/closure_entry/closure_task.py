"""Thin closure of actual checked work; historical effects are never replayed."""
import copy
from functools import lru_cache
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parent
sys.path.insert(0, str(AREA.parent/'correction_entry'))
import correction_task as previous
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, OLD = previous.ROOT, previous.AREA/'run-001'
ACTOR, SEED = previous.ACTOR, previous.SEED
OWNER_DIRECTION = 'Proceed with the finite saved-result closure of the checked interpolation contribution.'


@lru_cache(maxsize=1)
def inherited_material():
    seal = previous.original.read(OLD/'RESPONSE_SEAL.json')
    assert seal['disposition'] == 'request_allowance_exhausted'
    assert (seal['cumulative_requests'], seal['cumulative_operations']) == (80, 187)
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    for row in seal['files']:
        path = OLD/row['path']
        assert path.resolve().is_relative_to(OLD.resolve())
        raw = path.read_bytes()
        assert len(raw) == row['size_bytes'] and sha256_bytes(raw) == row['sha256'], row['path']
    state = previous.original.read(OLD/'final-state.json')
    candidate = previous.original.candidate_from_snapshot(previous.original.read(OLD/'final-candidate.json'))
    assert candidate.candidate_id == '83b7ac8d45e17af6d906928ee51c40dc77e9507285c6fc23de0c389de4b51603'
    assert len(state['pairs']) == 187 and state['requests_used'] == 80
    assert state['last']['sequence'] == 187 and state['last']['result']['passed']
    assert state['last']['result']['checked_candidate_id'] == candidate.candidate_id
    assert not state['submitted'] and not state['delivery_blocked']
    return state, candidate


class Task(previous.Task):
    def __init__(self, version='001'):
        super().__init__('001')
        self.phase, self.version, self.AREA, self.inherited = 'interpolation_closure', version, AREA, OLD
        self.PACKAGE, self.RUN = AREA/f'preparation-{version}', AREA/f'run-{version}'
        self.MANIFEST = AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.inherited_state, self.inherited_candidate = inherited_material()
        self.INHERITED_REQUESTS, self.INHERITED_OPERATIONS = 80, 187
        self.MAX_REQUESTS, self.MAX_OPERATIONS = 82, 191

    def initial_session(self, folder=None, replay=False):
        old = previous.Task('001')
        session = old.restore(self.inherited_state, self.inherited_candidate, OLD, replay=True)
        assert canonical_json_bytes(previous.original.snapshot(session)) == (OLD/'final-state.json').read_bytes()
        session.request_limit, session.call_limit = self.MAX_REQUESTS, self.MAX_OPERATIONS
        session.starting_archive_length = self.INHERITED_OPERATIONS
        session.task = (AREA/'TASK.txt').read_text(encoding='utf-8')
        session.observations = ObservationStore((Path(folder) if folder else OLD)/'observations',
                                                replay=replay or folder is None)
        return session

    def initial_preceding_feedback(self):
        return copy.deepcopy(previous.original.read(OLD/'final-preceding-feedback.json'))

    def implementation_identities(self):
        old_task = previous.Task('001')
        paths = [*AREA.glob('*.py'), *AREA.glob('*.txt'), AREA/'PLAN.md', AREA/'SPEC.md',
                 *sorted((AREA/'tests').glob('*.py')), OLD/'RESPONSE_SEAL.json']
        paths += [OLD/r['path'] for r in previous.original.read(OLD/'RESPONSE_SEAL.json')['files']]
        # Reused native decoder evidence is exact and separately identified.
        paths += [old_task.PACKAGE/'SEAL.json', old_task.PACKAGE/'QUALIFICATION.json',
                  old_task.PACKAGE/'initial-wire-request.json']
        paths += [old_task.PACKAGE/r['path'] for r in previous.original.read(old_task.PACKAGE/'SEAL.json')['files']
                  if r['path'].startswith('native-forms/')]
        return {**old_task.source_identities(), **{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}

    source_identities = implementation_identities

    def __getattr__(self, name):
        return globals()[name] if name in globals() else super().__getattr__(name)
