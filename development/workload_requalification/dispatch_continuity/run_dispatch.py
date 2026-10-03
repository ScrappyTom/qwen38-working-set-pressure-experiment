"""Qualify and execute one declared contribution using the current owned runtime."""
import argparse
import json
from types import SimpleNamespace

import bootstrap
import dispatch_task as study
import qualification_route
from manage import RUNTIME, legacy, load_helper
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

runner = load_helper('dispatch_contribution_runner', 'scripts/run_uncoached_contribution.py')
native_forms = load_helper('dispatch_native_forms', 'development/workload_requalification/ecological_import_entry/native_forms.py')
OriginalLoop = runner.Loop
INITIAL_KEYS = ('prompt_tokens','request_sha256','native_sha256','wire_request_sha256')


class Loop(OriginalLoop):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.sent = self.task.INHERITED_REQUESTS

    def invoke(self,session):
        if self.sent == self.task.INHERITED_REQUESTS and self.initial:
            self.measure(session.view())
            selected = self.cache[sha256_bytes(canonical_json_bytes(self.task.request_for(session.view())))]
            assert all(selected[k] == self.initial[k] for k in INITIAL_KEYS), 'Qualified initial input differs'
        return super().invoke(session)

    def execute(self,session):
        assert self.sent == session.requests_used == self.task.INHERITED_REQUESTS
        assert session.calls_used == self.task.INHERITED_OPERATIONS
        self.log.append('job_accounting', dict(phase=self.task.phase,
            inherited_requests=self.sent,inherited_operations=session.calls_used,
            additional_request_limit=24,additional_operation_limit=72), [])
        return super().execute(session)


runner.Loop = Loop


def prepare(module):
    folder = module.PACKAGE; folder.mkdir(parents=True,exist_ok=False)
    store = ArtifactStore(folder)
    log = legacy.QualificationLog(folder/'records.jsonl','dispatch-contribution-preparation',task_module=module)
    bound = module.source_identities()
    initial = forms = route = error = None
    try:
        session,adapter = module.initial_session(),runner.Adapter(module)
        module.attach_observations(session,folder,log)
        entry = canonical_json_bytes(module.snapshot(session))
        server,model,_ = module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop = Loop(folder,store,log,url=url,task_module=adapter,source_check=lambda:module.verify_sources(bound))
            request = adapter.request_for(session.view())
            count = loop.measure(session.view()); assert count <= 23808
            initial = {k:loop.cache[sha256_bytes(canonical_json_bytes(request))][k] for k in INITIAL_KEYS}
            loop.snapshot(session,'starting')
            store.put('initial-wire-request.json',completion_request_bytes(request))
            forms = native_forms.qualify(folder/'native-forms',task=module,request=request,source_identities=module.implementation_identities)
            route = qualification_route.qualify(module,loop,adapter,store,folder)
            assert canonical_json_bytes(module.snapshot(session)) == entry
            module.verify_sources(bound)
    except BaseException as problem:
        error = problem
        store.put('FAILED.json',canonical_json_bytes(dict(type=type(problem).__name__,message=str(problem))))
    finally:
        store.put('QUALIFICATION.json',canonical_json_bytes(dict(initial=initial,native_forms=forms,route=route,
            completion_requests=0,actor=module.ACTOR,inherited_requests=module.INHERITED_REQUESTS,
            inherited_operations=module.INHERITED_OPERATIONS,maximum_requests=module.MAX_REQUESTS,
            maximum_operations=module.MAX_OPERATIONS,memory=RUNTIME.memory_stats(folder/'memory.csv'),
            port_free=RUNTIME.port_free(RUNTIME.PORT))))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error: raise error
    manifest = dict(actor=module.ACTOR,seed=module.SEED,source_sha256=bound,
        preparation_seal_sha256=sha256_file(folder/'SEAL.json'),initial=initial,
        maximum_requests=module.MAX_REQUESTS,maximum_operations=module.MAX_OPERATIONS,
        inherited_requests=module.INHERITED_REQUESTS,inherited_operations=module.INHERITED_OPERATIONS,
        phase=module.phase,owner_direction=module.OWNER_DIRECTION,no_live_coaching=True,automatic_retry=False)
    with module.MANIFEST.open('xb') as stream: stream.write(canonical_json_bytes(manifest))
    runner.verify_package(module)
    print(json.dumps(dict(status='qualified',initial=initial,decisions=route['decisions'],completion_requests=0)),flush=True)


def run_once(module):
    manifest = runner.verify_package(module)
    assert not module.RUN.exists(), 'Attempt exists; no retry'
    module.RUN.mkdir(parents=True)
    store = ArtifactStore(module.RUN)
    log = runner.RunLog(module.RUN/'records.jsonl','dispatch-contribution',task_module=module)
    log.append('attempt_reserved',dict(owner_direction=module.OWNER_DIRECTION,manifest_sha256=sha256_file(module.MANIFEST)),
        [store.put('EXECUTION_MANIFEST.json',module.MANIFEST.read_bytes()),store.put('SPEC.md',(module.AREA/'SPEC.md').read_bytes())])
    session,adapter = module.initial_session(),runner.Adapter(module)
    module.attach_observations(session,module.RUN,log)
    error = outcome = None
    try:
        server,model,_ = module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=module.RUN),store,log) as url:
            loop = Loop(module.RUN,store,log,url=url,task_module=adapter,
                source_check=lambda:module.verify_sources(manifest['source_sha256']),initial=manifest['initial'])
            outcome = loop.execute(session)
    except BaseException as problem:
        error = problem
        log.append('attempt_stopped',dict(type=type(problem).__name__,message=str(problem)),[])
        for name,value in (('stopped-state.json',module.snapshot(session)),('stopped-candidate.json',module.candidate_bytes(session.candidate)),
                           ('stopped-preceding-feedback.json',adapter.preceding_feedback)):
            store.put(name,value if isinstance(value,bytes) else canonical_json_bytes(value))
    finally:
        records = verify_records(module.RUN/'records.jsonl',module.RUN)
        files = RUNTIME.file_inventory(module.RUN)
        seal = dict(disposition='stopped_without_retry' if error else outcome['disposition'],actor=module.ACTOR,
            source_sha256=manifest['source_sha256'],files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),
            record_count=len(records),sent_requests=sum(r['record_type']=='invocation_started' for r in records),
            returned_responses=sum(r['record_type']=='response_received' for r in records),
            processed_invocations=sum(r['record_type']=='invocation_completed' for r in records),
            cumulative_requests=session.requests_used,cumulative_operations=session.calls_used,
            actual_operations=session.calls_used-module.INHERITED_OPERATIONS,
            memory=RUNTIME.memory_stats(module.RUN/'memory.csv'),
            runtime=RUNTIME.runtime_evidence(module.RUN/'private-runtime/server.stderr.log'),
            port_free=RUNTIME.port_free(RUNTIME.PORT),private_runtime_files_local_only={
                p.name:sha256_file(p) for p in (module.RUN/'private-runtime').glob('*') if p.is_file()})
        store.put('RESPONSE_SEAL.json',canonical_json_bytes(seal))
    if error: raise error
    print('Closed: '+outcome['disposition'],flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',choices=('prepare','run'))
    parser.add_argument('--phase',choices=('union','dynamic'),default='union')
    parser.add_argument('--version',default='001')
    parser.add_argument('--inherited')
    args = parser.parse_args()
    module = study.Task(args.phase,args.version,args.inherited)
    (prepare if args.mode=='prepare' else run_once)(module)
