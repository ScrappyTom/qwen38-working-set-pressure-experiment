"""Qualify the implemented wire serializer with the pinned native GBNF sampler.

Loads only the model vocabulary. No model context, decode, endpoint or inference
call is made. Historical case files and the original stopped-backend probe stay
untouched. The output directory is exclusive and failures are preserved.
"""
import argparse
import ctypes as C
import importlib.util
import json
import math
import os
from pathlib import Path

import parser_documentation_session as task
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def qualify(output):
    output.mkdir(parents=True, exist_ok=False)
    review = task.AREA / "grammar-review"
    probe = module_at("recorded_gbnf_probe", review / "native_order_probe_gbnf.py")
    converter_module = module_at("pinned_schema_converter", review / "json_schema_to_grammar.py")
    sources = [Path(__file__), task.base.ROOT / "src/working_set_exp/contribution_reply.py",
               task.base.ROOT / "scripts/parser_documentation_session.py",
               review / "native_order_probe_gbnf.py", review / "json_schema_to_grammar.py"]
    bindings = {p.relative_to(task.base.ROOT).as_posix(): sha256_file(p) for p in sources}
    try:
        original = (task.AREA / "preparation-02/inputs/I0001-request.json").read_bytes()
        request = load_json_strict(original)
        wire = task.completion_request_bytes(request)
        decoded = load_json_strict(wire)
        assert decoded == request and canonical_json_bytes(decoded) == original
        assert task.base.expected_native(decoded) == task.base.expected_native(request)
        task.base.save(output, "wire-request.json", wire)
        fixed = decoded["response_format"]["json_schema"]["schema"]
        old = request["response_format"]["json_schema"]["schema"]
        final = load_json_strict((task.AREA / "turn-02/calls/T02-assistant-content.txt").read_bytes())
        combined = {**final, "check_after": "public"}
        missing_guard = json.loads(json.dumps(combined))
        del missing_guard["operation"]["expected_file_sha256"]
        cases = [("legacy_illustrated_combined", old, combined, False),
                 ("implemented_combined", fixed, combined, True),
                 ("implemented_ordinary", fixed, final, True),
                 ("implemented_discussion", fixed, dict(discussion="Which source applies?"), True),
                 ("unsupported_check", fixed, {**final, "check_after": "invented"}, False),
                 ("missing_pre_edit_guard", fixed, missing_guard, False)]
        old_evidence = task.base.read(review / "NATIVE_GBNF_ORDER_PROBE.json")
        binaries = {name: sha256_file(probe.BIN / name) for name in old_evidence["binaries"]}
        assert binaries == old_evidence["binaries"]
        assert sha256_file(review / "json_schema_to_grammar.py") == "ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3"
        _, model_path, _ = task.base.runtime_paths()
        assert sha256_file(model_path) == task.base.ACTOR["model_sha256"]
        rows = []
        with os.add_dll_directory(str(probe.BIN)):
            lib = C.CDLL(str(probe.BIN / "llama.dll"))
            def bind(name, result, *args):
                function = getattr(lib, name)
                function.restype, function.argtypes = result, args
                return function
            defaults = bind("llama_model_default_params", probe.ModelParams)
            load = bind("llama_model_load_from_file", C.c_void_p, C.c_char_p, probe.ModelParams)
            free_model = bind("llama_model_free", None, C.c_void_p)
            vocabulary = bind("llama_model_get_vocab", C.c_void_p, C.c_void_p)
            tokenize = bind("llama_tokenize", C.c_int32, C.c_void_p, C.c_char_p, C.c_int32,
                            C.POINTER(C.c_int32), C.c_int32, C.c_bool, C.c_bool)
            eos = bind("llama_vocab_eos", C.c_int32, C.c_void_p)
            sampler = bind("llama_sampler_init_grammar", C.c_void_p, C.c_void_p, C.c_char_p, C.c_char_p)
            apply = bind("llama_sampler_apply", None, C.c_void_p, C.POINTER(probe.Tokens))
            accept = bind("llama_sampler_accept", None, C.c_void_p, C.c_int32)
            free_sampler = bind("llama_sampler_free", None, C.c_void_p)
            params = defaults()
            params.n_gpu_layers, params.vocab_only, params.load_mtp = 0, True, False
            model = load(os.fsencode(model_path), params)
            if not model:
                raise ValueError("vocabulary loading failed")
            try:
                vocab = vocabulary(model)
                for name, schema, value, expected in cases:
                    converter = converter_module.SchemaConverter(prop_order={}, allow_fetch=False,
                                                                   dotall=False, raw_pattern=False)
                    converter.visit(schema, "")
                    grammar = converter.format_grammar().encode()
                    if schema is fixed:
                        assert grammar == (review / "corrected_illustrated_combined_order.gbnf").read_bytes()
                    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
                    task.base.save(output, name + ".json", raw)
                    task.base.save(output, name + ".gbnf", grammar)
                    smpl = sampler(vocab, grammar, b"root")
                    if not smpl:
                        raise ValueError("native grammar initialization failed")
                    try:
                        buffer = (C.c_int32 * (len(raw) + 16))()
                        count = tokenize(vocab, raw, len(raw), buffer, len(buffer), False, False)
                        if count < 0:
                            raise ValueError("tokenization buffer insufficient")
                        rejected = None
                        for index, token_id in enumerate([*buffer[:count], eos(vocab)]):
                            token = probe.Token(token_id, 0.0, 0.0)
                            tokens = probe.Tokens(C.pointer(token), 1, -1, False)
                            apply(smpl, C.byref(tokens))
                            if not math.isfinite(tokens.data[0].logit):
                                rejected = dict(token_index=index, token_id=token_id, is_eos=index == count)
                                break
                            accept(smpl, token_id)
                        row = dict(name=name, accepted_including_eos=rejected is None,
                                   expected=expected, rejected=rejected, response_sha256=sha256_bytes(raw),
                                   grammar_sha256=sha256_bytes(grammar), token_count=count)
                        rows.append(row)
                        task.base.save(output, name + "-result.json", row)
                        assert row["accepted_including_eos"] == expected
                        print(name + ": " + ("accepted through EOS" if rejected is None else "rejected as expected"), flush=True)
                    finally:
                        free_sampler(smpl)
            finally:
                free_model(model)
        result = dict(status="passed", model_inference_calls=0, vocabulary_only=True,
            no_context_or_decode_calls=True, native_input_unchanged=True, logical_request_unchanged=True,
            original_request_sha256=sha256_bytes(original), wire_request_sha256=sha256_bytes(wire),
            source_sha256=bindings, model_sha256=task.base.ACTOR["model_sha256"], binaries=binaries, cases=rows)
        task.base.save(output, "RESULTS.json", result)
    except BaseException as error:
        task.base.save(output, "FAILED.json", dict(error_type=type(error).__name__, error=str(error), source_sha256=bindings))
        raise
    finally:
        files = task.base.base.file_inventory(output)
        task.base.save(output, "SEAL.json", dict(files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    qualify(parser.parse_args().output)
