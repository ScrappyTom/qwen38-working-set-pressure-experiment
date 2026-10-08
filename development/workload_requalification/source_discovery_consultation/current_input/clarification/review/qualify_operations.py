"""Reviewer-only replay of the proposed read; no model or task mutation."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import sys

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import clarify
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count

task = clarify.study
execution = clarify.first.run_completion.execution
folder = Path(__file__).parent/'operation-qualification-001'
folder.mkdir(exist_ok=False)
store = ArtifactStore(folder)
log = execution.legacy.QualificationLog(folder/'records.jsonl', 'D2-operation-review', task_module=task)
bound = {**clarify.identities(), Path(__file__).relative_to(clarify.ROOT).as_posix(): sha256_file(Path(__file__)),
         (AREA/'turn-02/RESPONSE_SEAL.json').relative_to(clarify.ROOT).as_posix(): sha256_file(AREA/'turn-02/RESPONSE_SEAL.json')}
stem = 'after/C62-O01'
state = task.read(task.RUN/(stem+'-state.json'))
candidate = task.read(task.RUN/(stem+'-candidate.json'))
session = task.restore(state, candidate, task.RUN, replay=True)
adapter = execution.runner.Adapter(task)
adapter.preceding_feedback = task.read(task.RUN/(stem+'-preceding-feedback.json'))
_, model, tokenizer = task.runtime_paths()
profile = SimpleNamespace(model_path=model, tokenizer_path=tokenizer)
trial = 0


def measure(view):
    global trial
    trial += 1
    request = adapter.request_for(view)
    native = task.expected_native(request)
    count = tokenizer_count(profile, native)
    log.append('input_measured_offline', dict(trial=trial, prompt_tokens=count, completion_sent=False),
        [store.put(f'trial-{trial:03d}-request.json', completion_request_bytes(request)),
         store.put(f'trial-{trial:03d}-native.txt', native)])
    return count


failure, result = None, {}
try:
    original = (task.RUN/'calls/C63-wire-request.json').read_bytes()
    assert completion_request_bytes(adapter.request_for(session.view())) == original
    initial_tokens = measure(session.view())
    actual_usage = task.read(task.RUN/'calls/C63-endpoint-response.json')['usage']
    assert initial_tokens == actual_usage['prompt_tokens']
    original_candidate = session.candidate.candidate_id
    operation = dict(action='read', path='Lib/configparser.py', start_line=170, end_line=180)
    received = session.execute(operation, measure)
    assert received['accepted']
    final_tokens = measure(session.view())
    shown = [s for s in session.view()['working_set']['sources'] if s['path'] == operation['path']
             and s['returned_start_line'] <= 170 and s['returned_end_line'] >= 180]
    assert shown and 'self.message = msg' in shown[0]['content'] and '__str__ = __repr__' in shown[0]['content']
    assert session.candidate.candidate_id == original_candidate and final_tokens <= 23808
    log.append('hypothetical_read_qualified', dict(executed_by='reviewer', actual_actor_operation=False),
        [store.put('read-operation.json', canonical_json_bytes(operation)),
         store.put('read-result.json', canonical_json_bytes(received)),
         store.put('read-view.json', canonical_json_bytes(session.view()))])

    # D2 mentions search but gives no complete search action. These extra fields
    # are reviewer-selected solely to inspect the advertised route's actual scope.
    other = task.restore(state, candidate, task.RUN, replay=True)
    search = dict(action='search', path='Lib/configparser.py', query='class Error', offset=0, limit=1)
    searched = other.execute(search, measure)
    assert searched['accepted'] and searched['matches'][0]['line'] == 170
    region = next(r for r in searched['regions'] if r['extent_kind'] == 'search context')
    assert region['start_line'] <= 170 and region['end_line'] >= 180
    assert not any('self.message = msg' in m['text'] for m in searched['matches'])
    assert other.candidate.candidate_id == original_candidate
    log.append('alternative_search_scope_qualified', dict(executed_by='reviewer', actual_actor_operation=False),
        [store.put('search-operation.json', canonical_json_bytes(search)),
         store.put('search-result.json', canonical_json_bytes(searched)),
         store.put('search-view.json', canonical_json_bytes(other.view()))])
    result = dict(classification='Reviewer-only historical feasibility; no model execution or task credit',
        initial_tokens=initial_tokens, read_next_input_tokens=final_tokens, read_complete=True,
        read_lines=[170, 180], search_context=[region['start_line'], region['end_line']],
        search_returns_address_not_class_body=True, unchanged_candidate=original_candidate,
        completion_requests=0, offline_tokenizer_matches_actual_c63=True)
    store.put('RESULTS.json', canonical_json_bytes(result))
except BaseException as error:
    failure = error
    store.put('FAILED.json', canonical_json_bytes(dict(type=type(error).__name__, message=str(error))))
finally:
    execution.legacy.seal(folder, 'failed_preserved' if failure else 'qualified_no_model_inference',
                          bound, completion_requests=0)
if failure:
    raise failure
print(json.dumps(result, indent=2))
