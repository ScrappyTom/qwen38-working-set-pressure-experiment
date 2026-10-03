"""Read saved inputs and outputs; no intervention in the operating run."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'run-001'
parser = argparse.ArgumentParser()
parser.add_argument('mode', choices=('status', 'input', 'changes', 'sources', 'thinking', 'reply', 'effect'))
parser.add_argument('--call')
parser.add_argument('--start', type=int, default=0)
parser.add_argument('--end', type=int)
args = parser.parse_args()
read = lambda path: json.loads(path.read_text(encoding='utf-8'))
if args.mode == 'status':
    rows = [json.loads(line) for line in (RUN / 'records.jsonl').read_text(encoding='utf-8').splitlines()]
    for row in rows[-5:]:
        print(json.dumps(dict(type=row['record_type'], time=row['created_at_utc'], payload=row['payload'])))
    for file in sorted((RUN / 'calls').glob('*-endpoint-response.json')):
        response = read(file)
        choice = response['choices'][0]
        print(json.dumps(dict(call=file.name.split('-')[0], usage=response['usage'],
            timings=response.get('timings'), finish=choice['finish_reason'],
            reasoning_lines=len((choice['message'].get('reasoning_content') or '').splitlines()))))
else:
    stem = RUN / 'calls' / args.call
    if args.mode in ('input', 'changes', 'sources'):
        wire = read(stem.with_name(args.call + '-wire-request.json'))
        frame = json.loads(wire['messages'][1]['content'])
        if args.mode in ('input', 'changes'):
            previous = None
            if args.mode == 'changes':
                prior_path = stem.with_name('C' + str(int(args.call[1:])-1) + '-wire-request.json')
                prior_wire = read(prior_path)
                assert wire['messages'][0] == prior_wire['messages'][0]
                assert {k:v for k,v in wire.items() if k != 'messages'} == {k:v for k,v in prior_wire.items() if k != 'messages'}
                previous = json.loads(prior_wire['messages'][1]['content'])
                changed = {k:v for k,v in frame['workspace'].items() if v != previous['workspace'].get(k)}
                frame['workspace'] = changed
            for source in frame['workspace'].get('working_set', {}).get('sources', []):
                text = source.pop('content')
                source['review_content_sha256'] = hashlib.sha256(text.encode()).hexdigest()
                source['review_content_bytes'] = len(text.encode())
            settings = {k:v for k,v in wire.items() if k not in ('messages', 'grammar')}
            settings['review_grammar_sha256'] = hashlib.sha256(wire['grammar'].encode()).hexdigest()
            print('REQUEST SETTINGS', json.dumps(settings))
            print('SYSTEM SHA256', hashlib.sha256(wire['messages'][0]['content'].encode()).hexdigest())
            print(json.dumps(frame, indent=2))
        else:
            for source in frame['workspace']['working_set']['sources']:
                print('SOURCE', source['path'], source['returned_start_line'], source['returned_end_line'], source['file_sha256'])
                for index, line in enumerate(source['content'].splitlines()[args.start:args.end], args.start):
                    print(f'{source["returned_start_line"] + index}: {line}')
    elif args.mode == 'thinking':
        lines = stem.with_name(args.call + '-assistant-reasoning.txt').read_text(encoding='utf-8').splitlines()
        print('TOTAL LINES', len(lines))
        for index, line in enumerate(lines[args.start:args.end], args.start + 1):
            print(f'{index}: {line}')
    else:
        suffix = '-assistant-content.txt' if args.mode == 'reply' else '-host-result.json'
        print(stem.with_name(args.call + suffix).read_text(encoding='utf-8'))
