"""One finite successor using existing recording/runtime; truthful job accounting."""
import argparse
import json
from types import SimpleNamespace
import contract_task as study
import qualification_contract
import run_dispatch as execution
from working_set_exp.measurement import check_opportunities


def job_opportunities(pairs, *, inherited, call_limit):
    rows = [r for r in check_opportunities([*inherited, *pairs], call_limit=call_limit)
            if r['sequence'] > len(inherited)]
    for i, row in enumerate(rows):
        row['job_sequence'] = row['sequence'] - len(inherited)
        row['first_check'] = i == 0
    return rows


class Loop(execution.Loop):
    def execute(self, session):
        assert self.sent == session.requests_used == self.task.INHERITED_REQUESTS
        assert session.calls_used == self.task.INHERITED_OPERATIONS
        self.log.append('job_accounting', dict(phase=self.task.phase,
            inherited_requests=self.sent, inherited_operations=session.calls_used,
            additional_request_limit=self.task.MAX_REQUESTS - self.sent,
            additional_operation_limit=self.task.MAX_OPERATIONS - session.calls_used), [])
        previous = execution.runner.check_opportunities
        execution.runner.check_opportunities = lambda pairs, call_limit: job_opportunities(
            pairs, inherited=self.task.inherited_state['pairs'], call_limit=call_limit)
        try:
            return execution.OriginalLoop.execute(self, session)
        finally:
            execution.runner.check_opportunities = previous


def cpu(module):
    folder = study.HERE / 'cpu-route-002'
    folder.mkdir(exist_ok=False)
    store = execution.ArtifactStore(folder)
    log = execution.legacy.QualificationLog(folder / 'records.jsonl', 'assertion-contract-cpu', task_module=module)
    result = qualification_contract.qualify(module, SimpleNamespace(measure=lambda view: 0, log=log),
        SimpleNamespace(preceding_feedback=[]), store, folder)
    result.update(token_callback='zero; not native input-fit evidence', completion_requests=0)
    study.study.save(folder, 'QUALIFICATION.json', result)
    print(json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('cpu', 'prepare', 'run'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    module = study.Task(args.version)
    execution.Loop = execution.runner.Loop = Loop
    execution.qualification_route = qualification_contract
    if args.mode == 'cpu':
        cpu(module)
    else:
        (execution.prepare if args.mode == 'prepare' else execution.run_once)(module)


if __name__ == '__main__':
    main()
