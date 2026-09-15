"""Replay saved next-token masks; vocabulary only, no model inference or task actions."""
import ctypes as C
import importlib.util
import json
import math
import os
from pathlib import Path

from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / 'run-001'
PIN = 'development/bounded_working_set/parser-documentation/grammar-review/'


def main():
    output = HERE / 'channel-boundary-001'
    output.mkdir(exist_ok=False)
    layout_path = ROOT / PIN / 'native_order_probe_gbnf.py'
    spec = importlib.util.spec_from_file_location('pinned_layout', layout_path)
    layout = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(layout)
    binaries = json.loads((ROOT / PIN / 'NATIVE_GBNF_ORDER_PROBE.json').read_text())['binaries']
    assert {name: sha256_file(layout.BIN / name) for name in binaries} == binaries
    manifest = json.loads((RUN / 'EXECUTION_MANIFEST.json').read_text())
    request_path = RUN / 'calls/C01-wire-request.json'
    request = json.loads(request_path.read_text())
    grammar = request['grammar'].encode()
    # Use the same local model path resolver; no runtime server or model context.
    import live_task
    _, model_path, _ = live_task.runtime_paths()
    assert sha256_file(model_path) == live_task.ACTOR['model_sha256']
    native = (RUN / 'admission/I0001-native.txt').read_text(encoding='utf-8')
    assert native.endswith('<|im_start|>assistant\n<think>\n')
    observed = (RUN / 'calls/C01-assistant-reasoning.txt').read_text(encoding='utf-8')
    final = (RUN / 'calls/C01-assistant-content.txt').read_bytes()
    assert final == b''
    cases = [
        ('ordinary_thought_first', 'I need to inspect the source.', False, False),
        ('close_thinking_first', '</think>', False, False),
        ('json_start', '{', False, True),
        ('observed_reasoning_as_grammar_text', observed, True, True),
        ('observed_json_then_close_thinking', observed + '</think>', False, False),
        ('reasoning_then_final', 'Inspect the source.\n</think>\n' + observed, True, False),
    ]
    rows = []
    with os.add_dll_directory(str(layout.BIN)):
        lib = C.CDLL(str(layout.BIN / 'llama.dll'))
        def bind(name, result, *args):
            fn = getattr(lib, name)
            fn.restype, fn.argtypes = result, args
            return fn
        defaults = bind('llama_model_default_params', layout.ModelParams)
        load = bind('llama_model_load_from_file', C.c_void_p, C.c_char_p, layout.ModelParams)
        free = bind('llama_model_free', None, C.c_void_p)
        vocabulary = bind('llama_model_get_vocab', C.c_void_p, C.c_void_p)
        tokenize = bind('llama_tokenize', C.c_int32, C.c_void_p, C.c_char_p, C.c_int32,
                        C.POINTER(C.c_int32), C.c_int32, C.c_bool, C.c_bool)
        eos = bind('llama_vocab_eos', C.c_int32, C.c_void_p)
        sampler = bind('llama_sampler_init_grammar', C.c_void_p, C.c_void_p, C.c_char_p, C.c_char_p)
        apply = bind('llama_sampler_apply', None, C.c_void_p, C.POINTER(layout.Tokens))
        accept = bind('llama_sampler_accept', None, C.c_void_p, C.c_int32)
        release = bind('llama_sampler_free', None, C.c_void_p)
        params = defaults()
        params.n_gpu_layers, params.vocab_only, params.load_mtp = 0, True, False
        model = load(os.fsencode(model_path), params)
        assert model
        try:
            vocab = vocabulary(model)
            for name, text, include_eos, wanted in cases:
                raw = text.encode()
                (output / (name + '.txt')).write_bytes(raw)
                buf = (C.c_int32 * (len(raw) + 16))()
                # Special-token recognition is essential for </think>.
                count = tokenize(vocab, raw, len(raw), buf, len(buf), False, True)
                assert count >= 0
                ids = list(buf[:count]) + ([eos(vocab)] if include_eos else [])
                smpl = sampler(vocab, grammar, b'root')
                assert smpl
                try:
                    rejected = None
                    for index, token_id in enumerate(ids):
                        token = layout.Token(token_id, 0.0, 0.0)
                        candidates = layout.Tokens(C.pointer(token), 1, -1, False)
                        apply(smpl, C.byref(candidates))
                        if not math.isfinite(candidates.data[0].logit):
                            rejected = dict(index=index, token_id=token_id, is_eos=include_eos and index == count)
                            break
                        accept(smpl, token_id)
                    accepted = rejected is None
                    rows.append(dict(name=name, accepted=accepted, expected=wanted, include_eos=include_eos,
                                     rejected=rejected, token_count=count, sha256=sha256_bytes(raw)))
                    assert accepted == wanted, rows[-1]
                finally:
                    release(smpl)
        finally:
            free(model)
    result = dict(status='passed', cases=rows, model_inference_calls=0, task_operations=0,
                  vocabulary_only=True, binaries=binaries, model_sha256=live_task.ACTOR['model_sha256'],
                  wire_sha256=sha256_file(request_path), grammar_sha256=sha256_bytes(grammar),
                  native_sha256=sha256_file(RUN / 'admission/I0001-native.txt'),
                  script_sha256=sha256_file(Path(__file__)), layout_sha256=sha256_file(layout_path),
                  note='Masks replay user-grammar sampling; pinned server/sampler source establishes eager activation. No private draft is executed.')
    (output / 'RESULTS.json').write_bytes(canonical_json_bytes(result))
    files = [dict(path=p.relative_to(output).as_posix(), bytes=p.stat().st_size, sha256=sha256_file(p))
             for p in sorted(output.iterdir()) if p.is_file()]
    (output / 'SEAL.json').write_bytes(canonical_json_bytes(dict(files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files)))))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
