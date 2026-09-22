"""Exact C18-to-C19 change-detail inventory; no model or checker execution."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
AREA=ROOT/'development/workload_requalification/small_repairs/artifact_map'
RUN=AREA/'run-001'


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def strings(value,path='$'):
    if isinstance(value,str):yield path,value
    elif isinstance(value,dict):
        for k,v in value.items():yield from strings(v,path+'.'+k)
    elif isinstance(value,list):
        for i,v in enumerate(value):yield from strings(v,f'{path}[{i}]')


def main():
    request=read(RUN/'calls/C19-wire-request.json')
    user=json.loads(request['messages'][-1]['content']);w=user['workspace']
    action=read(RUN/'calls/C18-reply.json')['operation']
    stored=read(RUN/'after/C18-O01-state.json')['pairs'][-1]
    assert stored['response']==action
    diff=(RUN/'diffs/EVT-0027.patch').read_text(encoding='utf-8')
    old='    new_map = address_map\n';new='    new_map = build_address_map(new_artifact)\n'
    all_fields=list(strings(user))
    material=dict(old_fragment=action['old'],new_fragment=action['new'],changed_old_line=old,changed_new_line=new,diff=diff)
    occurrences={k:[p for p,text in all_fields if v in text] for k,v in material.items()}
    assert not occurrences['old_fragment'] and not occurrences['changed_old_line'] and not occurrences['diff']
    assert occurrences['new_fragment'] and occurrences['changed_new_line']
    assert all(old not in m['content'] for m in request['messages'])
    sources=[{k:s[k] for k in ['path','candidate_id','file_sha256','returned_start_line','returned_end_line','whole_file_shown']} for s in w['working_set']['sources']]
    records=[json.loads(x) for x in (RUN/'records.jsonl').read_text(encoding='utf-8').splitlines()]
    sizes={r['payload']['id']:r['payload']['prompt_tokens'] for r in records if r['record_type']=='invocation_started'}
    value=dict(scope='Complete C19 input, not only latest feedback',native_input_tokens=sizes['C19'],
        original_patch=action,archived_patch_matches_complete_reply=True,
        archived_diff=diff,material_occurrences_by_input_json_field=occurrences,
        system_message_contains_changed_old_line=old in request['messages'][0]['content'],
        source_extents=sources,latest_feedback=w['latest_feedback'],working_account=w['working_account'],
        verification=w['verification'],selected_saved_results=w['working_set']['saved_results'],
        original_bytes=[dict(path=str(p.relative_to(RUN)).replace('\\','/'),size_bytes=p.stat().st_size,
            sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in
            [RUN/'calls/C18-assistant-content.txt',RUN/'calls/C18-reply.json',RUN/'after/C18-O01-state.json',
             RUN/'diffs/EVT-0027.patch',RUN/'calls/C19-wire-request.json']],
        conclusion='The exact changed old line, full old fragment and diff are archived but absent from every C19 input field; the new fragment is present in refreshed source. No causal effect size is established.',
        model_requests=0,checker_executions=0,tokenizer_requests=0)
    target=AREA/'review/CHANGE_INFORMATION_PATH.json'
    raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    if target.exists():assert target.read_bytes()==raw
    else:target.write_bytes(raw)
    print(target)


if __name__=='__main__':main()
