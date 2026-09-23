"""Counterbalanced CPU-only timings, with full content verification every trial."""
import json
from pathlib import Path
import statistics
import time

import bootstrap
import source_verification
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


def main():
    area=Path(__file__).resolve().parent
    manifest=bootstrap.ROOT/'development/workload_requalification/configparser_operational/run-001/EXECUTION_MANIFEST.json'
    bound=json.loads(manifest.read_text())['source_sha256']
    rows=[]
    for workers in (1,4,4,1):
        started=time.perf_counter()
        source_verification.verify_sources(bootstrap.ROOT,bound,workers=workers)
        row=dict(workers=workers,seconds=time.perf_counter()-started,all_hashes_match=True)
        rows.append(row)
        print(json.dumps(row),flush=True)
    result=dict(files=len(bound),manifest_sha256=sha256_file(manifest),trials=rows,
        median_seconds={str(n):statistics.median(r['seconds'] for r in rows if r['workers']==n) for n in (1,4)},
        inference_requests=0,checker_executions=0,
        source_sha256={p.name:sha256_file(p) for p in (Path(__file__),area/'source_verification.py')},
        limitation='Local counterbalanced warm/cold filesystem timings; no model speed attribution.')
    with (area/'VERIFICATION_TIMING-001.json').open('xb') as stream:
        stream.write(canonical_json_bytes(result))


if __name__=='__main__':main()
