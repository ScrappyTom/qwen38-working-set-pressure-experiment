"""Qualify then execute the one controlled pair through the existing runner."""
import argparse
import copy
from datetime import datetime
import json
from types import SimpleNamespace

import bootstrap
import transition_task as study
import qualification_route
from manage import RUNTIME, legacy, load_helper
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.working_session import INPUT_LIMIT

contract_controller=load_helper('transition_old_controller',
    'development/workload_requalification/ecological_contract_continuation/run_continuation.py')
contract_controller.controller.INHERITED_REQUESTS=16
contract_controller.controller.INHERITED_OPERATIONS=24
runner=contract_controller.runner
Adapter=contract_controller.Adapter
native_forms=contract_controller.native_forms
INITIAL_KEYS=contract_controller.INITIAL_KEYS
memory_monitor=load_helper('transition_process_monitor',
    'development/workload_requalification/ecological_information_transition/apparatus_qualification/memory_monitor.py')

def declared_entry(module, session):
    assert session.candidate.candidate_id==study.SAVED_ID and not session.submitted
    assert (session.requests_used,session.calls_used,session.starting_archive_length)==(16,24,0)
    assert (session.request_limit,session.call_limit)==(24,72)
    assert session.pairs==study.inherited_state()['pairs']
    assert session.prerequisite_state()==study.inherited_state()['source_prerequisites']
    assert session.delivered_sources==[] and session.edit_checks=={}
    assert session.check_state() is None and session.transition_condition==module.condition
    assert len(session.ranges)==(7 if module.condition=='unchanged' else 1)

def verify_preparation(module):
    manifest=runner.verify_package(module)
    proof=module.read(module.PACKAGE/'QUALIFICATION.json')
    assert proof['status']=='qualified' and proof['completion_requests']==0
    assert proof['entry_unchanged_after_qualification'] and proof['route']['submitted']
    assert proof['initial']==manifest['initial'] and proof['native_forms']['status']=='passed'
    assert manifest['condition']==module.condition and manifest['inherited_requests']==16
    assert manifest['inherited_operations']==24 and manifest['maximum_new_requests']==8
    assert manifest['maximum_new_operations']==48 and manifest['checker_contracts']==study.contract_checker.contracts()
    assert manifest['source_release_is_evaluator_setup_not_actor_action']
    assert manifest['automatic_edit_checks']=={} and manifest['no_live_coaching']
    if module.PACKAGE.name != 'preparation-001':
        original = module.PACKAGE.parent / 'preparation-001'
        assert (module.PACKAGE/'initial-wire-request.json').read_bytes() == (original/'initial-wire-request.json').read_bytes()
        assert proof['initial'] == module.read(original/'QUALIFICATION.json')['initial']
    declared_entry(module,module.initial_session())
    return manifest

