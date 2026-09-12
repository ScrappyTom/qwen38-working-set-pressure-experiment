"""Prepare and conduct at most two separately recorded nonexecuting Qwen turns."""
from __future__ import annotations
import argparse
import copy
from pathlib import Path
import time
from types import SimpleNamespace

import prepare_incident_pressure as task
import qualify_compiler_delivery as probe
import saved_work_continuation as work
import run_saved_work_continuation as finished
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count

prep,base,require=task.pilot,task.base,task.require
AREA=prep.ROOT/'development/saved_work_dialogue'
SOURCE_SEAL='99055e218584b886244f7312a2fb6dde75859b1029c00331a613721b3cb827fe'
OLD=finished.RUN/'admission/P2-07-C09-x014'


def identities():
    paths=[Path(__file__),prep.ROOT/'scripts/delivery_dialogue.py',
        prep.ROOT/'scripts/qualify_compiler_delivery.py',
        prep.ROOT/'tests/test_saved_work_dialogue.py',AREA/'SPEC.md',AREA/'SYSTEM.txt',AREA/'QUESTION_1.txt',
        Path(str(OLD)+'-endpoint-request.json'),Path(str(OLD)+'-native.txt'),
        finished.RUN/'RESPONSE_SEAL.json',work.AREA/'review/DECISION.json']
    return {**work.sources(),**{p.relative_to(prep.ROOT).as_posix():sha256_file(p) for p in paths}}


def verify_source():
    require(sha256_file(finished.RUN/'RESPONSE_SEAL.json')==SOURCE_SEAL,'source seal differs')
    finished.check_sources(work.read(finished.MANIFEST))
    seal=base.verify_seal(finished.RUN)
    require(seal['actor']==work.ACTOR,'source actor differs')
    decision=work.read(work.AREA/'review/DECISION.json')
    require(decision['complete_direct_transcript_review'] and decision['response_seal_sha256']==SOURCE_SEAL,
            'source review is incomplete or unbound')
    return seal


class DialogueLog(finished.RunLog):
    def append(self,kind,payload,artifacts):
        if kind=='invocation_completed':
            payload={**payload,
                'runtime_helper_within_proposed_generation_reserve':payload['within_proposed_generation_reserve'],
                'within_proposed_generation_reserve':payload['usage']['completion_tokens']<=work.ACTOR['generation_reserve']}
        return super().append(kind,payload,artifacts)


def initial_request():
    require(sha256_file(finished.RUN/'RESPONSE_SEAL.json')==SOURCE_SEAL,'historical seal differs')
    old=load_json_strict(Path(str(OLD)+'-endpoint-request.json').read_bytes())
    request=copy.deepcopy(old);request.pop('response_format');request['seed']=42
    supplied='\n\n'.join('BEGIN EXACT HISTORICAL '+m['role'].upper()+' MESSAGE\n'+m['content']+
        '\nEND EXACT HISTORICAL '+m['role'].upper()+' MESSAGE' for m in old['messages'])
    request['messages']=[dict(role='system',content=(AREA/'SYSTEM.txt').read_text(encoding='utf-8')),
        dict(role='user',content=(AREA/'QUESTION_1.txt').read_text(encoding='utf-8')+'\n\n'+supplied)]
    validate(request)
    return request


def validate(request):
    roles=[m['role'] for m in request['messages']]
    require(roles in (['system','user'],['system','user','assistant','user']),'unexpected conversation roles')
    require(all(set(m)=={'role','content'} and isinstance(m['content'],str) and m['content'].strip()
                for m in request['messages']),'invalid conversation message')
    require(not any(k in request for k in ('response_format','tools','functions')),'execution channel in consultation')
    fresh=copy.deepcopy(request);fresh['messages']=fresh['messages'][:2]
    base.validate_request(fresh)


