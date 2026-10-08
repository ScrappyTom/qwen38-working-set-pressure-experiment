"""Check an unresolved review question about the saved test's original class.

The actor retains isinstance on the raised error. Exact type checks on transports
may nevertheless detect a subclass raised by the actual lookup. Test that narrow
behavior on isolated reviewer copies; never modify the actor candidate or grade.
"""
import ast
import io
import json
from pathlib import Path
import sys
import textwrap
import types
import unittest

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import correction_task as entry
from working_set_exp.jsonutil import canonical_json_bytes

task = entry.Task()
end = 'final' if (task.RUN/'final-candidate.json').exists() else 'stopped'
candidate = entry.original.candidate_from_snapshot(entry.original.read(task.RUN/f'{end}-candidate.json'))
files = candidate.file_map
source = files[entry.TEST].decode()
node = next(n for n in ast.parse(source).body if getattr(n, 'name', None) == 'InterpolationMissingOptionErrorTransportTestCase')
test_code = ast.get_source_segment(source, node)+'\n'
library_code = files['Lib/configparser.py'].decode()
out = Path(__file__).parent/'run-001/lookup-class-probe'
out.mkdir(parents=True, exist_ok=False)
(out/'saved_tests.py').write_text(test_code, encoding='utf-8')
old = 'raise InterpolationMissingOptionError('
assert library_code.count(old) == 3
rows = []
previous = sys.modules.get('configparser')
try:
    for label, altered in (('saved_control', False), ('review_lookup_subclass', True)):
        module = types.ModuleType('configparser')
        sys.modules['configparser'] = module
        code = library_code.replace(old, 'raise _ReviewLookupSubclass(') if altered else library_code
        (out/(label+'_library.py')).write_text(code, encoding='utf-8')
        exec(compile(code, label+'_library.py', 'exec'), module.__dict__)
        if altered:
            module._ReviewLookupSubclass = type('_ReviewLookupSubclass',
                (module.InterpolationMissingOptionError,), {'__module__':'configparser'})
        namespace = dict(__name__='review_saved_tests', configparser=module, unittest=unittest, textwrap=textwrap)
        exec(compile(test_code, 'saved_tests.py', 'exec'), namespace)
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(namespace[node.name])
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        (out/(label+'.log')).write_text(stream.getvalue(), encoding='utf-8')
        rows.append(dict(case=label, tests=result.testsRun, errors=len(result.errors),
            failures=len(result.failures), successful=result.wasSuccessful(), output=stream.getvalue()))
finally:
    if previous is None: sys.modules.pop('configparser', None)
    else: sys.modules['configparser'] = previous
report = dict(classification='Isolated reviewer probe; no new model work or replacement score',
    candidate_id=candidate.candidate_id, ordinary_lookup_sites_changed=3,
    unchanged_public_exception_binding=True, rows=rows, interpreter=sys.version)
(out/'RESULTS.json').write_bytes(canonical_json_bytes(report))
print(json.dumps([{k:v for k,v in r.items() if k!='output'} for r in rows]))
