"""Audit closed saved-library work; execution observations are not rerun."""
import ast,difflib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import saved_task as study
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file
run=study.AREA/'run-001';out=Path(__file__).parent
assert (run/'RESPONSE_SEAL.json').exists(),'Do not audit incomplete artifact as final'
def files(path):
    raw=study.read(path);return raw,{r['path']:r['content_utf8'] for r in raw['files']}
initial,before=files(run/'starting-candidate.json')
ending='final' if (run/'final-candidate.json').exists() else 'stopped'
raw,after=files(run/(ending+'-candidate.json'))
changed=[p for p in before if before[p]!=after[p]]
path='Lib/test/test_configparser.py'
def methods(source):
    return {(cls.name,f.name):ast.dump(f,include_attributes=False) for cls in ast.parse(source).body if isinstance(cls,ast.ClassDef)
            for f in cls.body if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef)) and f.name.startswith('test')}
old,new=methods(before[path]),methods(after[path])
checks=[]
for folder in sorted((run/'observations').iterdir()):
    report=study.read(folder/'stdout.bin');outcome=study.read(folder/'outcome.json')
    checks.append(dict(observation=folder.name,outcome=outcome,passed=report['passed'],
        suites={k:{f:report[k][f] for f in ('tests','failures','errors','skipped','successful')} for k in ('upstream','contract','candidate_tests','new_tests_on_original')},
        actual_failures={k:report[k]['details'] for k in ('contract','candidate_tests')}))
removed=[line[2:] for line in difflib.ndiff(before[path].splitlines(True),after[path].splitlines(True)) if line.startswith('- ')]
value=dict(classification='Post-run actual saved work and observation audit; semantic review remains separate',
    candidate_id=raw['candidate_id'],starting_candidate=initial['candidate_id'],changed_files=changed,
    library_bytes_preserved=before['Lib/configparser.py']==after['Lib/configparser.py'],
    existing_test_methods_AST_preserved=all(new.get(k)==v for k,v in old.items()),
    added_test_methods=[list(k) for k in new if k not in old],removed_test_lines=removed,checks=checks,
    audit_source_sha256=sha256_file(Path(__file__)),checker_executions=0,model_requests=0)
(out/'ARTIFACT_AUDIT.json').write_bytes(canonical_json_bytes(value))
print(json.dumps({k:v for k,v in value.items() if k!='checks'},indent=2))
