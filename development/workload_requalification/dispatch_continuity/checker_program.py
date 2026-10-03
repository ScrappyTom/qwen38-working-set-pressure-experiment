"""Execution-only checks; CONFIG is bound by task construction, never actor input."""
import abc
import ast
import base64
import collections
import contextlib
import decimal
import doctest
import importlib.util
import io
from itertools import permutations
import json
from pathlib import Path
import sys
import tempfile
import typing
import unittest
import weakref
from test import support


def load_library(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def suite_result(suite):
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                skipped=len(result.skipped), passed=result.wasSuccessful(),
                details=[dict(test=test.id(), trace=trace)
                         for test, trace in (*result.failures, *result.errors)],
                runner_output=stream.getvalue())


def upstream_suite(library):
    source = base64.b64decode(CONFIG['original_tests']).decode()
    node = next(n for n in ast.parse(source).body
                if isinstance(n, ast.ClassDef) and n.name == 'TestSingleDispatch')
    exact = ''.join(source.splitlines(keepends=True)[node.lineno-1:node.end_lineno])
    env = dict(globals(), functools=library, __name__='frozen_dispatch_tests')
    exec(compile(exact, 'frozen/TestSingleDispatch.py', 'exec'), env)
    return unittest.defaultTestLoader.loadTestsFromTestCase(env['TestSingleDispatch'])


class FeatureContract(unittest.TestCase):
    def exercise(self, union_style, mode):
        f = self.library
        union = typing.Union[int, str] if union_style == 'typing' else int | str
        @f.singledispatch
        def dispatch(value):
            return 'default'
        self.assertEqual(dispatch(1), 'default')  # registration must replace a cached result
        def handler(value):
            return 'union'
        if mode == 'explicit':
            returned = dispatch.register(union, handler)
        elif mode == 'decorator':
            returned = dispatch.register(union)(handler)
        else:
            handler.__annotations__ = {'value': union}
            returned = dispatch.register(handler)
        self.assertIs(returned, handler)
        self.assertIs(dispatch.registry[int], handler)
        self.assertIs(dispatch.registry[str], handler)
        self.assertNotIn(union, dispatch.registry)
        self.assertEqual([dispatch(1), dispatch('x'), dispatch(1.0)], ['union', 'union', 'default'])
        class Child(int):
            pass
        self.assertEqual(dispatch(Child()), 'union')

    def test_typing_explicit(self): self.exercise('typing', 'explicit')
    def test_typing_decorator(self): self.exercise('typing', 'decorator')
    def test_typing_inferred(self): self.exercise('typing', 'inferred')
    def test_pep604_explicit(self): self.exercise('pep604', 'explicit')
    def test_pep604_decorator(self): self.exercise('pep604', 'decorator')
    def test_pep604_inferred(self): self.exercise('pep604', 'inferred')

    def test_invalid_unions_are_atomic(self):
        for union in (typing.Union[int, list[str]], int | list[str]):
            for mode in ('explicit', 'decorator', 'inferred'):
                with self.subTest(union=union, mode=mode):
                    @self.library.singledispatch
                    def dispatch(value): return 'default'
                    before = dict(dispatch.registry)
                    def handler(value): return 'invalid'
                    handler.__annotations__ = {'value': union}
                    with self.assertRaises(TypeError):
                        if mode == 'explicit': dispatch.register(union, handler)
                        elif mode == 'decorator': dispatch.register(union)(handler)
                        else: dispatch.register(handler)
                    self.assertEqual(dict(dispatch.registry), before)
                    self.assertEqual(dispatch(1), 'default')

    def test_method_union(self):
        f = self.library
        class Receiver:
            @f.singledispatchmethod
            def handle(self, value): return 'default'
            @handle.register
            def _(self, value: typing.Union[int, str]): return 'union'
        self.assertEqual([Receiver().handle(1), Receiver().handle('x'), Receiver().handle([])],
                         ['union', 'union', 'default'])


class DynamicContract(unittest.TestCase):
    def exercise(self, style, mode):
        class Plugin(abc.ABC): pass
        class Payload: pass
        class Other: pass
        union = typing.Union[Plugin, int] if style == 'typing' else Plugin | int
        @self.library.singledispatch
        def dispatch(value): return 'default'
        def handler(value): return 'plugin'
        handler.__annotations__ = {'value': union}
        if mode == 'explicit': dispatch.register(union, handler)
        elif mode == 'decorator': dispatch.register(union)(handler)
        else: dispatch.register(handler)
        self.assertEqual(dispatch(Payload()), 'default')
        self.assertEqual(dispatch(Other()), 'default')
        Plugin.register(Payload)
        self.assertTrue(issubclass(Payload, Plugin))
        self.assertIs(dispatch.registry[Plugin], handler)
        self.assertEqual(dispatch(Payload()), 'plugin')
        self.assertIs(dispatch.dispatch(Payload), handler)
        self.assertEqual(dispatch(Other()), 'default')
        Plugin.register(Other)
        self.assertEqual(dispatch(Other()), 'plugin')
        self.assertEqual(dispatch(2), 'plugin')
    def test_typing_explicit(self): self.exercise('typing', 'explicit')
    def test_typing_decorator(self): self.exercise('typing', 'decorator')
    def test_typing_inferred(self): self.exercise('typing', 'inferred')
    def test_pep604_explicit(self): self.exercise('pep604', 'explicit')
    def test_pep604_decorator(self): self.exercise('pep604', 'decorator')
    def test_pep604_inferred(self): self.exercise('pep604', 'inferred')
    def test_method_virtual_union(self):
        class Plugin(abc.ABC): pass
        class Payload: pass
        f = self.library
        class Receiver:
            @f.singledispatchmethod
            def handle(self, value): return 'default'
            @handle.register(Plugin | int)
            def _(self, value): return 'plugin'
        receiver = Receiver()
        self.assertEqual(receiver.handle(Payload()), 'default')
        Plugin.register(Payload)
        self.assertEqual(receiver.handle(Payload()), 'plugin')


