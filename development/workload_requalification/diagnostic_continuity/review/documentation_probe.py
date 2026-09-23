"""Post-run probes of the saved prose's whitespace/setting description."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import bootstrap
import continuity_task as study
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file

run=study.AREA/'run-002'
assert (run/'RESPONSE_SEAL.json').exists()
raw=study.previous.read(run/'final-candidate.json')
source=next(x['content_utf8'] for x in raw['files'] if x['path']=='Lib/configparser.py')
space={'__name__':'reviewed_saved_configparser'}
exec(compile(source,'saved/Lib/configparser.py','exec'),space)
cases={
 'greater_indentation':'[s]\n    flag\n        continued\n',
 'same_indentation':'[s]\n    flag\n    next_flag\n',
 'whitespace_only':'[s]\nflag\n    \n',
 'indented_comment':'[s]\nflag\n    # comment\n'}
rows=[]
for name,text in cases.items():
 parser=space['ConfigParser'](allow_no_value=True)
 try:
  parser.read_string(text)
  result={'raised':None,'items':dict(parser.items('s'))}
 except Exception as error:
  result={'raised':type(error).__name__,'line':getattr(error,'line',None),'lineno':getattr(error,'lineno',None)}
 rows.append(dict(name=name,input=text,**result))
value=dict(classification='Independent post-run prose review, not model evidence or a changed acceptance score',
 candidate_id=raw['candidate_id'],cases=rows,
 public_allow_no_value_attribute=hasattr(space['ConfigParser'](allow_no_value=True),'allow_no_value'),
 source_sha256=sha256_file(Path(__file__)),model_requests=0,checker_executions=0)
assert rows[0]['raised']=='MultilineContinuationError'
assert all(row['raised'] is None for row in rows[1:])
Path(__file__).with_name('DOCUMENTATION_PROBE.json').write_bytes(canonical_json_bytes(value))
print(json.dumps(value,indent=2))
