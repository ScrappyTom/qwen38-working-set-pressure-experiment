"""Closed-run artifact comparison; no model or checker execution."""
import argparse,ast,difflib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TARGET='Lib/test/test_configparser.py'
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def files(path):return {r['path']:r['content_utf8'] for r in load(path)['files']}
def methods(text):
    return {(c.name,f.name):f for c in ast.parse(text).body if isinstance(c,ast.ClassDef)
            for f in c.body if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef)) and f.name.startswith('test')}
def main(version):
    run=ROOT.parent/f'run-{version}'
    assert (run/'RESPONSE_SEAL.json').exists(),'Only review closed work'
    stem='final' if (run/'final-candidate.json').exists() else 'stopped'
    initial=files(run/'starting-candidate.json');final=files(run/f'{stem}-candidate.json')
    old,new=methods(initial[TARGET]),methods(final[TARGET])
    changed=[p for p in initial if initial[p]!=final[p]]
    old_ok=all(k in new and ast.dump(v,include_attributes=False)==ast.dump(new[k],include_attributes=False) for k,v in old.items())
    added={'.'.join(k):ast.get_source_segment(final[TARGET],v) for k,v in new.items() if k not in old}
    saved_lines=initial[TARGET].splitlines(True);current_lines=final[TARGET].splitlines(True)
    removed=[]
    for op,a,b,c,d in difflib.SequenceMatcher(a=saved_lines,b=current_lines,autojunk=False).get_opcodes():
        if op in ('delete','replace'):removed.extend(saved_lines[a:b])
    snapshots=[]
    for path in sorted((run/'after').glob('*-candidate.json')):
        current=files(path)
        snapshots.append(dict(path=path.name,non_target_bytes_preserved=all(current[p]==initial[p] for p in initial if p!=TARGET)))
    checks=[]
    for path in sorted((run/'observations').glob('*/outcome.json')):
        out=load(path);report=load(path.parent/'stdout.bin')
        checks.append(dict(observation=path.parent.name,candidate_id=out['candidate_id'],executed=out['executed'],
            passed=out['passed'],termination=out['termination'],capture_complete=out['capture_complete'],
            report_passed=report.get('passed'),
            suite_counts={k:{f:report[k][f] for f in ('tests','failures','errors','skipped','successful')} for k in ('saved_suite','edited_suite','contract','transports')},
            modes={k:report['transports'][k] for k in ('observed_modes','required_modes','complete')},
            fault_counts={k:{f:v[f] for f in ('tests','failures','errors','successful')} for k,v in report['restoration_faults'].items()}))
    result=dict(classification='Post-run artifact preservation and recorded-check audit; direct review of new assertions remains necessary',
        candidate_id=load(run/f'{stem}-candidate.json')['candidate_id'],changed_files=changed,
        non_target_bytes_preserved=all(final[p]==initial[p] for p in initial if p!=TARGET),
        old_test_methods_preserved=old_ok,removed_old_nonblank_lines=[line for line in removed if line.strip()],
        added_methods=added,intermediate_snapshots=snapshots,checks=checks,
        model_requests=0,checker_executions=0)
    (ROOT/'ARTIFACT_AUDIT.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps({k:v for k,v in result.items() if k not in ('intermediate_snapshots','checks')},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--version',default='001');main(p.parse_args().version)
