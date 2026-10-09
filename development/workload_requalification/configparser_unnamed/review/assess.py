"""Closed coding-artifact checks; distinct from the model's recorded outcomes."""
import argparse
from collections import Counter
import difflib
import importlib.util
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unnamed_task as study
import unnamed_material as material
import unnamed_cpu as qualify_cpu
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else canonical_json_bytes(value)
    if path.exists():
        assert path.read_bytes() == raw, 'Do not overwrite a differing assessment'
    else:
        path.write_bytes(raw)


def assess(version):
    task = study.Task(version)
    verification_path = task.AREA/f'review/VERIFICATION-{version}.json'
    verification = task.read(verification_path)
    assert verification['status'] == 'replayed_exactly'
    manifest = task.read(task.RUN/'EXECUTION_MANIFEST.json')
    task.verify_sources(manifest['source_sha256'])
    assert verification['executed_manifest_sha256'] == sha256_file(task.RUN/'EXECUTION_MANIFEST.json')
    metric_path = task.ROOT/'development/workload_requalification/url_port_continuation/review/measure_run.py'
    spec = importlib.util.spec_from_file_location('write_safety_costs', metric_path)
    metrics = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(metrics)
    seal, records = metrics.checked_seal(task.RUN), metrics.records(task.RUN)
    calls = metrics.calls(task.RUN, records)
    operations = [(r['payload']['id'], task.read(task.RUN/r['artifacts'][0]['path']))
                  for r in records if r['record_type'] == 'contribution_operation']
    folder = task.AREA/f'review/{version}'
    stem = 'final' if (task.RUN/'final-state.json').exists() else 'stopped'
    candidate = task.candidate_from_snapshot(task.read(task.RUN/f'{stem}-candidate.json'))
    assert candidate.candidate_id == verification['final_candidate_id']
    before = task.candidate_from_snapshot(task.read(task.RUN/'starting-candidate.json')).file_map
    after = candidate.file_map
    changed = [p for p in before if before[p] != after[p]]
    diff = ''.join(''.join(difflib.unified_diff(before[p].decode().splitlines(True),
        after[p].decode().splitlines(True), fromfile='starting/'+p, tofile='saved/'+p)) for p in changed)
    save(folder/'SAVED-PATCH.diff', diff.encode())
    identity = dict(candidate_id=candidate.candidate_id,
        response_seal_sha256=sha256_file(task.RUN/'RESPONSE_SEAL.json'),
        exact_replay_sha256=sha256_file(verification_path), assessor_sha256=sha256_file(Path(__file__)))
    save(folder/'METRICS.json', dict(**identity, aggregate=metrics.aggregate(calls), calls=calls,
        actual_operations=len(operations), operation_types=dict(Counter(o['action']['action'] for _, o in operations)),
        rejected=[dict(id=tag, operation=o) for tag,o in operations if not o['result']['accepted']],
        task_loop=[r['payload'] for r in records if r['record_type']=='task_loop_completed'],
        runtime=seal['runtime'], memory=seal['memory'],
        limits=['Costs exclude preparation, independent assessment and reviewer work.',
                'Generated counts include thinking and final output, not a waste estimate.']))
    # These are new evaluator executions, never retroactively added to actor history.
    actual = qualify_cpu.run(after)
    save(folder/'CHECKER-REEXECUTION.json', actual)
    ordinary = qualify_cpu.run(after, ordinary=True)
    save(folder/'ORDINARY-UNITTEST.json', ordinary)
    contract = qualify_cpu.direct(after[material.LIBRARY], 'post_run_unnamed')
    save(folder/'DIRECT-CONTRACT.json', contract)
    report = json.loads(actual['stdout']) if actual['stdout'].strip().startswith('{') else None
    preserved = all(after[p] == raw for p,raw in material.baseline_files().items()
                    if p not in (material.LIBRARY, material.DOC))
    result = dict(**identity, submitted=verification['submitted'], changed_files=changed,
        preserved_old_tests_support_and_license=preserved,
        no_other_file_changes=set(changed) <= {material.LIBRARY, material.DOC, material.NEW_TESTS},
        checker_passed=bool(actual['returncode']==0 and report and report['passed']),
        ordinary_suite_passed=ordinary['returncode']==0,
        direct_contract_passed=contract['successful'],
        new_tests_disagree_missing_feature_baseline=bool(report and not report['new_tests_on_original']['successful']),
        report_counts={k:{f:report[k][f] for f in ('tests','failures','errors','skipped','successful')}
                       for k in ('upstream','contract','candidate_tests','new_tests_on_original')} if report else None,
        direct_code_test_and_prose_review_required=True,
        evaluation_returned_to_actor=False, no_new_model_inference=True)
    save(folder/'ASSESSMENT.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='001')
    assess(parser.parse_args().version)