def prepare(module):
    folder=module.PACKAGE
    folder.mkdir(parents=True,exist_ok=False)
    store, bound, log=ArtifactStore(folder),{},None
    initial=forms=route=error=None
    entry_unchanged=False
    try:
        log=legacy.QualificationLog(folder/'records.jsonl','ecological-information-transition-preparation',task_module=module)
        log.append('preparation_initialized',dict(condition=module.condition,completion_requests=0,
            inherited_requests=16,inherited_operations=24,evaluator_setup_not_actor_action=True),[])
        bound=module.source_identities()
        session,adapter=module.initial_session(),Adapter(module)
        module.attach_observations(session,folder,log)
        declared_entry(module,session)
        entry=canonical_json_bytes(module.snapshot(session))
        request=adapter.request_for(session.view())
        server,model,_=module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,
                source_check=lambda:module.verify_sources(bound))
            count=loop.measure(session.view())
            assert count<=INPUT_LIMIT
            initial={k:loop.cache[sha256_bytes(canonical_json_bytes(request))][k] for k in INITIAL_KEYS}
            loop.snapshot(session,'starting')
            store.put('initial-wire-request.json',completion_request_bytes(request))
            store.put('SETUP.json',canonical_json_bytes(dict(condition=module.condition,
                checkpoint_sha256=study.CHECKPOINT_SHA,recorded_actor_operations=24,
                recorded_actor_requests=16,setup_consumes_no_actor_operation=True,
                selected_sources=session.ranges,actual_account=session.working_account(),
                previous_dispatch_authority_cleared_in_both=True)))
            forms=native_forms.qualify(folder/'native-forms',task=module,request=request,
                source_identities=module.implementation_identities)
            route=qualification_route.qualify(module,loop,adapter,store,folder)
            entry_unchanged=canonical_json_bytes(module.snapshot(session))==entry
            assert entry_unchanged and adapter.request_for(session.view())==request
            declared_entry(module,session)
            module.verify_sources(bound)
    except BaseException as problem:
        error=problem
        failure=store.put('FAILED.json',canonical_json_bytes(dict(type=type(problem).__name__,message=str(problem))))
        if log is not None:
            log.append('preparation_failed',dict(type=type(problem).__name__,message=str(problem)),[failure])
    finally:
        store.put('QUALIFICATION.json',canonical_json_bytes(dict(status='failed' if error else 'qualified',
            initial=initial,native_forms=forms,route=route,completion_requests=0,
            entry_unchanged_after_qualification=entry_unchanged,actor=module.ACTOR,
            maximum_requests=24,maximum_operations=72,memory=RUNTIME.memory_stats(folder/'memory.csv'),
            port_free=RUNTIME.port_free(RUNTIME.PORT))))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:
        raise error
    manifest=dict(actor=module.ACTOR,seed=module.SEED,condition=module.condition,
        maximum_requests=24,maximum_operations=72,inherited_requests=16,inherited_operations=24,
        maximum_new_requests=8,maximum_new_operations=48,source_sha256=bound,initial=initial,
        preparation_seal_sha256=sha256_file(folder/'SEAL.json'),original_entry=False,
        starting_candidate_id=study.SAVED_ID,starting_archive_operations=24,
        inherited_run_seal_sha256=study.OLD_SEAL,checkpoint_sha256=study.CHECKPOINT_SHA,
        owner_direction=study.OWNER_DIRECTION,no_live_coaching=True,automatic_retry=False,
        automatic_edit_checks={},checker_contracts=study.contract_checker.contracts(),
        source_release_is_evaluator_setup_not_actor_action=True,source_coverage_policy=module.coverage_policy(),
        literal_source_reply=True,hidden_evaluation='after_response_seal_only',
        runtime_policy='same pinned medium/uncapped q4/56576/noMTP and common passive monitoring in both arms')
    manifest['apparatus_decision_sha256']=sha256_file(study.AREA/'review/APPARATUS-DECISION-001.json')
    with module.MANIFEST.open('xb') as stream:
        stream.write(canonical_json_bytes(manifest))
    verify_preparation(module)
    print(json.dumps(dict(condition=module.condition,status='qualified',initial=initial,
        scripted_decisions=route['scripted_decisions'],completion_requests=0)),flush=True)

def _timebox_basis(result, records):
    """A known screen deadline limits measurement, not the actor's opportunity."""
    assert result['status']=='stopped_preserved' and result['completion_requests']==3
    assert result['completed_responses']==2 and result['stable_all_responses_returned'] is False
    assert result['whole_generation_allowance']==32 and result['actor']==study.ACTOR
    assert result['behavioral_operations']==0 and result['runtime_policy_changed'] is False
    starts=[r for r in records if r['record_type']=='apparatus_invocation_started']
    assert [(r['payload']['id'],r['payload']['condition']) for r in starts] == [
        ('P01','unchanged'),('P02','released'),('P03','released')]
    returned=[r for r in records if r['record_type']=='apparatus_response_preserved']
    assert [r['payload']['id'] for r in returned]==['P01','P02']
    stopped=[r for r in records if r['record_type']=='apparatus_transport_stopped']
    assert len(stopped)==1 and stopped[0]['payload']['id']=='P03'
    monitoring=[r for r in records if r['record_type']=='process_memory_monitor_started']
    assert len(monitoring)==1
    elapsed=(datetime.fromisoformat(stopped[0]['created_at_utc'])-
             datetime.fromisoformat(monitoring[0]['created_at_utc'])).total_seconds()
    assert 899 <= elapsed <= 910,'Only the declared fifteen-minute deadline is eligible'
    ready=[r for r in records if r['record_type']=='runtime_ready']
    closed=[r for r in records if r['record_type']=='runtime_closed']
    assert len(ready)==len(closed)==1
    for row in ready+closed:
        effect=row['payload']['effective_runtime']
        assert effect['full_offload'] and effect['context_matches'] and effect['q4_k_and_v'] and effect['mtp_disabled']
        assert not effect['cuda_failure_observed'] and not effect['truncation_observed']
    assert closed[0]['payload']['owned_server_shutdown_verified'] and result['port_free']
    assert result['process_memory']['samples']>0 and result['process_memory']['unavailable_messages']==[]
    return 'two descriptive measurements; repeatability and performance cause remain unqualified'

