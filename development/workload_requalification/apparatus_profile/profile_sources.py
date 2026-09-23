"""Isolate full-hash time over a closed run's frozen manifest; no server."""
import hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/workload_requalification/saved_library_prose'))
import bootstrap
import source_verification
AREA=Path(__file__).resolve().parent
out=AREA/'qualification-001';out.mkdir(exist_ok=False)
manifest=ROOT/'development/workload_requalification/saved_library_prose/run-001/EXECUTION_MANIFEST.json'
value=json.loads(manifest.read_text(encoding='utf-8'));bound=value['source_sha256']
rows=[]
for workers in (4,8,4,8):
    started=time.perf_counter();source_verification.verify_sources(ROOT,bound,workers=workers)
    row=dict(workers=workers,seconds=time.perf_counter()-started,files=len(bound),all_full_hashes_verified=True)
    rows.append(row);print(json.dumps(row),flush=True)
    (out/'RESULTS.json').write_bytes((json.dumps(dict(classification='Isolated offline full-hash timings; no running model or server',
        manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        verifier_sha256=hashlib.sha256(Path(source_verification.__file__).read_bytes()).hexdigest(),
        trials=rows,model_requests=0,checker_executions=0,qualification_complete=len(rows)==4),indent=2)+'\n').encode())
