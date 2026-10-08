"""Reuse the existing owned lifecycle with accurate inherited receipts/accounting."""
import argparse
import json
from types import SimpleNamespace
import correction_task as entry
import run_completion as previous
import correction_route
from working_set_exp.measurement import check_opportunities

execution = previous.execution
OriginalAdapter = execution.runner.Adapter


class Adapter(OriginalAdapter):
    def __init__(self, module):
        super().__init__(module)
        self.preceding_feedback = module.initial_preceding_feedback()


class Loop(execution.Loop):
    def execute(self, session):
        assert self.sent == session.requests_used == self.task.INHERITED_REQUESTS
        assert session.calls_used == self.task.INHERITED_OPERATIONS
        self.log.append('job_accounting', dict(phase=self.task.phase,
            inherited_interpolation_dispatches=self.sent, inherited_operations=session.calls_used,
            earlier_work_operations=55, prior_interpolation_operations=97,
            prior_unknown_response='original interpolation C22: response, generation and timing remain unknown',
            additional_request_limit=self.task.MAX_REQUESTS-self.sent,
            additional_operation_limit=self.task.MAX_OPERATIONS-session.calls_used), [])
        original = execution.runner.check_opportunities
        def opportunities(pairs, *, call_limit):
            inherited = self.task.inherited_state['pairs']
            rows = [r for r in check_opportunities([*inherited, *pairs], call_limit=call_limit)
                    if r['sequence'] > len(inherited)]
            for i, row in enumerate(rows):
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
    execution.qualification_route = correction_route


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('cpu', 'prepare', 'run'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    module = entry.Task(args.version)
    configure()
    if args.mode == 'cpu':
        folder = entry.AREA/f'cpu-route-{args.version}'; folder.mkdir(exist_ok=False)
        store = execution.ArtifactStore(folder)
        log = execution.legacy.QualificationLog(folder/'records.jsonl', 'interpolation-correction-cpu', task_module=module)
        try:
            result = correction_route.qualify(module, SimpleNamespace(measure=lambda view: 0, log=log),
                Adapter(module), store, folder)
            result.update(completion_requests=0, token_callback='zero; not native admission evidence')
            entry.original.save(folder, 'QUALIFICATION.json', result)
            print(json.dumps(result), flush=True)
        except BaseException as error:
            entry.original.save(folder, 'FAILED.json', dict(type=type(error).__name__, message=str(error)))
            raise
    else:
        (execution.prepare if args.mode == 'prepare' else execution.run_once)(module)
