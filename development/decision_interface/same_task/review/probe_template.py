"""Read the pinned model's template without allocating a context or generating."""
import ctypes as C
import importlib.util
import json
import os
from pathlib import Path

import live_task
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

here = Path(__file__).resolve().parent
target = here / 'template-identification.json'
assert not target.exists()
layout_path = live_task.ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/native_order_probe_gbnf.py'
spec = importlib.util.spec_from_file_location('pinned_layout_template', layout_path)
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)
_, model_path, _ = live_task.runtime_paths()
assert sha256_file(model_path) == live_task.ACTOR['model_sha256']
with os.add_dll_directory(str(layout.BIN)):
    lib = C.CDLL(str(layout.BIN / 'llama.dll'))
    defaults = lib.llama_model_default_params
    defaults.restype, defaults.argtypes = layout.ModelParams, []
    load = lib.llama_model_load_from_file
    load.restype, load.argtypes = C.c_void_p, [C.c_char_p, layout.ModelParams]
    template = lib.llama_model_chat_template
    template.restype, template.argtypes = C.c_char_p, [C.c_void_p, C.c_char_p]
    free = lib.llama_model_free
    free.restype, free.argtypes = None, [C.c_void_p]
    params = defaults()
    params.n_gpu_layers, params.vocab_only, params.load_mtp = 0, True, False
    model = load(os.fsencode(model_path), params)
    assert model
    try:
        raw = template(model, None)
        assert raw
        (here / 'pinned-chat-template.txt').write_bytes(raw)
        result = dict(model_sha256=live_task.ACTOR['model_sha256'], template_sha256=sha256_bytes(raw),
                      bytes=len(raw), vocabulary_only=True, inference_calls=0,
                      markers={m: m.encode() in raw for m in ('<tool_call>', '<function=', '<parameter=', '<think>')},
                      script_sha256=sha256_file(Path(__file__)))
        target.write_bytes(canonical_json_bytes(result))
        print(json.dumps(result, indent=2))
    finally:
        free(model)
