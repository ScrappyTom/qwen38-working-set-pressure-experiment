"""Independent original ORBIT procedure/artifact screen after exact closed replay.

This evaluator does not enter actor inputs. A conservative source-acquisition
screen may require direct review of an alternative legitimate route.
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

AREA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AREA))
import recurrent_task as study
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


def save(path, value):
    raw = value if isinstance(value, bytes) else canonical_json_bytes(value)
    if path.exists():
        assert path.read_bytes() == raw, 'Preserve differing assessments separately'
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)


def execute(candidate, label, program):
    with tempfile.TemporaryDirectory(prefix='orbit-independent-') as temp:
        root = Path(temp)
        for name, raw in candidate.files:
            path = root / name
            assert path.resolve().is_relative_to(root.resolve())
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        name = '_independent_review.py'
        (root / name).write_bytes(program)
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', name], cwd=root,
                                capture_output=True, timeout=30)
    return dict(label=label, candidate_id=candidate.candidate_id,
        program_sha256=sha256_bytes(program), returncode=result.returncode,
        stdout=result.stdout.decode(), stderr=result.stderr.decode())


def assess(version):
    task = study.Task(version)
    run, folder = task.RUN, AREA / 'review' / version
    verification = task.read(AREA / f'review/VERIFICATION-{version}.json')
    assert verification['status'] == 'replayed_exactly'
    assert verification['executed_manifest_sha256'] == sha256_file(run / 'EXECUTION_MANIFEST.json')
    task.verify_sources(task.read(run / 'EXECUTION_MANIFEST.json')['source_sha256'])
    source = study.ROOT / 'development/workload_requalification/url_port_continuation/review/measure_run.py'
    spec = importlib.util.spec_from_file_location('recurrent_cost_reader', source)
    metric = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(metric)
    seal, records = metric.checked_seal(run), metric.records(run)
    calls = metric.calls(run, records)
    operations = [(r['payload']['id'], task.read(run / r['artifacts'][0]['path'])) for r in records
                  if r['record_type'] == 'contribution_operation']
    common = dict(case=task.CASE, version=version, response_seal_sha256=sha256_file(run / 'RESPONSE_SEAL.json'),
        records_sha256=sha256_file(run / 'records.jsonl'), assessment_sha256=sha256_file(Path(__file__)),
        exact_replay_sha256=sha256_file(AREA / f'review/VERIFICATION-{version}.json'))
    save(folder / 'METRICS.json', dict(**common, aggregate=metric.aggregate(calls), calls=calls,
        actual_operations=len(operations), operation_types=dict(Counter(o['action']['action'] for _, o in operations)),
        rejected=[dict(id=tag, operation=op) for tag, op in operations if not op['result']['accepted']],
        task_loop=[r['payload'] for r in records if r['record_type'] == 'task_loop_completed'],
        runtime=seal['runtime'], memory=seal['memory'],
        limits=['Costs exclude preparation, grading and reviewer work.',
                'Checks/examples are not independent model successes.']))
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
    decisions, forks, submitted, edits, policy_inputs, orientation = [], [], [], [], [], []
    for call in calls:
        tag = call['id']
        wire = task.read(run / f'calls/{tag}-wire-request.json')
        view = json.loads(wire['messages'][-1]['content'])['workspace']
        assert view['task'] == task.task_text()
        phase = view['phase']['current']
        own = [op for selected, op in operations if selected == tag]
        checkpoint = task.restore(task.read(run / f'before/{tag}-state.json'),
            task.read(run / f'before/{tag}-candidate.json'), replay_folder=run, replay=True)
        checkpoint.mark_delivered(view)
        policy = [r for r in checkpoint.delivered_sources if r.get('path') == 'policies/current.py'
                  and r.get('file_sha256') == checkpoint.candidate.file_sha256('policies/current.py')]
        for row in policy:
            # This is actual delivery, not remembered acquisition or an account.
            raw = checkpoint.candidate.file_map[row['path']].decode()
            assert row['content'] == ''.join(raw.splitlines(keepends=True)[
                row['returned_start_line'] - 1:row['returned_end_line']])
            policy_inputs.append(dict(id=tag, phase=phase, source=row,
                complete_definition_screen=row['content'] == raw))
        for op in own:
            action, result = op['action'], op['result']
            if not result['accepted']:
                continue
            if action['action'] == 'p0_page':
                orientation.append(dict(id=tag, phase=phase, action=action, result=result))
            if action['action'] in ('patch', 'replace_region'):
                edits.append(dict(id=tag, phase=phase, path=result.get('path', action.get('path')),
                    predecessor=view['candidate_id'], successor=result['candidate_id']))
            if action['action'] in ('fork_ready', 'submit'):
                scope = 'prefork' if phase == 'A' else 'public'
                check = view['verification']['checks'][scope]
                entry = dict(id=tag, phase=phase, candidate_id=view['candidate_id'], actual_receipt=result,
                    consumed_current_active_pass=bool(check and check['passed'] and check['applies_to_current']
                        and check['assessment']['checker_sha256'] == sha256_bytes(task.checker(phase))))
                (forks if action['action'] == 'fork_ready' else submitted).append(entry)
        decisions.append(dict(id=tag, phase=view['phase'], candidate_id=view['candidate_id'],
            actual_actions=[o['action'] for o in own], verification=view['verification'], account=view['working_account'],
            source_extents=[{k: v for k, v in r.items() if k != 'content'} for r in checkpoint.delivered_sources],
            presentation=view['presentation']))
    checks = [execute(session.versions[r['candidate_id']], 'original_' + r['phase'], task.checker(r['phase']))
              for r in forks]
    checks.append(execute(candidate, 'original_D_on_final', task.checker('D')))
    examples = """import json
