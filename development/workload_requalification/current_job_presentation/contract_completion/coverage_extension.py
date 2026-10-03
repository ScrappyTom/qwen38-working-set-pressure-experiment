"""Successor checker extension; executed observations, not model instructions."""

def method_nodes(source):
    tree = ast.parse(source)
    return {(cls.name, node.name): node for cls in tree.body if isinstance(cls, ast.ClassDef)
            for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith('test')}


def preserved_methods(original, current):
    before, after = method_nodes(original), method_nodes(current)
    return bool(before) and all(key in after and ast.dump(node) == ast.dump(after[key])
                               for key, node in before.items())


def test_cases(suite):
    for child in suite:
        if isinstance(child, unittest.TestSuite):
            yield from test_cases(child)
        else:
            yield child


def new_actor_suite(path, library, name):
    old = set(method_nodes(base64.b64decode(CONFIG['saved_tests']).decode()))
    return unittest.TestSuite(case for case in test_cases(actor_suite(path, library, name))
        if tuple(case.id().split('.')[-2:]) not in old)


AMBIGUITY_RAISE = 'raise RuntimeError("Ambiguous dispatch: {} or {}".format(\n                    match, t))'


def instrument_resolver(source):
    assert source.count(AMBIGUITY_RAISE) == 1
    assert '_qualification_exception' not in source
    helper = '''
_qualification_sites = 0
_qualification_target = None
_qualification_fault = None
class _QualificationRuntimeError(RuntimeError):
    pass
def _qualification_exception(match, other):
    global _qualification_sites
    _qualification_sites += 1
    message = "Ambiguous dispatch: {} or {}".format(match, other)
    if _qualification_sites == _qualification_target:
        if _qualification_fault == 'exception_class':
            return _QualificationRuntimeError(message)
        if _qualification_fault == 'diagnostic_text':
            message += ' [qualification fault]'
    return RuntimeError(message)
'''
    return source.replace(AMBIGUITY_RAISE,
        'raise _qualification_exception(match, t)', 1) + helper


def qualify_sites(path, source):
    """A strong assertion in one case must not hide a weak assertion elsewhere."""
    sites, baselines = [], []
    with tempfile.TemporaryDirectory(prefix='exact-exception-sites-') as folder:
        library_path = Path(folder) / 'instrumented_functools.py'
        library_path.write_text(instrument_resolver(source), encoding='utf-8')
        serial = 0
        def execute(key, target=None, fault=None):
            nonlocal serial
            serial += 1
            library = load_library(library_path, f'exact_site_library_{serial}')
            library._qualification_target, library._qualification_fault = target, fault
            cases = list(test_cases(new_actor_suite(path, library, f'exact_site_actor_{serial}')))
            selected = [case for case in cases if tuple(case.id().split('.')[-2:]) == key]
            result = suite_result(unittest.TestSuite(selected))
            return result, library._qualification_sites
        library = load_library(library_path, 'exact_site_inventory_library')
        cases = list(test_cases(new_actor_suite(path, library, 'exact_site_inventory_actor')))
        keys = sorted({tuple(case.id().split('.')[-2:]) for case in cases})
        for key in keys:
            ordinary, count = execute(key)
            baselines.append(dict(method=list(key), exception_sites=count, **ordinary))
            if not ordinary['passed']:
                continue
            for index in range(1, count + 1):
                trials = {}
                for fault in ('exception_class', 'diagnostic_text'):
                    result, visited = execute(key, index, fault)
                    trials[fault] = dict(detected=visited >= index and not result['passed'],
                        visited_sites=visited, fault_execution=result)
                sites.append(dict(method=list(key), site=index, trials=trials))
    return dict(instrumented_normal_executions=baselines, sites=sites,
        instrumentation_preserves_ordinary_tests=bool(baselines) and all(r['passed'] for r in baselines),
        exact_class_detected_at_every_site=bool(sites) and all(r['trials']['exception_class']['detected'] for r in sites),
        exact_text_detected_at_every_site=bool(sites) and all(r['trials']['diagnostic_text']['detected'] for r in sites))


def qualify_overlap(library, report):
    current = Path('tests/test_virtual_registration.py').read_text(encoding='utf-8')
    saved = base64.b64decode(CONFIG['saved_tests']).decode()
    report('saved_regression_methods_preserved', preserved_methods(saved, current),
        'The two original method bodies and assertions remain unchanged; new methods may be added in existing classes.')
    OverlapContract.library = library
    independent = suite_result(unittest.defaultTestLoader.loadTestsFromTestCase(OverlapContract))
    report('overlap_existing_behavior', independent['passed'],
        'Independent ordinary executions establish library behavior, not authored assertion strength or prose truth.', **independent)
    added = suite_result(new_actor_suite('tests/test_virtual_registration.py', library, 'new_overlap_current'))
    report('new_overlap_regressions', added['passed'] and added['tests'] >= 1,
        'New methods are identified relative to the two saved methods, including additions within the old class.', **added)
    source = Path('Lib/functools.py').read_text(encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='silent-resolver-fault-') as folder:
        path = Path(folder) / 'fault.py'
        path.write_text(source.replace(AMBIGUITY_RAISE, 'return registry[match]', 1), encoding='utf-8')
        fault = load_library(path, 'silent_resolver_fault')
        faulty = suite_result(new_actor_suite('tests/test_virtual_registration.py', fault, 'new_overlap_fault'))
    report('new_regressions_detect_resolver_fault', added['passed'] and faulty['tests'] >= 1 and not faulty['passed'],
        'An expected failure under intentional silent selection establishes sensitivity; it is not a current-candidate failure.',
        fault_execution=faulty)
    qualification = qualify_sites('tests/test_virtual_registration.py', source)
    normal = qualification['instrumentation_preserves_ordinary_tests']
    sites = qualification['sites']
    report('exception_site_execution_qualified', added['passed'] and normal and len(sites) >= 4,
        'Ordinary per-method executions must pass and reach the four required raising scenarios before intentional faults can grade coverage.',
        observed_sites=len(sites), ordinary_executions=qualification['instrumented_normal_executions'])
    for name, key, meaning in (
        ('authored_exact_exception_class', 'exception_class', 'Each observed exception site must detect a subclass with unchanged text.'),
        ('authored_exact_diagnostic_text', 'diagnostic_text', 'Each observed exception site must detect a changed full message; another strong assertion does not cover this site.')):
        records = [dict(method=r['method'], site=r['site'], **r['trials'][key]) for r in sites]
        report(name, added['passed'] and normal and len(sites) >= 4 and all(r['detected'] for r in records),
            meaning + ' Expected failures in these separate intentional-fault executions satisfy sensitivity, not failure of the real library.',
            evaluated_sites=len(records), undetected_sites=[dict(method=r['method'], site=r['site']) for r in records if not r['detected']],
            site_observations=records)
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
        'The preserved document executes as standalone __main__ with the candidate import; prose requires independent review.',
        namespace='__main__', failed=ordinary.failed, attempted=ordinary.attempted, runner_output=stream.getvalue())
