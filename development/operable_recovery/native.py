"""Actual pinned decoder grammar, vocabulary only: no model generation."""
import argparse
import copy
import ctypes as C
import json
import math
import os

import operable_task as study
from manage import load_helper, RUNTIME
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

REVIEW = 'development/bounded_working_set/parser-documentation/grammar-review/'


def cases():
    ref='SRC-'+'a'*64
    def reply(action,account=False):
        value=dict(discussion='A declared next operation.')
        if account:
            value['account']='The expectation remains provisional.'
        value['operation']=json.loads(canonical_json_bytes(action))
        return value
    exact=dict(action='work_on_exact',regions=[ref],results=[])
    inspection=dict(action='inspect_observation',observation='CHK-0001',stream='stderr',offset=0)
    yield 'joint_exact',reply(exact,True),True
    yield 'exact_alone',reply(exact),True
    yield 'inspect_observation',reply(inspection),True
    yield 'selection_page',reply(dict(action='selection_page',offset=8)),True
    yield 'empty_group',reply(dict(action='work_on_exact',regions=[],results=[])),True
    yield 'bad_region',reply({**exact,'regions':['SRC-a']}),False
    yield 'too_many_regions',reply({**exact,'regions':[ref]*17}),False
    yield 'missing_regions',reply(dict(action='work_on_exact',results=[])),False
    yield 'bad_stream',reply({**inspection,'stream':'invented'}),False
    yield 'bad_observation',reply({**inspection,'observation':'RES-0001'}),False
    yield 'negative_offset',reply({**inspection,'offset':-1}),False


def run(output):
    output.mkdir(parents=True,exist_ok=False)
    bound, rows = study.source_identities(),[]
    probe=load_helper('operable_native_layout',REVIEW+'native_order_probe_gbnf.py')
    converter_module=load_helper('operable_native_converter',REVIEW+'json_schema_to_grammar.py')
    try:
        original=study.read(study.ROOT/REVIEW/'NATIVE_GBNF_ORDER_PROBE.json')
        binaries={name:sha256_file(probe.BIN/name) for name in original['binaries']}
        assert binaries==original['binaries']
        assert sha256_file(study.ROOT/REVIEW/'json_schema_to_grammar.py')=='ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
        _,model_path,_=study.runtime_paths()
        assert sha256_file(model_path)==study.ACTOR['model_sha256']
        adapter=study.runner.Adapter(study.Task())
        wire=completion_request_bytes(adapter.request_for(study.initial_session().view()))
        study.save(output,'wire-request.json',wire)
        schema=json.loads(wire)['response_format']['json_schema']['schema']
        converter=converter_module.SchemaConverter(prop_order={},allow_fetch=False,dotall=False,raw_pattern=False)
        converter.visit(schema,'')
        grammar=converter.format_grammar().encode()
        study.save(output,'reply.gbnf',grammar)
        with os.add_dll_directory(str(probe.BIN)):
            lib=C.CDLL(str(probe.BIN/'llama.dll'))
            def bind(name,result,*args):
                function=getattr(lib,name);function.restype,function.argtypes=result,args
                return function
            defaults=bind('llama_model_default_params',probe.ModelParams)
            load=bind('llama_model_load_from_file',C.c_void_p,C.c_char_p,probe.ModelParams)
            free_model=bind('llama_model_free',None,C.c_void_p)
            vocabulary=bind('llama_model_get_vocab',C.c_void_p,C.c_void_p)
            tokenize=bind('llama_tokenize',C.c_int32,C.c_void_p,C.c_char_p,C.c_int32,C.POINTER(C.c_int32),C.c_int32,C.c_bool,C.c_bool)
            eos=bind('llama_vocab_eos',C.c_int32,C.c_void_p)
            sampler=bind('llama_sampler_init_grammar',C.c_void_p,C.c_void_p,C.c_char_p,C.c_char_p)
            apply=bind('llama_sampler_apply',None,C.c_void_p,C.POINTER(probe.Tokens))
            accept=bind('llama_sampler_accept',None,C.c_void_p,C.c_int32)
            free_sampler=bind('llama_sampler_free',None,C.c_void_p)
            params=defaults();params.n_gpu_layers,params.vocab_only,params.load_mtp=0,True,False
            model=load(os.fsencode(model_path),params)
            assert model
            try:
                vocab=vocabulary(model)
                for name,value,expected in cases():
                    raw=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()
                    study.save(output,name+'.json',raw)
                    smpl=sampler(vocab,grammar,b'root');assert smpl
                    try:
                        buffer=(C.c_int32*(len(raw)+16))()
                        count=tokenize(vocab,raw,len(raw),buffer,len(buffer),False,False);assert count>=0
                        rejected=None
                        for index,token_id in enumerate([*buffer[:count],eos(vocab)]):
                            token=probe.Token(token_id,0.0,0.0)
                            tokens=probe.Tokens(C.pointer(token),1,-1,False)
                            apply(smpl,C.byref(tokens))
                            if not math.isfinite(tokens.data[0].logit):
                                rejected=dict(index=index,token_id=token_id,is_eos=index==count);break
                            accept(smpl,token_id)
                        row=dict(name=name,accepted_including_eos=rejected is None,expected=expected,
                                 rejected=rejected,token_count=count,response_sha256=sha256_bytes(raw))
                        rows.append(row);study.save(output,name+'-result.json',row)
                        assert row['accepted_including_eos']==expected
                        print(name,expected,flush=True)
                    finally:
                        free_sampler(smpl)
            finally:
                free_model(model)
        study.save(output,'RESULTS.json',dict(status='passed',cases=rows,source_sha256=bound,
            model_inference_calls=0,vocabulary_only=True,no_context_or_decode_calls=True,
            binaries=binaries,model_sha256=study.ACTOR['model_sha256'],wire_sha256=sha256_bytes(wire)))
    except BaseException as error:
        study.save(output,'FAILED.json',dict(type=type(error).__name__,message=str(error),source_sha256=bound))
        raise
    finally:
        files=RUNTIME.file_inventory(output)
        study.save(output,'SEAL.json',dict(files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',default='native-001')
    run(study.AREA/parser.parse_args().folder)
