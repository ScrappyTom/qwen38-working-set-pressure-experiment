"""Read full saved response and actual changing input, keeping opaque ledgers compact.

This evaluator display never edits or invokes the actor. Large source extents are
checked against the exact saved candidate; this is not a semantic reading claim.
"""
import argparse
import json
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AREA))
import probe_task as study

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('tag')
parser.add_argument('--version', default='001')
args = parser.parse_args()
sys.stdout.reconfigure(encoding='utf-8')
task = study.Task(args.version)
folder = task.RUN / 'calls'
wire = task.read(folder / f'{args.tag}-wire-request.json')
view = json.loads(wire['messages'][-1]['content'])
number = int(args.tag[1:])
prior = None
if number > 1:
    earlier = task.read(folder / f'C{number-1:02d}-wire-request.json')
    assert wire['messages'][0] == earlier['messages'][0]
    prior = json.loads(earlier['messages'][-1]['content'])
    candidates = sorted((task.RUN / 'after').glob(f'C{number-1:02d}-O*-candidate.json'))
    candidate = task.candidate_from_snapshot(task.read(candidates[-1]))
else:
    candidate = task.candidate_from_snapshot(task.read(task.RUN / 'starting-candidate.json'))
assert view['workspace']['candidate_id'] == candidate.candidate_id
for row in view['workspace']['working_set']['sources']:
    raw = candidate.file_map[row['path']]
    assert row['file_sha256'] == candidate.file_sha256(row['path'])
    body = row['content']
    assert body == ''.join(raw.decode().splitlines(keepends=True)[row['returned_start_line']-1:row['returned_end_line']])
    if len(body) > 3000:
        row.pop('content')
        row['evaluator_exact_bytes_match_candidate_extent'] = True
        row['evaluator_first_two_lines'] = body.splitlines()[:2]
        row['evaluator_last_four_lines'] = body.splitlines()[-4:]
if prior:
    for key in ('task', 'episode_annotation', 'candidate_limits', 'current_p0',
                'phase', 'verification', 'observation_directory', 'working_account',
                'presentation', 'visibility'):
        if view['workspace'][key] == prior['workspace'][key]:
            view['workspace'][key] = {'evaluator_display': 'unchanged from preceding actual input'}
print(json.dumps(view, indent=2, ensure_ascii=False))
for suffix in ('assistant-reasoning.txt', 'assistant-content.txt'):
    path = folder / f'{args.tag}-{suffix}'
    if path.exists():
        print('\n' + suffix + '\n' + path.read_text(encoding='utf-8'))
for path in sorted(folder.glob(f'{args.tag}-operation-*.json')):
    value = task.read(path)
    # Operation source bodies are separately authenticated above or in the next
    # call; retain exact result extents and candidate/probe/check effects here.
    for row in [value['result'], *value['result'].get('sources', []), value['result'].get('source', {})]:
        if isinstance(row, dict) and len(row.get('content', '')) > 3000:
            row['content'] = '<evaluator display omission; inspect exact next-input source>'
    print(path.name + '\n' + json.dumps(value, indent=2, ensure_ascii=False))
