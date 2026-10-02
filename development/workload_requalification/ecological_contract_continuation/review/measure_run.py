"""Saved-only accounting for the explicitly reopened E20 contract job."""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OLD = HERE.parents[1] / 'ecological_import_entry/run-001'
ACCOUNTING_WRAPPER = ROOT / 'development/workload_requalification/ecological_import_entry/review/measure_run.py'
ACCOUNTING_CORE = ROOT / 'development/workload_requalification/url_port_continuation/review/measure_run.py'
OLD_SEAL_SHA = '6550a09cdadf7369e6151bcf39ec8baef11c855df08b10bfb5fa022ceaf1182b'
OLD_VERIFICATION_SHA = '8f060fc5d62dbb2fc75dd7a99935eb8e88c64783741133e5a3f8317398d712a0'

spec = importlib.util.spec_from_file_location('ecological_contract_saved_accounting', ACCOUNTING_WRAPPER)
saved = importlib.util.module_from_spec(spec)
spec.loader.exec_module(saved)
core = saved.core


def measure(version='001'):
    assert re.fullmatch(r'[0-9]{3}', version)
    run = HERE.parent / f'run-{version}'
    assert (run / 'RESPONSE_SEAL.json').is_file(), 'Do not account for an open run as closed'
    verification_path = HERE / f'VERIFICATION-{version}.json'
    verification = core.read(verification_path)
    assert verification['status'] == 'replayed_exactly' and not verification['fresh_original_entry']
    assert verification['response_seal_sha256'] == core.digest(run / 'RESPONSE_SEAL.json')
    assert verification['records_sha256'] == core.digest(run / 'records.jsonl')
    assert verification['original_run_seal_sha256'] == core.digest(OLD / 'RESPONSE_SEAL.json') == OLD_SEAL_SHA
    assert core.digest(OLD.parent / 'review/VERIFICATION-001.json') == OLD_VERIFICATION_SHA
    old_seal, seal = core.checked_seal(OLD), core.checked_seal(run)
    old_records, records = core.records(OLD), core.records(run)
    inherited = saved.saved_calls(OLD, old_records)
    new = saved.saved_calls(run, records)
    assert len(inherited) == old_seal['sent_requests'] == 19
    assert old_seal['actual_operations'] == 28 and old_seal['disposition'] == 'checked_submission'
    assert len(new) == seal['sent_requests'] == verification['new_requests']
    assert verification['inherited_requests'] == seal['inherited_requests'] == 19
    assert verification['inherited_operations'] == seal['inherited_operations'] == 28
    assert verification['cumulative_requests'] == seal['cumulative_requests_used'] == 19 + len(new) <= 32
    assert seal['actual_operations'] == verification['cumulative_operations'] <= 72
    assert [row['id'] for row in new] == [f'C{i:02d}' for i in range(20, 20 + len(new))]
    assert all(row['requests_used_before_response'] == i for i, row in enumerate(new, 19))
    assert sum(row['complete_response_processed'] for row in new) == seal['processed_invocations']
    operations = [row for row in records if row['record_type'] == 'contribution_operation']
    assert len(operations) == seal['new_operations'] == verification['new_operations']
    assert seal['actual_operations'] == 28 + len(operations)
    types = Counter(core.read(run / row['artifacts'][0]['path'])['action']['action'] for row in operations)
    native = [row['payload'] for row in records if row['record_type'] == 'native_input_prepared']
    loops = [row['payload'] for row in records if row['record_type'] == 'task_loop_completed']
    closures = [row['payload'] for row in records if row['record_type'] == 'runtime_closed']
    assert len(loops) <= 1 and len(closures) == 1
    assert closures[0]['owned_server_shutdown_verified'] and closures[0]['dedicated_port_free']
    return dict(status='recomputed_from_sealed_saved_wires_and_endpoints',
        response_seal_sha256=core.digest(run / 'RESPONSE_SEAL.json'),
        original_seal_sha256=core.digest(OLD / 'RESPONSE_SEAL.json'),
        verification_sha256=core.digest(verification_path),
        accounting_source_sha256=core.digest(Path(__file__)),
        accounting_wrapper_sha256=core.digest(ACCOUNTING_WRAPPER),
        accounting_core_sha256=core.digest(ACCOUNTING_CORE),
        disposition=seal['disposition'], fresh_original_entry=False,
        entry='saved_checked_work_with_declared_successor_contract_job',
        inherited=core.aggregate(inherited), new=core.aggregate(new),
        combined=core.aggregate(inherited + new),
        inherited_operations=28, new_operations=len(operations),
        cumulative_operations=seal['actual_operations'], new_operation_types=dict(types),
        new_native_measurements_including_unsent=len(native),
        new_peak_native_input_including_unsent=max((row['prompt_tokens'] for row in native), default=None),
        new_task_loop_seconds=loops[0]['task_loop_seconds'] if loops else None,
        final_feedback_has_no_later_request=bool(new and new[-1]['complete_response_processed']),
        final_candidate_id=verification['final_candidate_id'], submitted=verification['submitted'],
        runtime_closure=closures[0], calls=new, no_additional_checker_model_or_native_execution=True,
        interpretation_limits=[
            'The earlier checked submission stays closed; this is an explicitly reopened job, not a fresh original entry.',
            'Inherited, new and combined costs and opportunity counters are distinct; no allowance was reset.',
            'The original public pass and successor checker pass have different definitions and scopes.',
            'A prepared final receipt is not delivered to a nonexistent following request.',
            'Native sizing maxima include rejected/unsent proposals and are not sent input maxima.',
            'Unavailable generation or timing remains unknown rather than estimated.',
            'Generated usage includes thinking and final output; accounting does not identify wasted reasoning.',
            'Mechanical replay and grader outcomes do not replace direct interpretation and artifact review.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or HERE / f'METRICS-{args.version}.json'
    result = measure(args.version)
    raw = (json.dumps(result, indent=2, ensure_ascii=False) + '\n').encode()
    if output.exists():
        assert output.read_bytes() == raw, 'Preserve earlier differing accounting attempts'
    else:
        output.write_bytes(raw)
    print(json.dumps(result, indent=2))
