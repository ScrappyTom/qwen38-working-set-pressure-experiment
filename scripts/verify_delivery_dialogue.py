"""Verify the closed dialogue offline, preserving its legacy reserve-field defect."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import delivery_dialogue as dialogue
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_file
from working_set_exp.runtime import tokenizer_count

require, base, prep = dialogue.require, dialogue.base, dialogue.prep


def verify(args):
    require(not args.output.exists(), 'verification already exists; preserve it')
    require(sha256_file(args.model) == prep.ACTOR['model_sha256'], 'model differs')
    require(sha256_file(args.tokenizer) == dialogue.probe.TOKENIZER_SHA, 'tokenizer differs')
    dialogue.probe.verify_originals()
    profile = SimpleNamespace(model_path=args.model, tokenizer_path=args.tokenizer)
    plan = load_json_strict((dialogue.AREA/'preparation-001/PREPARATION.json').read_bytes())
    require(plan['source_sha256'] == dialogue.identities(), 'preparation source differs')
    initial_native = (dialogue.AREA/'preparation-001/D1-native.txt').read_bytes()
    rows = []
    for turn in (1, 2):
        folder, tag = dialogue.AREA/f'turn-{turn:02d}', f'D{turn}'
        seal = base.verify_seal(folder)
        require(seal['disposition'] == 'completed_dialogue_turn' and seal['sent_requests'] == 1, 'turn incomplete')
        require(seal['actor'] == prep.ACTOR and seal['memory_policy'] == prep.cont.POLICY, 'settings differ')
        require(seal['source_sha256'] == dialogue.identities(), 'turn sources differ')
        public = {p.relative_to(folder).as_posix() for p in folder.rglob('*')
                  if p.is_file() and 'private-runtime' not in p.relative_to(folder).parts}
        require(public == {p['path'] for p in seal['files']} | {'RESPONSE_SEAL.json'}, 'unsealed evidence')
        for name, digest in seal['private_runtime_files_local_only'].items():
            require(sha256_file(folder/'private-runtime'/name) == digest, 'private evidence differs')
        records = verify_records(folder/'records.jsonl', folder)
        require(len(records) == seal['record_count'], 'record count differs')

        def record(kind):
            found = [r['payload'] for r in records if r['record_type'] == kind]
            require(len(found) == 1, 'expected one '+kind)
            return found[0]

        made = record('turn_prepared')
        require(made['owner_direction'] == 'Proceed' and made['maximum_dialogue_calls'] == 2, 'scope differs')
        require(made['historical_seal_sha256'] == dialogue.probe.SEAL_SHA, 'historical identity differs')
        follow = dialogue.AREA/'FOLLOW_UP.txt'
        require(made['follow_up_sha256'] == (sha256_file(follow) if turn == 2 else None), 'follow-up binding differs')
        for kind in ('runtime_closed', 'turn_closed'):
            require(record(kind)['owned_server_shutdown_verified'] and record(kind)['dedicated_port_free'], 'closure differs')
        runtime = record('runtime_prepared')
        require(runtime['actor'] == prep.ACTOR and runtime['memory_policy'] == prep.cont.POLICY, 'runtime metadata differs')
        health = dict(full_offload=True, context_matches=True, q4_k_and_v=True,
                      mtp_disabled=True, truncation_observed=False, cuda_failure_observed=False)
        require(seal['effective_runtime'] == health, 'effective runtime differs')
        require(seal['memory'] == base.memory_stats(folder/'memory.csv'), 'memory summary differs')
        for kind in ('invocation_started', 'post_response_runtime_check'):
            require(record(kind)['effective_runtime'] == health and record(kind)['memory']['reference_is_advisory'], 'health differs')
        launch = load_json_strict((folder/'private-runtime/launch.json').read_bytes())
        require(sha256_file(Path(launch[0])) == prep.ACTOR['server_sha256'], 'server identity differs')
        require(launch == base.launch_args(Path(launch[0]), args.model), 'launch differs')
        path = lambda suffix: folder/'calls'/f'{tag}-{suffix}'
        request = dialogue.request_for(turn, follow if turn == 2 else None)
        require(path('endpoint-request.json').read_bytes() == canonical_json_bytes(request), 'conversation differs')
        native = path('rendered-prompt.txt').read_bytes()
        require(load_json_strict(path('template-response.json').read_bytes())['prompt'].encode() == native, 'template receipt differs')
        if turn == 1:
            expected_native = initial_native
        else:
            tail = b'<|im_start|>assistant\n<think>\n'
            require(initial_native.endswith(tail), 'initial native envelope differs')
            expected_native = (initial_native[:-len(tail)] + b'<|im_start|>assistant\n<think>\n\n</think>\n\n'
                + request['messages'][2]['content'].strip().encode() + b'<|im_end|>\n<|im_start|>user\n'
                + request['messages'][3]['content'].strip().encode() + b'<|im_end|>\n' + tail)
        require(native == expected_native, 'complete native conversation differs')
        n = tokenizer_count(profile, native)
        require(n == len(load_json_strict(path('tokenization.json').read_bytes())['tokens'])
                == record('invocation_prepared')['prompt_tokens'] <= prep.INPUT_CEILING, 'input accounting differs')
        require(record('invocation_started')['prompt_tokens'] == n, 'dispatch differs')
        response = load_json_strict(path('endpoint-response.json').read_bytes())
        require(len(response['choices']) == 1 and response['choices'][0]['finish_reason'] == 'stop', 'incomplete response')
        message, usage, timings = response['choices'][0]['message'], response['usage'], response['timings']
        require(not message.get('tool_calls') and not message.get('function_call'), 'unexpected execution channel')
        for field, suffix in (('reasoning_content', 'assistant-reasoning.txt'), ('content', 'assistant-content.txt')):
            require(message[field].encode() == path(suffix).read_bytes(), 'raw output field differs')
        require(message['content'].strip(), 'empty final answer')
        require(usage['prompt_tokens'] == timings['prompt_n'] == n and usage['completion_tokens'] == timings['predicted_n'], 'usage differs')
        require(usage['prompt_tokens_details']['cached_tokens'] == timings['cache_n'] == 0, 'cache reused')
        require(usage['total_tokens'] == n + usage['completion_tokens'] <= prep.ACTOR['context'], 'physical accounting differs')
        host = load_json_strict(path('host-result.json').read_bytes())
        require(host == dict(candidate_mutated=False, executed=False, finish_reason='stop', mode='delivery_dialogue',
            nonexecuting_response_not_a_coding_continuation=True, tool_execution_enabled=False), 'host result differs')
        done = record('invocation_completed')
        require(done['host_result'] == host and done['usage'] == usage, 'completion record differs')
        require(record('response_received')['elapsed_seconds'] == done['elapsed_seconds'], 'time differs')
        # This is a verified historical measurement defect, not a corrected seal.
        require(base.ACTOR['generation_reserve'] == 20480 and prep.ACTOR['generation_reserve'] == 32768, 'reserve identity differs')
        require(done['within_proposed_generation_reserve'] == (usage['completion_tokens'] <= 20480), 'legacy flag differs from its source')
        remaining = prep.ACTOR['context'] - usage['total_tokens']
        require(done['physical_tokens_remaining'] == remaining, 'remaining space differs')
        require(not record('next_turn_decision')['next_request_sent'], 'unexpected successor')
        require(record('next_turn_decision')['next_step'] == ('seal_and_directly_review_before_adaptive_follow_up' if turn == 1 else 'seal_and_review'), 'next decision differs')
        stamps = [datetime.strptime(line.split(',')[0], '%Y/%m/%d %H:%M:%S.%f')
                  for line in (folder/'memory.csv').read_text().splitlines()]
        rows.append(dict(id=tag, seal_sha256=sha256_file(folder/'RESPONSE_SEAL.json'),
            public_files=len(seal['files']), source_identities=len(seal['source_sha256']), records=len(records),
            input_tokens=n, output_tokens=usage['completion_tokens'], request_seconds=done['elapsed_seconds'],
            reasoning_characters=len(message['reasoning_content']), final_characters=len(message['content']),
            physical_tokens_remaining=remaining, recorded_legacy_reserve_flag=done['within_proposed_generation_reserve'],
            derived_within_selected_32768_reserve=usage['completion_tokens'] <= 32768, memory=seal['memory'],
            maximum_sampling_gap_seconds=max((b-a).total_seconds() for a,b in zip(stamps,stamps[1:]))))
    result = dict(verification_source_sha256=sha256_file(Path(__file__)), completion_requests=2,
        model_actions_executed=0, native_cli_counts_match=True, complete_native_messages_match=True,
        first_answer_retained_exactly=True, first_thinking_omitted=True, raw_output_fields_exact=True,
        original_compiler_evidence_unchanged=True, historical_seal_sha256=dialogue.probe.SEAL_SHA,
        first_review_sha256=sha256_file(dialogue.AREA/'D1_REVIEW.md'), follow_up_sha256=sha256_file(follow),
        legacy_reserve_flag_defect_preserved=True, turns=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(result))
    print(canonical_json_bytes(result).decode())


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model', type=Path, required=True)
    p.add_argument('--tokenizer', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    verify(p.parse_args())
