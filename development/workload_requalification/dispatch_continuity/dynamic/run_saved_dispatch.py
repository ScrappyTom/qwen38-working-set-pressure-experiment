"""Actual saved-work entry; reuse the host, task text and monitored runner."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap
import dispatch_task as study
import run_dispatch as execution
import qualification_saved
from working_set_exp.jsonutil import sha256_file

HERE = Path(__file__).resolve().parent


class Session(study.Session):
    @property
    def calls_used(self):
        # This runner and task use cumulative limits. History scope is separate
        # from counting the actually archived operations against those limits.
        return len(self.pairs)


class Task(study.Task):
    def initial_session(self, folder=None, replay=False):
        session = super().initial_session(folder, replay)
        assert self.phase == 'dynamic' and self.inherited is not None
        session.__class__ = Session
        # The archived acts stay exact; their relationship to this new job is
        # derived from its explicitly restored starting boundary.
        session.starting_archive_length = self.INHERITED_OPERATIONS
        return session

    def implementation_identities(self):
        extra = [HERE/'run_saved_dispatch.py', HERE/'qualification_saved.py',
                 HERE/'tests/test_saved_transition.py', HERE/'ENTRY_PLAN.md']
        extra += sorted(p for p in (HERE/'cpu-route-001').rglob('*') if p.is_file())
        return {**super().implementation_identities(),
                **{p.relative_to(study.ROOT).as_posix():sha256_file(p) for p in extra}}

    source_identities = implementation_identities


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare', 'run'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    module = Task('dynamic', args.version, study.AREA/'union/run-002')
    execution.qualification_route = qualification_saved
    (execution.prepare if args.mode == 'prepare' else execution.run_once)(module)


if __name__ == '__main__': main()
