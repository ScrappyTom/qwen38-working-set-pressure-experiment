"""Same task and final forms; corrected pinned thinking-channel transport only."""
import copy
from functools import lru_cache
from pathlib import Path

import live_task as prior
from working_set_exp.jsonutil import sha256_file
from working_set_exp.thinking_grammar import require_open_thinking, with_thinking

ROOT, AREA = prior.ROOT, Path(__file__).resolve().parent
ACTOR, SEED = prior.ACTOR, prior.SEED
MAX_REQUESTS, MAX_OPERATIONS = 16, 48
OWNER_DIRECTION = 'Complete the repairs and then rerun.'


@lru_cache(maxsize=1)
def response_constraints():
    return dict(grammar=with_thinking(prior.response_constraints()['grammar']))


def expected_native(request):
    assert request['grammar'] == response_constraints()['grammar'] and 'response_format' not in request
    old = copy.deepcopy(request)
    old['grammar'] = prior.response_constraints()['grammar']
    native = prior.expected_native(old)
    require_open_thinking(native)
    return native


def source_identities():
    own = [*AREA.glob('*.py'), AREA/'PLAN.md', AREA/'SPEC.md', AREA/'SYSTEM.txt',
           ROOT/'src/working_set_exp/thinking_grammar.py', ROOT/'tests/test_thinking_grammar.py']
    return {**prior.source_identities(), **{p.relative_to(ROOT).as_posix():sha256_file(p) for p in own}}


class Task(prior.Task):
    def __init__(self, version='001', replay_folder=None):
        super().__init__(version, replay_folder)
        self.PACKAGE, self.RUN = AREA/f'preparation-{version}', AREA/'run-001'
        self.MANIFEST = AREA/'EXECUTION_MANIFEST.json'

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(prior, name)


def __getattr__(name):
    return getattr(prior, name)
