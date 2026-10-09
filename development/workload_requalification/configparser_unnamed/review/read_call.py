"""Display actual input deltas and exact response/effect text for direct review.

Input deltas require the preceding input to have been read. A source body may be
identified as identical to the preceding reviewed result; this is a byte comparison,
not a summary or a claim of semantic use. This script never changes a run.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_bytes())


def contents(value):
    if isinstance(value, dict):
        for k,v in value.items():
            if k == 'content' and isinstance(v,str):
                yield v
            yield from contents(v)
    elif isinstance(value,list):
        for v in value:
            yield from contents(v)


def differences(a, b, known, path='input'):
    if a == b:
        return
    if isinstance(b,dict):
        a = a if isinstance(a,dict) else {}
        for k in sorted(a.keys()|b.keys()):
            if k not in b:
                print(path+'/'+k, '[removed]')
            else:
                differences(a.get(k),b[k],known,path+'/'+k)
    elif isinstance(b,list):
        a = a if isinstance(a,list) else []
        for i in range(max(len(a),len(b))):
            if i>=len(b):print(path+'/'+str(i),'[removed]')
            else:differences(a[i] if i<len(a) else None,b[i],known,path+'/'+str(i))
    elif path.endswith('/content') and isinstance(b,str) and b in known:
        print(path, '[exact preceding input/result body]',hashlib.sha256(b.encode()).hexdigest())
    elif path.endswith('/content') and isinstance(a,str) and isinstance(b,str) and b.startswith(a) and any(b[len(a):] in x for x in known):
        print(path, '[exact preceding input plus text present in preceding input/result]',hashlib.sha256(b.encode()).hexdigest())
    elif path.endswith('/content') and isinstance(a,str) and isinstance(b,str):
        print(path, '[exact textual delta from preceding input]',hashlib.sha256(b.encode()).hexdigest())
        print(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='preceding',tofile='current')))
    else:
        print(path)
        print(b if isinstance(b,str) else json.dumps(b,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser()
    parser.add_argument('number',type=int)
    parser.add_argument('--version',default='001')
    parser.add_argument('--part',choices=('input','reasoning','final','effect'),required=True)
    parser.add_argument('--start',type=int,default=0)
    parser.add_argument('--end',type=int,default=30000)
    args=parser.parse_args()
    folder=AREA/f'run-{args.version}/calls'
    tag=f'C{args.number:02d}'
    if args.part=='input':
        current=read(folder/f'{tag}-wire-request.json')
        packet=json.loads(current['messages'][-1]['content'])
        old={}; known=set()
        if args.number>1:
            previous_folder = folder
            previous=read(previous_folder/f'C{args.number-1:02d}-wire-request.json')
            assert current['messages'][0] == previous['messages'][0], 'System changed; read both in full'
            old=json.loads(previous['messages'][-1]['content'])
            known=set(contents(read(previous_folder/f'C{args.number-1:02d}-host-result.json')))
            known.update(contents(old))
        differences(old,packet,known)
    else:
        suffix={'reasoning':'assistant-reasoning.txt','final':'assistant-content.txt','effect':'host-result.json'}[args.part]
        value=(folder/f'{tag}-{suffix}').read_text(encoding='utf-8')
        print(f'EXACT CHARACTERS {args.start}:{min(args.end,len(value))} OF {len(value)}')
        print(value[args.start:args.end])
