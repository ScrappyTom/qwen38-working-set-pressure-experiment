"""Read-only verification of the frozen native qualification and actual entry."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contract_task as entry
import run_contract as execution
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

task = entry.Task('001')
manifest = execution.execution.runner.verify_package(task)
seal = entry.read(task.PACKAGE / 'SEAL.json')
assert seal['status'] == 'qualified_no_model_inference', seal.keys()
for row in seal['files']:
    path = task.PACKAGE / row['path']
    assert path.stat().st_size == row['size_bytes'] and sha256_file(path) == row['sha256'], row['path']
assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
task.verify_sources(manifest['source_sha256'])
records = verify_records(task.PACKAGE / 'records.jsonl', task.PACKAGE)
qualified = entry.read(task.PACKAGE / 'QUALIFICATION.json')
assert qualified['completion_requests'] == 0 and qualified['port_free']
assert qualified['native_forms']['status'] == 'passed'
assert all(row['accepted_including_eos'] == row['expected'] for row in qualified['native_forms']['cases'])
assert qualified['native_forms']['model_inference_calls'] == 0
assert qualified['route']['submitted'] and qualified['route']['failed_then_passed']
wire = entry.read(task.PACKAGE / 'initial-wire-request.json')
frame = json.loads(wire['messages'][1]['content'])
workspace = frame['workspace']
session = task.initial_session()
assert (session.requests_used, session.calls_used, session.request_limit, session.call_limit) == (47, 77, 59, 113)
assert wire['seed'] == 314159 and wire['chat_template_kwargs'] == dict(enable_thinking=True, reasoning_effort='medium')
assert wire['max_tokens'] == wire['n_predict'] == -1 and wire['cache_prompt'] is False
assert not workspace['working_set']['sources']
assert session.candidate.candidate_id == '3f726b6d0241fee324b48ecf49f4fbef51495ae18f6b4be79c219f7d217cd804'
result = dict(status='verified', artifacts=len(seal['files']), source_bindings=len(manifest['source_sha256']),
              custody_records=len(records), native_forms=len(qualified['native_forms']['cases']),
              completion_requests=0, initial_tokens=qualified['initial']['prompt_tokens'],
              maximum_scripted_input=max(max(r['input_tokens'], r['following_tokens']) for r in qualified['route']['trace']),
              scripted_decisions=qualified['route']['decisions'], checker_sha256=session.check_contracts['public']['checker_sha256'],
              memory=qualified['memory'], port_free=qualified['port_free'])
entry.study.save(Path(__file__).parent, 'PREPARATION_VERIFICATION-001.json', result)
print(json.dumps(result))
