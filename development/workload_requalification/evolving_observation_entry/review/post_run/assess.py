"""Post-seal cost, exact information-path and ordinary artifact assessment."""
from collections import Counter
import argparse
import difflib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

AREA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AREA))
import observation_task as study
from temporal_audit import Trace
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_file


def save(path, value):
    raw = canonical_json_bytes(value)
    if path.exists():
        assert path.read_bytes() == raw, 'Preserve an earlier different assessment: ' + str(path)
    else:
        with path.open('xb') as stream:
            stream.write(raw)


def main(version='001'):
    run, review = AREA / f'run-{version}', AREA / 'review'
    seal = study.read(run / 'RESPONSE_SEAL.json')
    verified = study.read(review / f'VERIFICATION-{version}.json')
    assert verified['status'] == 'replayed_exactly'
    assert verified['response_seal_sha256'] == sha256_file(run / 'RESPONSE_SEAL.json')
    assert verified['records_sha256'] == sha256_file(run / 'records.jsonl')
    path = study.ROOT / 'development/workload_requalification/url_port_continuation/review/measure_run.py'
    spec = importlib.util.spec_from_file_location('e18_observation_cost_reader', path)
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
        assessment_source_sha256=sha256_file(Path(__file__)))
    save(review / f'METRICS-{version}.json', dict(**common, status='recomputed_from_sealed_evidence',
        aggregate=metric.aggregate(calls), calls=calls,
        endpoint_timings=[dict(id=row['id'], timings=study.read(run / f"calls/{row['id']}-endpoint-response.json").get('timings'))
            for row in calls if (run / f"calls/{row['id']}-endpoint-response.json").exists()],
        operations=len(operations), operation_types=dict(Counter(op['action']['action'] for _, op in operations)),
        rejected_operations=[dict(id=tag, operation=op) for tag, op in operations if not op['result']['accepted']],
        task_loop=[row['payload'] for row in records if row['record_type'] == 'task_loop_completed'],
        runtime_closure=closed, memory=seal['memory'], runtime=seal['runtime'],
        limits=['Generated usage includes thinking and final output, not a waste measure.',
                'Preparation, review and independent grading are additional costs.']))

    stem = 'final' if (run / 'final-state.json').exists() else 'stopped'
    state = study.read(run / (stem + '-state.json'))
    versions = {row['candidate_id']: study.candidate_from_snapshot(row) for row in state['source_versions']}
    trace, decisions = Trace(study), []
    for row in records:
        if row['record_type'] != 'invocation_started':
            continue
        tag = row['payload']['id']
        wire = study.read(run / f'calls/{tag}-wire-request.json')
        envelope = load_json_strict(wire['messages'][-1]['content'])
        view = envelope['workspace']
        assert view['task'] == study.task_text()
        own = [op for selected, op in operations if selected == tag]
        trace.observe(tag, view, own, versions, state['pairs'], envelope['preceding_operation_feedback'])
        decisions.append(dict(id=tag, wire_sha256=sha256_file(run / f'calls/{tag}-wire-request.json'),
            account=view['working_account'], allowance=view['allowance'],
            presentation=view['presentation'], verification=view['verification'],
            actions=[dict(action=op['action'], result={k:v for k,v in op['result'].items()
                if k not in ('source', 'sources')}) for op in own]))
    temporal = trace.result()
    save(review / f'TEMPORAL-AUDIT-{version}.json', dict(**common, status='actual_sent_inputs_and_effects',
        case=study.CASE, **temporal, decision_context=decisions))

    candidate = study.read(run / (stem + '-candidate.json'))
    files = {row['path']: row['content_utf8'].encode() for row in candidate['files']}
    original = study.starting_files()
    assert set(files) == set(original)
    changed = [name for name in original if original[name] != files[name]]
    allowed = {study.TARGET, study.SECONDARY}
    diff = ''.join(''.join(difflib.unified_diff(original[name].decode().splitlines(True),
        files[name].decode().splitlines(True), fromfile='entry/' + name, tofile='saved/' + name)) for name in changed)
    diff_path = review / ('SAVED-PATCH.diff' if version=='001' else f'SAVED-PATCH-{version}.diff')
    if diff_path.exists():
        assert diff_path.read_bytes() == diff.encode()
    else:
        diff_path.write_bytes(diff.encode())
    independent = '''import json
from codec.label import codec_label
from codec.footer import codec_footer
from codec.wire import encode_wire
values = ['', ' a ', ' B7 ', ' MiX ', ' Straße ', '\\tÅß\\n', '  İ  ', ' 0 ']
rows = [dict(value=x, label=codec_label(x), footer=codec_footer(x), wire=encode_wire(x)) for x in values]
for row in rows:
    x = row['value']
    assert row['label'] == 'HARBOR-K9::' + x.strip().upper()
    assert row['footer'] == 'HARBOR-K9::' + x.strip().casefold()
    assert row['wire'] == row['label'] + '|' + row['footer']
print(json.dumps(rows, ensure_ascii=False))
'''
    assert study.public_checker() == study.hidden_checker()
    results = []
    with tempfile.TemporaryDirectory(prefix='e18_observation_review_') as folder:
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
        changed_files=changed, only_target_files_changed=set(changed).issubset(allowed),
        unchanged_other_files=sum(original[name] == files[name] for name in original if name not in allowed),
        checks=results, original_public_and_hidden_identical=True,
        ordinary_behavior_passed=all(row['returncode'] == 0 for row in results),
        temporal_contract_met=temporal['temporal_contract_met'],
        environment=dict(interpreter=sys.executable, cwd='fresh candidate root', flags=['-B', '-X', 'utf8']),
        limits=['Repeated original acceptance establishes reproducibility, not independent hidden coverage.',
            'Independent concrete examples and source review are not new model trajectories.',
            'Successful execution does not establish the separate acquisition/order contract.'])
    save(review / f'ARTIFACT-ASSESSMENT-{version}.json', assessment)
    print(json.dumps(dict(metrics=metric.aggregate(calls),
        temporal={k:v for k,v in temporal.items() if k not in ('decisions','marker_deliveries')},
        artifact=assessment), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    main(args.version)
