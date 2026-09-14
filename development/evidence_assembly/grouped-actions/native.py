"""Exact wire schema through pinned native GBNF; vocabulary only, no inference."""
import argparse
import copy
import ctypes as C
import importlib.util
import json
import math
import os
from pathlib import Path

import qualify
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

AREA, TASK, study = qualify.AREA, qualify.TASK, qualify.study
REVIEW = study.ROOT / "development/bounded_working_set/parser-documentation/grammar-review"


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cases(schema, old_schema):
    # Canonical nested operation order matches the actual wire schema. The
    # contribution wrapper still offers discussion before operation.
    def value(handles):
        action = dict(action="work_on", sources=copy.deepcopy(qualify.prior.GROUP), results=handles)
        return dict(discussion="Select exact source and saved work.",
                    operation=json.loads(canonical_json_bytes(action)))
    good = value(["EVT-0071"])
    missing = copy.deepcopy(good)
    del missing["operation"]["results"]
    return [("legacy_rejects_action", old_schema, good, False),
            ("selected_action", schema, good, True),
            ("mixed_action_result", schema, value(["EVT-0071", "RES-0071"]), True),
            ("legacy_result", old_schema, value(["RES-0071"]), True),
            ("current_result", schema, value(["RES-0071"]), True),
            ("empty_handles", schema, value([]), True),
            ("unsupported_prefix", schema, value(["ACT-0071"]), False),
            ("short_handle", schema, value(["EVT-71"]), False),
            ("missing_results", schema, missing, False),
            ("too_many_handles", schema, value(["EVT-0071"] * 17), False)]


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    bound, rows = qualify.identities(), []
    probe = module_at("qualified_gbnf_layout", REVIEW / "native_order_probe_gbnf.py")
    converter_module = module_at("pinned_group_schema_converter", REVIEW / "json_schema_to_grammar.py")
    try:
        session, adapter = qualify.checkpoint()
        wire = completion_request_bytes(adapter.request_for(session.view()))
        study.save(output, "wire-request.json", wire)
        schema = json.loads(wire)["response_format"]["json_schema"]["schema"]
        original_wire = (qualify.SOURCE / "calls/C04-wire-request.json").read_bytes()
        old_schema = json.loads(original_wire)["response_format"]["json_schema"]["schema"]
        original = study.read(REVIEW / "NATIVE_GBNF_ORDER_PROBE.json")
        binaries = {name: sha256_file(probe.BIN / name) for name in original["binaries"]}
        study.require(binaries == original["binaries"], "native binaries differ")
        converter_sha = sha256_file(REVIEW / "json_schema_to_grammar.py")
        study.require(converter_sha == "ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3",
                      "pinned schema converter differs")
        _, model_path, _ = TASK.runtime_paths()
        study.require(sha256_file(model_path) == TASK.ACTOR["model_sha256"], "model differs")
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
            study.require(bool(model), "vocabulary loading failed")
            try:
                vocab = vocabulary(model)
                for name, rule, value, expected in cases(schema, old_schema):
                    converter = converter_module.SchemaConverter(prop_order={}, allow_fetch=False,
                                                                   dotall=False, raw_pattern=False)
                    converter.visit(rule, "")
                    grammar = converter.format_grammar().encode()
                    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
                    study.save(output, name + ".json", raw)
                    study.save(output, name + ".gbnf", grammar)
                    smpl = sampler(vocab, grammar, b"root")
                    study.require(bool(smpl), "native grammar initialization failed")
                    try:
                        buffer = (C.c_int32 * (len(raw) + 16))()
                        count = tokenize(vocab, raw, len(raw), buffer, len(buffer), False, False)
                        study.require(count >= 0, "tokenization buffer insufficient")
                        rejected = None
                        for index, token_id in enumerate([*buffer[:count], eos(vocab)]):
                            token = probe.Token(token_id, 0.0, 0.0)
                            tokens = probe.Tokens(C.pointer(token), 1, -1, False)
                            apply(smpl, C.byref(tokens))
                            if not math.isfinite(tokens.data[0].logit):
                                rejected = dict(token_index=index, token_id=token_id, is_eos=index == count)
                                break
                            accept(smpl, token_id)
                        row = dict(name=name, accepted_including_eos=rejected is None, expected=expected,
                                   rejected=rejected, response_sha256=sha256_bytes(raw),
                                   grammar_sha256=sha256_bytes(grammar), token_count=count)
                        rows.append(row)
                        study.save(output, name + "-result.json", row)
                        study.require(row["accepted_including_eos"] == expected, "native result differs")
                        print(name + ": " + ("accepted through EOS" if rejected is None else "rejected as expected"), flush=True)
                    finally:
                        free_sampler(smpl)
            finally:
                free_model(model)
        study.save(output, "RESULTS.json", dict(status="passed", model_inference_calls=0,
            vocabulary_only=True, no_context_or_decode_calls=True, source_sha256=bound,
            converter_sha256=converter_sha, native_probe_sha256=sha256_file(REVIEW / "native_order_probe_gbnf.py"),
            model_sha256=TASK.ACTOR["model_sha256"], binaries=binaries,
            wire_request_sha256=sha256_bytes(wire), original_wire_sha256=sha256_bytes(original_wire), cases=rows))
    except BaseException as error:
        study.save(output, "FAILED.json", dict(type=type(error).__name__, message=str(error), source_sha256=bound))
        raise
    finally:
        files = qualify.RUNTIME.file_inventory(output)
        study.save(output, "SEAL.json", dict(files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", default="native-001")
    run(AREA / parser.parse_args().folder)
