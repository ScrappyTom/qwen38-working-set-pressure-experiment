"""A new checker identity; the parent definition stays byte-exact."""
import hashlib
import json
from pathlib import Path

AREA = Path(__file__).resolve().parent
PARENT = AREA.parent
ROOT = PARENT.parents[2]
ORIGINAL = ROOT / 'experiments/020_owner_controlled_ecological_pilot_v2/fresh_bank/execution_only/E20-OBS-VERIFIER-SAFETY/public.py'
PARENT_SHA = '2218de2cfcb55bee1a3bd65bb49f5536919b9de1e435460eb9d667c50a73f278'
OLD_SEAL = 'e097eee7afe3b17b926401d3545b8ee0eed12a4b85cb0f708f1598bb90c17fe1'


def public_checker():
    parent = ORIGINAL.read_bytes() + b'\n# Declared contract extension follows the unchanged original.\n' + (PARENT/'contract_checks.py').read_bytes()
    assert hashlib.sha256(parent).hexdigest() == PARENT_SHA
    return parent + b'\n# Separately declared native composition contract follows.\n' + (AREA/'composition_check.py').read_bytes()


def saved_candidate():
    run = PARENT / 'run-003'
    assert hashlib.sha256((run/'RESPONSE_SEAL.json').read_bytes()).hexdigest() == OLD_SEAL
    seal = json.loads((run/'RESPONSE_SEAL.json').read_bytes())
    row = next(r for r in seal['files'] if r['path'] == 'final-candidate.json')
    raw = (run/row['path']).read_bytes()
    assert len(raw) == row['size_bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
    return json.loads(raw)
