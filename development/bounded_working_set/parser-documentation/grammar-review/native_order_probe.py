"""Pinned native LLGuidance masks; vocabulary only, no context or inference."""
import ctypes as C
import hashlib
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AREA = ROOT.parent
BIN = Path("C:/Users/danmc/llama_cpp_b10434/llama-b10434-cuda-13.3")


class ModelParams(C.Structure):
    # Exact build 10434 / 7e4c0a968 include/llama.h, struct llama_model_params.
    _fields_ = [("devices", C.c_void_p), ("tensor_buft_overrides", C.c_void_p),
        ("n_gpu_layers", C.c_int32), ("split_mode", C.c_int), ("load_mode", C.c_int), ("main_gpu", C.c_int32),
        ("tensor_split", C.c_void_p), ("progress_callback", C.c_void_p),
        ("progress_callback_user_data", C.c_void_p), ("kv_overrides", C.c_void_p),
        ("vocab_only", C.c_bool), ("check_tensors", C.c_bool), ("use_extra_bufts", C.c_bool),
        ("no_host", C.c_bool), ("no_alloc", C.c_bool), ("load_mtp", C.c_bool)]


class Token(C.Structure):
    _fields_ = [("id", C.c_int32), ("logit", C.c_float), ("p", C.c_float)]


class Tokens(C.Structure):
    _fields_ = [("data", C.POINTER(Token)), ("size", C.c_size_t), ("selected", C.c_int64), ("sorted", C.c_bool)]


def fix_schema(schema):
    # Only top-level reply form property order changes. Every nested action and
    # every logical JSON constraint remains identical to the actual sent schema.
    result = json.loads(json.dumps(schema))
    for form in result["oneOf"]:
        form["properties"] = {key: form["properties"][key] for key in form["required"]}
    assert result == schema
    return result


def main():
    out = ROOT / "NATIVE_ORDER_PROBE.json"
    if out.exists():
        raise ValueError("preserve the completed probe")
    request = json.loads((AREA/"preparation-02/inputs/I0001-request.json").read_text())
    old = request["response_format"]["json_schema"]["schema"]
    fixed = fix_schema(old)
    final = json.loads((AREA/"turn-02/calls/T02-assistant-content.txt").read_text())
    wanted = {**final, "check_after": "public"}
    first = {"check_after": "public", **final}
    invalid = {**final, "check_after": "invented"}
    cases = [("legacy_emitted_reply", old, final, True),
             ("legacy_illustrated_combined_order", old, wanted, False),
             ("legacy_combined_tag_first", old, first, True),
             ("corrected_illustrated_combined_order", fixed, wanted, True),
             ("corrected_ordinary_reply", fixed, final, True),
             ("corrected_invalid_check", fixed, invalid, False)]
    rows = []
    with os.add_dll_directory(str(BIN)):
        lib = C.CDLL(str(BIN/"llama.dll"))
        common = C.CDLL(str(BIN/"llama-common.dll"))
        def bind(owner, name, result, *args):
            fn = getattr(owner, name)
            fn.restype, fn.argtypes = result, args
            return fn
        defaults = bind(lib, "llama_model_default_params", ModelParams)
        load = bind(lib, "llama_model_load_from_file", C.c_void_p, C.c_char_p, ModelParams)
        free_model = bind(lib, "llama_model_free", None, C.c_void_p)
        vocabulary = bind(lib, "llama_model_get_vocab", C.c_void_p, C.c_void_p)
        tokenize = bind(lib, "llama_tokenize", C.c_int32, C.c_void_p, C.c_char_p, C.c_int32,
                        C.POINTER(C.c_int32), C.c_int32, C.c_bool, C.c_bool)
        eos = bind(lib, "llama_vocab_eos", C.c_int32, C.c_void_p)
        # Exact exported name observed in the pinned DLL; declaration in sampling.h.
        sampler = bind(common, "?llama_sampler_init_llg@@YAPEAUllama_sampler@@PEBUllama_vocab@@PEBD1@Z",
                       C.c_void_p, C.c_void_p, C.c_char_p, C.c_char_p)
        apply = bind(lib, "llama_sampler_apply", None, C.c_void_p, C.POINTER(Tokens))
        accept = bind(lib, "llama_sampler_accept", None, C.c_void_p, C.c_int32)
        free_sampler = bind(lib, "llama_sampler_free", None, C.c_void_p)
        params = defaults()
        params.n_gpu_layers, params.vocab_only, params.load_mtp = 0, True, False
        launch = json.loads((AREA/"turn-02/private-runtime/launch.json").read_text())
        model = load(os.fsencode(launch[2]), params)
        if not model:
            raise ValueError("vocabulary loading failed")
        try:
            vocab = vocabulary(model)
            for name, schema, value, expected in cases:
                raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
                grammar = ("%llguidance {}\nstart: %json " + json.dumps(schema, ensure_ascii=False, separators=(",", ":"))).encode()
                smpl = sampler(vocab, b"lark", grammar)
                if not smpl:
                    raise ValueError("native matcher construction failed")
                try:
                    buf = (C.c_int32 * (len(raw)+16))()
                    count = tokenize(vocab, raw, len(raw), buf, len(buf), False, False)
                    if count < 0:
                        raise ValueError("tokenization failed")
                    ids = [*buf[:count], eos(vocab)]
                    rejected = None
                    for index, token_id in enumerate(ids):
                        item = Token(token_id, 0.0, 0.0)
                        data = Tokens(C.pointer(item), 1, -1, False)
                        apply(smpl, C.byref(data))
                        if not math.isfinite(data.data[0].logit):
                            rejected = dict(token_index=index, token_id=token_id, is_eos=index == count)
                            break
                        accept(smpl, token_id)
                    row = dict(name=name, accepted_including_eos=rejected is None, expected=expected,
                               rejected=rejected, token_count=count,
                               response_sha256=hashlib.sha256(raw).hexdigest(), grammar_sha256=hashlib.sha256(grammar).hexdigest())
                    rows.append(row)
                    (ROOT/(name+".json")).write_bytes(raw)
                    (ROOT/(name+".llguidance")).write_bytes(grammar)
                    print(row, flush=True)
                    if row["accepted_including_eos"] != expected:
                        raise AssertionError("native result differs from proposed diagnosis")
                finally:
                    free_sampler(smpl)
        finally:
            free_model(model)
    out.write_text(json.dumps(dict(status="passed", model_inference_calls=0,
        vocabulary_only=True, no_context_or_decode_calls=True, engine="pinned native LLGuidance",
        binaries={name:hashlib.sha256((BIN/name).read_bytes()).hexdigest() for name in ("llama.dll", "llama-common.dll")},
        cases=rows),indent=2),encoding="utf-8")


if __name__ == "__main__":
    main()
