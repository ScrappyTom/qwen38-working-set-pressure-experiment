"""Original probe procedure and saved artifact, after independent exact replay."""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

AREA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AREA))
import probe_task as study
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


def save(path, value):
    raw = canonical_json_bytes(value)
    if path.exists():
        assert path.read_bytes() == raw, 'Preserve differing assessments separately'
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)


def exact_pages(view, session):
    pages = list(view['working_set']['saved_results'])
    latest = (view.get('latest_feedback') or {}).get('result', {})
    pages.extend(latest.get('saved_results', []))
    if latest.get('kind') == 'saved_bytes':
        pages.append(latest)
    found = {}
    # Permit exact complete wrappers produced by ordinary recovery as well as
    # direct original RES pages. Do not mine account prose or arbitrary strings.
    for _ in range(3):
        following = []
        for page in pages:
            if page.get('kind') != 'saved_bytes' or page.get('offset') != 0 or page.get('next_offset') is not None:
                continue
            handle = page.get('handle', '')
            try:
                raw = session.payload(handle)
            except (ValueError, KeyError):
                continue
            if (page.get('exact_utf8', '').encode() != raw or len(raw) != page.get('total_bytes')
                    or sha256_bytes(raw) != page.get('sha256')):
                continue
            found[handle] = raw
            value = load_json_strict(raw)
            if isinstance(value, dict):
                following.extend(value.get('saved_results', []))
                if value.get('kind') == 'saved_bytes':
                    following.append(value)
        pages = following
    return found


