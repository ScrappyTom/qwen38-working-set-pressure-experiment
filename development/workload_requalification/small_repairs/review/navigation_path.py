"""Read-only extraction of the observed artifact-map navigation information path.

This is not native counterfactual sizing and issues no inference/checker requests.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
AREA=ROOT/'development/workload_requalification/small_repairs/artifact_map'
RUN=AREA/'run-001'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    records=[json.loads(x) for x in (RUN/'records.jsonl').read_text(encoding='utf-8').splitlines()]
    sizes={r['payload']['id']:r['payload']['prompt_tokens'] for r in records if r['record_type']=='invocation_started'}
    rows=[]
    for n in range(4,14):
        tag=f'C{n:02d}';wire=RUN/f'calls/{tag}-wire-request.json'
        raw=wire.read_bytes();request=json.loads(raw);user=json.loads(request['messages'][-1]['content']);w=user['workspace']
        last=w['latest_feedback'];result=last['result']
        prior=[]
        for i in range(1,n):
            for op in read(RUN/f'calls/C{i:02d}-host-result.json')['operations']:
                if op['action']['action']=='tree':
                    prior.extend(e['path'] for e in op['result'].get('entries',[]))
        named=[p for p in sorted(set(prior)) if p in request['messages'][-1]['content']]
        rows.append(dict(id=tag,wire_sha256=hashlib.sha256(raw).hexdigest(),native_input_tokens=sizes[tag],
            current_p0=w['current_p0'],recent_activity=w['recent_activity'],
            account=w['working_account'],latest_feedback=last,
            selected_source_count=len(w['working_set']['sources']),
            selected_result_count=len(w['working_set']['saved_results']),
            omitted_by_capacity=w['presentation']['selected_bodies_omitted'],
            all_previously_returned_navigation_paths=sorted(set(prior)),
            previous_navigation_paths_whose_complete_path_text_occurs_in_input=named,
            note='A path-text occurrence may be an action target, account or entry, not proof that its complete result remains shown.'))
    output=dict(scope='C04 through C13 actual inputs; no counterfactual tokenization',
        tree_entry_limit=16,rows=rows,model_requests=0,checker_executions=0,tokenizer_requests=0)
    target=AREA/'review/NAVIGATION_INFORMATION_PATH.json'
    raw=(json.dumps(output,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    if target.exists():assert target.read_bytes()==raw
    else:target.write_bytes(raw)
    print(target)


if __name__=='__main__':main()
