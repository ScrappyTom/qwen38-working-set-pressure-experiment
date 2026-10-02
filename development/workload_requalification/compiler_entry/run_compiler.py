"""Qualify exact capture paths, then execute one published original-entry attempt."""
import argparse
import json
from types import SimpleNamespace
import bootstrap
import compiler_task as study
import native_forms
import qualification_route
from manage import RUNTIME, legacy, load_helper
from working_set_exp.custody import ArtifactStore
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

runner = load_helper('compiler_entry_runner', 'scripts/run_uncoached_contribution.py')
INITIAL_KEYS = ('prompt_tokens','request_sha256','native_sha256','wire_request_sha256')

def prepare(module):
    folder = module.PACKAGE; folder.mkdir(exist_ok=False)
    bound = module.source_identities(); store = ArtifactStore(folder)
    log = legacy.QualificationLog(folder/'records.jsonl','compiler-capture-preparation',task_module=module)
    session, adapter = module.initial_session(), runner.Adapter(module)
    initial, error, forms, route = None, None, None, None
    try:
        module.attach_observations(session,folder,log)
        assert not session.pairs and not session.ranges and not session.saved and session.working_account() is None
        server, model, _ = module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop = runner.Loop(folder,store,log,url=url,task_module=adapter,source_check=lambda:module.verify_sources(bound))
            request = adapter.request_for(session.view())
            count = loop.measure(session.view()); assert count <= 23808
            selected = loop.cache[sha256_bytes(canonical_json_bytes(request))]
            initial = {k:selected[k] for k in INITIAL_KEYS}
            loop.snapshot(session,'starting')
            store.put('initial-wire-request.json', completion_request_bytes(request))
            forms = native_forms.qualify(module, folder/'native-forms', url, store, log)
            route = qualification_route.qualify(module,loop,adapter,store,folder)
            assert not session.pairs and session.candidate.candidate_id == study.STARTING_ID
            module.verify_sources(bound)
    except BaseException as exc:
        error=exc
        study.save(folder,'FAILED.json',{'type':type(exc).__name__,'message':str(exc)})
    finally:
        study.save(folder,'QUALIFICATION.json',dict(initial=initial,native_forms=forms,route=route,
            completion_requests=0,actor=module.ACTOR,maximum_requests=module.MAX_REQUESTS,
            maximum_operations=module.MAX_OPERATIONS,memory=RUNTIME.memory_stats(folder/'memory.csv'),
            port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error: raise error
    study.save(module.AREA,module.MANIFEST.name,dict(actor=module.ACTOR,seed=module.SEED,
        maximum_requests=module.MAX_REQUESTS,maximum_operations=module.MAX_OPERATIONS,
        source_sha256=bound,preparation_seal_sha256=sha256_file(folder/'SEAL.json'),initial=initial,
        imported_capture_retention=('retain-requested-immutable-captures-v1'
            if module.retain_imported_captures else 'latest-feedback-only'),
        owner_direction=study.OWNER_DIRECTION,no_live_coaching=True,automatic_retry=False))
    runner.verify_package(module)
    print(json.dumps(dict(status='qualified',initial=initial,route=route,completion_requests=0)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('prepare','run'));p.add_argument('--version',default='001')
    args=p.parse_args(); module=study.Task(args.version)
    if args.mode=='prepare': prepare(module)
    else: runner.run_once(SimpleNamespace(owner_direction=study.OWNER_DIRECTION,
                manifest_sha256=sha256_file(module.MANIFEST)),module)
