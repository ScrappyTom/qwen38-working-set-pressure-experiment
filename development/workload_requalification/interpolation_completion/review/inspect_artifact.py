"""Isolated CPU probes of saved public work; never modify the run or its candidate."""
import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import textwrap
import types
import unittest

AREA = Path(__file__).resolve().parents[1]
OUT = AREA / 'review/run-002/artifact-probes'
OUT.mkdir(exist_ok=True)
snapshot = json.loads((AREA / 'run-002/final-candidate.json').read_text(encoding='utf-8'))
files = {r['path']: r['content_utf8'] for r in snapshot['files']}
source = files['Lib/test/test_configparser.py']
node = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef)
            and n.name == 'InterpolationMissingOptionErrorTransportTestCase')
saved = ast.get_source_segment(source, node) + '\n'
old = 'except configparser.InterpolationMissingOptionError as e:\n            pass'
assert saved.count(old) == 3
lifetime = saved.replace(old, 'except configparser.InterpolationMissingOptionError as caught:\n            e = caught')
diagnostic = lifetime.replace('self.assertEqual(str(e), str(expected_args))', '''self.assertEqual(str(e),
            ("Bad value substitution: option {!r} in section {!r} contains "
             "an interpolation key {!r} which is not a valid option name. "
             "Raw value: {!r}").format(expected_args[0], expected_args[1],
                                      expected_args[3], expected_args[2]))''')
assert diagnostic != lifetime
library = types.ModuleType('configparser')
sys.modules['configparser'] = library
exec(compile(files['Lib/configparser.py'], 'Lib/configparser.py', 'exec'), library.__dict__)


def run(label, code, substitute_copy=False):
    (OUT / (label + '.py')).write_text(code, encoding='utf-8')
    scope = dict(__name__='review_tests', configparser=library, unittest=unittest, textwrap=textwrap)
    exec(compile(code, str(OUT / (label + '.py')), 'exec'), scope)
    original = copy.copy
    class RestoredSubclass(library.InterpolationMissingOptionError):
        pass
    def changed(value):
        if type(value) is library.InterpolationMissingOptionError:
            return RestoredSubclass(*value.args)
        return original(value)
    stream = io.StringIO()
    try:
        if substitute_copy:
            copy.copy = changed
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(scope[node.name])
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    finally:
        copy.copy = original
    (OUT / (label + '.log')).write_text(stream.getvalue(), encoding='utf-8')
    return dict(label=label, tests=result.testsRun, errors=len(result.errors),
                failures=len(result.failures), successful=result.wasSuccessful(),
                error_types=[text.splitlines()[-1] for _, text in result.errors],
                failures_text=[text for _, text in result.failures])


rows = [run('saved_public_class', saved), run('review_lifetime_only', lifetime),
        run('review_lifetime_and_diagnostic', diagnostic),
        run('review_same_with_subclass_copy', diagnostic, substitute_copy=True)]
assert [(r['errors'], r['failures']) for r in rows] == [(3, 0), (0, 3), (0, 0), (0, 0)]
base = next(n for n in ast.parse(files['Lib/configparser.py']).body
            if isinstance(n, ast.ClassDef) and n.name == 'Error')
result = dict(kind='Reviewer-only isolated CPU probes; no actor correction or full checker rerun',
    candidate_id=snapshot['candidate_id'], interpreter=sys.version, executable=sys.executable,
    source_sha256={p: hashlib.sha256(s.encode()).hexdigest() for p, s in files.items()},
    actual_Error_source=ast.get_source_segment(files['Lib/configparser.py'], base),
    Error_extent=[base.lineno, base.end_lineno], rows=rows)
(OUT / 'RESULTS.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: result[k] for k in ('kind', 'candidate_id', 'actual_Error_source', 'Error_extent')}))
print(json.dumps([{k:r[k] for k in ('label','tests','errors','failures','successful')} for r in rows]))
