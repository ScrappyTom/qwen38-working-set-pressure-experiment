"""Included inside the registered checker; ordinary executions, no inference."""

class OverlapContract(unittest.TestCase):
    def exercise(self, style, related=False):
        class Left(abc.ABC): pass
        class Right(Left if related else abc.ABC): pass
        class Value: pass
        @self.library.singledispatch
        def route(value): return 'default'
        union = Left | Right if style == 'pipe' else typing.Union[Left, Right]
        def shared(value): return 'shared'
        route.register(union, shared)
        value = Value()
        self.assertEqual(route(value), 'default')
        Left.register(Value)
        self.assertEqual(route(value), 'shared')
        Right.register(Value)
        if related:
            self.assertIs(route.dispatch(Value), shared)
            self.assertEqual(route(value), 'shared')
        else:
            with self.assertRaises(RuntimeError) as caught:
                route(value)
            self.assertIs(type(caught.exception), RuntimeError)
            self.assertEqual(str(caught.exception), f'Ambiguous dispatch: {Left} or {Right}')
        def explicit(value): return 'explicit'
        self.assertIs(route.register(Value, explicit), explicit)
        self.assertIs(route.dispatch(Value), explicit)
        self.assertEqual(route(value), 'explicit')

    def test_pipe_unrelated(self): self.exercise('pipe')
    def test_typing_unrelated(self): self.exercise('typing')
    def test_pipe_related(self): self.exercise('pipe', related=True)
    def test_typing_related(self): self.exercise('typing', related=True)


def new_actor_suite(path, library, name):
    suite = actor_suite(path, library, name)
    def cases(item):
        for child in item:
            if isinstance(child, unittest.TestSuite): yield from cases(child)
            else: yield child
    return unittest.TestSuite(case for case in cases(suite)
        if case.id().split('.')[-2] != 'LateVirtualRegistration')


def resolver_fault(source):
    old = 'raise RuntimeError("Ambiguous dispatch: {} or {}".format(\n                    match, t))'
    assert source.count(old) == 1
    return source.replace(old, 'return registry[match]', 1)


def qualify_overlap(library, report):
    saved = base64.b64decode(CONFIG['saved_tests'])
    marker = b'\n\nif __name__ == "__main__":'
    assert saved.count(marker) == 1
    prefix, suffix = saved.split(marker, 1)
    current = Path('tests/test_virtual_registration.py').read_bytes()
    doc = Path('Doc/howto/union-dispatch.rst').read_bytes()
    report('saved_contribution_preserved', current.startswith(prefix)
        and current.endswith(marker + suffix)
        and doc.startswith(base64.b64decode(CONFIG['saved_doc'])),
        'Earlier regression bodies and the complete saved document remain exact; additions do not replace them.')
    OverlapContract.library = library
    independent = suite_result(unittest.defaultTestLoader.loadTestsFromTestCase(OverlapContract))
    report('overlap_existing_behavior', independent['passed'],
        'Independent ordinary executions establish existing resolver behavior; they do not grade prose.', **independent)
    added = suite_result(new_actor_suite('tests/test_virtual_registration.py', library, 'new_overlap_current'))
    report('new_overlap_regressions', added['passed'] and added['tests'] >= 1,
        'Only newly authored test classes count here; earlier tests cannot satisfy new coverage.', **added)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'resolver_fault.py'
        path.write_text(resolver_fault(Path('Lib/functools.py').read_text(encoding='utf-8')), encoding='utf-8')
        fault = load_library(path, 'overlap_resolver_fault')
        faulty = suite_result(new_actor_suite('tests/test_virtual_registration.py', fault, 'new_overlap_fault'))
    report('new_regressions_detect_resolver_fault', faulty['tests'] >= 1 and not faulty['passed'],
        'Failure under the specified resolver fault satisfies sensitivity. It is not a failure of the current candidate.',
        fault_execution=faulty)
    previous = sys.modules['functools']
    sys.modules['functools'] = library
    try:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            ordinary = doctest.testfile('Doc/howto/union-dispatch.rst', module_relative=False,
                globs={'functools': library}, verbose=True)
    finally:
        sys.modules['functools'] = previous
    report('ordinary_standalone_documentation', ordinary.failed == 0 and ordinary.attempted > 17,
        'Ordinary doctest.testfile with candidate import and its __main__ namespace. Prose remains independently reviewed.',
        namespace='__main__', failed=ordinary.failed, attempted=ordinary.attempted, runner_output=stream.getvalue())
