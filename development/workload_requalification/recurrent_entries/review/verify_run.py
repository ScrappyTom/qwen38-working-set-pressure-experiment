"""Reuse pinned exact replay; bind historical checks at their actual phase."""
import argparse
import json
from pathlib import Path
import sys
import traceback
from types import ModuleType
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import recurrent_task as study
import run_recurrent
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

CORE = study.ROOT / 'development/workload_requalification/url_port_entry/review/verify_run.py'
CORE_SHA256 = '0c62d4c9d6285901d9d8c8017c2d366442148d26f12d422e2ce750f477532ed6'


def checker_bytes_at(session, target):
    index = 0
    for pair in session.pairs:
        if pair is target:
            phase = session.order[index]
            assert pair['response']['check_id'] == ('prefork' if phase == 'A' else 'public')
            return session.phase_checkers[phase]
        if pair['response']['action'] == 'fork_ready' and pair['result'].get('accepted'):
            assert (pair['result']['completed_phase'], pair['result']['next_phase']) == session.order[index:index+2]
            index += 1
    raise AssertionError('check is not in the replayed operation history')


assert sha256_file(CORE) == CORE_SHA256
original = CORE.read_text(encoding='utf-8')
before = "assert outcome['checker_sha256'] == receipt['check_definition_sha256'] == sha256_bytes(session.checkers[action['check_id']])"
after = "assert outcome['checker_sha256'] == receipt['check_definition_sha256'] == sha256_bytes(checker_bytes_at(session, pair))"
assert original.count(before) == 1
adapted = original.replace(before, after)
core = ModuleType('recurrent_exact_replay_core')
core.__file__ = str(CORE)
core.checker_bytes_at = checker_bytes_at
with patch.dict(sys.modules, {'url_task': study}):
    exec(compile(adapted, str(CORE), 'exec'), core.__dict__)


def preparation(module, seal):
    manifest = run_recurrent.configure().verify_preparation(module)
    assert module.MANIFEST.read_bytes() == (module.RUN / 'EXECUTION_MANIFEST.json').read_bytes()
    assert manifest['source_sha256'] == seal['source_sha256'] == module.source_identities()
    assert manifest['actor'] == seal['actor'] == module.ACTOR
    assert (manifest['maximum_requests'], manifest['maximum_operations']) == (64, 192)
    proof = module.read(module.PACKAGE / 'SEAL.json')
    core._inventory(module.PACKAGE, proof)
    assert proof['status'] == 'qualified_no_model_inference' and proof['completion_requests'] == 0
    first = module.RUN / 'calls/C01-wire-request.json'
    if first.exists():
        assert first.read_bytes() == (module.PACKAGE / 'initial-wire-request.json').read_bytes()
        assert sha256_file(first) == manifest['initial']['wire_request_sha256']
    return manifest


core._preparation = preparation


def verify(version='001'):
    return dict(core.verify(version), adapter_sha256=sha256_file(Path(__file__)),
        adapted_core_sha256=sha256_bytes(adapted.encode()),
        historical_checker_binding='original definition at each actual accepted phase boundary')


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(value)
    if path.exists():
        assert path.read_bytes() == raw
    else:
        with path.open('xb') as stream:
            stream.write(raw)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    output = Path(__file__).with_name(f'VERIFICATION-{args.version}.json')
    try:
        value = verify(args.version)
    except BaseException as error:
        save(output.with_name(output.stem + '-FAILED.json'), dict(status='failed', type=type(error).__name__,
             message=str(error), traceback=traceback.format_exc()))
        raise
    save(output, value)
    print(json.dumps(value, indent=2))
