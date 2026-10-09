"""Post-seal validator-to-native-consumer review; no candidate filesystem writes."""
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import string

AREA=Path(__file__).resolve().parents[2]
RUN=AREA/'run-001'
assert (RUN/'RESPONSE_SEAL.json').is_file(), 'Wait for closure'
saved=json.loads((RUN/'final-candidate.json').read_bytes())
row=next(r for r in saved['files'] if r['path'].endswith('/verifiers.py'))
source=row['content_utf8']; tree=ast.parse(source)
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_safe_relative_path')
consumer=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_materialize_artifacts')
space={'PurePosixPath':PurePosixPath,'PureWindowsPath':PureWindowsPath,'Path':Path,'re':re}
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<saved-validator>','exec'),space)
unsafe=[]
for letter in string.ascii_letters:
 for prefix in ('','./','nested/','nested/./'):
  for tail in ('/file.py','file.py',''):
   text=prefix+letter+':'+tail
   unsafe.extend((text,text.replace('/',chr(92))))
unsafe=sorted(set(unsafe)|{'','.', '..','nested/../file.py','/rooted.py',chr(92)+'rooted.py','//server/share/file.py',chr(92)*2+'server'+chr(92)+'share'+chr(92)+'file.py'})
valid=('file.py','nested/file.py','nested'+chr(92)+'file.py','./nested/file.py','nested//file.py','.hidden/file.py','alpha/beta/file.py')
results=[]
for spelling in unsafe+list(valid):
 relative=space['_safe_relative_path'](spelling)
 targets=[]
 for root in ('C:/workspace','D:/workspace'):
  workspace=PureWindowsPath(root)
  target=workspace.joinpath(*relative.parts) if relative is not None else None
  targets.append(dict(root=root,joined=str(target) if target is not None else None,
   contained=target.is_relative_to(workspace) if target is not None else None,
   expected_destination_matches=(target==workspace/str(PurePosixPath(spelling.replace(chr(92),'/')))) if target is not None else None))
 expected_reject=spelling in unsafe
 passed=(relative is None) if expected_reject else (relative is not None and all(t['contained'] and t['expected_destination_matches'] for t in targets))
 results.append(dict(spelling=spelling,expected_reject=expected_reject,returned=str(relative) if relative is not None else None,targets=targets,passed=passed))
out=dict(candidate_id=saved['candidate_id'],source_sha256=row['sha256'],script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 validator_source=ast.get_source_segment(source,fn),consumer_source=ast.get_source_segment(source,consumer),
 cases=len(results),unsafe_cases=len(unsafe),valid_cases=len(valid),passed=all(r['passed'] for r in results),failures=[r for r in results if not r['passed']],results=results,
 scope='Exact saved validator; native PureWindowsPath component join matching the inspected materializer. No unsafe materialization or filesystem write. Finite lexical composition coverage, not general filesystem/security certification.',
 role='Independent post-seal artifact review; not registered feedback or extra Qwen trajectories.')
with (AREA/'review/PATH-BOUNDARY-PROBE-001.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
print(json.dumps({k:v for k,v in out.items() if k not in ('results','validator_source','consumer_source')},indent=2))
