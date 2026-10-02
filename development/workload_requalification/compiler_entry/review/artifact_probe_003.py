"""Post-closure reviewer probes; not actor/checker/model-performance evidence."""
import ast
import copy
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
ENTRY = ROOT / 'development/workload_requalification/compiler_entry'
RUN = ENTRY / 'run-003'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def load_dump(text):
    """Interpret the frozen AST-constructor notation, with no executable names."""
    def node(value):
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            constructor = getattr(ast, value.func.id, None)
            if not isinstance(constructor, type) or not issubclass(constructor, ast.AST) or value.args:
                raise ValueError('not AST constructor notation')
            fields = {key.arg: node(key.value) for key in value.keywords}
            if len(fields) != len(value.keywords):
                raise ValueError('repeated field')
            if fields.get('type_params') == [] and 'type_params' not in constructor._fields:
                fields.pop('type_params')
            if set(fields) - set(constructor._fields):
                raise ValueError('unknown AST field')
            return constructor(**fields)
        if isinstance(value, ast.List):
            return [node(x) for x in value.elts]
        return ast.literal_eval(value)
    return node(ast.parse(text, mode='eval').body)


def first_kind_change(before, after):
    if isinstance(before, ast.expr) and isinstance(after, ast.expr) and type(before) is not type(after):
        return {'before': ast.unparse(before), 'after': ast.unparse(after),
                'before_kind': type(before).__name__, 'after_kind': type(after).__name__}
    if isinstance(before, ast.AST) and type(before) is type(after):
        pairs = [(getattr(before, key), getattr(after, key)) for key in before._fields]
    elif isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        pairs = zip(before, after)
    else:
        return None
    for left, right in pairs:
        found = first_kind_change(left, right)
        if found:
            return found
    return None


def value_record(value):
    result = {'type': type(value).__name__, 'repr': repr(value)}
    if isinstance(value, float) and value == 0:
        result['zero_sign'] = math.copysign(1, value)
    return result


def main():
    assert (RUN / 'RESPONSE_SEAL.json').exists(), 'must not probe an active run'
    start, final = read(RUN / 'starting-candidate.json'), read(RUN / 'final-candidate.json')
    old = {f['path']: f for f in start['files']}
    files = {f['path']: f for f in final['files']}
    assert set(old) == set(files)
    for f in files.values():
        assert hashlib.sha256(f['content_utf8'].encode()).hexdigest() == f['sha256']
    result = {'scope': __doc__, 'python': sys.version, 'candidate_id': final['candidate_id'],
              'changed_files': [path for path in files if old[path]['content_utf8'] != files[path]['content_utf8']]}

    # Obtain exact capture bodies from the actual report-edit input, not inventory flags.
    wire = read(RUN / 'calls/C12-wire-request.json')
    view = json.loads(next(m['content'] for m in wire['messages'] if m['role'] == 'user'))['workspace']
    captures = {}
    for page in view['working_set']['saved_results']:
        if page['offset'] != 0 or page['next_offset'] is not None:
            continue
        receipt = json.loads(page['exact_utf8'])
        if receipt.get('kind') != 'imported_observation':
            continue
        raw = receipt['content_utf8'].encode()
        assert len(raw) == receipt['size_bytes']
        assert hashlib.sha256(raw).hexdigest() == receipt['sha256']
        captures[receipt['handle']] = json.loads(raw)
    assert set(captures) == {'OBS-0001', 'OBS-0002', 'OBS-0003'}
    sealed = read(ROOT / 'development/compiler_incident/preparation-001/captures.json')
    assert list(captures.values()) == sealed
    original = load_dump(captures['OBS-0001']['ast_dump'])
    functions = [f for f in original.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))]
    comparisons = []
    for handle in ('OBS-0002', 'OBS-0003'):
        emitted = load_dump(captures[handle]['ast_dump'])
        emitted_functions = {f.name: f for f in emitted.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}
        changed = [f for f in functions if ast.dump(f) != ast.dump(emitted_functions[f.name])]
        first = next(({'function': f.name, **x} for f in changed
                      if (x := first_kind_change(f, emitted_functions[f.name]))), None)
        comparisons.append({'capture': handle, 'changed_functions': [f.name for f in changed], 'first_change': first})
    report = json.loads(files['reports/incident.json']['content_utf8'])
    normalized = {'builds': [{**r, 'first_change': {k: v for k, v in r['first_change'].items() if not k.endswith('_kind')}}
                            for r in comparisons]}
    assert report == normalized
    result['captured_tree_comparison'] = comparisons

    # Execute the exact saved package in an isolated temporary directory.
    with tempfile.TemporaryDirectory(prefix='compiler003-review-') as folder:
        scratch = Path(folder)
        for path, f in files.items():
            destination = scratch / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(f['content_utf8'], encoding='utf-8', newline='')
        sys.path.insert(0, str(scratch))
        optimize = importlib.import_module('compiler.api').optimize
        expressions = ('+True', '-True', '+(+True)', '-(-True)', '+(-True)', '-(+True)',
                       '-0.0', '+(-0.0)', '-(-0.0)', '-(-(+0.0))', '+1j', '-1j',
                       '-(-3)', '+(-2.5)', '~(-3)', 'not -0')
        rows = []
        for expression in expressions:
            source = 'def f():\n    return ' + expression + '\n'
            original_tree = ast.parse(source)
            before_dump = ast.dump(original_tree, include_attributes=True)
            optimized_tree = optimize(original_tree)
            assert ast.dump(original_tree, include_attributes=True) == before_dump
            values = []
            for tree in (original_tree, optimized_tree):
                namespace = {}
                exec(compile(tree, '<reviewer-probe>', 'exec'), namespace)
                values.append(value_record(namespace['f']()))
            assert values[0] == values[1]
            rows.append({'expression': expression, 'value': values[1]})
        result['parsed_expression_equivalence'] = rows

        dispatch_source = '''events=[]
class I(int):
    def __pos__(self):
        events.append('pos')
        return 'positive'
    def __neg__(self):
        events.append('neg')
        return 'negative'
def f(x):
    return +x, -x
'''
        dispatch = []
        for tree in (ast.parse(dispatch_source), optimize(dispatch_source)):
            namespace = {}
            exec(compile(tree, '<runtime-subclass>', 'exec'), namespace)
            dispatch.append({'value': namespace['f'](namespace['I'](3)), 'events': namespace['events']})
        assert dispatch[0] == dispatch[1]
        result['runtime_numeric_subclass_dispatch'] = dispatch[1]

        # This deliberately manufactured Constant is invalid Python AST input.
        # It exposes the exact-vs-isinstance boundary; it is not parsed-literal failure.
        events = []
        class I(int):
            def __neg__(self):
                events.append('neg during optimize')
                return -99
        malformed = ast.parse('def f():\n    return -3\n')
        malformed.body[0].body[0].value.operand.value = I(3)
        try:
            compile(malformed, '<malformed-before>', 'exec')
        except TypeError as error:
            before = str(error)
        else:
            raise AssertionError('probe input unexpectedly accepted by Python')
        rewritten = optimize(malformed)
        namespace = {}
        exec(compile(rewritten, '<malformed-after>', 'exec'), namespace)
        result['malformed_AST_boundary'] = {'original_compile': before, 'events': events,
                                          'optimized_return': namespace['f'](),
                                          'classification': 'invalid Constant payload; outside ordinary parsed Python literals'}
        sys.path.pop(0)
    destination = Path(__file__).with_name('ARTIFACT_PROBES-003.json')
    destination.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
