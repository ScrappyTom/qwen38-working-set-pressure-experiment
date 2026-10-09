"""Post-seal cost, information-path and ordinary artifact review; no model call."""
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
import continuation_task as study
import qualification_route
from temporal_audit import Trace, source_rows
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_file


def save(path, value):
    with path.open('xb') as stream:
        stream.write(canonical_json_bytes(value))


def main():
    run, review = AREA / 'run-001', AREA / 'review'
    seal = study.read(run / 'RESPONSE_SEAL.json')
    verified = study.read(review / 'VERIFICATION-001.json')
    assert verified['status'] == 'replayed_exactly'
    assert verified['executed_manifest_sha256'] == sha256_file(run / 'EXECUTION_MANIFEST.json')
    path = study.ROOT / 'development/workload_requalification/url_port_continuation/review/measure_run.py'
    spec = importlib.util.spec_from_file_location('evolving_cost_reader', path)
    metric = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(metric)
    metric.checked_seal(run)
    records = metric.records(run)
    calls = metric.calls(run, records)
    operations = [(row['payload']['id'], study.read(run / row['artifacts'][0]['path']))
        for row in records if row['record_type'] == 'contribution_operation']
    closed, = [row['payload'] for row in records if row['record_type'] == 'runtime_closed']
    assert closed['owned_server_shutdown_verified'] and closed['dedicated_port_free']
    common = dict(response_seal_sha256=sha256_file(run / 'RESPONSE_SEAL.json'),
        script_sha256=sha256_file(Path(__file__)))
    old_calls = metric.calls(study.OLD, metric.records(study.OLD))
    save(review / 'METRICS-001.json', dict(**common, status='recomputed_from_sealed_evidence',
        inherited=metric.aggregate(old_calls), complete_lineage=metric.aggregate(old_calls + calls),
        aggregate=metric.aggregate(calls), calls=calls,
        endpoint_timings=[dict(id=row['id'], timings=study.read(run / f"calls/{row['id']}-endpoint-response.json").get('timings')) for row in calls],
        operations=len(operations), operation_types=dict(Counter(op['action']['action'] for _, op in operations)),
        read_pages=[dict(id=tag, requested=op['action'], accepted=op['result']['accepted'],
            delivered_by_operation=[dict(path=s['path'], first=s['returned_start_line'],
                last=s['returned_end_line'], next_start_line=s['next_start_line'],
                whole_file_shown=s['whole_file_shown'], bytes=len(s['content'].encode()))
                for s in source_rows(op['result'])])
            for tag, op in operations if op['action']['action'] in ('read','work_on','work_on_exact')],
        processing=[row['payload'] for row in records if row['record_type'] == 'reply_processed'],
        rejected_operations=[dict(id=tag, operation=op) for tag, op in operations if not op['result']['accepted']],
        task_loop=[row['payload'] for row in records if row['record_type'] == 'task_loop_completed'],
        runtime_closure=closed, memory=seal['memory'], runtime=seal['runtime'],
        limits=['Generated usage includes thinking and final output, not a waste measure.',
                'Preparation, review and independent grading are additional costs.']))
    state = study.read(run / 'final-state.json')
    versions = {row['candidate_id']: study.core.candidate_from_snapshot(row) for row in state['source_versions']}
    trace = qualification_route.parent_trace(study, versions)
    decisions = []
    for row in records:
        if row['record_type'] != 'invocation_started':
            continue
        tag = row['payload']['id']
        wire = study.read(run / f'calls/{tag}-wire-request.json')
        view = load_json_strict(wire['messages'][-1]['content'])['workspace']
        assert view['task'] == study.task_text()
        own = [op for selected, op in operations if selected == tag]
        trace.observe(tag, view, own, versions)
        decisions.append(dict(id=tag, wire_sha256=sha256_file(run / f'calls/{tag}-wire-request.json'),
            account=view['working_account'], allowance=view['allowance'],
            presentation=view['presentation'], verification=view['verification'],
            actions=[dict(action=op['action'], result={k:v for k,v in op['result'].items()
                if k not in ('source', 'sources')}) for op in own]))
    temporal = trace.result()
    save(review / 'TEMPORAL-AUDIT-001.json', dict(**common, status='actual_sent_inputs_and_effects',
        case=study.CASE, **temporal, decision_context=decisions))

    candidate = study.read(run / 'final-candidate.json')
    files = {row['path']: row['content_utf8'].encode() for row in candidate['files']}
    original = study.starting_files()
    inherited = study.previous.core.candidate_from_snapshot(study.read(study.OLD / 'final-candidate.json')).file_map
    preserved_parent = [name for name in inherited if inherited[name] == files[name]]
    assert all(name in preserved_parent for name in inherited if name != study.SECONDARY)
    assert set(files) == set(original)
    changed = [name for name in original if original[name] != files[name]]
    allowed = {study.TARGET, study.POLICY, study.SECONDARY}
    diff = ''.join(''.join(difflib.unified_diff(original[name].decode().splitlines(True),
        files[name].decode().splitlines(True), fromfile='entry/' + name, tofile='saved/' + name)) for name in changed)
    with (review / 'SAVED-PATCH.diff').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(diff)
    independent = '''import json
from api.primary import normalize_primary
from api.secondary import normalize_secondary
from api.render import render_pair
from policy.current import active_prefix
values = ['', ' a ', ' B7 ', ' MiX ', ' Straße ', '\\tÅß\\n', '  İ  ', ' 0 ']
rows = [dict(value=x, primary=normalize_primary(x), secondary=normalize_secondary(x), pair=render_pair(x,x)) for x in values]
for row in rows:
    x = row['value']
    assert row['primary'] == 'ember-' + x.strip().casefold()
    assert row['secondary'] == 'quartz-' + x.strip().upper()
    assert row['pair'] == row['primary'] + '|' + row['secondary']
assert active_prefix() == 'quartz-'
print(json.dumps(rows, ensure_ascii=False))
'''
    results = []
    with tempfile.TemporaryDirectory(prefix='evolving_source_review_') as folder:
        root = Path(folder)
        for name, raw in files.items():
            dest = root / name
            assert dest.resolve().is_relative_to(root.resolve())
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        for label, program in [('original_public', study.public_checker()), ('independent_examples', independent.encode())]:
            file = '_' + label + '.py'
            (root / file).write_bytes(program)
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', file], cwd=root,
                capture_output=True, timeout=30)
            results.append(dict(label=label, returncode=result.returncode,
                stdout=result.stdout.decode(), stderr=result.stderr.decode()))
    assessment = dict(**common, status='assessed', candidate_id=candidate['candidate_id'],
        changed_files=changed, only_permitted_files_changed=set(changed).issubset(allowed),
        inherited_candidate_id=study.SAVED_ID, inherited_files_preserved=len(preserved_parent),
        continuation_changed_files=[name for name in inherited if name not in preserved_parent],
        unchanged_other_files=sum(original[name] == files[name] for name in original if name not in allowed),
        checks=results, original_public_and_hidden_identical=True,
        ordinary_behavior_passed=all(row['returncode'] == 0 for row in results),
        temporal_contract_met=temporal['temporal_contract_met'],
        environment=dict(interpreter=sys.executable, cwd='fresh candidate root', flags=['-B', '-X', 'utf8']),
        limits=['Repeated original acceptance establishes reproducibility, not independent hidden coverage.',
            'Independent concrete examples and source review are not new model trajectories.',
            'Successful execution does not establish the separate historical acquisition/order contract.'])
    save(review / 'ARTIFACT-ASSESSMENT-001.json', assessment)
    print(json.dumps(dict(metrics=metric.aggregate(calls), temporal={k:v for k,v in temporal.items()
        if k not in ('ledger_witnesses','policy_changes','policy_acquisitions','policy_deliveries','decisions')},
        artifact=assessment), indent=2))


if __name__ == '__main__':
    main()
