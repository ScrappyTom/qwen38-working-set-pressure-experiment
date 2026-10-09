"""Existing owned runtime with the original cumulative opportunity."""
import argparse
import bootstrap
import continuation_task as study
import continuation_route as route
import run_dispatch as runner

runner.qualification_route = route


class Loop(runner.Loop):
    def execute(self, session):
        assert self.sent == session.requests_used == 9 and session.calls_used == 12
        self.log.append('job_accounting', dict(phase=self.task.phase,
            inherited_requests=9, inherited_operations=12,
            additional_request_limit=31, additional_operation_limit=108), [])
        return runner.OriginalLoop.execute(self, session)


runner.Loop = runner.runner.Loop = Loop


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare', 'run'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    task = study.Task(args.version)
    (runner.prepare if args.mode == 'prepare' else runner.run_once)(task)