def require_apparatus():
    folder=study.AREA/'apparatus_qualification/run-001'
    seal=study.read(folder/'SEAL.json')
    assert sha256_bytes(canonical_json_bytes(seal['files']))==seal['aggregate_sha256']
    for row in seal['files']:
        assert sha256_file(folder/row['path'])==row['sha256']
    for name,digest in seal['private_runtime_files_local_only'].items():
        assert sha256_file(folder/'private-runtime'/name)==digest
    result=study.read(folder/'RESULT.json')
    assert result['behavioral_operations']==0 and result['runtime_policy_changed'] is False
    if result['status']=='completed':
        assert result['completion_requests']==4 and result['port_free'] and result['stable_all_responses_returned']
    else:
        decision=study.read(study.AREA/'review/APPARATUS-DECISION-001.json')
        assert decision['status']=='prospective_reduced_apparatus_basis'
        assert decision['apparatus_seal_sha256']==sha256_file(folder/'SEAL.json')
        assert not decision['repetition_or_causal_speed_qualified'] and not decision['actor_policy_changes']
        for field,name in (('verification_sha256','APPARATUS-VERIFICATION-001.json'),
                           ('metrics_sha256','APPARATUS-METRICS-001.json'),
                           ('review_sha256','APPARATUS-RESULTS-001.md')):
            assert sha256_file(study.AREA/'review'/name)==decision[field]
        assert study.read(folder/'FAILED.json')==dict(type='ResponseFailure',message='TimeoutError')
        records=verify_records(folder/'records.jsonl',folder)
        assert len(records)==seal['record_count']
        _timebox_basis(result,records)
        for index,condition in ((1,'unchanged'),(2,'released')):
            stem=folder/f'calls/P{index:02d}'
            raw=study.read(stem.with_name(stem.name+'-endpoint-response.json'))
            request=study.read(stem.with_name(stem.name+'-wire-request.json'))
            old=study.Task(condition).PACKAGE
            expected=copy.deepcopy(study.read(old/'initial-wire-request.json'))
            expected['max_tokens']=expected['n_predict']=32
            assert request==expected
            assert stem.with_name(stem.name+'-native.txt').read_bytes()==(old/'admission/I0001-native.txt').read_bytes()
            usage,timing=raw['usage'],raw['timings']
            assert usage['prompt_tokens']==study.read(old/'QUALIFICATION.json')['initial']['prompt_tokens']
            assert usage['completion_tokens']==32 and usage['prompt_tokens_details']['cached_tokens']==timing['cache_n']==0
    return sha256_file(folder/'SEAL.json')

