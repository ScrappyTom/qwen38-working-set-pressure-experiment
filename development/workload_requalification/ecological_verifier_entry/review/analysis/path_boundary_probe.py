"""Post-seal probe of validator-to-materializer composition; no writes by candidate."""
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re

AREA=Path(__file__).resolve().parents[2]
RUN=AREA/'run-003'
assert (RUN/'RESPONSE_SEAL.json').is_file(), 'Run must be closed first'
saved=json.loads((RUN/'final-candidate.json').read_text(encoding='utf-8'))
row=next(r for r in saved['files'] if r['path'].endswith('/verifiers.py'))
source=row['content_utf8']
tree=ast.parse(source)
function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_safe_relative_path')
materializer=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_materialize_artifacts')
space={'PurePosixPath':PurePosixPath,'re':re}
exec(compile(ast.Module(body=[function],type_ignores=[]),'<saved-validator>','exec'),space)
cases=('nested/module.py','C:/outside.py','C:outside.py','./C:/outside.py',
       'nested/C:/outside.py','nested/D:/outside.py','./D:/outside.py',
       'nested/../outside.py','')
results=[]
for base in ('C:/workspace','D:/workspace'):
    workspace=PureWindowsPath(base)
    for spelling in cases:
        relative=space['_safe_relative_path'](spelling)
        target=workspace.joinpath(*relative.parts) if relative is not None else None
        results.append(dict(workspace=str(workspace),spelling=spelling,
            validator_result=str(relative) if relative is not None else None,
            materialization_target=str(target) if target is not None else None,
            contained_by_native_join=target.is_relative_to(workspace) if target is not None else None))
result=dict(candidate_id=saved['candidate_id'],source_sha256=row['sha256'],
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    validator_source=ast.get_source_segment(source,function),
    materializer_source=ast.get_source_segment(source,materializer),
    results=results,
    accepted_outside_targets=[r for r in results if r['contained_by_native_join'] is False],
    scope='Exact saved validator executed; its returned parts passed to the same join expression using PureWindowsPath. No candidate materialization or filesystem write was performed.',
    role='Post-seal independent boundary review, not registered checker feedback or another model trajectory.')
path=AREA/'review/PATH-BOUNDARY-PROBE-003.json'
with path.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result,indent=2))
