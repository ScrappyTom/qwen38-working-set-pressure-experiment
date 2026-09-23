"""Reproduce recorded wall intervals; no model, checker or runtime requests."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE.parent / 'run-001' / 'records.jsonl'
rows = [json.loads(line) for line in LOG.read_text(encoding='utf-8').splitlines()]
def elapsed(a, b):
    return (datetime.fromisoformat(b['created_at_utc']) - datetime.fromisoformat(a['created_at_utc'])).total_seconds()

native = []
post = []
pre = []
for index, row in enumerate(rows):
    kind = row['record_type']
    previous = rows[index-1] if index else None
    if kind == 'native_response_received':
        assert previous['record_type'] == 'native_request_started'
        assert previous['payload']['route'] == row['payload']['route']
        native.append(elapsed(previous, row))
    elif kind == 'post_response_runtime_check':
        assert previous['record_type'] == 'response_extracted'
        assert previous['payload']['id'] == row['payload']['id']
        post.append(dict(id=row['payload']['id'], seconds=elapsed(previous, row)))
    elif kind == 'input_constructed':
        pre.append(dict(previous_record=previous['record_type'], seconds=elapsed(previous, row)))

expected = json.loads((HERE/'APPARATUS_INTERVALS.json').read_text(encoding='utf-8'))
assert expected['native_roundtrips'] == len(native)
assert abs(expected['native_roundtrip_seconds'] - sum(native)) < 1e-9
assert expected['post_response_intervals'] == post
assert expected['pre_native_input_intervals'] == pre
assert abs(expected['post_response_validation_health_seconds'] - sum(x['seconds'] for x in post)) < 1e-9
provenance = dict(records_sha256=hashlib.sha256(LOG.read_bytes()).hexdigest(),
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    intervals_sha256=hashlib.sha256((HERE/'APPARATUS_INTERVALS.json').read_bytes()).hexdigest(),
    classification='Recorded elapsed intervals, not isolated measurements of hashing or health checks.',
    native_roundtrips=len(native), post_response_intervals=len(post), pre_native_intervals=len(pre),
    model_requests=0, checker_executions=0, runtime_requests=0)
(HERE/'APPARATUS_INTERVALS_PROVENANCE.json').write_bytes((json.dumps(provenance,indent=2)+'\n').encode())
print(json.dumps(provenance,indent=2))
