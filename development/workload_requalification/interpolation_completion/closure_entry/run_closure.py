"""Owned lifecycle and cumulative accounting for the finite closure job."""
import argparse
import closure_task as entry
import run_correction as previous
import closure_route
import decoder_reuse
from working_set_exp.measurement import check_opportunities

execution = previous.execution
Adapter = previous.Adapter


class Loop(previous.Loop):
    def execute(self, session):
        assert self.sent == session.requests_used == self.task.INHERITED_REQUESTS
        assert session.calls_used == self.task.INHERITED_OPERATIONS
        self.log.append('job_accounting', dict(phase=self.task.phase,
            inherited_interpolation_dispatches=self.sent, inherited_operations=session.calls_used,
            earlier_work_operations=55, prior_interpolation_operations=132,
            prior_unknown_response='original interpolation C22: response, generation and timing remain unknown',
            additional_request_limit=self.task.MAX_REQUESTS-self.sent,
            additional_operation_limit=self.task.MAX_OPERATIONS-session.calls_used), [])
        original = execution.runner.check_opportunities
        def opportunities(pairs, *, call_limit):
            inherited = self.task.inherited_state['pairs']
            rows = [r for r in check_opportunities([*inherited, *pairs], call_limit=call_limit)
                    if r['sequence'] > len(inherited)]
            for i,row in enumerate(rows):
                row.update(job_sequence=row['sequence']-len(inherited), first_check=i == 0)
            return rows
        execution.runner.check_opportunities = opportunities
        try:
            return execution.OriginalLoop.execute(self, session)
        finally:
            execution.runner.check_opportunities = original


def configure():
    execution.Loop = execution.runner.Loop = Loop
    execution.runner.Adapter = Adapter
    execution.qualification_route = closure_route
    execution.native_forms = decoder_reuse


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare', 'run'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    configure()
    (execution.prepare if args.mode == 'prepare' else execution.run_once)(entry.Task(args.version))
