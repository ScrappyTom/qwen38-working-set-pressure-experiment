"""Bounded reports over unchanged small-investigation checker observations."""
import copy
import json

from working_set_exp.observations import text_tail


def assessment(store, handle, contract=None):
    record=store.read(handle)
    if contract and contract['checker_sha256'] != record['checker_sha256']:
        raise ValueError('interpretation contract has another checker')
    stdout=(store.directory(handle)/'stdout.bin').read_bytes()
    stderr=(store.directory(handle)/'stderr.bin').read_bytes()
    rows=[];input_observations=[]
    try:
        parsed=[json.loads(line) for line in stdout.decode().splitlines()]
        known=bool(parsed) and all(isinstance(r,dict) for r in parsed)
    except (ValueError,UnicodeError):
        parsed=[];known=False
    if known and 'failed_cases' in parsed[-1]:
        input_observations=[r for r in parsed[:-1] if set(r)=={'observation','csv'}
                            and r['observation']=='input sequence' and isinstance(r['csv'],str)]
        cases=[r for r in parsed[:-1] if r not in input_observations];summary=parsed[-1]
        known=(all(isinstance(r.get('case'),str) and type(r.get('passed')) is bool for r in cases)
            and isinstance(summary['failed_cases'],list)
            and summary['failed_cases']==[r['case'] for r in cases if not r['passed']]
            and summary.get('passed')==(not summary['failed_cases']))
        if known:
            for case in cases:
                rows.append(dict(criterion=case['case'],met=case['passed'],
                    meaning='Original public behavioral case.',observation=case))
    if not rows:
        # Artifact-map emits one exact state observation followed by assertions.
        # No field in that object is reinterpreted as an independent acceptance rule.
        rows=[dict(criterion='public_execution',met=record['passed'],
            meaning='Exit status of the original public checker; inspect its exact observations and assertion diagnostic.',
            stdout=text_tail(stdout,8192),stderr=text_tail(stderr,4096))]
    if not record['capture_complete']:
        # A complete-looking case summary can precede timeout or stream loss.
        # Keep its observed cases, but never hide the uncompleted outer execution.
        incomplete=dict(criterion='public_execution',met=False,
            meaning='The public check did not complete normally; captured case records do not establish completed verification.',
            termination=record['termination'],returncode=record['returncode'],
            observation_capture_complete=False,stderr=text_tail(stderr,4096))
        existing=next((row for row in rows if row['criterion']=='public_execution'),None)
        if existing is None:
            rows.insert(0,incomplete)
        else:
            existing.update(incomplete)  # Keep fallback's exact bounded stdout too.
    elif record['passed'] != all(r['met'] for r in rows):
        rows.insert(0,dict(criterion='public_execution',met=record['passed'],
            meaning='Actual execution outcome governs; case records alone do not establish successful closure.',
            stderr=text_tail(stderr,4096)))
    rows.sort(key=lambda r:r['met'] is not False)
    return dict(observation=handle,scope=record['check_id'],candidate_id=record['candidate_id'],
        checker_sha256=record['checker_sha256'],executed=record['executed'],passed=record['passed'],
        termination=record['termination'],returncode=record['returncode'],
        observation_capture_complete=record['capture_complete'],assessment_available=True,
        criteria=rows,input_observations=input_observations,
        failed_criteria=[r['criterion'] for r in rows if r['met'] is False],
        raw_access=dict(action='inspect_observation',observation=handle,stream='stdout',offset=0),
        explanation='Original behavioral acceptance and actual execution. No injected faults in this task.')


def overview(value):
    result=copy.deepcopy(value)
    rows=[r for r in result['criteria'] if r['met'] is not True]
    result.update(criteria=rows[:2],failed_records_total=len(rows),failed_records_shown=min(2,len(rows)),
                  failed_records_remaining=max(0,len(rows)-2))
    return result


def inspect_check(store, handle, offset, contract=None):
    value=assessment(store,handle,contract);rows=value.pop('criteria')
    if type(offset) is not int or not 0 <= offset <= len(rows):
        raise ValueError('assessment offset is outside complete records')
    page=rows[offset:offset+4]
    return dict(accepted=True,kind='check_criteria',**value,entries=page,offset=offset,total_records=len(rows),
        next_offset=offset+len(page) if offset+len(page)<len(rows) else None,
        records_complete=True,all_records_shown=offset==0 and len(page)==len(rows))
