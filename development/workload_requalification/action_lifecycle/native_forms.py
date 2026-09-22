"""Qualify operational reply forms with the pinned vocabulary/grammar matcher.

Call qualify(folder, task=task, request=exact_prospective_request) from the
owner's preparation. This helper neither starts a server nor sends endpoint,
completion, checker, context-creation or model-decode calls. It loads vocabulary
only (zero GPU layers), using the same pinned structures and DLL entry points as
small_repairs/native-005. The caller owns runtime scheduling and outer sealing.

decode_reply may be supplied as a one-argument callable. source_identities may be
a callable returning the complete prerequisite map; it defaults to the task's
implementation_identities to avoid a preparation-gate cycle. Synthetic thinking
is split only to test the production final decoder, never to recover an action
from a live model response. No command-line launch is provided.
"""
from __future__ import annotations

import ctypes as C
import importlib.util
import json
import math
import os
from pathlib import Path

from working_set_exp import working_view
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

REVIEW = Path('development/bounded_working_set/parser-documentation/grammar-review')
ORIGINAL = Path('development/workload_requalification/navigation_continuity/receipts/run-001')


def cases(checks, original_final):
    """Researcher-authored strings; no proposed operation is executed."""
    def ordinary(name, value, wanted=True, thinking='Decide the next operation.\n'):
        final = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        return dict(name=name, text=thinking+'</think>\n'+final, final=final,
                    expected=wanted)

    read = dict(action='read', path='README.md', start_line=1, end_line=0)
    header = dict(action='replace_region', region='SRC-'+'a'*64,
                  expected_candidate_id='b'*64)
    yield ordinary('ordinary_read', dict(discussion='Read exact source.', operation=read))
    yield ordinary('account_only', dict(discussion='Preserve the question.',
        account='The source is not yet inspected.\nResolve the behavior before editing.'))
    yield ordinary('empty_account_clear', dict(discussion='Clear the account.', account=''))
    yield ordinary('account_and_read', dict(discussion='Acquire evidence.',
        account='README remains unread.', operation=read))
    for name, body, account in [
        ('literal_multiline', 'def f():\n    return "\\n"  # é\n', None),
        ('literal_empty', '', None),
        ('literal_crlf', 'x = 1\r\n', None),
        ('literal_separator_in_source', 'SOURCE\n{"text":"value"}\n', None),
        ('literal_account_source', 'x = "quoted\\n"\n', 'This edit remains untested.'),
    ]:
        fields = dict(discussion='Save exact source.')
        if account is not None:
            fields['account'] = account
        fields['operation'] = header
        final = json.dumps(fields, ensure_ascii=False, separators=(',', ':'))+'\nSOURCE\n'+body
        yield dict(name=name, text='</think>\n'+final, final=final, expected=True,
                   exact_source=body)
    yield ordinary('ordinary_json_replacement', dict(discussion='Save source.',
        operation={**header, 'new':'x = "\\n"\n'}))
    patch = dict(action='patch', path='app.py', old='old', new='new',
                 expected_candidate_id='b'*64, expected_file_sha256='a'*64)
    yield ordinary('explicit_patch', dict(discussion='Save.', operation=patch))
    yield ordinary('ordinary_submit', dict(discussion='Submit checked work.',
        operation=dict(action='submit', expected_candidate_id='b'*64)))
    for scope in dict.fromkeys([*checks, 'public', 'tests', 'examples', 'unsupported_scope']):
        yield ordinary('scope_'+scope, dict(discussion='Check.', operation=dict(
            action='check', check_id=scope, expected_candidate_id='b'*64)), scope in checks)
    yield ordinary('unsupported_check_after', dict(discussion='Save.', operation=patch,
                                                 check_after='public'), False)
    yield ordinary('discussion_only', dict(discussion='I will read the source.'), False)
    yield dict(name='actual_C05_discussion_only', text='</think>\n'+original_final,
               final=original_final, expected=False)
    yield dict(name='discussion_prefix_eos', text='</think>\n{"discussion":"Read next."',
               expected=False, require_eos_rejection=True)
    yield dict(name='empty_object', text='</think>\n{}', expected=False)
    yield dict(name='incomplete_final', text='</think>\n{"discussion":',
               expected=False, require_eos_rejection=True)
    yield dict(name='thinking_without_final', text='Consider the next operation.',
               expected=False, require_eos_rejection=True)
    yield dict(name='wrong_final_text', text='</think>\nRead README now.', expected=False)
    yield ordinary('empty_thinking', dict(discussion='Read.', operation=read), thinking='')
    yield ordinary('action_shaped_private_text', dict(discussion='Save the question.',
        account='Need exact source.'), thinking='{"operation":{"action":"submit"}}\n')
    yield ordinary('overlapping_delimiter_prefixes', dict(discussion='Read.', operation=read),
        thinking='<< / </t </th </thi </thin </think <<think> é\n')
    yield ordinary('long_synthetic_thinking', dict(discussion='Read.', operation=read),
        thinking='Review a provisional result.\n'*4000)
    bare = json.dumps(dict(discussion='Save.', operation=header), separators=(',', ':'))
    yield dict(name='missing_source_separator', text='</think>\n'+bare+'\nx=1', expected=False)
    yield dict(name='multiline_source_header', text='</think>\n'+json.dumps(
        dict(discussion='Save.', operation=header), indent=2)+'\nSOURCE\nx=1\n', expected=False)
    yield dict(name='wrong_source_action', text='</think>\n'+json.dumps(dict(
        discussion='Save.', operation=dict(action='submit', expected_candidate_id='b'*64)))+
        '\nSOURCE\nx=1\n', expected=False)


