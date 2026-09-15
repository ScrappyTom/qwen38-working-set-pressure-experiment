"""One owner-authorized same-task attempt on the qualified decision host."""
from pathlib import Path

import decision_task as parent
from working_set_exp.jsonutil import sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = parent.ROOT, Path(__file__).resolve().parent
MAX_REQUESTS, MAX_OPERATIONS = 16, 48
ACTOR, SEED = parent.ACTOR, parent.SEED
OWNER_DIRECTION = 'Run qwen on same task with revised host'


def source_identities():
    paths=[*AREA.glob('*.py'),AREA/'SPEC.md',AREA/'SYSTEM.txt',
           parent.OLD/'starting-state.json',parent.OLD/'starting-candidate.json',
           parent.OLD/'RESPONSE_SEAL.json',parent.AREA/'qualification-003/SEAL.json',
           parent.AREA/'native-003/SEAL.json']
    return {**parent.source_identities(),**{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}


class Task:
    def __init__(self, version='001', replay_folder=None):
        self.PACKAGE=AREA/f'preparation-{version}'
        self.RUN,self.MANIFEST=AREA/'run-001',AREA/'EXECUTION_MANIFEST.json'
        self.replay_folder=replay_folder

    def initial_session(self):
        s=parent.from_checkpoint('starting')
        assert len(s.pairs)==5 and s.working_account() is None and not s.submitted
        assert s.candidate.candidate_id=='2921cbc8a115c86871a11f8eaea929c3d48a8e4d2bb2ca03bf48971c36cf15cd'
        assert s.recovery and not s.recovery_focus and not s.delivered_sources
        if self.replay_folder:
            s.observations=ObservationStore(self.replay_folder/'observations',replay=True)
        return s

    def __getattr__(self,name):
        return globals()[name] if name in globals() else getattr(parent,name)


def __getattr__(name):
    return getattr(parent,name)
