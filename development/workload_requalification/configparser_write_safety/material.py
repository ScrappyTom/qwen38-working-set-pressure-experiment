"""Exact saved code and evaluator reference, separate from actor presentation."""
import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AREA = Path(__file__).resolve().parent
BASELINE = AREA.parent / 'documentation_followup/run-001/final-candidate.json'
BASELINE_ID = '20c32a7ff719a132b258d292f8e21122cd211d860469c227b9a7cc9b0da4755b'
LIBRARY = 'Lib/configparser.py'
DOC = 'Doc/library/configparser.rst'
NEW_TESTS = 'Lib/test/test_configparser_write_safety.py'
SKELETON = 'import configparser\nimport io\nimport unittest\n\n\n# Add public write() regression tests here.\n'


def baseline_files():
    value = json.loads(BASELINE.read_bytes())
    assert value['candidate_id'] == BASELINE_ID
    files = {r['path']: r['content_utf8'].encode() for r in value['files']}
    assert len(files) == 10
    return files


def starting_files():
    return {**baseline_files(), NEW_TESTS: SKELETON.encode()}


def reference_source():
    manifest = json.loads((AREA / 'upstream/MANIFEST.json').read_bytes())
    for row in manifest['files']:
        raw = (AREA / 'upstream' / row['path']).read_bytes()
        assert len(raw) == row['size_bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
    return (AREA / 'upstream' / LIBRARY).read_text(encoding='utf-8')


def reference_library():
    """Minimal known implementation, excluded from actor files and input."""
    source = baseline_files()[LIBRARY].decode()
    upstream = reference_source()
    start = upstream.index('class InvalidWriteError(Error):')
    exception = upstream[start:upstream.index('\n\nUNNAMED_SECTION =', start)]
    start = upstream.index('    def _validate_key_contents(self, key):')
    method = upstream[start:upstream.index('    def _validate_value_types(', start)]
    old = '           "ConfigParser", "RawConfigParser",'
    assert source.count(old) == 1
    source = source.replace(old, '           "InvalidWriteError", "ConfigParser", "RawConfigParser",')
    marker = 'class Interpolation:'
    assert source.count(marker) == 1
    source = source.replace(marker, exception + '\n\n' + marker)
    marker = '        for key, value in section_items:\n'
    assert source.count(marker) == 1
    source = source.replace(marker, marker + '            self._validate_key_contents(key)\n')
    marker = '    def _validate_value_types('
    assert source.count(marker) == 1
    source = source.replace(marker, method + marker)
    return source.encode()


def baseline_with_exception():
    source = baseline_files()[LIBRARY]
    # The comparison has the promised exception API, but keeps unsafe write().
    # AttributeError from merely importing a new name cannot establish detection.
    return source + b'\n\nclass InvalidWriteError(Error):\n    pass\n\n__all__ += ("InvalidWriteError",)\n'


def checker_configuration():
    original = baseline_files()
    return dict(
        baseline_library=base64.b64encode(baseline_with_exception()).decode(),
        baseline_tests=base64.b64encode(original['Lib/test/test_configparser.py']).decode(),
        unchanged={name: hashlib.sha256(raw).hexdigest() for name, raw in original.items()
                   if name not in (LIBRARY, DOC)},
        new_tests=NEW_TESTS,
    )
