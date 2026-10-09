"""Read saved endpoint timing fields; no model invocation or runtime change."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import phase_task as study
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file

task = study.Task('002')
rows = []
for path in sorted((task.RUN / 'calls').glob('*-endpoint-response.json')):
    value = task.read(path)
    rows.append(dict(id=path.name.split('-')[0], source_sha256=sha256_file(path),
        timings=value['timings'], usage=value['usage']))
result = dict(source_sha256=sha256_file(Path(__file__)),
    response_seal_sha256=sha256_file(task.RUN / 'RESPONSE_SEAL.json'), calls=rows,
    prompt_seconds=sum(r['timings']['prompt_ms'] for r in rows) / 1000,
    generation_seconds=sum(r['timings']['predicted_ms'] for r in rows) / 1000,
    limits=['Endpoint timing fields are measured components, not complete controller or review costs.'])
raw = canonical_json_bytes(result)
path = task.AREA / 'review/002/TIMINGS.json'
if path.exists():
    assert path.read_bytes() == raw
else:
    path.write_bytes(raw)
print(json.dumps({k: v for k, v in result.items() if k != 'calls'}, indent=2))
