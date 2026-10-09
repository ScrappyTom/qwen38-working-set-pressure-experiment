"""Correct call-site contract for the frozen preparation replay helper."""
import importlib.util
import json
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'verify_run.py'
spec = importlib.util.spec_from_file_location('e18_continuation_preparation_audit', path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
original = audit._preparation


def preparation(module, seal):
    assert seal == module.read(module.PACKAGE / 'SEAL.json')
    qualification = module.read(module.PACKAGE / 'QUALIFICATION.json')
    assert qualification['actor'] == module.ACTOR
    # The helper otherwise expects a RESPONSE_SEAL. Do not mutate either seal.
    return original(module, {**seal, 'actor': qualification['actor']})


audit._preparation = preparation
result = audit.verify_preparation('001')
result['audit_adapter'] = 'Preparation actor authenticated from QUALIFICATION.json; original run-seal auditor preserved unchanged.'
assert audit.canonical_json_bytes(result) == path.with_name('PREPARATION-VERIFICATION-002.json').read_bytes()
print(json.dumps(result, indent=2))
