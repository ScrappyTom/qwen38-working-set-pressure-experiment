"""Pinned vocabulary/grammar qualification; no context, decode or completion calls."""
import argparse
import ctypes as C
import json
import math
import os

import decision_task as study
from manage import load_helper, RUNTIME
from working_set_exp import decision_view
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

REVIEW='development/bounded_working_set/parser-documentation/grammar-review/'


def cases():
    header=dict(discussion='Save exact source.',operation=dict(action='replace_region',region='SRC-'+'a'*64,expected_candidate_id='b'*64))
    raw=json.dumps(header,separators=(',',':'))
    for name, body in [('multiline','x = "\\n"\n# é\n'),('empty',''),('crlf','a=1\r\n'),('separator_in_source','SOURCE\n{"text":"value"}\n')]:
        yield name,raw+'\nSOURCE\n'+body,True
    with_account=dict(discussion='Save.',account='Pending check.',operation=header['operation'])
    yield 'account_source',json.dumps(with_account)+'\nSOURCE\nx=1\n',True
    yield 'ordinary_inspection',json.dumps(dict(discussion='Inspect criteria.',operation=dict(action='inspect_check',observation='CHK-0020',offset=0))),True
    yield 'ordinary_json_replacement',json.dumps(dict(discussion='Replace.',operation={**header['operation'],'new':'x="\\n"\n'})),True
    yield 'truncated_header',raw[:-3],False
    yield 'missing_separator',raw+'\nx=1',False
    yield 'wrong_action_source',json.dumps(dict(discussion='Bad.',operation=dict(action='submit',expected_candidate_id='b'*64)))+'\nSOURCE\nx=1',False
    yield 'bad_region',raw.replace('SRC-'+'a'*64,'SRC-x')+'\nSOURCE\nx=1',False
    yield 'multiline_header',json.dumps(header,indent=2)+'\nSOURCE\nx=1',False


def run(folder):
    folder.mkdir(parents=True,exist_ok=False)
    rows=[]
    bound=study.source_identities()
    probe=load_helper('decision_native_layout',REVIEW+'native_order_probe_gbnf.py')
    try:
        expected=study.read(study.ROOT/REVIEW/'NATIVE_GBNF_ORDER_PROBE.json')['binaries']
        binaries={name:sha256_file(probe.BIN/name) for name in expected}
        assert binaries==expected
        _,model_path,_=study.runtime_paths()
        assert sha256_file(model_path)==study.ACTOR['model_sha256']
        adapter=study.runner.Adapter(study.Task())
        request=adapter.request_for(study.initial_session().view())
        wire=completion_request_bytes(request)
        assert 'response_format' not in request
        study.save(folder,'wire-request.json',wire)
        grammar=request['grammar'].encode()
        study.save(folder,'reply.gbnf',grammar)
        with os.add_dll_directory(str(probe.BIN)):
            lib=C.CDLL(str(probe.BIN/'llama.dll'))
            def bind(name,result,*args):
                fn=getattr(lib,name);fn.restype,fn.argtypes=result,args;return fn
            defaults=bind('llama_model_default_params',probe.ModelParams)
            load=bind('llama_model_load_from_file',C.c_void_p,C.c_char_p,probe.ModelParams)
            free=bind('llama_model_free',None,C.c_void_p)
            vocabulary=bind('llama_model_get_vocab',C.c_void_p,C.c_void_p)
            tokenize=bind('llama_tokenize',C.c_int32,C.c_void_p,C.c_char_p,C.c_int32,C.POINTER(C.c_int32),C.c_int32,C.c_bool,C.c_bool)
            eos=bind('llama_vocab_eos',C.c_int32,C.c_void_p)
            sampler=bind('llama_sampler_init_grammar',C.c_void_p,C.c_void_p,C.c_char_p,C.c_char_p)
            apply=bind('llama_sampler_apply',None,C.c_void_p,C.POINTER(probe.Tokens))
            accept=bind('llama_sampler_accept',None,C.c_void_p,C.c_int32)
            release=bind('llama_sampler_free',None,C.c_void_p)
            params=defaults();params.n_gpu_layers,params.vocab_only,params.load_mtp=0,True,False
            model=load(os.fsencode(model_path),params);assert model
            try:
                vocab=vocabulary(model)
                for name,text,wanted in cases():
                    raw=text.encode()
                    study.save(folder,name+'.txt',raw)
                    smpl=sampler(vocab,grammar,b'root');assert smpl
                    try:
                        buf=(C.c_int32*(len(raw)+16))()
                        count=tokenize(vocab,raw,len(raw),buf,len(buf),False,False);assert count>=0
                        rejected=None
                        for index,token_id in enumerate([*buf[:count],eos(vocab)]):
                            token=probe.Token(token_id,0.0,0.0);tokens=probe.Tokens(C.pointer(token),1,-1,False)
                            apply(smpl,C.byref(tokens))
                            if not math.isfinite(tokens.data[0].logit):
                                rejected=dict(index=index,token_id=token_id,is_eos=index==count);break
                            accept(smpl,token_id)
                        valid=rejected is None
                        if wanted:
                            decoded=decision_view.decode_reply(text)
                            study.save(folder,name+'-decoded.json',decoded)
                        rows.append(dict(name=name,accepted_including_eos=valid,expected=wanted,rejected=rejected,sha256=sha256_bytes(raw)))
                        assert valid==wanted,(name,rejected)
                    finally:
                        release(smpl)
            finally:
                free(model)
        assert study.source_identities()==bound, 'implementation changed during native qualification'
        study.save(folder,'RESULTS.json',dict(status='passed',cases=rows,model_inference_calls=0,vocabulary_only=True,binaries=binaries,wire_sha256=sha256_bytes(wire)))
    except BaseException as error:
        study.save(folder,'FAILED.json',dict(type=type(error).__name__,message=str(error),cases=rows))
        raise
    finally:
        files=RUNTIME.file_inventory(folder)
        study.save(folder,'SEAL.json',dict(files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),source_sha256=bound))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',default='native-001')
    run(study.AREA/p.parse_args().folder)
