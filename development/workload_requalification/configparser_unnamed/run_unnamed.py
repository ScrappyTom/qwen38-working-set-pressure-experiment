"""Existing owned runtime; one declared coding opportunity and immutable closure."""
import argparse
import bootstrap
import unnamed_task as study
import unnamed_route as route
import run_dispatch as runner

runner.qualification_route = route


class Loop(runner.Loop):
    def execute(self, session):
        assert self.sent == session.requests_used == 0 and session.calls_used == 0
        self.log.append('job_accounting', dict(phase=self.task.phase,
            inherited_requests=0, inherited_operations=0,
            additional_request_limit=self.task.MAX_REQUESTS,
            additional_operation_limit=self.task.MAX_OPERATIONS), [])
        return runner.OriginalLoop.execute(self, session)


runner.Loop = runner.runner.Loop = Loop


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare', 'run'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    task = study.Task(args.version)
    (runner.prepare if args.mode == 'prepare' else runner.run_once)(task)
