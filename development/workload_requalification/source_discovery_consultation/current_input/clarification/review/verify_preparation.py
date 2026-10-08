"""Verify exact D2 input, source bindings and zero-completion native preparation."""
import json
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import clarify
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

read = lambda p: json.loads(p.read_bytes())
folder = AREA/'native-preparation-02'
seal, plan = read(folder/'SEAL.json'), read(AREA/'preparation-02/PLAN.json')
assert seal['status'] == 'qualified_no_model_inference' and seal['completion_requests'] == 0
assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
for row in seal['files']:
    raw = (folder/row['path']).read_bytes()
    assert len(raw) == row['size_bytes'] and sha256_bytes(raw) == row['sha256']
assert seal['source_sha256'] == plan['source_sha256'] == clarify.identities()
for path, digest in seal['source_sha256'].items():
    assert sha256_file(clarify.ROOT/path) == digest, path
records = verify_records(folder/'records.jsonl', folder)
assert not any(r['record_type'] == 'invocation_started' for r in records)
request = read(folder/'request.json')
assert request == read(AREA/'preparation-02/request.json') == clarify.request_for(2, clarify.FOLLOW)
assert sha256_bytes(canonical_json_bytes(request)) == plan['request_sha256']
native = (folder/'native.txt').read_bytes()
assert native == (AREA/'preparation-02/native.txt').read_bytes() == clarify.first.native_for(request)
assert sha256_bytes(native) == plan['native_sha256'] and plan['prompt_tokens'] <= 23808
result = dict(status='verified_no_completions', files=len(seal['files']),
    source_bindings=len(seal['source_sha256']), custody_records=len(records),
    prompt_tokens=plan['prompt_tokens'], physical_generation_space=plan['physical_generation_space'],
    exact_original_library_excerpt=True, full_d1_public_answer=True, reviewer_source_facts=True,
    executor_attached=False, unchanged_d1_source_bindings=True)
(Path(__file__).parent/'PREPARATION_AUDIT.json').write_bytes(canonical_json_bytes(result))
print(json.dumps(result, indent=2))
