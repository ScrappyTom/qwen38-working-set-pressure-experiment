"""Review saved contribution and actual observations, without executing another check."""
import ast,json,sys,difflib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import bootstrap
import continuity_task as study
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file


def main():
    run=study.AREA/'run-002';out=Path(__file__).parent
    assert (run/'RESPONSE_SEAL.json').exists(),'Run must be closed'
    raw=study.previous.read(run/'final-candidate.json')
    files={r['path']:r['content_utf8'] for r in raw['files']}
    original={k:v.decode() for k,v in study.original.starting_candidate().file_map.items()}
    tests=files['Lib/test/test_configparser.py'];tree=ast.parse(tests)
    base=ast.parse(original['Lib/test/test_configparser.py'])
    oldclasses={n.name:ast.dump(n,include_attributes=False) for n in base.body if isinstance(n,ast.ClassDef)}
    classes={n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.ClassDef)}
    preserved=all(classes.get(k)==v for k,v in oldclasses.items())
    changes=[p for p in files if files[p]!=original[p]]
    patch=''.join(''.join(difflib.unified_diff(original[p].splitlines(True),files[p].splitlines(True),fromfile='original/'+p,tofile='saved/'+p)) for p in changes)
    (out/'complete-contribution.patch').write_bytes(patch.encode())
    checks=[]
    for folder in sorted((run/'observations').iterdir()):
        report=study.previous.read(folder/'stdout.bin')
        outcome=study.previous.read(folder/'outcome.json')
        checks.append(dict(observation=folder.name,outcome=outcome,
            suites={k:{f:report[k][f] for f in ('tests','failures','errors','skipped','successful')} for k in ('upstream','contract','candidate_tests','new_tests_on_original')},
            diagnostics={k:report[k]['details'] for k in ('contract','candidate_tests')},
            passed=report['passed']))
    result=dict(classification='Direct saved-artifact and actual-observation audit; no new execution',
        candidate_id=raw['candidate_id'],changed_files=changes,existing_test_class_ASTs_preserved=preserved,
        checks=checks,model_requests=0,checker_executions=0,audit_source_sha256=sha256_file(Path(__file__)),
        documentation_semantics='Require direct review; no success inferred from declaration presence')
    (out/'ARTIFACT_AUDIT.json').write_bytes(canonical_json_bytes(result))
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))

if __name__=='__main__':main()
