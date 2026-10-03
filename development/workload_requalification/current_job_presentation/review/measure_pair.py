"""Extract recorded costs and input facts; semantic judgments require direct review."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def measure(condition, version):
    run = HERE / condition / f'run-{version}'
    records = [json.loads(line) for line in (run/'records.jsonl').read_text(encoding='utf-8').splitlines()]
    complete = {r['payload']['id']: r['payload'] for r in records if r['record_type'] == 'invocation_completed'}
    started = {r['payload']['id']: r['payload'] for r in records if r['record_type'] == 'invocation_started'}
    calls = []
    for name, start in started.items():
        wire = read(run/'calls'/f'{name}-wire-request.json')
        state = json.loads(wire['messages'][1]['content'])['workspace']
        item = dict(id=name, complete=name in complete, prompt_tokens=start['prompt_tokens'],
            sources=[{k: s.get(k) for k in ('path','returned_start_line','returned_end_line','file_sha256','region_ref','whole_file_shown')}
                     for s in state['working_set']['sources']],
            verification=state['verification'], account=state.get('working_account'),
            actual_obstacle=state.get('recent_edit_rejection'),
            latest_feedback=state['latest_feedback'])
        if name in complete:
            result = read(run/'calls'/f'{name}-host-result.json')
            response = read(run/'calls'/f'{name}-endpoint-response.json')
            item.update(elapsed_seconds=complete[name]['elapsed_seconds'], usage=complete[name]['usage'],
                timings=response.get('timings'), actual_operations=complete[name]['actual_operations'],
                maximum_input_plus_generation=complete[name]['usage']['total_tokens'],
                operations=result.get('operations', []), executed=result.get('executed'))
        calls.append(item)
    ended = [c for c in calls if c['complete']]
    summary = dict(condition=condition, version=version, requests_completed=len(ended),
        requests_sent=len(calls), operations=sum(c['actual_operations'] for c in ended),
        prompt_tokens=sum(c['usage']['prompt_tokens'] for c in ended),
        generated_tokens=sum(c['usage']['completion_tokens'] for c in ended),
        model_seconds=sum(c['elapsed_seconds'] for c in ended),
        peak_input=max((c['prompt_tokens'] for c in calls),default=0),
        peak_input_plus_generation=max((c['maximum_input_plus_generation'] for c in ended),default=0),
        calls=calls, semantic_review_required=True)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('condition', choices=('control','current_job'))
    parser.add_argument('--version', default='003')
    parser.add_argument('--save', action='store_true')
    args = parser.parse_args()
    value = measure(args.condition,args.version)
    if args.save:
        seal = HERE/args.condition/f'run-{args.version}'/'RESPONSE_SEAL.json'
        assert seal.is_file(), 'Only save a closed-run measurement'
        value['seal_sha256'] = hashlib.sha256(seal.read_bytes()).hexdigest()
        path = HERE/'review'/f'MEASUREMENTS-{args.condition}-{args.version}.json'
        with path.open('x',encoding='utf-8') as stream:
            json.dump(value,stream,ensure_ascii=False,indent=2)
            stream.write('\n')
    print(json.dumps({k:v for k,v in value.items() if k!='calls'},ensure_ascii=False))
    for c in value['calls']:
        print(json.dumps(dict(id=c['id'], complete=c['complete'], prompt_tokens=c['prompt_tokens'],
            generated_tokens=c.get('usage',{}).get('completion_tokens'),
            seconds=c.get('elapsed_seconds'),
            operations=[dict(action=o['action']['action'],path=o['action'].get('path'),
                accepted=o['result'].get('accepted'),passed=o['result'].get('passed')) for o in c.get('operations',[]) ])))


if __name__=='__main__': main()