def request_for(turn,follow_up=None):
    require(turn in (1,2),'unsupported turn')
    request=initial_request()
    if turn==2:
        first=AREA/'turn-01';seal=base.verify_seal(first)
        require(seal['disposition']=='completed_dialogue_turn' and seal['sent_requests']==1,'first turn not complete')
        require(seal['source_sha256']==identities(),'source changed between turns')
        require((first/'calls/D1-endpoint-request.json').read_bytes()==canonical_json_bytes(request),'origin differs')
        require(follow_up is not None and follow_up.is_file(),'saved adaptive follow-up required')
        request['messages'] += [dict(role='assistant',content=(first/'calls/D1-assistant-content.txt').read_bytes().decode()),
                               dict(role='user',content=follow_up.read_bytes().decode())]
    validate(request)
    return request


def prepare(tokenizer):
    output=AREA/'preparation-001'
    require(not output.exists(),'preparation exists; preserve it')
    manifest=verify_source()
    launch=probe.read(finished.RUN/'private-runtime/launch.json')
    require(sha256_file(tokenizer)==probe.TOKENIZER_SHA,'tokenizer differs')
    require(sha256_file(Path(launch[2]))==manifest['actor']['model_sha256'],'model differs')
    request=initial_request()
    original=probe.read(Path(str(OLD)+'-endpoint-request.json'))
    # Seed/output grammar do not enter this saved text envelope. Actual server
    # rendering must confirm exact equality before the first completion.
    envelope=copy.deepcopy(original);envelope.pop('response_format');envelope['seed']=42
    native=probe.native_for(request,envelope,Path(str(OLD)+'-native.txt').read_bytes().decode())
    count=tokenizer_count(SimpleNamespace(model_path=Path(launch[2]),tokenizer_path=tokenizer),native)
    require(count<=prep.INPUT_CEILING,'prepared input exceeds existing admission ceiling')
    output.mkdir(parents=True)
    (output/'D1-endpoint-request.json').write_bytes(canonical_json_bytes(request))
    (output/'D1-native.txt').write_bytes(native)
    plan=dict(source_sha256=identities(),actor=prep.ACTOR,maximum_completion_requests=2,completion_calls=0,
        request_sha256=sha256_bytes(canonical_json_bytes(request)),native_sha256=sha256_bytes(native),prompt_tokens=count,
        physical_generation_space=56576-count,server_native_equality_required_before_dispatch=True,
        historical_seal_sha256=SOURCE_SEAL,tokenizer_sha256=probe.TOKENIZER_SHA)
    (output/'PREPARATION.json').write_bytes(canonical_json_bytes(plan))
    print(plan['prompt_tokens'],'input tokens;',plan['physical_generation_space'],'physical generation space; zero completions')


