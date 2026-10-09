"""Pinned exact replay with explicit inherited-state and accounting adaptations."""
import argparse
import json
from pathlib import Path
import sys
import traceback
from types import ModuleType
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import continuation_task as study
import run_continuation
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

CORE = study.ROOT/'development/workload_requalification/url_port_entry/review/verify_run.py'
assert sha256_file(CORE) == '0c62d4c9d6285901d9d8c8017c2d366442148d26f12d422e2ce750f477532ed6'
adapted = CORE.read_text(encoding='utf-8')
changes = [
    ("assert failures[0] == dict(error_type=type(error).__name__, error=str(error))",
     "assert failures[0] == dict(type=type(error).__name__, message=str(error))"),
    ("""        assert starting['candidate_id'] == module.STARTING_ID and starting['pairs'] == []
        assert starting['ranges'] == [] and starting['saved'] == {} and starting['requests_used'] == 0
        assert starting['starting_archive_length'] == 0 and session.working_account() is None""",
     """        assert canonical_json_bytes(starting) == (module.OLD/'final-state.json').read_bytes()
        assert starting['candidate_id'] == module.STARTING_ID
        assert starting['requests_used'] == module.INHERITED_REQUESTS
        assert len(starting['pairs']) == module.INHERITED_OPERATIONS
        assert (run/'starting-candidate.json').read_bytes() == (module.OLD/'final-candidate.json').read_bytes()
        assert (run/'starting-preceding-feedback.json').read_bytes() == (module.OLD/'final-preceding-feedback.json').read_bytes()"""),
    ("assert tag == f'C{len(starts)+1:02d}' and session.requests_used == len(starts)",
     "assert tag == f'C{module.INHERITED_REQUESTS+len(starts)+1:02d}' and session.requests_used == module.INHERITED_REQUESTS+len(starts)"),
    ("expected = dict(sent_requests=len(starts), actual_operations=session.calls_used,",
     "expected = dict(sent_requests=module.INHERITED_REQUESTS+len(starts), actual_operations=session.calls_used,"),
    ("assert len(starts) == seal['sent_requests'] == session.requests_used",
     "assert len(starts) == seal['sent_requests'] == session.requests_used-module.INHERITED_REQUESTS\n        assert seal['cumulative_requests'] == session.requests_used"),
    ("assert session.calls_used == seal['actual_operations']",
     "assert session.calls_used-module.INHERITED_OPERATIONS == seal['actual_operations']\n        assert seal['cumulative_operations'] == session.calls_used"),
    ("actual_operations=session.calls_used, native_inputs=len(counts), custody_records=len(records),",
     "actual_operations=session.calls_used-module.INHERITED_OPERATIONS, cumulative_requests=session.requests_used, cumulative_operations=session.calls_used, native_inputs=len(counts), custody_records=len(records),"),
    ("fresh_original_entry=True, initial_candidate_id=module.STARTING_ID, submitted=session.submitted,",
     "fresh_original_entry=False, inherited_requests=module.INHERITED_REQUESTS, inherited_operations=module.INHERITED_OPERATIONS, initial_candidate_id=module.STARTING_ID, submitted=session.submitted,"),
]
for old, new in changes:
    assert adapted.count(old) == 1, old
    adapted = adapted.replace(old, new)
core = ModuleType('corrected_write_safety_continuation_replay')
core.__file__ = str(CORE)
with patch.dict(sys.modules, {'url_task': study}):
    exec(compile(adapted, str(CORE), 'exec'), core.__dict__)


def preparation(module, seal):
    manifest = run_continuation.runner.runner.verify_package(module)
    assert module.MANIFEST.read_bytes() == (module.RUN/'EXECUTION_MANIFEST.json').read_bytes()
    assert manifest['source_sha256'] == seal['source_sha256'] == module.source_identities()
    assert manifest['actor'] == seal['actor'] == module.ACTOR
    assert manifest['seed'] == module.SEED
    assert (manifest['maximum_requests'], manifest['maximum_operations']) == (40, 120)
    assert (manifest['inherited_requests'], manifest['inherited_operations']) == (9, 12)
    proof = module.read(module.PACKAGE/'SEAL.json')
    core._inventory(module.PACKAGE, proof)
    assert proof['status'] == 'qualified_no_model_inference' and proof['completion_requests'] == 0
    first = module.RUN/'calls/C10-wire-request.json'
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
