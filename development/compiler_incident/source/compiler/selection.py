import ast


def selected_functions(module, names):
    available = {node.name for node in module.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if names is None:
        return available
    if isinstance(names, str):
        raise ValueError("function names must be a sequence, not one string")
    requested = set(names)
    if not requested <= available:
        raise ValueError("unknown selected function")
    return requested
