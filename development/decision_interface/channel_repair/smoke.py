"""Two real endpoint transport calls; no task evidence or operation execution."""
import json
import time
from types import SimpleNamespace

import channel_task as study
from manage import RUNTIME, legacy
import run_uncoached_contribution as runner
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes
from working_set_exp import working_view


def main():
    folder = study.AREA/'smoke-001'
    folder.mkdir(exist_ok=False)
    bound = study.source_identities()
    store = ArtifactStore(folder)
    log = runner.RunLog(folder/'records.jsonl', 'channel-transport-smoke', task_module=study)
    server, model, _ = study.runtime_paths()
    rows, error = [], None
    header = dict(discussion='transport ready', operation=dict(action='replace_region',
                  region='SRC-'+'a'*64, expected_candidate_id='b'*64))
    body = 'path = r"C:\\tmp"\ntext = "é"\n'
    requested = [
        ('S01', json.dumps(dict(discussion='transport ready'), separators=(',', ':')), None),
        ('S02', json.dumps(header, separators=(',', ':'))+'\nSOURCE\n'+body, body),
    ]
    try:
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            for tag, target, source in requested:
                adapter = runner.Adapter(study.Task())
                request = adapter.request_for(adapter.initial_session().view())
                request['messages'] = [
                    dict(role='system', content='This is a response transport test, not repository work. Think briefly, then return the exact requested final reply. Do not use Markdown fences. No operation will execute.'),
                    dict(role='user', content='Return the following exact final reply. Preserve the literal source and its trailing newline when present.\n\n'+target),
                ]
                class SmokeAdapter(runner.Adapter):
                    def request_for(self, view):
                        return request
                loop = runner.Loop(folder, store, log, url=url, task_module=SmokeAdapter(study.Task()),
                                   source_check=lambda: study.verify_sources(bound))
                # Different stems for independent fresh conversations.
                loop.counter = 0 if tag == 'S01' else 1
                count = loop.measure({})
                wire = completion_request_bytes(request)
                log.append('invocation_started', dict(id=tag, prompt_tokens=count, completion_sent=True,
                    transport_only=True, operation_execution_enabled=False), [store.put(f'calls/{tag}-wire-request.json', wire)])
                started = time.monotonic()
                raw = loop.post(url, '/v1/chat/completions', wire, adapter.base.HTTP_TIMEOUT_SECONDS)
                elapsed = time.monotonic()-started
                log.append('response_received', dict(id=tag, elapsed_seconds=elapsed),
                           [store.put(f'calls/{tag}-endpoint-response.json', raw)])
                response = json.loads(raw)
                choice, usage = response['choices'][0], response['usage']
                message = choice['message']
                thinking, final = message.get('reasoning_content') or '', message.get('content') or ''
                log.append('response_extracted', dict(id=tag, finish_reason=choice['finish_reason'], usage=usage),
                    [store.put(f'calls/{tag}-assistant-reasoning.txt', thinking.encode()),
                     store.put(f'calls/{tag}-assistant-content.txt', final.encode())])
                assert choice['finish_reason']=='stop' and thinking and final
                assert usage['prompt_tokens']==count and usage['total_tokens']==count+usage['completion_tokens']
                assert usage['prompt_tokens_details']['cached_tokens']==0 and response['timings']['cache_n']==0
                decoded = study.decode_reply(final)
                working_view.validate(decoded, study.reply_schema()['json_schema']['schema'])
                if source is None:
                    assert decoded == dict(discussion='transport ready')
                else:
                    assert decoded == {**header, 'operation':{**header['operation'], 'new':source}}
                store.put(f'calls/{tag}-decoded.json', canonical_json_bytes(decoded))
                rows.append(dict(id=tag, usage=usage, seconds=elapsed, reasoning_chars=len(thinking),
                                 final_chars=len(final), exact_decoded_payload=True, task_operations=0))
                log.append('transport_verified', rows[-1], [])
                study.verify_sources(bound)
                print(tag+' transport verified', flush=True)
        study.save(folder, 'RESULTS.json', dict(status='passed', calls=rows, task_operations=0,
                   completion_requests=2, memory=RUNTIME.memory_stats(folder/'memory.csv')))
    except BaseException as problem:
        error = problem
        study.save(folder, 'FAILED.json', dict(type=type(problem).__name__, message=str(problem), completed=rows))
        raise
    finally:
        verify_records(folder/'records.jsonl', folder)
        legacy.seal(folder, 'failed_preserved' if error else 'transport_qualified', bound, completion_requests=len(rows))


if __name__ == '__main__':
    main()
