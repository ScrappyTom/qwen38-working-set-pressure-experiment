"""Post-seal metrics, actual information path and independent artifact execution."""
import ast
from collections import Counter
import difflib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

AREA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AREA))
import historical_task as study
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


def save(path, value):
    raw = canonical_json_bytes(value)
    with path.open('xb') as stream:
        stream.write(raw)


def assess():
    run, review = AREA / 'run-001', AREA / 'review'
    seal = study.read(run / 'RESPONSE_SEAL.json')
    verified = study.read(review / 'VERIFICATION-001.json')
    assert verified['status'] == 'replayed_exactly'
    assert verified['executed_manifest_sha256'] == sha256_file(run / 'EXECUTION_MANIFEST.json')
    assert verified['final_candidate_id'] == study.read(run / 'final-candidate.json')['candidate_id']
    path = study.ROOT / 'development/workload_requalification/url_port_continuation/review/measure_run.py'
    spec = importlib.util.spec_from_file_location('historical_cost_reader', path)
    metric = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(metric)
    metric.checked_seal(run)
    records = metric.records(run)
    calls = metric.calls(run, records)
    operations = [(row['payload']['id'], study.read(run / row['artifacts'][0]['path']))
        for row in records if row['record_type'] == 'contribution_operation']
    loops = [row['payload'] for row in records if row['record_type'] == 'task_loop_completed']
    closed, = [row['payload'] for row in records if row['record_type'] == 'runtime_closed']
    assert closed['owned_server_shutdown_verified'] and closed['dedicated_port_free']
    save(review / 'METRICS-001.json', dict(status='recomputed_from_sealed_evidence',
        response_seal_sha256=sha256_file(run / 'RESPONSE_SEAL.json'),
        verification_sha256=sha256_file(review / 'VERIFICATION-001.json'),
        aggregate=metric.aggregate(calls), calls=calls,
        endpoint_timings=[dict(id=row['id'], timings=study.read(run / f"calls/{row['id']}-endpoint-response.json").get('timings')) for row in calls],
        operations=len(operations), operation_types=dict(Counter(op['action']['action'] for _, op in operations)),
        rejected_operations=[dict(id=tag, operation=op) for tag, op in operations if not op['result']['accepted']],
        inherited_operations=1, task_loop=loops, runtime_closure=closed,
        memory=seal['memory'], runtime=seal['runtime'], script_sha256=sha256_file(Path(__file__)),
        limits=['Generated usage includes private thinking and final output, not a waste measure.',
            'Preparation, direct review and independent grading are additional costs.',
            'Final submission receipt has no subsequent model request.']))

    pair = study.inherited_pair()
    marker = pair['response']['old'].removeprefix('legacy_marker=').removesuffix('\n')
    trace = []
    for call in calls:
        tag = call['id']
        wire = study.read(run / f'calls/{tag}-wire-request.json')
        user = load_json_strict(wire['messages'][-1]['content'])
        view = user['workspace']
        pages = list(view['working_set']['saved_results'])
        if view['latest_feedback'] and view['latest_feedback']['result'].get('kind') == 'saved_bytes':
            pages.append(view['latest_feedback']['result'])
        recovered = [page for page in pages if page.get('handle') == 'EVT-0001'
            and page.get('offset') == 0 and page.get('next_offset') is None
            and page.get('exact_utf8', '').encode() == canonical_json_bytes(pair['response'])]
        own = [op for selected, op in operations if selected == tag]
        trace.append(dict(id=tag, input_wire_sha256=sha256_file(run / f'calls/{tag}-wire-request.json'),
            task_is_original=view['task'] == study.task_text(), candidate_id=view['candidate_id'],
            historical_action_complete_in_input=bool(recovered), marker_occurs_in_input=marker in wire['messages'][-1]['content'],
            current_source=[dict(path=row['path'], candidate_id=row['candidate_id'], content=row['content'],
                extent=[row['returned_start_line'], row['returned_end_line']]) for row in view['working_set']['sources']],
            account=view['working_account'], current_verification=view['verification'],
            actions_and_effects=own, allowance=view['allowance'], mode=view['presentation']['mode']))
    assert trace and not trace[0]['marker_occurs_in_input']
    assert all(row['task_is_original'] for row in trace)
    initial_retrievals = [tag for tag, op in operations if op['action']['action'] == 'reopen_event'
        and op['action']['handle'] == 'EVT-0001' and op['result']['accepted']]
    mutation_inputs = [row for row in trace if any(op['action']['action'] in ('patch', 'replace_region')
        and op['result']['accepted'] for op in row['actions_and_effects'])]
    submissions = [row for row in trace if any(op['action']['action'] == 'submit'
        and op['result']['accepted'] for op in row['actions_and_effects'])]
    save(review / 'DECISION-TRACE-001.json', dict(status='actual_sent_input_and_effects',
        exact_historical_retrieval_calls=initial_retrievals,
        all_edit_inputs_have_historical_action=bool(mutation_inputs) and all(row['historical_action_complete_in_input'] for row in mutation_inputs),
        all_edit_inputs_have_current_target=bool(mutation_inputs) and all(any(source['path'] == 'report.py'
            and source['candidate_id'] == row['candidate_id'] for source in row['current_source']) for row in mutation_inputs),
        submission_consumed_current_pass=bool(submissions) and all(row['current_verification']['submission']['eligible'] for row in submissions),
        trace=trace, limits=['Availability and observed operations are mechanical facts; interpretation requires direct transcript review.']))

    final_path = run / 'final-candidate.json'
    candidate = study.read(final_path)
    files = {row['path']: row['content_utf8'].encode() for row in candidate['files']}
    original = study.starting_files()
    changed = [name for name in original if original[name] != files[name]]
    assert changed == ['report.py'] and files['archive/source.dat'] == original['archive/source.dat']
    tree = ast.parse(files['report.py'].decode())
    function, = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    assert function.name == 'restored_marker' and not function.args.args
    diff = ''.join(difflib.unified_diff(original['report.py'].decode().splitlines(True),
        files['report.py'].decode().splitlines(True), fromfile='entry/report.py', tofile='saved/report.py'))
    with (review / 'SAVED-PATCH.diff').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(diff)
    with tempfile.TemporaryDirectory(prefix='historical_marker_review_') as folder:
        root = Path(folder)
        for name, raw in files.items():
            dest = root / name
            assert dest.resolve().is_relative_to(root.resolve())
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        checker = study.public_checker()
        (root / '_original_check.py').write_bytes(checker)
        started = time.monotonic()
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '_original_check.py'], cwd=root,
            capture_output=True, timeout=30)
        check_seconds = time.monotonic() - started
        actual = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c',
            'import json; from report import restored_marker; print(json.dumps(restored_marker()))'],
            cwd=root, capture_output=True, timeout=30)
        observed = json.loads(actual.stdout) if actual.returncode == 0 else None
    save(review / 'ARTIFACT-ASSESSMENT-001.json', dict(status='assessed', candidate_id=candidate['candidate_id'],
        response_seal_sha256=sha256_file(run / 'RESPONSE_SEAL.json'), final_candidate_sha256=sha256_file(final_path),
        changed_files=changed, retired_source_unchanged=True, historical_marker=marker, observed_value=observed,
        exact_value_matches_history=observed == marker, original_checker_sha256=sha256_bytes(checker),
        checker_returncode=result.returncode, checker_stdout=result.stdout.decode(), checker_stderr=result.stderr.decode(),
        checker_seconds=check_seconds, behavior_returncode=actual.returncode, behavior_stderr=actual.stderr.decode(),
        environment=dict(interpreter=sys.executable, cwd='fresh candidate root', flags=['-B', '-X', 'utf8']),
        original_public_and_hidden_are_identical=True, script_sha256=sha256_file(Path(__file__)),
        limits=['Repeated original program is reproducibility, not independent hidden coverage.',
            'Independent ordinary execution and source preservation review are not new model trajectories.']))
    print(json.dumps(dict(metrics=metric.aggregate(calls), changed_files=changed,
        historical_retrieval=initial_retrievals, ordinary_result=observed, original_check_passed=result.returncode == 0), indent=2))


if __name__ == '__main__':
    assess()
