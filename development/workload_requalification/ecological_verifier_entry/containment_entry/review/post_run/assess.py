"""Post-seal accounting and ordinary execution; never part of actor inputs."""
import ast
from collections import Counter
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

AREA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AREA))
import continuation_task as study


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    raw = (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)


def assess():
    run = AREA / 'run-001'
    review = AREA / 'review'
    read = study.read
    seal = read(run / 'RESPONSE_SEAL.json')
    verified = read(review / 'VERIFICATION-001.json')
    assert verified['status'] == 'replayed_exactly'
    assert verified['response_seal_sha256'] == digest((run/'RESPONSE_SEAL.json').read_bytes())
    metric = study.load_private('verifier_cost_reader', study.ROOT /
        'development/workload_requalification/url_port_continuation/review/measure_run.py')
    metric.checked_seal(run)
    records = metric.records(run)
    calls = metric.calls(run, records)
    ops = [read(run/r['artifacts'][0]['path']) for r in records
           if r['record_type'] == 'contribution_operation']
    loops = [r['payload'] for r in records if r['record_type'] == 'task_loop_completed']
    closure = [r['payload'] for r in records if r['record_type'] == 'runtime_closed']
    assert len(closure) == 1 and closure[0]['owned_server_shutdown_verified']
    assert closure[0]['dedicated_port_free']
    timings = []
    for c in calls:
        endpoint = read(run / f"calls/{c['id']}-endpoint-response.json")
        timings.append(dict(id=c['id'], timings=endpoint.get('timings')))
    save(review/'METRICS-001.json', dict(
        status='recomputed_from_sealed_records', seal_sha256=digest((run/'RESPONSE_SEAL.json').read_bytes()),
        aggregate=metric.aggregate(calls), calls=calls, endpoint_timings=timings,
        operations=len(ops), operation_types=dict(Counter(o['action']['action'] for o in ops)),
        rejected_operations=[dict(action=o['action'], result=o['result']) for o in ops if not o['result']['accepted']],
        task_loop=loops, runtime_closure=closure[0], memory=seal['memory'], runtime=seal['runtime'],
        script_sha256=digest(Path(__file__).read_bytes()),
        limits=['Generated tokens include thinking and public output; not a waste estimate.',
                'Preparation, source review and independent grading are additional development costs.',
                'A prepared terminal receipt has no subsequent model request.']))
    final_path = run/('final-candidate.json' if (run/'final-candidate.json').exists() else 'stopped-candidate.json')
    candidate = read(final_path)
    files = {r['path']:r['content_utf8'].encode() for r in candidate['files']}
    for row in candidate['files']:
        assert digest(files[row['path']]) == row['sha256']
    original = {r['path']:r['content_utf8'].encode() for r in study.read(study.OLD/'final-candidate.json')['files']}
    changed = [p for p in files if files[p] != original[p]]
    assert changed == [study.TARGET], changed
    before, after = (ast.parse(data.decode()) for data in (original[study.TARGET], files[study.TARGET]))
    funcs = lambda tree: {n.name:n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    old, new = funcs(before), funcs(after)
    assert old.keys() == new.keys()
    changed_functions = []
    for name in old:
        assert ast.dump(old[name].args) == ast.dump(new[name].args), name
        assert (ast.dump(old[name].returns) if old[name].returns else None) == (
            ast.dump(new[name].returns) if new[name].returns else None), name
        if ast.dump(old[name]) != ast.dump(new[name]): changed_functions.append(name)
    declarations = lambda tree: [ast.dump(n) for n in tree.body if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    diff = ''.join(difflib.unified_diff(original[study.TARGET].decode().splitlines(True),
                                      files[study.TARGET].decode().splitlines(True),fromfile='original',tofile='saved'))
    with (review/'SAVED-PATCH.diff').open('x',encoding='utf-8',newline='\n') as stream: stream.write(diff)
    checks = []
    programs = [('original_public',study.exact(study.EXECUTION_ONLY/'public.py',study.ORIGINAL_PUBLIC_SHA)),
                ('original_hidden',study.exact(study.EVALUATOR_ONLY/'hidden.py',study.HIDDEN_SHA)),
                ('parent_expanded_public',study.previous.public_checker()),
                ('successor_composition_public',study.contract_checker.public_checker())]
    for name, program in programs:
        with tempfile.TemporaryDirectory(prefix='verifier_review_') as folder:
            root = Path(folder)
            for path, raw in files.items():
                target=root/path
                assert target.resolve().is_relative_to(root.resolve())
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(raw)
            check=root/'_review_check.py';check.write_bytes(program)
            start=time.monotonic()
            result=subprocess.run([sys.executable,'-B','-X','utf8',str(check)],cwd=root,
                capture_output=True,timeout=90)
            checks.append(dict(name=name,checker_sha256=digest(program),returncode=result.returncode,
                stdout_utf8=result.stdout.decode('utf-8'),stderr_utf8=result.stderr.decode('utf-8'),
                elapsed_seconds=time.monotonic()-start,candidate_id=candidate['candidate_id'],
                environment=dict(interpreter=sys.executable,cwd='fresh candidate root',
                    argv=['-B','-X','utf8','_review_check.py']),
                interpretation='Independent post-seal artifact execution, not another Qwen trajectory.'))
    save(review/'ARTIFACT-ASSESSMENT-001.json',dict(status='assessed',candidate_id=candidate['candidate_id'],
        final_candidate_sha256=digest(final_path.read_bytes()),changed_files=changed,unchanged_files=len(files)-len(changed),
        changed_functions=changed_functions,function_count=len(old),all_function_signatures_preserved=True,
        nonfunction_declarations_unchanged=declarations(before)==declarations(after),checks=checks,
        script_sha256=digest(Path(__file__).read_bytes()),
        limits=['Finite acceptance cases and direct source review, not comprehensive security certification.',
                'Original and expanded checker definitions remain separately reported.']))
    print(json.dumps(dict(metrics=metric.aggregate(calls),operations=len(ops),candidate_id=candidate['candidate_id'],
        changed_files=changed,changed_functions=changed_functions,checks=[(c['name'],c['returncode']) for c in checks]),indent=2))


if __name__ == '__main__':
    assess()