def actor_suite(path, library, name):
    previous = sys.modules['functools']
    sys.modules['functools'] = library
    try:
        module = load_library(path, name)
        return unittest.defaultTestLoader.loadTestsFromModule(module)
    finally:
        sys.modules['functools'] = previous


def main():
    rows = []
    def report(case, met, meaning, **observation):
        if 'passed' in observation:
            observation['execution_passed'] = observation.pop('passed')
        row = dict(case=case, passed=bool(met), meaning=meaning, **observation)
        rows.append(row)
        print(json.dumps(row, ensure_ascii=True, separators=(',', ':')), flush=True)
    library = load_library(Path('Lib/functools.py'), 'candidate_functools')
    import hashlib
    preserved = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                 for path in CONFIG['unchanged']}
    report('preserved_material', preserved == CONFIG['unchanged'],
           'Unchanged material is an explicit task constraint.', actual=preserved)
    old = suite_result(upstream_suite(library))
    report('original_single_dispatch_suite', old['passed'],
           'Exact historical TestSingleDispatch class under the documented harness.', **old)
    FeatureContract.library = library
    feature = suite_result(unittest.defaultTestLoader.loadTestsFromTestCase(FeatureContract))
    report('union_feature_contract', feature['passed'], 'Independent requested behavior.', **feature)
    new = suite_result(actor_suite('tests/test_union_registration.py', library, 'actor_union_tests'))
    report('authored_union_regressions', new['passed'] and new['tests'] >= 3,
           'Current authored regressions must pass and include at least three methods.', **new)
    with tempfile.TemporaryDirectory(prefix='dispatch-sensitivity-') as folder:
        baseline = Path(folder) / 'functools.py'
        baseline.write_bytes(base64.b64decode(CONFIG['original_library']))
        original = load_library(baseline, 'original_functools')
        before = suite_result(actor_suite('tests/test_union_registration.py', original, 'baseline_union_tests'))
        report('regressions_expose_original_missing_feature', not before['passed'] and before['tests'] >= 3,
               'A failure on the original is successful sensitivity, not a current-candidate failure.',
               original_execution=before)
        if CONFIG['phase'] == 'dynamic':
            DynamicContract.library = library
            dynamic = suite_result(unittest.defaultTestLoader.loadTestsFromTestCase(DynamicContract))
            report('late_virtual_registration_contract', dynamic['passed'],
                   'Independent current dynamic-registration behavior.', **dynamic)
            current = suite_result(actor_suite('tests/test_virtual_registration.py', library, 'actor_dynamic_tests'))
            report('authored_dynamic_regressions', current['passed'] and current['tests'] >= 2,
                   'Current authored regressions must pass and include at least two methods.', **current)
            baseline.write_bytes(base64.b64decode(CONFIG['merged_library']))
            merged = load_library(baseline, 'historical_union_functools')
            before = suite_result(actor_suite('tests/test_virtual_registration.py', merged, 'baseline_dynamic_tests'))
            report('regressions_expose_historical_virtual_behavior', not before['passed'] and before['tests'] >= 2,
                   'Failure on historical union implementation is successful sensitivity, not another current fault.',
                   historical_execution=before)
            doc = Path('Doc/howto/union-dispatch.rst').read_text(encoding='utf-8')
            test = doctest.DocTestParser().get_doctest(doc, {'functools': library},
                'authored_union_docs', 'Doc/howto/union-dispatch.rst', 0)
            stream = io.StringIO()
            previous = sys.modules['functools']
            sys.modules['functools'] = library
            try:
                result = doctest.DocTestRunner(verbose=True).run(test, out=stream.write)
            finally:
                sys.modules['functools'] = previous
            report('executable_documentation', result.failed == 0 and result.attempted >= 6,
                   'Added interactive examples execute; prose still requires direct review.',
                   failed=result.failed, attempted=result.attempted, runner_output=stream.getvalue())
    failures = [row['case'] for row in rows if not row['passed']]
    print(json.dumps(dict(passed=not failures, failed_cases=failures), separators=(',', ':')), flush=True)
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
