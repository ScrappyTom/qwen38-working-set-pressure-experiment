"""Offline weak-assertion fixture correction only; never an actor input."""
import ast


def correct(source):
    lines = source.splitlines(keepends=True)
    edits = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.With) or len(node.items) != 1:
            continue
        item = node.items[0]
        call = item.context_expr
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr == 'assertRaises' and len(call.args) == 1
                and isinstance(call.args[0], ast.Name) and call.args[0].id == 'RuntimeError'):
            continue
        captured = item.optional_vars
        assert captured is None or isinstance(captured, ast.Name)
        name = captured.id if captured else 'caught'
        if captured is None:
            old = lines[node.lineno-1]
            assert old.rstrip().endswith(':')
            edits.append((node.lineno-1, node.lineno, old.rstrip()[:-1] + ' as caught:\n'))
        indent = ' ' * node.col_offset
        addition = indent + f'self.assertIs(type({name}.exception), RuntimeError)\n'
        if captured is None:
            # Both actual saved explicit-registration methods name these classes.
            addition += indent + f'self.assertEqual(str({name}.exception), f"Ambiguous dispatch: {{AlphaBase}} or {{BetaBase}}")\n'
        edits.append((node.end_lineno, node.end_lineno, addition))
    assert len([e for e in edits if 'self.assertIs(type(' in e[2]]) == 4
    for start, end, text in sorted(edits, reverse=True):
        lines[start:end] = [text]
    result = ''.join(lines)
    ast.parse(result)
    return result


def place_in_old_class(source):
    tree = ast.parse(source)
    old = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'LateVirtualRegistration')
    extra = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name != old.name]
    assert len(extra) == 1
    lines = source.splitlines(keepends=True)
    methods = [n for n in extra[0].body if isinstance(n, ast.FunctionDef)]
    inserted = '\n' + ''.join(''.join(lines[n.lineno-1:n.end_lineno]) + '\n' for n in methods)
    return ''.join(lines[:old.end_lineno]) + inserted + ''.join(lines[extra[0].end_lineno:])
