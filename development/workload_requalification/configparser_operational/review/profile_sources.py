"""Profile frozen source verification after closure; no inference or checking."""
import cProfile
import json
import pstats
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bootstrap
import operational_task as study
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


def main():
    run = study.AREA / 'run-001'
    assert (run / 'RESPONSE_SEAL.json').exists(), 'Profile only after live closure'
    manifest = json.loads((run / 'EXECUTION_MANIFEST.json').read_text(encoding='utf-8'))
    bound = manifest['source_sha256']
    module = study.Task()
    profiler = cProfile.Profile()
    start = time.perf_counter()
    profiler.enable()
    module.verify_sources(bound)
    profiler.disable()
    elapsed = time.perf_counter() - start
    stats = pstats.Stats(profiler)
    rows = []
    for (filename, line, name), (primitive, calls, own, cumulative, callers) in stats.stats.items():
        rows.append(dict(file=filename, line=line, function=name, calls=calls,
                         own_seconds=own, cumulative_seconds=cumulative))
    rows.sort(key=lambda row: row['cumulative_seconds'], reverse=True)
    result = dict(status='all_frozen_sources_match', files=len(bound),
        bytes=sum((study.ROOT / name).stat().st_size for name in bound),
        elapsed_seconds=elapsed, top_functions=rows[:30],
        manifest_sha256=sha256_file(run / 'EXECUTION_MANIFEST.json'),
        profile_source_sha256=sha256_file(Path(__file__)),
        inference_requests=0, checker_executions=0,
        limitation='One post-run profile; not a causal allocation of live timing.')
    output = Path(__file__).with_name('SOURCE_PROFILE.json')
    with output.open('xb') as stream:
        stream.write(canonical_json_bytes(result))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