def run_once(module):
    manifest=verify_preparation(module)
    apparatus_sha=require_apparatus()
    assert manifest['apparatus_decision_sha256']==sha256_file(study.AREA/'review/APPARATUS-DECISION-001.json')
    assert not module.RUN.exists(),'Attempt exists; no retry'
    module.RUN.mkdir()
    store=ArtifactStore(module.RUN)
    log=runner.RunLog(module.RUN/'records.jsonl','ecological-information-transition',task_module=module)
    log.append('attempt_reserved',dict(condition=module.condition,owner_direction=module.OWNER_DIRECTION,
        apparatus_seal_sha256=apparatus_sha,manifest_sha256=sha256_file(module.MANIFEST),
        apparatus_decision_sha256=manifest['apparatus_decision_sha256'],performance_cause_and_repeatability_unqualified=True),
        [store.put('EXECUTION_MANIFEST.json',module.MANIFEST.read_bytes()),
         store.put('SPEC.md',(module.AREA/'SPEC.md').read_bytes())])
    session=adapter=error=outcome=None
    try:
        session,adapter=module.initial_session(),Adapter(module)
        module.attach_observations(session,module.RUN,log)
        declared_entry(module,session)
        server,model,_=module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=module.RUN),store,log) as url:
            with memory_monitor.monitor(module.RUN,RUNTIME.PORT,log):
                loop=runner.Loop(module.RUN,store,log,url=url,task_module=adapter,
                    source_check=lambda:module.verify_sources(manifest['source_sha256']),initial=manifest['initial'])
                outcome=loop.execute(session)
                module.base.pilot.health(module.RUN)
    except BaseException as problem:
        error=problem
        failure=store.put('FAILED.json',canonical_json_bytes(dict(type=type(problem).__name__,message=str(problem))))
        log.append('attempt_stopped',dict(error_type=type(problem).__name__,error=str(problem)),[failure])
        if session is not None:
            for name,value in (('stopped-state.json',canonical_json_bytes(module.snapshot(session))),
                ('stopped-candidate.json',module.candidate_bytes(session.candidate)),
                ('stopped-preceding-feedback.json',canonical_json_bytes(adapter.preceding_feedback))):
                store.put(name,value)
    finally:
        records,files=verify_records(module.RUN/'records.jsonl',module.RUN),RUNTIME.file_inventory(module.RUN)
        store.put('RESPONSE_SEAL.json',canonical_json_bytes(dict(
            disposition='stopped_without_retry' if error else outcome['disposition'],condition=module.condition,
            actor=module.ACTOR,source_sha256=manifest['source_sha256'],files=files,
            aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),record_count=len(records),
            sent_requests=sum(r['record_type']=='invocation_started' for r in records),
            returned_responses=sum(r['record_type']=='response_received' for r in records),
            processed_invocations=sum(r['record_type']=='invocation_completed' for r in records),
            inherited_requests=16,inherited_operations=24,actual_operations=session.calls_used if session else 24,
            new_operations=session.calls_used-24 if session else 0,
            cumulative_requests_used=session.requests_used if session else 16,
            memory=RUNTIME.memory_stats(module.RUN/'memory.csv'),
            runtime=RUNTIME.runtime_evidence(module.RUN/'private-runtime/server.stderr.log'),
            port_free=RUNTIME.port_free(RUNTIME.PORT),
            private_runtime_files_local_only={p.name:sha256_file(p)
                for p in (module.RUN/'private-runtime').glob('*') if p.is_file()})))
    if error:
        raise error
    print('Closed '+module.condition+': '+outcome['disposition'],flush=True)

def isolation():
    a,b=[study.Task(c) for c in study.CONDITIONS]
    ma,mb=verify_preparation(a),verify_preparation(b)
    ra,rb=[study.read(m.PACKAGE/'initial-wire-request.json') for m in (a,b)]
    va,vb=[study.load_json_strict(r['messages'][1]['content']) for r in (ra,rb)]
    changed={k for k in va['workspace'] if va['workspace'][k]!=vb['workspace'][k]}
    assert changed=={'working_set','visibility'}
    expected=copy.deepcopy(ra)
    expected['messages'][1]['content']=rb['messages'][1]['content']
    assert expected==rb
    expected=copy.deepcopy(va)
    expected['workspace']['working_set']['sources']=vb['workspace']['working_set']['sources']
    expected['workspace']['visibility']=vb['workspace']['visibility']
    assert expected==vb
    assert ma['source_sha256']==mb['source_sha256']
    proof=dict(status='isolated',changed_workspace_keys=sorted(changed),
        common_task_account_receipts_checker_transport_opportunity=True,
        native_prompt_tokens={c:m['initial']['prompt_tokens'] for c,m in zip(study.CONDITIONS,(ma,mb))},
        manifests={c:sha256_file(m.MANIFEST) for c,m in zip(study.CONDITIONS,(a,b))})
    with (study.AREA/'INITIAL-ISOLATION-001.json').open('xb') as stream:
        stream.write(canonical_json_bytes(proof))
    print(json.dumps(proof),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('prepare','run','isolation'))
    parser.add_argument('--condition',choices=study.CONDITIONS,default='unchanged')
    parser.add_argument('--version',default='001')
    args=parser.parse_args()
    if args.mode=='isolation':
        isolation()
    else:
        module=study.Task(args.condition,args.version)
        prepare(module) if args.mode=='prepare' else run_once(module)
