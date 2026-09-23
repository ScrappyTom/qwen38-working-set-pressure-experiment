"""Review closed prose work, exact preservation and recorded checks; no inference."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import bootstrap
import followup_task as study
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file

run=study.AREA/'run-001'; out=Path(__file__).parent
assert (run/'RESPONSE_SEAL.json').exists(),'Run must be closed'
def files(path):
    value=study.read(path)
    return value,{r['path']:r['content_utf8'] for r in value['files']}
raw,final=files(run/'final-candidate.json'); _,initial=files(run/'starting-candidate.json')
changed=[p for p in initial if initial[p]!=final[p]]
assert changed==['Doc/library/configparser.rst'],changed
snapshots=[]
for path in sorted((run/'after').glob('*-candidate.json')):
    value,current=files(path)
    assert all(current[p]==initial[p] for p in initial if p!='Doc/library/configparser.rst')
    snapshots.append(dict(snapshot=path.name,candidate_id=value['candidate_id']))
checks=[]
for folder in sorted((run/'observations').iterdir()):
    report=study.read(folder/'stdout.bin'); outcome=study.read(folder/'outcome.json')
    checks.append(dict(observation=folder.name,outcome=outcome,passed=report['passed'],
        suites={k:{f:report[k][f] for f in ('tests','failures','errors','skipped','successful')} for k in ('upstream','contract','candidate_tests','new_tests_on_original')}))
start=final['Doc/library/configparser.rst'].index('.. exception:: MultilineContinuationError')
end=final['Doc/library/configparser.rst'].find('.. exception::',start+1)
entry=final['Doc/library/configparser.rst'][start:end if end!=-1 else None]
space={'__name__':'review_saved_configparser'}
exec(compile(final['Lib/configparser.py'],'saved/Lib/configparser.py','exec'),space)
cases={'greater_indentation':'[s]\n    flag\n        continued\n','same_indentation':'[s]\n    flag\n    next_flag\n',
       'whitespace_only':'[s]\nflag\n    \n','indented_comment':'[s]\nflag\n    # comment\n'}
probes=[]
for name,text in cases.items():
    parser=space['ConfigParser'](allow_no_value=True)
    try:
        parser.read_string(text); result=dict(raised=None,items=dict(parser.items('s')))
    except Exception as error:
        result=dict(raised=type(error).__name__,line=getattr(error,'line',None),lineno=getattr(error,'lineno',None))
    probes.append(dict(name=name,input=text,**result))
assert probes[0]['raised']=='MultilineContinuationError' and all(x['raised'] is None for x in probes[1:])
assert not hasattr(space['ConfigParser'](allow_no_value=True),'allow_no_value')
value=dict(classification='Independent post-run artifact/prose review; no new model-performance evidence',
    candidate_id=raw['candidate_id'],changed_files=changed,non_documentation_bytes_preserved_every_snapshot=True,
    snapshots=snapshots,entry=entry,checks=checks,documentation_probes=probes,
    source_sha256=sha256_file(Path(__file__)),model_requests=0,checker_executions=0,isolated_source_probes=4)
(out/'ARTIFACT_AUDIT.json').write_bytes(canonical_json_bytes(value))
print(json.dumps({k:v for k,v in value.items() if k not in ('checks','snapshots')},indent=2))
