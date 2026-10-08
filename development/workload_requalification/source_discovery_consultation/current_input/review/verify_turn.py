"""Exact custody/runtime audit; interpretation still requires direct reading."""
import json
from pathlib import Path
import sys

AREA=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(AREA))
import consult
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file

RUN=AREA/'turn-01'
read=lambda p:json.loads(p.read_bytes())
seal=consult.RUNTIME.verify_seal(RUN)
assert seal['source_sha256']==consult.identities()
assert seal['sent_requests']==1
plan=read(AREA/'preparation-01/PLAN.json')
request=read(RUN/'calls/D1-endpoint-request.json')
assert request==consult.request_for(1)
assert sha256_bytes(canonical_json_bytes(request))==plan['request_sha256']
native=(RUN/'calls/D1-native.txt').read_bytes()
assert native==consult.native_for(request) and sha256_bytes(native)==plan['native_sha256']
response=read(RUN/'calls/D1-endpoint-response.json')
choice,usage=response['choices'][0],response['usage']
assert usage['prompt_tokens']==plan['prompt_tokens']==22789
assert usage['total_tokens']==usage['prompt_tokens']+usage['completion_tokens']<=56576
assert usage.get('prompt_tokens_details',{}).get('cached_tokens')==0
message=choice['message']
assert (RUN/'calls/D1-assistant-content.txt').read_bytes()==(message.get('content') or '').encode()
assert (RUN/'calls/D1-assistant-reasoning.txt').read_bytes()==(message.get('reasoning_content') or '').encode()
host=read(RUN/'calls/D1-host-result.json')
assert host['executed'] is False and host['candidate_mutated'] is False
assert host['tool_execution_enabled'] is False
records=verify_records(RUN/'records.jsonl',RUN)
row=next(r['payload'] for r in records if r['record_type']=='invocation_completed')
private={name:sha256_file(RUN/'private-runtime'/name)==digest
         for name,digest in seal['private_runtime_files_local_only'].items()}
assert all(private.values())
runtime=seal['runtime']
assert seal['port_free'] and all(runtime[k] for k in ('full_offload','context_matches','q4_k_and_v','mtp_disabled'))
result=dict(disposition=seal['disposition'],files=len(seal['files']),custody_records=len(records),
    source_bindings=len(seal['source_sha256']),usage=usage,finish_reason=choice['finish_reason'],
    model_request_seconds=row['elapsed_seconds'],timings=response.get('timings'),
    no_execution=True,private_files_verified=private,runtime=runtime,memory=seal['memory'],
    port_free=seal['port_free'])
(Path(__file__).parent/'VERIFICATION.json').write_bytes(canonical_json_bytes(result))
print(json.dumps(result,indent=2))
