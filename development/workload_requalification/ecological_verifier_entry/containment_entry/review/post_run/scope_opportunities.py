"""Correct post-run opportunity reporting across explicitly changed job budgets."""
import json
from pathlib import Path
import sys
AREA=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(AREA))
import continuation_task as m
from working_set_exp.measurement import check_opportunity
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file


def scoped(pairs, start, limit):
    if type(start) is not int or not 0 <= start <= len(pairs) <= limit:
        raise ValueError('Job interval or allowance differs')
    rows=[]
    for sequence,pair in enumerate(pairs[start:],start+1):
        if pair['response'].get('action')=='check':
            rows.append(dict(sequence=sequence,first_check=not rows,
                **check_opportunity(calls_used=sequence-1,call_limit=limit,result=pair['result'])))
    return rows


def main():
    old=m.inherited_state();new=m.read(AREA/'run-001/final-state.json')
    original=scoped(old['pairs'],0,old['call_limit'])
    current=scoped(new['pairs'],m.INHERITED_OPERATIONS,new['call_limit'])
    records=[json.loads(r) for r in (m.OLD/'records.jsonl').read_bytes().splitlines()]
    old_record=next(r['payload']['check_opportunities'] for r in records if r['record_type']=='task_loop_completed')
    assert original==old_record
    assert [r['calls_remaining_before'] for r in original]==[72,69]
    assert len(current)==1 and current[0]['sequence']==31 and current[0]['first_check']
    assert current[0]['calls_remaining_before']==35 and current[0]['calls_remaining_after']==34
    records=[json.loads(r) for r in (AREA/'run-001/records.jsonl').read_bytes().splitlines()]
    raw=next(r['payload']['check_opportunities'] for r in records if r['record_type']=='task_loop_completed')
    assert [r['calls_remaining_before'] for r in raw]==[41,38,35]
    value=dict(status='scoped_reporting_corrected',parent_job=original,current_job=current,
        raw_continuation_recomputed_history=raw,script_sha256=sha256_file(Path(__file__)),
        explanation='The generic terminal report applies the new65-operation limit to inherited checks originally made under96. Its inherited rows are not historical allowance observations. Preserve sealed output; use original parent rows and only new-job rows here. No model input or execution counter was affected. Future continuation reporting must carry the job interval and declared limit.')
    with (AREA/'review/OPPORTUNITY-SCOPE-001.json').open('xb') as f:f.write(canonical_json_bytes(value))
    print(json.dumps(value,indent=2))

if __name__=='__main__':main()