def run_turn(args):
    require(args.owner_direction.strip(),'owner direction required')
    plan=load_json_strict((AREA/'preparation-001/PREPARATION.json').read_bytes())
    require(plan['source_sha256']==identities(),'prepared sources differ')
    verify_source()
    request=request_for(args.turn,args.follow_up);pinned=identities();raw_request=canonical_json_bytes(request)
    output=AREA/f'turn-{args.turn:02d}'
    require(not output.exists(),'turn consumed; no retry or replacement')
    output.mkdir();args.output=output
    store,log=ArtifactStore(output),DialogueLog(output/'records.jsonl',f'saved-work-dialogue-{args.turn}')
    tag=f'D{args.turn}'
    log.append('turn_prepared',dict(owner_direction=args.owner_direction,maximum_dialogue_calls=2,turn=args.turn,
        source_sha256=pinned,historical_seal_sha256=SOURCE_SEAL,
        follow_up_sha256=sha256_file(args.follow_up) if args.turn==2 else None),
        [store.put('SPEC.md',(AREA/'SPEC.md').read_bytes()),store.put(f'calls/{tag}-endpoint-request.json',raw_request)])
    failure,disposition=None,'completed_dialogue_turn'
    try:
        with base.owned_runtime(args,store,log) as url:
            template,native,tokens,count=prep.render_only(url,request)
            log.append('invocation_prepared',dict(id=tag,prompt_tokens=count,physical_generation_space=56576-count,
                input_ceiling=prep.INPUT_CEILING,completion_sent=False),[store.put(f'calls/{tag}-template-response.json',template),
                store.put(f'calls/{tag}-rendered-prompt.txt',native),store.put(f'calls/{tag}-tokenization.json',tokens)])
            require(count<=prep.INPUT_CEILING,'native input exceeds planning allowance; no dispatch')
            if args.turn==1:
                require(sha256_bytes(raw_request)==plan['request_sha256'] and sha256_bytes(native)==plan['native_sha256']
                        and count==plan['prompt_tokens'],'actual first render differs from preparation')
            require(pinned==identities() and canonical_json_bytes(request_for(args.turn,args.follow_up))==raw_request,'input drift')
            log.append('invocation_started',dict(id=tag,prompt_tokens=count,**prep.health(output)),[])
            print(f'{tag} dispatched: {count} input, {56576-count} physical generation space',flush=True)
            started=time.monotonic()
            try:
                raw=base.post(url,'/v1/chat/completions',raw_request,base.HTTP_TIMEOUT_SECONDS)
            except base.ResponseFailure as error:
                log.append('response_failed',dict(id=tag,error_type=type(error).__name__,http_status=error.status),
                    [store.put(f'calls/{tag}-partial-response.bin',error.data)])
                raise
            outcome=base.receive_nonexecuting(store,log,dict(id=tag,stage='saved_work_dialogue',prompt_tokens=count),raw,time.monotonic()-started)
            require(outcome['physical_tokens_remaining']>=0,'physical accounting differs')
            require(pinned==identities() and canonical_json_bytes(request_for(args.turn,args.follow_up))==raw_request,'input drift during call')
            log.append('post_response_runtime_check',dict(id=tag,**prep.health(output)),[])
            log.append('next_turn_decision',dict(id=tag,next_request_sent=False,
                next_step='seal_and_directly_review_before_adaptive_follow_up' if args.turn==1 else 'seal_and_review'),[])
        closed=verify_records(output/'records.jsonl',output)[-1]
        require(closed['record_type']=='runtime_closed' and closed['payload']['owned_server_shutdown_verified']
                and closed['payload']['dedicated_port_free'],'runtime closure incomplete')
    except BaseException as error:
        failure,disposition=error,'stopped_without_retry'
        detail=str(error)
        for path in (args.model,args.server,output): detail=detail.replace(str(path),'<local path>')
        log.append('turn_stopped',dict(error_type=type(error).__name__,error=detail),[])
    finally:
        log.append('turn_closed',dict(disposition=disposition,dedicated_port_free=base.port_free(base.PORT),
            owned_server_shutdown_verified=not base.running_process_ids(args.server.name)),[])
        records=verify_records(output/'records.jsonl',output);files=base.file_inventory(output)
        base.write_json(output/'RESPONSE_SEAL.json',dict(disposition=disposition,actor=prep.ACTOR,memory_policy=prep.cont.POLICY,
            source_sha256=pinned,sent_requests=sum(r['record_type']=='invocation_started' for r in records),record_count=len(records),
            files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),memory=base.memory_stats(output/'memory.csv'),
            effective_runtime=base.runtime_evidence(output/'private-runtime/server.stderr.log'),
            private_runtime_files_local_only={p.name:sha256_file(p) for p in (output/'private-runtime').glob('*') if p.is_file()}))
    if failure: raise failure
    print(tag+' closed and sealed; complete response awaits direct review',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare',action='store_true');p.add_argument('--tokenizer',type=Path)
    p.add_argument('--turn',type=int,choices=(1,2));p.add_argument('--follow-up',type=Path)
    p.add_argument('--model',type=Path);p.add_argument('--server',type=Path);p.add_argument('--owner-direction',default='')
    a=p.parse_args()
    if a.prepare:
        require(a.tokenizer is not None and a.turn is None,'preparation requires only tokenizer');prepare(a.tokenizer)
    else:
        require(a.turn in (1,2) and a.model is not None and a.server is not None,'missing execution arguments');run_turn(a)
