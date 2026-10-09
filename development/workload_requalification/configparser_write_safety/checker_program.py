"""Bound to candidate by the existing host. Full observations precede reduction."""
import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_suite(suite):
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                skipped=len(result.skipped), successful=result.wasSuccessful(),
                details=[dict(test=test.id(), trace=trace)
                         for test, trace in (*result.failures, *result.errors)],
                runner_output=stream.getvalue())


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def tests(path, name):
    return unittest.defaultTestLoader.loadTestsFromModule(load(path, name))


def main():
    sys.path.insert(0, str(Path('Lib').resolve()))
    library = load(Path('Lib/configparser.py'), 'configparser')
    upstream = run_suite(tests(Path('Lib/test/test_configparser.py'), 'saved_parser_tests'))
    suite = tests(Path(CONFIG['new_tests']), 'current_write_safety_tests')
    added = [test.id() for test in flatten(suite)]
    current = run_suite(suite)
    with tempfile.TemporaryDirectory(prefix='parser-write-sensitivity-') as folder:
        baseline = Path(folder) / 'configparser.py'
        baseline.write_bytes(base64.b64decode(CONFIG['baseline_library']))
        load(baseline, 'configparser')
        original = run_suite(tests(Path(CONFIG['new_tests']), 'current_write_safety_tests'))
    sys.modules['configparser'] = library
    WriteSafetyContract.library = library

    class ContributionContract(unittest.TestCase):
        def test_preserves_saved_tests_and_support(self):
            actual = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                      for name in CONFIG['unchanged']}
            self.assertEqual(actual, CONFIG['unchanged'])

        def test_regressions_reject_unsafe_write_not_only_missing_api(self):
            self.assertTrue(added, 'Add executable public write() regression tests')
            self.assertGreater(original['failures'], 0,
                'New tests must produce an assertion failure on unsafe write() even with InvalidWriteError exported; an import or missing-attribute error alone is insufficient.')

    contract_suite = unittest.TestSuite((
        unittest.defaultTestLoader.loadTestsFromTestCase(WriteSafetyContract),
        unittest.defaultTestLoader.loadTestsFromTestCase(ContributionContract)))
    contract = run_suite(contract_suite)
    document = Path('Doc/library/configparser.rst').read_text(encoding='utf-8')
    declared = '.. exception:: InvalidWriteError' in document
    detects = bool(added) and not original['successful']
    passed = all(row['successful'] for row in (upstream, contract, current)) and detects and declared
    report = dict(observation_schema='configparser-original-v1', passed=passed,
        upstream=upstream, contract=contract, candidate_tests=current,
        new_tests_on_original=original, added_tests=added,
        regression_detects_original=detects, documentation_directive_present=declared,
        documentation_semantics_require_direct_review=True,
        environment=dict(interpreter=sys.version, candidate_module=str(Path(library.__file__).resolve()),
            suite='Saved 3.12.10 tests including the completed multiline backport; ordinary unittest loading.',
            sensitivity='Saved library with InvalidWriteError API added, but unchanged unsafe write behavior.'))
    print(json.dumps(report, ensure_ascii=True, separators=(',', ':')), flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