from api.name import normalize_name
from api.footer import normalize_footer
from api.render import render_identity
from policies.current import active_policy_prefix
from workflow.progress import completed_phases
values=['',' a ',' MiX ',' Straße ',' Åß ','\\tNAME\\n',' İ ',' Σςσ ']
assert completed_phases()==1
assert active_policy_prefix()=='zenith-'
rows=[]
for value in values:
    name,footer=normalize_name(value),normalize_footer(value)
    assert name=='orbit-'+value.strip().casefold()
    assert footer=='zenith-'+value.strip().upper()
    assert render_identity(value,value)==name+'|'+footer
    rows.append(dict(value=value,name=name,footer=footer))
print(json.dumps(rows,ensure_ascii=False))
"""
    checks.append(execute(candidate, 'independent_final_examples', examples.encode()))
    name_edits = [r for r in edits if r['path'] == 'api/name.py']
    footer_edits = [r for r in edits if r['path'] == 'api/footer.py']
    b_policy = [r for r in policy_inputs if r['phase'] == 'B' and r['complete_definition_screen']]
    d_policy = [r for r in policy_inputs if r['phase'] == 'D' and r['complete_definition_screen']]
    b_acquired = bool(name_edits and any(r['id'] <= name_edits[0]['id'] for r in b_policy))
    d_acquired = bool(footer_edits and any(r['id'] <= footer_edits[0]['id'] for r in d_policy))
    p0_route = bool(b_policy and any(r['phase'] == 'B' and r['id'] < b_policy[0]['id']
        and 'policies/current.py' in canonical_json_bytes(r['result']).decode() for r in orientation))
    b_boundary = next((r for r in forks if r['phase'] == 'B'), None)
    preserved = bool(b_boundary)
    if b_boundary:
        saved_name = session.versions[b_boundary['candidate_id']].file_map['api/name.py']
        preserved = all(session.versions[r['successor']].file_map['api/name.py'] == saved_name
                        for r in edits if r['id'] > b_boundary['id']) and after['api/name.py'] == saved_name
    coverage = {phase: session.coverage_status(phase) for phase in study.ORDER}
    complete = bool(session.submitted and [r['phase'] for r in forks] == ['A','B','C']
        and len(submitted) == 1 and submitted[0]['phase'] == 'D'
        and all(r['consumed_current_active_pass'] for r in forks + submitted)
        and all(r['complete'] for rows in coverage.values() for r in rows)
        and b_acquired and d_acquired and p0_route and preserved
        and all(r['returncode'] == 0 for r in checks)
        and set(changed) <= {'workflow/progress.py','api/name.py','policies/current.py','api/footer.py'})
    save(folder / 'ASSESSMENT.json', dict(**common, candidate_id=candidate.candidate_id,
        changed_files=changed, unchanged_files=len(before)-len(changed), checks=checks,
        forks=forks, submissions=submitted, edits=edits, coverage=coverage, decisions=decisions,
        policy_inputs=policy_inputs, orientation=orientation, original_contract_screen_passed=complete,
        phase_b_policy_before_name=b_acquired, phase_d_current_policy_before_footer=d_acquired,
        p0_discovery_before_phase_b_policy=p0_route, completed_b_name_preserved=preserved,
        environment=dict(interpreter=sys.executable, flags=['-B','-X','utf8'], cwd='fresh phase-candidate root'),
        limits=['Conservative full-policy/P0 screen requires direct review of legitimate alternative evidence routes.',
            'Exact input delivery is not proof of semantic understanding.',
            'Boundary releases are original declared task transitions, not natural pressure events.',
            'Earlier checkers run on actual completed phase candidates, not on the final authorized changed policy.',
            'Account usefulness and action judgment require direct full-response review.',
            'Four original programs and additional examples are scoped checks, not independent model trials.']))
    print(json.dumps(dict(case=task.CASE, original_contract_screen_passed=complete, changed_files=changed,
        coverage=coverage, checks=checks, metrics=metric.aggregate(calls)), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    assess(parser.parse_args().version)
