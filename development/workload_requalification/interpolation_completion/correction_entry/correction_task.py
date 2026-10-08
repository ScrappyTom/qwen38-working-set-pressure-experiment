"""Thin saved-work successor; no reset, reference repair or consultation input."""
import copy
from functools import lru_cache
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parent
sys.path.insert(0, str(AREA.parent))
import qualified_task
import completion_task as original
sys.path.insert(0, str(AREA.parent/'correction_context'))
from correction_context import CorrectionContextMixin
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, OLD = original.ROOT, AREA.parent/'run-002'
ACTOR, SEED = original.ACTOR, original.SEED
TEST, DOC = original.TEST, original.DOC
OWNER_DIRECTION = 'Proceed with one finite uncoached correction from actual saved interpolation failure, preserving C64 and adopting the qualified correction view.'


@lru_cache(maxsize=1)
def inherited_material():
    seal = original.read(OLD/'RESPONSE_SEAL.json')
    assert seal['disposition'] == 'request_allowance_exhausted'
    assert seal['cumulative_requests'] == 64 and seal['cumulative_operations'] == 152
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    for row in seal['files']:
        raw = (OLD/row['path']).read_bytes()
        assert len(raw) == row['size_bytes'] and sha256_bytes(raw) == row['sha256'], row['path']
    state = original.read(OLD/'final-state.json')
    candidate = original.candidate_from_snapshot(original.read(OLD/'final-candidate.json'))
    assert candidate.candidate_id == '90a025e9c7c79ffc06b720fa7f1522d61cb2963662d91acf904ead7f7f204229'
    assert len(state['pairs']) == 152 and state['requests_used'] == 64
    assert state['pairs'][-1]['response'] == dict(action='read', path=TEST, start_line=2200, end_line=2360)
    return state, candidate


def operating_reference():
    return original.operating_reference() + '\n\n' + (
        'In recovery presentation, after an accepted edit or its immediately following check, '
        'the host attempts to show the whole recorded current replacement region beside the '
        'admitted feedback and existing inspection. This does not remove other selected designations '
        'or infer a correction. If the complete input cannot fit that region, the existing truthful '
        'recovery view remains. Actual current source in working_set.sources supplies editing '
        'authority; an omitted region or recorded diff does not.')


class Session(CorrectionContextMixin, original.Session):
    pass


class Task(qualified_task.Task):
    def __init__(self, version='001'):
        super().__init__('002')
        self.phase, self.version, self.AREA, self.inherited = 'interpolation_correction', version, AREA, OLD
        self.PACKAGE, self.RUN = AREA/f'preparation-{version}', AREA/f'run-{version}'
        self.MANIFEST = AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.inherited_state, self.inherited_candidate = inherited_material()
        self.INHERITED_REQUESTS, self.INHERITED_OPERATIONS = 64, 152
        self.MAX_REQUESTS, self.MAX_OPERATIONS = 80, 200

    def initial_session(self, folder=None, replay=False):
        # Establish the old checkpoint using its own typed restoration contract
        # before applying this declared job's boundary and opportunity.
        previous = qualified_task.Task('002')
        session = previous.restore(self.inherited_state, self.inherited_candidate, OLD, replay=True)
        assert canonical_json_bytes(original.snapshot(session)) == (OLD/'final-state.json').read_bytes()
        session.__class__ = Session
        session.request_limit, session.call_limit = self.MAX_REQUESTS, self.MAX_OPERATIONS
        session.starting_archive_length = self.INHERITED_OPERATIONS
        session.task = (AREA/'TASK.txt').read_text(encoding='utf-8')
        session.observations = ObservationStore((Path(folder) if folder else OLD)/'observations',
                                                replay=replay or folder is None)
        assert not session.submitted and not session.delivery_blocked
        return session

    def initial_preceding_feedback(self):
        return copy.deepcopy(original.read(OLD/'final-preceding-feedback.json'))

    def restore(self, state, candidate, replay_folder=None, replay=False):
        # Reuse the typed address rule, covering both accepted edit forms. This
        # lineage's earlier receipts predate applied_diff and stay inherited.
        value, restored = state['diffs'], {}
        if not isinstance(value, dict):
            raise ValueError('checkpoint diff map is not an address map')
        for key, diff in value.items():
            if type(key) is int:
                number = key
            elif type(key) is str and key.isascii() and key.isdecimal() and str(int(key)) == key:
                number = int(key)
            else:
                raise ValueError('checkpoint diff address is not canonical')
            if number <= 0 or number in restored or type(diff) is not str:
                raise ValueError('checkpoint diff address or value differs')
            restored[number] = diff
        expected = {int(k): v for k, v in self.inherited_state['diffs'].items()}
        for number, pair in enumerate(state['pairs'], 1):
            if number <= self.INHERITED_OPERATIONS:
                continue
            if pair['response'].get('action') in ('patch', 'replace_region') and pair['result'].get('accepted'):
                diff = pair['result'].get('applied_diff')
                if type(diff) is not str:
                    raise ValueError('accepted edit lacks its exact recorded diff')
                expected[number] = diff
        if restored != expected:
            raise ValueError('checkpoint diff map differs from accepted edit history')
        return original.Task.restore(self, {**state, 'diffs': restored}, candidate, replay_folder, replay)

    def implementation_identities(self):
        paths = [*AREA.glob('*.py'), *AREA.glob('*.txt'), AREA/'PLAN.md', AREA/'SPEC.md',
                 *sorted((AREA/'tests').glob('*.py')),
                 AREA.parent/'correction_context/correction_context.py', OLD/'RESPONSE_SEAL.json']
        paths += [OLD/r['path'] for r in original.read(OLD/'RESPONSE_SEAL.json')['files']]
        return {**qualified_task.Task('002').source_identities(),
                **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}

    source_identities = implementation_identities

    def __getattr__(self, name):
        return globals()[name] if name in globals() else super().__getattr__(name)
