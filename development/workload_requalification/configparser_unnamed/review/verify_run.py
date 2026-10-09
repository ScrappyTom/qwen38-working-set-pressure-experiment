"""Exact closed-run replay with this task's preparation and stop-record schema."""
import argparse
import json
from pathlib import Path
import sys
import traceback
from types import ModuleType
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unnamed_task as study
import run_unnamed
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

CORE = study.ROOT/'development/workload_requalification/url_port_entry/review/verify_run.py'
assert sha256_file(CORE) == '0c62d4c9d6285901d9d8c8017c2d366442148d26f12d422e2ce750f477532ed6'
original = CORE.read_text(encoding='utf-8')
old = "assert failures[0] == dict(error_type=type(error).__name__, error=str(error))"
new = "assert failures[0] == dict(type=type(error).__name__, message=str(error))"
assert original.count(old) == 1
adapted = original.replace(old, new)
core = ModuleType('unnamed_exact_replay')
core.__file__ = str(CORE)
with patch.dict(sys.modules, {'url_task': study}):
    exec(compile(adapted, str(CORE), 'exec'), core.__dict__)


def preparation(module, seal):
    manifest = run_unnamed.runner.runner.verify_package(module)
    assert module.MANIFEST.read_bytes() == (module.RUN/'EXECUTION_MANIFEST.json').read_bytes()
    assert manifest['source_sha256'] == seal['source_sha256'] == module.source_identities()
    assert manifest['actor'] == seal['actor'] == module.ACTOR
    assert manifest['seed'] == module.SEED
    assert (manifest['maximum_requests'], manifest['maximum_operations']) == (40, 120)
    proof = module.read(module.PACKAGE/'SEAL.json')
    core._inventory(module.PACKAGE, proof)
    assert proof['status'] == 'qualified_no_model_inference' and proof['completion_requests'] == 0
    first = module.RUN/'calls/C01-wire-request.json'
    if first.exists():
        assert first.read_bytes() == (module.PACKAGE/'initial-wire-request.json').read_bytes()
        assert sha256_file(first) == manifest['initial']['wire_request_sha256']
    return manifest


core._preparation = preparation


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(value)
    if path.exists():
        assert path.read_bytes() == raw, 'Preserve differing verification attempts separately'
    else:
        path.write_bytes(raw)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    output = Path(__file__).with_name(f'VERIFICATION-{args.version}.json')
    try:
        value = dict(core.verify(args.version), adapter_sha256=sha256_file(Path(__file__)),
                     adapted_core_sha256=sha256_bytes(adapted.encode()))
    except BaseException as error:
        save(output.with_name(output.stem+'-FAILED.json'), dict(status='failed',
             type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
        raise
    save(output, value)
    print(json.dumps(value, indent=2))