def qualify(folder, *, task, request, decode_reply=None, source_identities=None):
    """Save immutable cases/tokens/results; return RESULTS after a complete pass.

    Required task attributes: ROOT, ACTOR, runtime_paths(), reply_schema(),
    decode_reply(content), implementation_identities() (or explicit callback).
    request must be the exact request later measured by the owner's preparation.
    Includes SOURCE forms and the already-open thinking grammar, not a substitute
    schema-only grammar. Existing output folders are never reused.
    """
    folder, root = Path(folder), Path(task.ROOT)
    identity = source_identities or (task.implementation_identities
        if hasattr(task, 'implementation_identities') else task.source_identities)
    decode = decode_reply or task.decode_reply
    schema = task.reply_schema()['json_schema']['schema']
    checks = set()
    for form in schema['oneOf']:
        if 'operation' in form['properties']:
            for operation in form['properties']['operation']['oneOf']:
                if operation['properties']['action']['const'] == 'check':
                    checks.update(operation['properties']['check_id']['enum'])
    assert checks, 'Operational schema has no named checks'
    assert 'response_format' not in request and isinstance(request.get('grammar'), str)
    assert not any(set(form['properties']) == {'discussion'} for form in schema['oneOf'])
    grammar = request['grammar'].encode('utf-8')
    assert 'channel-think-0' in request['grammar'], 'Expected qualified thinking wrapper'
    folder.mkdir(parents=True, exist_ok=False)

    def save(name, value):
        raw = value if isinstance(value, bytes) else canonical_json_bytes(value)
        with (folder/name).open('xb') as stream:
            stream.write(raw)

    bound, rows, result = {}, [], None
    try:
        original_identities = dict(identity())
        bound = dict(original_identities)
        layout_path = root/REVIEW/'native_order_probe_gbnf.py'
        pinned_path = root/REVIEW/'NATIVE_GBNF_ORDER_PROBE.json'
        old_seal_path = root/ORIGINAL/'RESPONSE_SEAL.json'
        old_final_path = root/ORIGINAL/'calls/C05-assistant-content.txt'
        for path in [Path(__file__).resolve(), layout_path, pinned_path, old_seal_path, old_final_path]:
            relative = path.relative_to(root.resolve()).as_posix()
            digest = sha256_file(path)
            assert relative not in bound or bound[relative] == digest
            bound[relative] = digest
        old_seal = json.loads(old_seal_path.read_bytes())
        old_row, = [row for row in old_seal['files'] if row['path']=='calls/C05-assistant-content.txt']
        old_final = old_final_path.read_bytes()
        assert len(old_final)==old_row['size_bytes'] and sha256_bytes(old_final)==old_row['sha256']
        spec = importlib.util.spec_from_file_location('operational_native_layout', layout_path)
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        expected = json.loads(pinned_path.read_bytes())['binaries']
        binaries = {name:sha256_file(probe.BIN/name) for name in expected}
        assert binaries == expected, 'Pinned native matcher DLLs differ'
        _, model_path, _ = task.runtime_paths()
        assert sha256_file(model_path) == task.ACTOR['model_sha256'], 'Model vocabulary differs'
        wire = completion_request_bytes(request)
        save('wire-request.json', wire)
        save('reply.gbnf', grammar)
        save('reply-schema.json', schema)
        save('BINDINGS.json', dict(source_sha256=bound, binaries=binaries,
            model_sha256=task.ACTOR['model_sha256'], original_C05_final_sha256=old_row['sha256']))

        with os.add_dll_directory(str(probe.BIN)):
            lib = C.CDLL(str(probe.BIN/'llama.dll'))
            def bind(name, result_type, *args):
                function = getattr(lib, name)
                function.restype, function.argtypes = result_type, args
                return function
            defaults = bind('llama_model_default_params', probe.ModelParams)
            load = bind('llama_model_load_from_file', C.c_void_p, C.c_char_p, probe.ModelParams)
            free = bind('llama_model_free', None, C.c_void_p)
            vocabulary = bind('llama_model_get_vocab', C.c_void_p, C.c_void_p)
            tokenize = bind('llama_tokenize', C.c_int32, C.c_void_p, C.c_char_p, C.c_int32,
                            C.POINTER(C.c_int32), C.c_int32, C.c_bool, C.c_bool)
            eos = bind('llama_vocab_eos', C.c_int32, C.c_void_p)
            sampler = bind('llama_sampler_init_grammar', C.c_void_p, C.c_void_p, C.c_char_p, C.c_char_p)
            apply = bind('llama_sampler_apply', None, C.c_void_p, C.POINTER(probe.Tokens))
            accept = bind('llama_sampler_accept', None, C.c_void_p, C.c_int32)
            release = bind('llama_sampler_free', None, C.c_void_p)
            params = defaults()
            params.n_gpu_layers, params.vocab_only, params.load_mtp = 0, True, False
            model = load(os.fsencode(model_path), params)
            assert model, 'Vocabulary loading failed'
            try:
                vocab = vocabulary(model)
                for case in cases(sorted(checks), old_final.decode('utf-8')):
                    name, raw = case['name'], case['text'].encode('utf-8')
                    save(name+'.txt', raw)
                    matcher = sampler(vocab, grammar, b'root')
                    assert matcher, 'Native grammar sampler construction failed'
                    try:
                        buffer = (C.c_int32*(len(raw)+16))()
                        # Parse real </think> special tokens, as native-005 does.
                        count = tokenize(vocab, raw, len(raw), buffer, len(buffer), False, True)
                        assert count >= 0, 'Native tokenization failed'
                        ids = [*buffer[:count], eos(vocab)]
                        save(name+'-tokens.json', dict(ids_including_eos=ids, token_count=count,
                            add_special=False, parse_special=True, eos_token_id=ids[-1]))
                        rejected = None
                        for index, token_id in enumerate(ids):
                            token = probe.Token(token_id, 0.0, 0.0)
                            tokens = probe.Tokens(C.pointer(token), 1, -1, False)
                            apply(matcher, C.byref(tokens))
                            if not math.isfinite(tokens.data[0].logit):
                                rejected = dict(index=index, token_id=token_id, is_eos=index==count)
                                break
                            accept(matcher, token_id)
                        row = dict(name=name, accepted_including_eos=rejected is None,
                            expected=case['expected'], rejected=rejected, token_count=count,
                            response_sha256=sha256_bytes(raw), grammar_sha256=sha256_bytes(grammar))
                        rows.append(row)
                        save(name+'-result.json', row)
                        assert row['accepted_including_eos']==case['expected'], (name, rejected)
                        if case.get('require_eos_rejection'):
                            assert rejected and rejected['is_eos'], (name, rejected)
                        if case['expected']:
                            # Only these researcher-authored specimens are split.
                            final = case['text'].split('</think>', 1)[1].lstrip()
                            assert final == case['final']
                            decoded = decode(final)
                            working_view.validate(decoded, schema)
                            if 'exact_source' in case:
                                assert decoded['operation']['new'] == case['exact_source']
                            if name=='action_shaped_private_text':
                                assert 'operation' not in decoded
                            save(name+'-decoded.json', decoded)
                    finally:
                        release(matcher)
            finally:
                free(model)
        assert all(sha256_file(root/name)==digest for name,digest in bound.items()), 'Source changed'
        assert identity()==original_identities, 'Source closure changed'
        assert completion_request_bytes(request)==wire, 'Prospective request changed'
        result = dict(status='passed', cases=rows, completion_requests=0, model_inference_calls=0,
            vocabulary_only=True, no_context_or_decode_calls=True, checker_executions=0,
            binaries=binaries, wire_sha256=sha256_bytes(wire), grammar_sha256=sha256_bytes(grammar))
        save('RESULTS.json', result)
        return result
    except BaseException as error:
        save('FAILED.json', dict(type=type(error).__name__, message=str(error), cases=rows))
        raise
    finally:
        files = [dict(path=path.relative_to(folder).as_posix(), size_bytes=path.stat().st_size,
                      sha256=sha256_file(path)) for path in sorted(folder.rglob('*')) if path.is_file()]
        save('SEAL.json', dict(status='qualified_no_model_inference' if result else 'failed_preserved',
            completion_requests=0, files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),
            source_sha256=bound))


run = qualify
