"""Pinned native reply-form qualification for the imported compiler captures.

The caller owns the runtime and outer preparation seal. This helper never starts
a server, creates a context, decodes a model token, executes a checker, or sends a
completion request. It checks researcher-authored specimens against the actual
prospective decoder grammar and pinned model vocabulary, including EOS. Native
template rendering and input admission remain the caller's Loop.measure work.
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


def cases(checks):
    """Specimens test forms only; no specimen becomes an executed operation."""
    def ordinary(name, value, expected=True, thinking='Decide the next operation.\n'):
        final = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        return dict(name=name, text=thinking+'</think>\n'+final, final=final,
                    expected=expected)

    read = dict(action='read', path='README.md', start_line=1, end_line=0)
    for handle in ('OBS-0001', 'OBS-0002', 'OBS-0003'):
        yield ordinary('imported_'+handle, dict(discussion='Retrieve exact incident evidence.',
            operation=dict(action='reopen_observation', handle=handle)))
    yield ordinary('account_and_imported', dict(discussion='Acquire prior evidence.',
        account='The reported capture is historical, not a check of this repair.',
        operation=dict(action='reopen_observation', handle='OBS-0002')))
    for name, operation in (
        ('missing_handle', dict(action='reopen_observation')),
        ('wrong_handle_field', dict(action='reopen_observation', observation='OBS-0001')),
        ('wrong_handle_prefix', dict(action='reopen_observation', handle='CHK-0001')),
        ('malformed_handle', dict(action='reopen_observation', handle='OBS-x')),
        ('extra_offset', dict(action='reopen_observation', handle='OBS-0001', offset=0)),
        ('unknown_action', dict(action='refresh_observation', handle='OBS-0001')),
    ):
        yield ordinary(name, dict(discussion='Inspect prior evidence.', operation=operation), False)
    yield ordinary('ordinary_read', dict(discussion='Read exact source.', operation=read))
    yield ordinary('ordinary_result_retrieval', dict(discussion='Retrieve saved evidence.',
        operation=dict(action='reopen_result', handle='RES-0001', offset=0)))
    yield ordinary('ordinary_group', dict(discussion='Keep exact evidence together.',
        operation=dict(action='work_on', sources=[], results=['RES-0001'])))
    yield ordinary('account_only', dict(discussion='Save the pending question.',
        account='The current candidate has not been checked.'))
    yield ordinary('empty_account_clear', dict(discussion='Clear the account.', account=''))
    header = dict(action='replace_region', region='SRC-'+'a'*64,
                  expected_candidate_id='b'*64)
    for name, body, account in (
        ('literal_multiline', 'def f():\n    return "\\n"  # é\n', None),
        ('literal_empty', '', None),
        ('literal_crlf', 'x = 1\r\n', None),
        ('literal_separator_in_source', 'SOURCE\n{"text":"value"}\n', None),
        ('literal_account_source', 'x = "quoted\\n"\n', 'This edit remains untested.'),
    ):
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
    for scope in dict.fromkeys([*checks, 'tests', 'examples', 'unsupported_scope']):
        yield ordinary('scope_'+scope, dict(discussion='Check.', operation=dict(
            action='check', check_id=scope, expected_candidate_id='b'*64)), scope in checks)
    yield ordinary('unsupported_check_after', dict(discussion='Save.', operation=patch,
                                                 check_after='public'), False)
    yield ordinary('discussion_only', dict(discussion='I will read the source.'), False)
    yield dict(name='discussion_prefix_eos', text='</think>\n{"discussion":"Read next."',
               expected=False, require_eos_rejection=True)
    yield dict(name='thinking_without_final', text='Consider the next operation.',
               expected=False, require_eos_rejection=True)
    yield dict(name='incomplete_final', text='</think>\n{"discussion":',
               expected=False, require_eos_rejection=True)
    yield ordinary('empty_thinking', dict(discussion='Read.', operation=read), thinking='')
    yield ordinary('action_shaped_private_text', dict(discussion='Save the question.',
        account='Need exact source.'), thinking='{"operation":{"action":"submit"}}\n')
    bare = json.dumps(dict(discussion='Save.', operation=header), separators=(',', ':'))
    yield dict(name='missing_source_separator', text='</think>\n'+bare+'\nx=1', expected=False)
    yield dict(name='wrong_source_action', text='</think>\n'+json.dumps(dict(
        discussion='Save.', operation=dict(action='submit', expected_candidate_id='b'*64)))+
        '\nSOURCE\nx=1\n', expected=False)


def qualify(module, folder, url, store, log, *, specimens=None, required_forms=None):
    """Qualify exact wire/form compatibility during caller-owned preparation.

    module is compiler_task.Task. Required inherited APIs: ROOT, ACTOR,
    runtime_paths, source_identities, initial_session, response_constraints,
    reply_schema, decode_reply; run_uncoached_contribution.Adapter builds the
    actual request. url identifies the owner runtime but is not contacted here.
    Unknown capture existence is an executor property, not a grammar property;
    this qualification tests the advertised known addresses and invalid forms.
    """
    from run_uncoached_contribution import Adapter

    root, folder = Path(module.ROOT).resolve(), Path(folder).resolve()
    assert folder.is_relative_to(Path(store.root).resolve()), 'Native output leaves custody root'
    folder.mkdir(parents=True, exist_ok=False)
    prefix = folder.relative_to(Path(store.root).resolve()).as_posix()
    bound, rows, result = {}, [], None

    def save(name, value):
        raw = value if isinstance(value, bytes) else canonical_json_bytes(value)
        return store.put(prefix+'/'+name, raw)

    try:
        bound = dict(module.source_identities())
        original_bound = dict(bound)
        request = Adapter(module).request_for(module.initial_session().view())
        schema = module.reply_schema()['json_schema']['schema']
        constraints = module.response_constraints()
        assert request['grammar'] == constraints['grammar'] and 'response_format' not in request
        assert 'channel-think-0' in request['grammar'], 'Qualified thinking wrapper is absent'
        assert not any(set(form['properties']) == {'discussion'} for form in schema['oneOf'])
        checks, operations = set(), {}
        for form in schema['oneOf']:
            if 'operation' not in form['properties']:
                continue
            for operation in form['properties']['operation']['oneOf']:
                name = operation['properties']['action']['const']
                if name == 'check':
                    checks.update(operation['properties']['check_id']['enum'])
                operations.setdefault(name, []).append(operation)
        required_forms = ({'reopen_observation': {'action', 'handle'}}
                          if required_forms is None else required_forms)
        assert checks and required_forms, 'Expected check/extension contract is absent'
        for name, fields in required_forms.items():
            assert name in operations and all(set(form['properties']) == set(fields)
                for form in operations[name]), 'Required operation form differs: ' + name
        wire, grammar = completion_request_bytes(request), request['grammar'].encode('utf-8')
        layout_path, pinned_path = root/REVIEW/'native_order_probe_gbnf.py', root/REVIEW/'NATIVE_GBNF_ORDER_PROBE.json'
        for path in (Path(__file__).resolve(), layout_path, pinned_path):
            name, digest = path.relative_to(root).as_posix(), sha256_file(path)
            assert name not in bound or bound[name] == digest
            bound[name] = digest
        spec = importlib.util.spec_from_file_location('compiler_native_layout', layout_path)
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        expected = json.loads(pinned_path.read_bytes())['binaries']
        binaries = {name:sha256_file(probe.BIN/name) for name in expected}
        assert binaries == expected, 'Pinned native matcher DLLs differ'
        _, model_path, _ = module.runtime_paths()
        assert sha256_file(model_path) == module.ACTOR['model_sha256'], 'Model vocabulary differs'
        log.append('compiler_reply_qualification_started', dict(owner_runtime_url=url,
            completion_sent=False, no_endpoint_requests=True, vocabulary_only=True),
            [save('wire-request.json', wire), save('reply.gbnf', grammar),
             save('reply-schema.json', schema), save('BINDINGS.json', dict(source_sha256=bound,
                binaries=binaries, model_sha256=module.ACTOR['model_sha256']))])
        with os.add_dll_directory(str(probe.BIN)):
            lib = C.CDLL(str(probe.BIN/'llama.dll'))
            def bind(name, result_type, *arguments):
                function = getattr(lib, name)
                function.restype, function.argtypes = result_type, arguments
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
                for case in (specimens or cases)(sorted(checks)):
                    name, raw = case['name'], case['text'].encode('utf-8')
                    artifacts = [save(name+'.txt', raw)]
                    matcher = sampler(vocab, grammar, b'root')
                    assert matcher, 'Native grammar sampler construction failed'
                    try:
                        buffer = (C.c_int32*(len(raw)+16))()
                        count = tokenize(vocab, raw, len(raw), buffer, len(buffer), False, True)
                        assert count >= 0, 'Native tokenization failed'
                        ids = [*buffer[:count], eos(vocab)]
                        artifacts.append(save(name+'-tokens.json', dict(ids_including_eos=ids,
                            token_count=count, add_special=False, parse_special=True, eos_token_id=ids[-1])))
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
                        artifacts.append(save(name+'-result.json', row))
                        log.append('compiler_reply_form_qualified', row, artifacts)
                        assert row['accepted_including_eos'] == case['expected'], (name, rejected)
                        if case.get('require_eos_rejection'):
                            assert rejected and rejected['is_eos'], (name, rejected)
                        if case['expected']:
                            # These are authored test specimens, never live private reasoning.
                            final = case['text'].split('</think>', 1)[1].lstrip()
                            assert final == case['final']
                            decoded = module.decode_reply(final)
                            working_view.validate(decoded, schema)
                            if 'exact_source' in case:
                                assert decoded['operation']['new'] == case['exact_source']
                            if name == 'action_shaped_private_text':
                                assert 'operation' not in decoded
                            log.append('compiler_reply_form_decoded', dict(name=name,
                                source_preserved='exact_source' in case, no_operation_executed=True),
                                [save(name+'-decoded.json', decoded)])
                    finally:
                        release(matcher)
            finally:
                free(model)
        assert all(sha256_file(root/name) == digest for name,digest in bound.items()), 'Source changed'
        assert module.source_identities() == original_bound, 'Source closure changed'
        assert completion_request_bytes(request) == wire, 'Prospective request changed'
        result = dict(status='passed', cases=rows, completion_requests=0, model_inference_calls=0,
            checker_executions=0, endpoint_requests=0, vocabulary_only=True,
            no_context_or_decode_calls=True, binaries=binaries,
            wire_sha256=sha256_bytes(wire), grammar_sha256=sha256_bytes(grammar))
        log.append('compiler_reply_qualification_closed', dict(status='passed', cases=len(rows)),
                   [save('RESULTS.json', result)])
        return result
    except BaseException as error:
        log.append('compiler_reply_qualification_failed', dict(type=type(error).__name__,
            message=str(error), cases_completed=len(rows)),
            [save('FAILED.json', dict(type=type(error).__name__, message=str(error), cases=rows))])
        raise
    finally:
        files = [dict(path=path.relative_to(folder).as_posix(), size_bytes=path.stat().st_size,
                      sha256=sha256_file(path)) for path in sorted(folder.rglob('*')) if path.is_file()]
        seal = dict(status='qualified_no_model_inference' if result else 'failed_preserved',
            completion_requests=0, files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),
            source_sha256=bound)
        log.append('compiler_reply_qualification_sealed', dict(status=seal['status']),
                   [save('SEAL.json', seal)])