def assess(version):
    task = study.Task(version)
    run = task.RUN
    proof = task.read(AREA / f'review/VERIFICATION-{version}.json')
    assert proof['status'] == 'replayed_exactly'
    assert proof['executed_manifest_sha256'] == sha256_file(run / 'EXECUTION_MANIFEST.json')
    task.verify_sources(task.read(run / 'EXECUTION_MANIFEST.json')['source_sha256'])
    path = study.ROOT / 'development/workload_requalification/url_port_continuation/review/measure_run.py'
    spec = importlib.util.spec_from_file_location('probe_cost_reader', path)
    metric = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(metric)
    seal, records = metric.checked_seal(run), metric.records(run)
    calls = metric.calls(run, records)
    operations = [(r['payload']['id'], task.read(run / r['artifacts'][0]['path'])) for r in records
                  if r['record_type'] == 'contribution_operation']
    common = dict(case=task.CASE, version=version, response_seal_sha256=sha256_file(run / 'RESPONSE_SEAL.json'),
        records_sha256=sha256_file(run / 'records.jsonl'), assessment_sha256=sha256_file(Path(__file__)),
        exact_replay_sha256=sha256_file(AREA / f'review/VERIFICATION-{version}.json'))
    folder = AREA / 'review' / version
    timing = [dict(id=c['id'], timings=task.read(run / f"calls/{c['id']}-endpoint-response.json").get('timings')) for c in calls]
    save(folder / 'METRICS.json', dict(**common, aggregate=metric.aggregate(calls), calls=calls,
        actual_operations=len(operations), operation_types=dict(Counter(op['action']['action'] for _, op in operations)),
        rejected=[dict(id=tag, operation=op) for tag, op in operations if not op['result']['accepted']],
        task_loop=[r['payload'] for r in records if r['record_type'] == 'task_loop_completed'],
        endpoint_timings=timing, runtime=seal['runtime'], memory=seal['memory'],
        limits=['Costs exclude preparation, independent execution and reviewer effort.']))
    stem = 'final' if (run / 'final-state.json').exists() else 'stopped'
    state = task.read(run / (stem + '-state.json'))
    candidate = task.candidate_from_snapshot(task.read(run / (stem + '-candidate.json')))
    assert candidate.candidate_id == proof['final_candidate_id']
    session = task.restore(state, candidate, run, replay=True)
    before, after = task.starting_files(), candidate.file_map
    changed = [p for p in before if before[p] != after[p]]
    marker, = [line.split('=', 1)[1] for line in session.probe_body.splitlines() if line.startswith('marker=')]
    examples = ("import json\nfrom codec.label import codec_label\nfrom codec.wire import encode_wire\n"
        "from workflow.progress import completed_phases\nassert completed_phases()==1\n"
        "values=['',' a ',' MiX ',' Straße ',' Åß ','\\tNAME\\n',' İ ',' Σςσ ']\n"
        "rows=[dict(value=v,actual=codec_label(v)) for v in values]\n"
        f"for row in rows: assert row['actual']=={marker!r}+row['value'].strip().upper()\n"
        f"assert encode_wire(' Ab ')=={(marker+'AB').encode()!r}\nprint(json.dumps(rows,ensure_ascii=False))\n").encode()
    checks = []
    with tempfile.TemporaryDirectory(prefix='probe-artifact-review-') as temp:
        root = Path(temp)
        for name, raw in after.items():
            path = root / name
            assert path.resolve().is_relative_to(root.resolve())
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        for label, program in [('original_prefork', task.checker('A')), ('original_public', task.checker('B')),
                              ('independent_examples', examples)]:
            name = '_' + label + '.py'
            (root / name).write_bytes(program)
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', name], cwd=root, capture_output=True, timeout=30)
            checks.append(dict(label=label, program_sha256=sha256_bytes(program), returncode=result.returncode,
                stdout=result.stdout.decode(), stderr=result.stderr.decode()))
    decisions, forks, submissions, recoveries, label_edits = [], [], [], [], []
    for call in calls:
        tag = call['id']
        envelope = json.loads(task.read(run / f'calls/{tag}-wire-request.json')['messages'][-1]['content'])
        view = envelope['workspace']
        assert view['task'] == task.task_text()
        shown = exact_pages(view, session)
        matching = [r for r in session.observation_rows() if r['action'] == 'probe' and r['target'] == 'integrity'
            and r['result_handle'] in shown and r['observed_candidate_id'] == view['candidate_id']]
        if view['phase']['current'] == 'B' and matching:
            recoveries.append(dict(id=tag, candidate_id=view['candidate_id'], exact_current_probes=matching))
        own = [op for selected, op in operations if selected == tag]
        for op in own:
            action, result = op['action'], op['result']
            if not result['accepted']:
                continue
            if action['action'] == 'fork_ready':
                check = view['verification']['checks']['prefork']
                candidates = [r for r in session.observation_rows() if r['action'] == 'probe'
                    and r['observed_candidate_id'] == view['candidate_id']
                    and r['operation_sequence'] <= view['archive']['action_count']]
                forks.append(dict(id=tag, consumed_current_prefork_pass=bool(check and check['passed'] and check['applies_to_current']),
                    current_probe_preceded_boundary=bool(candidates), receipt=result))
            if action['action'] in ('patch', 'replace_region') and (action.get('path') == 'codec/label.py' or result.get('path') == 'codec/label.py'):
                label_edits.append(dict(id=tag, candidate_before=view['candidate_id'],
                    exact_current_probe_delivered_in_B=any(r['candidate_id'] == view['candidate_id'] for r in recoveries)))
            if action['action'] == 'submit':
                check = view['verification']['checks']['public']
                submissions.append(dict(id=tag, consumed_current_public_pass=bool(check and check['passed'] and check['applies_to_current'])))
        decisions.append(dict(id=tag, phase=view['phase'], candidate_id=view['candidate_id'],
            operations=own, exact_saved_handles=list(shown), current_probe_evidence=matching,
            account=view['working_account'], verification=view['verification'], presentation=view['presentation'],
            source_extents=[{k: v for k, v in row.items() if k != 'content'} for row in view['working_set']['sources']]))
    coverage = {p: session.coverage_status(p) for p in ('A', 'B')}
    complete = bool(session.submitted and len(forks) == len(submissions) == 1 and label_edits
        and forks[0]['consumed_current_prefork_pass'] and forks[0]['current_probe_preceded_boundary']
        and submissions[0]['consumed_current_public_pass'] and all(r['exact_current_probe_delivered_in_B'] for r in label_edits)
        and all(r['complete'] for rows in coverage.values() for r in rows)
        and all(r['returncode'] == 0 for r in checks) and set(changed) <= {'workflow/progress.py', 'codec/label.py'})
    save(folder / 'ASSESSMENT.json', dict(**common, candidate_id=candidate.candidate_id,
        changed_files=changed, unchanged_files=len(before)-len(changed), checks=checks,
        changed_source={p:dict(original=before[p].decode(), saved=after[p].decode()) for p in changed},
        original_contract_screen_passed=complete, coverage=coverage, observations=session.observation_rows(),
        forks=forks, submissions=submissions, recovered_current_probe_inputs=recoveries,
        label_edits=label_edits, decisions=decisions,
        environment=dict(interpreter=sys.executable, flags=['-B','-X','utf8'], cwd='fresh saved-candidate root'),
        limits=['Screen requires direct review of full replies, task order, exact evidence and saved code.',
            'Current-probe fork protection is an explicit strengthened guard, not independent model judgment.',
            'The probe is authored fixture output, not an external measurement.',
            'Alternate exact recovery routes need direct review; accounts or inventory alone do not establish recovery.',
            'Phase release is declared; record delivery is not proof of semantic comprehension.']))
    print(json.dumps(dict(case=task.CASE, complete=complete, changed=changed, checks=checks,
        recoveries=[r['id'] for r in recoveries], metrics=metric.aggregate(calls)), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    assess(parser.parse_args().version)
