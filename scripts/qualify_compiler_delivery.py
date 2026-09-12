"""Offline capacity probes on sealed compiler evidence; no HTTP or completion path."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from types import SimpleNamespace

from working_set_exp.event_frame_v3 import event_from_pair_v3, resident_pair_v3, verify_event_sequence_v3
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count

ROOT = Path(__file__).resolve().parents[1]
AREA = ROOT / 'development/compiler_incident'
RUN = AREA / 'run-001'
DEST = AREA / 'delivery-qualification'
SEAL_SHA = 'f8135f0fe20734fcbe90707a9bbe792fecee1acc89b315ce588f0dfc4c015cf5'
TOKENIZER_SHA = 'd435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c'
CASES = [('C01',22),('C02',20),('C01',29),('C02',28)]
GROUPS = {
    'local_repair': ['README.md','compiler/unary.py'],
    'report_A': ['README.md','reports/incident.json','OBS-0001','OBS-0002'],
    'report_both': ['README.md','reports/incident.json','OBS-0001','OBS-0002','OBS-0003'],
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return load_json_strict(path.read_bytes())


def state_of(request):
    require([m['role'] for m in request['messages']] == ['system','user'], 'unexpected message shape')
    return load_json_strict(request['messages'][1]['content'].encode())


def native_for(request, original, native):
    """Substitute exact text only within a verified, unchanged two-message envelope."""
    require(set(request) == set(original), 'request key drift')
    require({k:v for k,v in request.items() if k!='messages'} ==
            {k:v for k,v in original.items() if k!='messages'}, 'model/grammar/settings drift')
    require([m['role'] for m in request['messages']] == ['system','user'], 'unexpected roles')
    system, user = [m['content'].strip() for m in original['messages']]
    require(native.count(system) == native.count(user) == 1, 'ambiguous native envelope')
    before, after = native.split(system)
    middle, tail = after.split(user)
    require(before.endswith('<|im_start|>system\n') or '<|im_start|>system\n' in before,
            'unexpected system envelope')
    require(middle == '<|im_end|>\n<|im_start|>user\n', 'unexpected message separator')
    require(tail == '<|im_end|>\n<|im_start|>assistant\n<think>\n', 'unexpected thinking envelope')
    return (before + request['messages'][0]['content'].strip() + middle +
            request['messages'][1]['content'].strip() + tail).encode()


def exact_pairs_match(request, pairs):
    events=state_of(request)['active_phase_event_frame']['events']
    require(len(events)==len(pairs), 'pair count mismatch')
    expected=[event_from_pair_v3(p['response'],p['result'],sequence=i,payload_residency='external')
              for i,p in enumerate(pairs,1)]
    require(events==expected, 'saved all-external events differ from exact pairs')


def grouped_request(original, pairs, retained):
    require(all(type(i) is int and 1<=i<=len(pairs) for i in retained), 'invalid retained sequence')
    request=copy.deepcopy(original)
    state=state_of(request)
    frame=state['active_phase_event_frame']
    frame.pop('externalized_payload_through_sequence')
    frame['schema_version']='development-exact-event-selected-residency-probe-v1'
    frame['resident_payload_sequences']=sorted(retained)
    frame['events']=[event_from_pair_v3(p['response'],p['result'],sequence=i,
        payload_residency='resident' if i in retained else 'external') for i,p in enumerate(pairs,1)]
    state['event_frame_verification']=verify_event_sequence_v3(frame['events'])
    for i in retained:
        require(resident_pair_v3(frame['events'][i-1])==pairs[i-1], 'body delivery identity differs')
    request['messages'][1]['content']=canonical_json_bytes(state).decode()
    return request


def material_sequence(pairs, material, file_hashes):
    """Use the latest actual acquisition; old candidate IDs are valid only for unchanged files."""
    for i in range(len(pairs),0,-1):
        result=pairs[i-1]['result']
        if not result.get('accepted'):
            continue
        if material.startswith('OBS-'):
            if result.get('handle')==material and 'exact_result_utf8' in result:
                require(sha256_bytes(result['exact_result_utf8'].encode())==result['exact_result_sha256'], 'capture identity differs')
                return i
            continue
        if 'exact_result_utf8' in result:
            raw=result['exact_result_utf8'].encode()
            require(sha256_bytes(raw)==result['exact_result_sha256'], 'recovered result identity differs')
            result=load_json_strict(raw)
        if result.get('path')!=material or 'content' not in result:
            continue
        content=result['content'].encode()
        if (result.get('file_sha256')==file_hashes.get(material)
                and sha256_bytes(content)==file_hashes[material]
                and result.get('returned_start_line')==1 and result.get('next_start_line') is None):
            return i
    raise ValueError('no acquired complete current material: '+material)


def verify_originals():
    require(sha256_file(RUN/'RESPONSE_SEAL.json')==SEAL_SHA, 'original seal changed')
    seal=read(RUN/'RESPONSE_SEAL.json')
    for item in seal['files']:
        p=RUN/item['path']
        require(p.stat().st_size==item['size_bytes'] and sha256_file(p)==item['sha256'], 'original changed: '+item['path'])
    manifest=read(AREA/'EXECUTION_MANIFEST.json')
    require(sha256_file(AREA/'EXECUTION_MANIFEST.json')==seal['execution_manifest_sha256'], 'manifest changed')
    for name,digest in manifest['execution_source_sha256'].items():
        require(sha256_file(ROOT/name)==digest, 'frozen source changed: '+name)
    return manifest


def qualify(tokenizer, output):
    require(not output.exists(), 'output already exists; preserve the prior attempt')
    manifest=verify_originals()
    launch=read(RUN/'private-runtime/launch.json')
    model=Path(launch[2])
    require(sha256_file(model)==manifest['actor']['model_sha256'], 'model identity changed')
    require(sha256_file(tokenizer)==TOKENIZER_SHA, 'tokenizer changed')
    profile=SimpleNamespace(model_path=model,tokenizer_path=tokenizer)
    output.mkdir(parents=True)
    counts={}
    def save(name,raw):
        p=output/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    def count(raw):
        if raw not in counts: counts[raw]=tokenizer_count(profile,raw)
        return counts[raw]
    rows=[]
    try:
        for cell,n in CASES:
            tag=f'{cell}-X16000-{n+1:03d}-x{n:03d}'
            stem=RUN/'admission'/tag
            original=read(Path(str(stem)+'-endpoint-request.json'))
            native=Path(str(stem)+'-native.txt').read_bytes().decode()
            require(native_for(original,original,native)==native.encode(), 'original envelope replay differs')
            pairs=read(RUN/'segments'/f'{cell}-X16000-pairs.json')[:n]
            exact_pairs_match(original,pairs)
            candidate=read(Path(str(stem)+'-candidate.json'))
            hashes={f['path']:f['sha256'] for f in candidate['files']}
            recorded=count(native.encode())
            require(recorded==len(read(Path(str(stem)+'-tokens.json'))['tokens']), 'original tokenizer disagreement')
            materials={m:material_sequence(pairs,m,hashes) for m in set(sum(GROUPS.values(),[]))}
            selections={'all_external_probe':set(), 'newest_only':{n}}
            selections.update({name:{n,*[materials[m] for m in group]} for name,group in GROUPS.items()})
            row=dict(id=tag,recorded_input=recorded,original_request_sha256=sha256_file(Path(str(stem)+'-endpoint-request.json')),
                     recorded_next_request_sent=n in (20,22),actions_remaining=32-n,material_sequences=materials,variants=[])
            for name,selected in selections.items():
                req=grouped_request(original,pairs,selected)
                raw=native_for(req,original,native)
                tokens=count(raw)
                save(f'{tag}/{name}-request.json',canonical_json_bytes(req))
                save(f'{tag}/{name}-native.txt',raw)
                row['variants'].append(dict(name=name,retained_sequences=sorted(selected),input_tokens=tokens,
                    fits_16000=tokens<=16000,fits_23808=tokens<=23808,physical_generation_space=56576-tokens,
                    delta_from_recorded=tokens-recorded,completion_sent=False))
            # Remove complete components only for marginal cost measurement; these are not usable inputs.
            for name in ('event_history','system_content'):
                req=copy.deepcopy(original)
                if name=='event_history':
                    state=state_of(req);state.pop('active_phase_event_frame');state.pop('event_frame_verification')
                    req['messages'][1]['content']=canonical_json_bytes(state).decode()
                else:
                    req['messages'][0]['content']=''
                raw=native_for(req,original,native)
                tokens=count(raw)
                save(f'{tag}/cost-only-without-{name}.txt',raw)
                row.setdefault('cost_ablations',[]).append(dict(removed=name,input_tokens=tokens,
                    marginal_tokens=recorded-tokens,not_an_executable_input=True))
            rows.append(row)
            print(json.dumps(dict(id=tag,recorded=recorded,variants={v['name']:v['input_tokens'] for v in row['variants']})),flush=True)
        verify_originals()
        result=dict(status='offline_capacity_measured_no_completions',original_seal_sha256=SEAL_SHA,
            actor=manifest['actor'],tokenizer_sha256=TOKENIZER_SHA,cases=rows,distinct_tokenizer_calls=len(counts),
            source_sha256={p.relative_to(ROOT).as_posix():sha256_file(p) for p in
                (Path(__file__),DEST/'SPEC.md',ROOT/'tests/test_compiler_delivery.py')},
            representation='reviewer-selected exact payload residency; frozen runner and archive unchanged',
            live_requests=0,operating_host_changed=False,model_selected_groups=False,
            limitation='Capacity probes and nonexecutable cost ablations, not action or task success; no output bound.')
        save('MEASUREMENTS.json',canonical_json_bytes(result))
        files=[dict(path=p.relative_to(output).as_posix(),sha256=sha256_file(p),size_bytes=p.stat().st_size)
               for p in sorted(output.rglob('*')) if p.is_file()]
        save('SEAL.json',canonical_json_bytes(dict(files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files)))))
        return result
    except BaseException as error:
        save('FAILED.json',canonical_json_bytes(dict(error_type=type(error).__name__,error=str(error),completed_cases=rows)))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=DEST/'offline-001')
    args=parser.parse_args()
    qualify(args.tokenizer,args.output)
