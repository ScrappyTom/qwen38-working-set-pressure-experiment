"""Reuse exact run audit with this task's actual decoder and checkpoint adapter."""
import importlib.util
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import completion_task as entry
import qualified_task

path = entry.AREA.parent / 'dispatch_continuity/review/verify_dispatch.py'
spec = importlib.util.spec_from_file_location('interpolation_run_verifier', path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
task = qualified_task.Task()
audit.study = task
output = Path(__file__).parent / 'run-002'
output.mkdir(exist_ok=True)
audit.verify(task, output)

versions = {}
for path in task.RUN.rglob('*-state.json'):
    if not path.relative_to(task.RUN).as_posix().startswith(('after/', 'starting', 'final', 'stopped')):
        continue
    for value in entry.read(path)['source_versions']:
        candidate = entry.candidate_from_snapshot(value)
        versions[candidate.candidate_id] = candidate
presentations = []
for path in sorted((task.RUN / 'calls').glob('*-wire-request.json')):
    request = entry.read(path)
    import json
    view = json.loads(request['messages'][1]['content'])['workspace']
    candidate = versions[view['candidate_id']]
    for source in view['working_set']['sources']:
        raw = candidate.file_map[source['path']]
        assert source['file_sha256'] == entry.sha256_bytes(raw)
        expected = ''.join(raw.decode().splitlines(keepends=True)[source['returned_start_line']-1:source['returned_end_line']])
        assert source['content'] == expected
        presentations.append(dict(call=path.name.split('-')[0], path=source['path'],
            first=source['returned_start_line'], last=source['returned_end_line']))
entry.save(output, 'SOURCE_PRESENTATIONS.json', dict(status='verified', presentations=presentations))
print('Verified current-source presentations:', len(presentations))
