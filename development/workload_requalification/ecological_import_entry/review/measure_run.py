"""Fresh E20 accounting from sealed saved records; no host/model/check calls."""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CORE = ROOT / 'development/workload_requalification/url_port_continuation/review/measure_run.py'
spec = importlib.util.spec_from_file_location('ecological_saved_accounting_core', CORE)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def saved_calls(run, records):
    original_read = core.read
    undecodable = set()
    def read_for_accounting(path):
        try:
            return original_read(path)
        except (json.JSONDecodeError, UnicodeDecodeError):
            if not path.name.endswith('-endpoint-response.json'):
                raise
            undecodable.add(path.name.removesuffix('-endpoint-response.json'))
            return None
    # A malformed, preserved endpoint stop contains no qualified token usage.
    # Keep its bytes unchanged and still count its sent input and receipt time.
    with patch.object(core, 'read', read_for_accounting):
        rows = core.calls(run, records)
    for row in rows:
        path = run / 'calls' / (row['id'] + '-endpoint-response.json')
        row['saved_endpoint_response_status'] = (
            'malformed_json_usage_unavailable' if row['id'] in undecodable else
            'saved_json' if path.is_file() else 'not_saved')
    return rows


def measure(version='001'):
    assert re.fullmatch(r'[0-9]{3}', version)
    run = HERE.parent / f'run-{version}'
    assert (run / 'RESPONSE_SEAL.json').is_file(), 'Do not account for an open run as closed'
    verification_path = HERE / f'VERIFICATION-{version}.json'
    verification = core.read(verification_path)
    assert verification['status'] == 'replayed_exactly' and verification['fresh_original_entry'] is True
    assert verification['response_seal_sha256'] == core.digest(run / 'RESPONSE_SEAL.json')
    assert verification['records_sha256'] == core.digest(run / 'records.jsonl')
    seal, records = core.checked_seal(run), core.records(run)
    calls = saved_calls(run, records)
    assert len(calls) == seal['sent_requests'] == verification['requests_used']
    assert [row['id'] for row in calls] == [f'C{i:02d}' for i in range(1, len(calls)+1)]
    assert all(row['requests_used_before_response'] == i for i, row in enumerate(calls))
    assert sum(row['complete_response_processed'] for row in calls) == seal['processed_invocations']
    operations = [row for row in records if row['record_type'] == 'contribution_operation']
    assert len(operations) == seal['actual_operations'] == verification['actual_operations']
    types = Counter(core.read(run / row['artifacts'][0]['path'])['action']['action'] for row in operations)
    native = [row['payload'] for row in records if row['record_type'] == 'native_input_prepared']
    loops = [row['payload'] for row in records if row['record_type'] == 'task_loop_completed']
    closures = [row['payload'] for row in records if row['record_type'] == 'runtime_closed']
    assert len(loops) <= 1 and len(closures) == 1
    assert closures[0]['owned_server_shutdown_verified'] and closures[0]['dedicated_port_free']
    return dict(status='recomputed_from_sealed_saved_wires_and_endpoints',
        response_seal_sha256=core.digest(run / 'RESPONSE_SEAL.json'),
        verification_sha256=core.digest(verification_path),
        accounting_source_sha256=core.digest(Path(__file__)), accounting_core_sha256=core.digest(CORE),
        disposition=seal['disposition'], fresh_original_entry=True, inherited_requests=0, inherited_operations=0,
        totals=core.aggregate(calls), operations=len(operations), operation_types=dict(types),
        native_measurements_including_unsent=len(native),
        peak_native_input_including_unsent=max((row['prompt_tokens'] for row in native), default=None),
        task_loop_seconds=loops[0]['task_loop_seconds'] if loops else None,
        final_feedback_has_no_later_request=bool(calls and calls[-1]['complete_response_processed']),
        final_candidate_id=verification['final_candidate_id'], submitted=verification['submitted'],
        runtime_closure=closures[0], calls=calls, no_additional_checker_model_or_native_execution=True,
        interpretation_limits=['Native sizing maxima include rejected/unsent proposals and are not sent input maxima.',
            'Unavailable generation or timing remains unknown rather than estimated.',
            'Generated usage includes thinking and final output; accounting does not identify wasted reasoning.',
            'Named source inspection, model interpretation, hidden acceptance and artifact preservation require separate audits.',
            'A prepared final receipt is not delivered to a nonexistent following request.'])


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
