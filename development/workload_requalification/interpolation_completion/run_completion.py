"""One finite completion; reuse owned runtime, custody and native qualification."""
import argparse
import json
from types import SimpleNamespace
import completion_task as entry
import qualification_route
import run_dispatch as execution
from working_set_exp.measurement import check_opportunities


class Loop(execution.Loop):
    def execute(self, session):
        assert self.sent==session.requests_used==self.task.INHERITED_REQUESTS
        assert session.calls_used==self.task.INHERITED_OPERATIONS
        self.log.append('job_accounting',dict(phase=self.task.phase,
            inherited_interpolation_dispatches=self.sent,inherited_operations=session.calls_used,
            earlier_work_operations=55,prior_interpolation_operations=46,
            prior_unknown_response='interpolation/run-002 C22; timing and generation remain unknown',
            additional_request_limit=self.task.MAX_REQUESTS-self.sent,
            additional_operation_limit=self.task.MAX_OPERATIONS-session.calls_used),[])
        previous=execution.runner.check_opportunities
        def opportunities(pairs, *, call_limit):
            inherited=self.task.inherited_state['pairs']
            rows=[r for r in check_opportunities([*inherited,*pairs],call_limit=call_limit) if r['sequence']>len(inherited)]
            for i,row in enumerate(rows):
                row['job_sequence']=row['sequence']-len(inherited)
                row['first_check']=i==0
            return rows
        execution.runner.check_opportunities=opportunities
        try: return execution.OriginalLoop.execute(self,session)
        finally: execution.runner.check_opportunities=previous


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=('cpu','prepare','run'))
    parser.add_argument('--version',default='001')
    parser.add_argument('--cpu-name',default='cpu-route-001')
    args=parser.parse_args()
    module=entry.Task(args.version)
    execution.Loop=execution.runner.Loop=Loop
    execution.qualification_route=qualification_route
    if args.mode=='cpu':
        folder=entry.AREA/args.cpu_name;folder.mkdir(exist_ok=False)
        store=execution.ArtifactStore(folder)
        log=execution.legacy.QualificationLog(folder/'records.jsonl','interpolation-completion-cpu',task_module=module)
        try:
            value=qualification_route.qualify(module,SimpleNamespace(measure=lambda view:0,log=log),
                SimpleNamespace(preceding_feedback=[]),store,folder)
            value.update(completion_requests=0,token_callback='zero; not native input-fit evidence')
            entry.save(folder,'QUALIFICATION.json',value)
            print(json.dumps(value),flush=True)
        except BaseException as error:
            entry.save(folder,'FAILED.json',dict(type=type(error).__name__,message=str(error)))
            raise
    else:
        (execution.prepare if args.mode=='prepare' else execution.run_once)(module)


if __name__=='__main__': main()
