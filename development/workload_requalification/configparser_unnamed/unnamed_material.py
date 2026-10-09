"""Exact saved contribution; upstream is an evaluator reference, not an oracle."""
import base64
import hashlib
import json
from pathlib import Path

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
PARENT = AREA.parent/'configparser_write_safety_continuation'
BASELINE = PARENT/'run-001/final-candidate.json'
BASELINE_ID = '0f23fd5116a90cda202f48b5010e4eed6057ce99cea921a9328009b79c9ee3c4'
LIBRARY = 'Lib/configparser.py'
DOC = 'Doc/library/configparser.rst'
NEW_TESTS = 'Lib/test/test_configparser_unnamed.py'
SKELETON = 'import configparser\nimport io\nimport unittest\n\n\n# Add public unnamed-section regression tests here.\n'
UPSTREAM = AREA.parent/'configparser_write_safety/upstream'


def baseline_files():
    value = json.loads(BASELINE.read_bytes())
    assert value['candidate_id'] == BASELINE_ID
    inventory = json.loads((PARENT/'review/001/SAVED-WORK.json').read_bytes())
    files = {row['path']: row['content_utf8'].encode() for row in value['files']}
    assert len(files) == len(inventory['files']) == 11
    for row in inventory['files']:
        assert hashlib.sha256(files[row['path']]).hexdigest() == row['sha256']
    return files


def starting_files():
    return {**baseline_files(), NEW_TESTS: SKELETON.encode()}


def upstream_library():
    manifest = json.loads((UPSTREAM/'MANIFEST.json').read_bytes())
    row = next(row for row in manifest['files'] if row['path'] == LIBRARY)
    raw = (UPSTREAM/LIBRARY).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row['sha256']
    return raw


def checker_configuration():
    original = baseline_files()
    return dict(baseline_library=base64.b64encode(original[LIBRARY]).decode(),
        unchanged={name: hashlib.sha256(raw).hexdigest() for name, raw in original.items()
                   if name not in (LIBRARY, DOC)}, new_tests=NEW_TESTS)
