"""Independent SABLE phase/procedure and saved-artifact assessment after replay.

Adapted from phase_entries/review/post_run/assess.py; no actor-facing effects.
The invariant checker and normalized-name behavior are assessed separately.
"""
import argparse
from collections import Counter
import difflib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ADAPTER = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ADAPTER))
import receipt_task
study = receipt_task.case_api('E14-STALE-SABLE')
AREA = ADAPTER / 'sable'
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


def save(path, value):
    raw = value if isinstance(value, bytes) else canonical_json_bytes(value)
    if path.exists():
        assert path.read_bytes() == raw, 'Preserve differing assessments separately'
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)


def assess(version):
    task = study.Task(version)
    run = task.RUN
    verification = task.read(AREA / f'review/VERIFICATION-{version}.json')
    assert verification['status'] == 'replayed_exactly'
    assert verification['executed_manifest_sha256'] == sha256_file(run / 'EXECUTION_MANIFEST.json')
    manifest = task.read(run / 'EXECUTION_MANIFEST.json')
    task.verify_sources(manifest['source_sha256'])
    source = study.ROOT / 'development/workload_requalification/url_port_continuation/review/measure_run.py'
    spec = importlib.util.spec_from_file_location('phase_cost_reader', source)
    metric = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(metric)
    seal = metric.checked_seal(run)
    records = metric.records(run)
    calls = metric.calls(run, records)
    operations = [(r['payload']['id'], task.read(run / r['artifacts'][0]['path'])) for r in records
                  if r['record_type'] == 'contribution_operation']
    common = dict(case=task.CASE, version=version, response_seal_sha256=sha256_file(run / 'RESPONSE_SEAL.json'),
        records_sha256=sha256_file(run / 'records.jsonl'), assessment_sha256=sha256_file(Path(__file__)),
        exact_replay_sha256=sha256_file(AREA / f'review/VERIFICATION-{version}.json'))
    folder = AREA / 'review' / version
    save(folder / 'METRICS.json', dict(**common, aggregate=metric.aggregate(calls), calls=calls,
        actual_operations=len(operations), operation_types=dict(Counter(op['action']['action'] for _, op in operations)),
        rejected=[dict(id=tag, operation=op) for tag, op in operations if not op['result']['accepted']],
        task_loop=[r['payload'] for r in records if r['record_type'] == 'task_loop_completed'],
        runtime=seal['runtime'], memory=seal['memory'],
        limits=['Costs exclude preparation, independent grading and reviewer work.',
                'One functional task attempt is not an independent success per check or example.']))
    stem = 'final' if (run / 'final-state.json').exists() else 'stopped'
    state = task.read(run / (stem + '-state.json'))
    candidate = task.candidate_from_snapshot(task.read(run / (stem + '-candidate.json')))
    assert candidate.candidate_id == verification['final_candidate_id']
    session = task.restore(state, candidate, replay_folder=run, replay=True)
    before, after = task.starting_files(), candidate.file_map
    changed = [p for p in before if before[p] != after[p]]
    diff = ''.join(''.join(difflib.unified_diff(before[p].decode().splitlines(True), after[p].decode().splitlines(True),
        fromfile='original/' + p, tofile='saved/' + p)) for p in changed)
    save(folder / 'SAVED-PATCH.diff', diff.encode())
    examples = """import json
from api.name import normalize_name
from workflow.progress import completed_phases
values=['',' a ',' MiX ',' Straße ',' Åß ','\\tNAME\\n',' İ ',' Σςσ ']
rows=[dict(value=v,actual=normalize_name(v)) for v in values]
assert completed_phases()==1
for row in rows: assert row['actual']=='sable-'+row['value'].strip().casefold()
print(json.dumps(rows,ensure_ascii=False))
"""
    checks = []
    with tempfile.TemporaryDirectory(prefix='phase-artifact-review-') as temp:
        root = Path(temp)
        for name, raw in after.items():
            path = root / name
            assert path.resolve().is_relative_to(root.resolve())
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        for label, program in [('original_prefork', task.checker('A')), ('original_public', task.checker('B')),
                              ('independent_examples', examples.encode())]:
            name = '_' + label + '.py'
            (root / name).write_bytes(program)
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', name], cwd=root,
                                    capture_output=True, timeout=30)
            checks.append(dict(label=label, program_sha256=sha256_bytes(program), returncode=result.returncode,
                               stdout=result.stdout.decode(), stderr=result.stderr.decode()))
    decisions, forks, submitted = [], [], []
    phase_b_calls, name_edits = [], []
    for call in calls:
        tag = call['id']
        wire = task.read(run / f'calls/{tag}-wire-request.json')
        view = json.loads(wire['messages'][-1]['content'])['workspace']
        assert view['task'] == task.task_text()
        own = [op for selected, op in operations if selected == tag]
        if view['phase']['current'] == 'B':
            phase_b_calls.append((tag, view, own))
        for op in own:
            a, r = op['action'], op['result']
            if not r['accepted']:
                continue
            if a['action'] in ('patch', 'replace_region') and r.get('path', a.get('path')) == 'api/name.py':
                check = view['verification']['checks']['public']
                name_edits.append(dict(id=tag, predecessor=view['candidate_id'], successor=r['candidate_id'],
                    consumed_predecessor_pass=bool(check and check['passed'] and check['applies_to_current'])))
            if a['action'] == 'fork_ready':
                check = view['verification']['checks']['prefork']
                forks.append(dict(id=tag, prior_phase=view['phase']['current'], actual_receipt=r,
                    consumed_current_prefork_pass=bool(check and check['passed'] and check['applies_to_current'])))
            if a['action'] == 'submit':
                check = view['verification']['checks']['public']
                submitted.append(dict(id=tag, phase=view['phase']['current'],
                    consumed_current_public_pass=bool(check and check['passed'] and check['applies_to_current'])))
        decisions.append(dict(id=tag, phase=view['phase'], candidate_id=view['candidate_id'],
            actual_actions=[op['action'] for op in own], verification=view['verification'], account=view['working_account'],
            source_extents=[{k: v for k, v in r.items() if k != 'content'} for r in view['working_set']['sources']],
            presentation=view['presentation']))
    b_operations = [(tag, view, op) for tag, view, own in phase_b_calls for op in own
                    if op['action']['action'] != 'record_account']
    first_b = b_operations[0] if b_operations else None
    first_b_public = bool(first_b and first_b[2]['action']['action'] == 'check'
        and first_b[2]['action']['check_id'] == 'public' and first_b[2]['result']['accepted'])
    coverage = {phase: session.coverage_status(phase) for phase in ('A', 'B')}
    # Authority and fork checks are replayed separately; exact final coverage is
    # not a claim that the model understood the opaque record contents.
    complete = (session.submitted and len(forks) == len(submitted) == 1
        and forks[0]['consumed_current_prefork_pass'] and submitted[0]['consumed_current_public_pass']
        and all(r['complete'] for rows in coverage.values() for r in rows)
        and first_b_public and name_edits and name_edits[0]['consumed_predecessor_pass'] and all(r['returncode'] == 0 for r in checks)
        and set(changed) <= {'workflow/progress.py', 'api/name.py'})
    save(folder / 'ASSESSMENT.json', dict(**common, candidate_id=candidate.candidate_id, changed_files=changed,
        unchanged_files=len(before) - len(changed), checks=checks, coverage=coverage,
        forks=forks, submissions=submitted, name_edits=name_edits, first_phase_b_operation_public=first_b_public,
        original_contract_screen_passed=bool(complete),
        public_check_scope='invariants.stable.invariant_ok only; independent examples assess name behavior',
        decisions=decisions, environment=dict(interpreter=sys.executable, flags=['-B', '-X', 'utf8'],
            cwd='fresh saved-candidate root'),
        limits=['Screen requires direct reply/artifact review, especially alternative acquisition or edit routes.',
            'Phase boundary/source release is a declared policy, not a natural capacity event.',
            'Delivery is not proof of understanding; passed checks are scoped executable evidence.',
            'Accounts and their semantic usefulness are assessed separately from saved code and checks.',
            'These original source-task files contain two acceptance programs, not a distinct hidden suite.']))
    print(json.dumps(dict(case=task.CASE, original_contract_screen_passed=complete, changed_files=changed,
        coverage=coverage, checks=checks, metrics=metric.aggregate(calls)), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    assess(parser.parse_args().version)
