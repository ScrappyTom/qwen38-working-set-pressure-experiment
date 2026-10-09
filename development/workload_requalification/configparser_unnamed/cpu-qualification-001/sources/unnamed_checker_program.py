"""Candidate execution, preservation and explicit old-library comparison."""
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
        details=[dict(test=test.id(), trace=trace) for test, trace in (*result.failures, *result.errors)],
        runner_output=stream.getvalue())


def tests(path, name):
    return unittest.defaultTestLoader.loadTestsFromModule(load(path, name))


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def main():
    sys.path.insert(0, str(Path('Lib').resolve()))
    library = load(Path('Lib/configparser.py'), 'configparser')
    upstream = run_suite(unittest.TestSuite([
        tests(Path('Lib/test/test_configparser.py'), 'saved_parser_tests'),
        tests(Path('Lib/test/test_configparser_write_safety.py'), 'saved_write_tests')]))
    suite = tests(Path(CONFIG['new_tests']), 'current_unnamed_tests')
    added = [test.id() for test in flatten(suite)]
    current = run_suite(suite)
    with tempfile.TemporaryDirectory(prefix='unnamed-baseline-') as folder:
        path = Path(folder)/'configparser.py'
        path.write_bytes(base64.b64decode(CONFIG['baseline_library']))
        load(path, 'configparser')
        original = run_suite(tests(Path(CONFIG['new_tests']), 'current_unnamed_tests'))
    sys.modules['configparser'] = library
    UnnamedContract.library = WriteSafetyContract.library = library

    class ContributionContract(unittest.TestCase):
        def test_preserves_previous_tests_support_data_and_license(self):
            self.assertEqual({name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                for name in CONFIG['unchanged']}, CONFIG['unchanged'])

        def test_adds_executable_regressions(self):
            self.assertTrue(added, 'Add public-API unnamed-section unittest regressions')

    contract = run_suite(unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(cls)
        for cls in (UnnamedContract, WriteSafetyContract, ContributionContract)]))
    document = Path('Doc/library/configparser.rst').read_text(encoding='utf-8')
    declared = all(text in document for text in ('allow_unnamed_section',
        '.. data:: UNNAMED_SECTION', '.. exception:: UnnamedSectionDisabledError'))
    detects = bool(added) and not original['successful']
    passed = all(row['successful'] for row in (upstream, contract, current)) and detects and declared
    report = dict(observation_schema='configparser-original-v1', passed=passed,
        upstream=upstream, contract=contract, candidate_tests=current,
        new_tests_on_original=original, added_tests=added, regression_detects_original=detects,
        documentation_directive_present=declared, documentation_semantics_require_direct_review=True,
        environment=dict(interpreter=sys.version, candidate_module=str(Path(library.__file__).resolve()),
            suite='Preserved parser and write-safety suites using ordinary unittest imports.',
            sensitivity='Exact saved library without unnamed-section API; errors here establish incompatibility, not by themselves assertion quality.'))
    print(json.dumps(report, ensure_ascii=True, separators=(',', ':')), flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
