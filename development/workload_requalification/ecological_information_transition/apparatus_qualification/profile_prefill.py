"""Four nonexecuting, bounded apparatus calls; no actor action or driver change."""
import copy
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bootstrap
import transition_task as study
import run_transition as controller
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file

RUNTIME=controller.RUNTIME
AREA=Path(__file__).resolve().parent

def profile():
    modules={c:study.Task(c) for c in study.CONDITIONS}
    manifests={c:controller.verify_preparation(m) for c,m in modules.items()}
    bound=modules['unchanged'].source_identities()
    assert bound==modules['released'].source_identities()
    folder=AREA/'run-001'
    folder.mkdir(exist_ok=False)
    store=ArtifactStore(folder)
    log=controller.runner.RunLog(folder/'records.jsonl','transition-apparatus-qualification',task_module=modules['unchanged'])
    log.append('apparatus_reserved',dict(maximum_completion_requests=4,
        whole_generation_tokens=32,timebox_seconds_from_readiness=900,
        schedule=['unchanged','released','released','unchanged'],behavioral_operations=0,
        runtime_policy_changed=False),[store.put('PLAN.md',(AREA/'PLAN.md').read_bytes())])
    rows,error,pid,sent=[],None,None,0
    server,model,_=modules['unchanged'].runtime_paths()
    try:
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            with controller.memory_monitor.monitor(folder,RUNTIME.PORT,log) as pid:
                deadline=time.monotonic()+900
                for index,condition in enumerate(('unchanged','released','released','unchanged'),1):
                    module=modules[condition]
                    module.verify_sources(bound)
                    if time.monotonic()>=deadline:
                        raise TimeoutError('Apparatus timebox consumed; no next completion sent')
                    request=copy.deepcopy(study.read(module.PACKAGE/'initial-wire-request.json'))
                    request['max_tokens']=request['n_predict']=32
                    wire=completion_request_bytes(request)
                    stem=f'calls/P{index:02d}'
                    template=RUNTIME.post(url,'/apply-template',wire,60)
                    native=load_json_strict(template)['prompt'].encode()
                    original=(module.PACKAGE/'admission/I0001-native.txt').read_bytes()
                    if native!=original:
                        raise ValueError('Generation-only cap changed rendered input')
                    log.append('apparatus_invocation_started',dict(id=f'P{index:02d}',condition=condition,
                        prompt_tokens=manifests[condition]['initial']['prompt_tokens'],
                        wire_sha256=sha256_bytes(wire),no_operation_execution=True),
                        [store.put(stem+'-wire-request.json',wire),store.put(stem+'-native.txt',native),
                         store.put(stem+'-template.json',template)])
                    sent+=1
                    started=time.monotonic()
                    try:
                        raw=RUNTIME.post(url,'/v1/chat/completions',wire,max(1,int(deadline-started)))
                    except RUNTIME.ResponseFailure as failure:
                        log.append('apparatus_transport_stopped',dict(id=f'P{index:02d}',status=failure.status),
                            [store.put(stem+'-partial-response.bin',failure.data)])
                        raise
                    elapsed=time.monotonic()-started
                    response=load_json_strict(raw)
                    log.append('apparatus_response_preserved',dict(id=f'P{index:02d}',elapsed_seconds=elapsed),
                        [store.put(stem+'-endpoint-response.json',raw)])
                    usage,timing=response['usage'],response['timings']
                    if (usage['prompt_tokens']!=manifests[condition]['initial']['prompt_tokens']
                            or usage['completion_tokens']>32
                            or usage.get('prompt_tokens_details',{}).get('cached_tokens')!=0
                            or timing.get('cache_n')!=0):
                        raise ValueError('Apparatus input/cap/cache accounting differs')
                    choice=response['choices'][0]
                    row=dict(id=f'P{index:02d}',condition=condition,elapsed_seconds=elapsed,
                        finish_reason=choice['finish_reason'],usage=usage,timings=timing,
                        no_action_parsed_or_executed=True)
                    rows.append(row)
                    log.append('apparatus_invocation_completed',row,[])
                    print(json.dumps(dict(id=row['id'],condition=condition,elapsed_seconds=elapsed,
                        prompt_per_second=timing.get('prompt_per_second'),prompt_ms=timing.get('prompt_ms'),
                        predicted_ms=timing.get('predicted_ms'))),flush=True)
                modules['unchanged'].verify_sources(bound)
    except BaseException as problem:
        error=problem
        log.append('apparatus_stopped',dict(type=type(problem).__name__,message=str(problem)),
            [store.put('FAILED.json',canonical_json_bytes(dict(type=type(problem).__name__,message=str(problem))))])
    finally:
        memory=(controller.memory_monitor.summary(folder/'process-memory.jsonl',pid)
                if pid is not None and (folder/'process-memory.jsonl').exists() else None)
        value=dict(status='stopped_preserved' if error else 'completed',completion_requests=sent,
            completed_responses=len(rows),stable_all_responses_returned=not error and len(rows)==4,
            whole_generation_allowance=32,behavioral_operations=0,runtime_policy_changed=False,
            actor=study.ACTOR,measurements=rows,process_memory=memory,
            memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT),
            performance_cause_not_established=True,
            prepared_manifests={c:sha256_file(m.MANIFEST) for c,m in modules.items()})
        store.put('RESULT.json',canonical_json_bytes(value))
        files=RUNTIME.file_inventory(folder)
        store.put('SEAL.json',canonical_json_bytes(dict(status=value['status'],source_sha256=bound,
            files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),
            record_count=len(verify_records(folder/'records.jsonl',folder)),
            private_runtime_files_local_only={p.name:sha256_file(p)
                for p in (folder/'private-runtime').glob('*') if p.is_file()})))
    if error:
        raise error
    print(json.dumps(dict(status=value['status'],process_memory=memory,port_free=value['port_free'])),flush=True)

if __name__=='__main__':
    profile()
