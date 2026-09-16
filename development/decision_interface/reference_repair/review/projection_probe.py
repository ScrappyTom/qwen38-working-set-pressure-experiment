"""Native sizing only: can omitted C06 rejection detail and account fit?"""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import reference_task as study
import run_uncoached_contribution as runner
from manage import RUNTIME,legacy
from working_set_exp import decision_view
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file


def main():
    folder=study.AREA/'review/projection-001';folder.mkdir(parents=True,exist_ok=False)
    module=study.Task();store=ArtifactStore(folder)
    bound={**study.source_identities(),Path(__file__).resolve().relative_to(study.ROOT).as_posix():sha256_file(Path(__file__))}
    log=legacy.QualificationLog(folder/'records.jsonl','C06-projection-counterfactual',task_module=module)
    s=study.restore(module.RUN,'after/C05-O02')
    adapter=runner.Adapter(module)
    adapter.preceding_feedback=study.read(module.RUN/'after/C05-O02-preceding-feedback.json')
    actual=s.view()
    assert completion_request_bytes(adapter.request_for(actual))==(module.RUN/'calls/C06-wire-request.json').read_bytes()
    variants={'actual':actual}
    full=copy.deepcopy(actual)
    full['latest_feedback']=decision_view.receipt_view(s.last)
    variants['full_rejection']=full
    both=copy.deepcopy(full)
    both['working_account']={**s.working_account(),'text_complete':True}
    variants['full_rejection_and_account']=both
    results={};error=None
    try:
        server,model,_=study.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,source_check=lambda:study.verify_sources(bound))
            for name,view in variants.items():
                count=loop.measure(view)
                store.put(name+'-view.json',canonical_json_bytes(view))
                results[name]=dict(tokens=count,source_bodies=len(view['working_set']['sources']),
                    match_regions=len(view['latest_feedback']['result'].get('match_regions',[])),
                    account_text_complete=view['working_account']['text_complete'])
            assert results['actual']['tokens']==6115
            assert results['full_rejection_and_account']['tokens']<=23808
            results['scope']='Post-run native counterfactual only; no model call, operation or candidate change. Source omission remains unchanged.'
    except BaseException as exc:
        error=exc;study.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        study.save(folder,'RESULTS.json',results)
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    main()
