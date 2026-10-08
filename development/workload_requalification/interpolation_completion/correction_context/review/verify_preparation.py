"""Independently inspect sealed no-inference trials and their actual inputs."""
import json
from pathlib import Path
import sys

AREA=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(AREA))
import study
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file

ROOT=study.original.ROOT
read=lambda p:json.loads(p.read_bytes())
consult=ROOT/'development/workload_requalification/source_discovery_consultation/current_input'
rows=[]
for folder in (AREA/'native-001',consult/'native-preparation-01'):
    seal=read(folder/'SEAL.json')
    assert seal['status']=='qualified_no_model_inference' and seal['completion_requests']==0
    assert sha256_bytes(canonical_json_bytes(seal['files']))==seal['aggregate_sha256']
    for row in seal['files']:
        raw=(folder/row['path']).read_bytes()
        assert len(raw)==row['size_bytes'] and sha256_bytes(raw)==row['sha256']
    for path,digest in seal['source_sha256'].items():
        assert sha256_file(ROOT/path)==digest,path
    records=verify_records(folder/'records.jsonl',folder)
    assert not any(r['record_type']=='invocation_started' for r in records)
    rows.append(dict(folder=folder.relative_to(ROOT).as_posix(),files=len(seal['files']),
                     source_bindings=len(seal['source_sha256']),custody_records=len(records)))

before,after=[read(AREA/'native-001'/f'{name}-view.json') for name in ('baseline','revised')]
differences=[key for key in before if before[key]!=after[key]]
assert set(differences)=={'working_set','visibility'},differences
assert before['latest_feedback']==after['latest_feedback']
source,=after['working_set']['sources']
candidate=read(study.qualified_task.Task().RUN/'after/C63-O03-candidate.json')
file=next(f for f in candidate['files'] if f['path']==source['path'])
assert source['candidate_id']==candidate['candidate_id'] and source['file_sha256']==file['sha256']
assert source['content']==''.join(file['content_utf8'].splitlines(keepends=True)[2203:2356])
assert 'UnboundLocalError' in str(after['latest_feedback'])

plan=read(consult/'preparation-01/PLAN.json')
request=read(consult/'native-preparation-01/request.json')
old=read(study.qualified_task.Task().RUN/'calls/C63-wire-request.json')
assert request==read(consult/'preparation-01/request.json')
assert plan['prompt_tokens']==22789 and request['seed']==42
assert not {'grammar','response_format','tools','functions'} & request.keys()
assert request['chat_template_kwargs']==dict(enable_thinking=True,reasoning_effort='medium')
assert all(request[k]==-1 for k in ('max_tokens','n_predict','reasoning_budget_tokens','thinking_budget_tokens'))
for message in old['messages']:
    assert message['content'] in request['messages'][1]['content']
assert (consult/'preparation-01/native.txt').read_bytes()==(consult/'native-preparation-01/native.txt').read_bytes()
assert sha256_file(consult/'native-preparation-01/native.txt')==plan['native_sha256']
result=dict(status='verified_no_completions',qualifications=rows,
            changed_view_fields=differences,exact_target_lines=[2204,2356],
            unchanged_real_failure=True,consultation_input_tokens=plan['prompt_tokens'])
(Path(__file__).parent/'PREPARATION_AUDIT.json').write_bytes(canonical_json_bytes(result))
print(json.dumps(result,indent=2))
