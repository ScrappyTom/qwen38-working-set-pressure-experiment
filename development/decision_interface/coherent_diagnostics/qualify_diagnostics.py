"""Re-render the actual failed-check inputs; no inference, grading or semantic aid."""
import json
from types import SimpleNamespace

import diagnostic_task as study
import run_uncoached_contribution as runner
from manage import RUNTIME,legacy
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore,verify_records
from working_set_exp.jsonutil import canonical_json_bytes


def main():
    folder=study.QUALIFIED;folder.mkdir(parents=True,exist_ok=False)
    bound=study.source_identities();store=ArtifactStore(folder)
    module=study.Task()
    log=legacy.QualificationLog(folder/'records.jsonl','coherent-diagnostic-qualification',task_module=module)
    results=[];error=None
    try:
        server,model,_=study.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            for tag,stem in [('C06','after/C05-O03'),('C07','after/C06-O01')]:
                adapter=runner.Adapter(study.prior.Task())
                adapter.preceding_feedback=study.read(study.OLD/(stem+'-preceding-feedback.json'))
                old=study.restore(stem,corrected=False)
                old_view=old.view()
                actual=(study.OLD/f'calls/{tag}-wire-request.json').read_bytes()
                assert completion_request_bytes(adapter.request_for(old_view))==actual
                # Each Loop needs distinct admission paths despite shared custody.
                target=folder/tag;target.mkdir()
                item_store=ArtifactStore(target)
                item_log=legacy.QualificationLog(target/'records.jsonl',tag,task_module=module)
                loop=runner.Loop(target,item_store,item_log,url=url,task_module=adapter,
                                source_check=lambda:study.verify_sources(bound),
                                health=lambda:study.base.pilot.health(folder))
                before=loop.measure(old_view)
                new=study.restore(stem)
                view=new.view();after=loop.measure(view)
                assert after<=23808
                assert study.snapshot(old)==study.snapshot(new)
                assert {k:v for k,v in old_view.items() if k not in ('verification','latest_feedback')} == {
                    k:v for k,v in view.items() if k not in ('verification','latest_feedback')}
                assessment=view['verification']['checks']['public']['assessment']
                criterion=next(r for r in assessment['criteria'] if r['criterion']=='examples.execution')
                assert [r['location']['line'] for r in criterion['diagnostics']]==[172,175,178,181]
                assert all(r['diagnostic']['complete'] for r in criterion['diagnostics'])
                assert not assessment['passed']
                if tag=='C06':
                    assert view['latest_feedback']['result']['report']==assessment
                item_store.put('corrected-view.json',canonical_json_bytes(view))
                item_store.put('corrected-wire-request.json',completion_request_bytes(adapter.request_for(view)))
                results.append(dict(input=tag,original_byte_identical=True,before_tokens=before,after_tokens=after,
                    four_complete_failure_records=True,candidate_and_account_and_selection_unchanged=True))
                assert not any(r['record_type']=='invocation_started' for r in verify_records(target/'records.jsonl',target))
    except BaseException as exc:
        error=exc;study.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        study.save(folder,'RESULTS.json',dict(cases=results,completion_requests=0,checks_executed=0))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
