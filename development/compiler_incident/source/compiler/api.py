import ast
import copy

from .selection import selected_functions
from .unary import UnarySimplifier


def optimize(source, functions=None):
    original = ast.parse(source) if isinstance(source, str) else source
    if not isinstance(original, ast.Module):
        raise ValueError("expected a module or Python source")
    result = copy.deepcopy(original)
    selected = selected_functions(result, functions)
    transform = UnarySimplifier()
    for index, node in enumerate(result.body):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in selected:
            result.body[index] = transform.visit(node)
    return ast.fix_missing_locations(result)
