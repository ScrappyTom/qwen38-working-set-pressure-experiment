"""Behavioral contract checks, independent of the calculation donor.

The preparation builder supplies EXPECTED_REPORT from the exact captured trees.
That value is grader-side evidence, never a diagnostic answer or candidate file.
"""
import ast
import json
import math
from pathlib import Path

from compiler.api import optimize


CASES = []


def case(name):
    def register(function):
        CASES.append((name, function))
        return function
    return register


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def compiled(source, functions=None):
    tree = optimize(source, functions)
    require(isinstance(tree, ast.Module), "optimize must return an AST module")
    namespace = {}
    exec(compile(tree, "contract-example", "exec"), namespace)
    return tree, namespace


for expression, argument, expected in (
    ("-x", 7, -7), ("-x", -4, 4), ("-x", 0.0, -0.0),
    ("+x", True, 1), ("-3", None, -3), ("-(x + 2)", 5, -7),
    ("-(-x)", 9, 9), ("+(-x)", 9, -9), ("2 * -x", 3, -6),
    ("not x", 0, True), ("~x", 5, -6), ("-2.5", None, -2.5),
):
    @case("numeric " + expression + " at " + repr(argument))
    def numeric(expression=expression, argument=argument, expected=expected):
        _, namespace = compiled("def f(x):\n    return " + expression + "\n")
        actual = namespace["f"](argument)
        require(type(actual) is type(expected) and actual == expected, "incorrect value or type")
        if isinstance(expected, float) and expected == 0:
            require(math.copysign(1, actual) == math.copysign(1, expected), "zero sign changed")


for literal in ("3", "2.5", "0", "0.0"):
    @case("required literal-plus folding " + literal)
    def fold(literal=literal):
        tree, namespace = compiled("def f():\n    return +" + literal + "\n")
        expression = tree.body[0].body[0].value
        require(isinstance(expression, ast.Constant), "literal unary plus was not folded")
        expected = ast.literal_eval(literal)
        require(type(namespace["f"]()) is type(expected) and namespace["f"]() == expected,
                "literal value or type changed")


@case("custom plus and minus dispatch")
def dispatch():
    source = """events = []
class Operand:
    def __pos__(self):
        events.append('pos')
        return 'positive result'
    def __neg__(self):
        events.append('neg')
        return 'negative result'
def f(x):
    return +x, -x
"""
    _, namespace = compiled(source)
    actual = namespace["f"](namespace["Operand"]())
    require(actual == ("positive result", "negative result") and namespace["events"] == ["pos", "neg"],
            "custom unary operations were skipped or duplicated")


@case("unary exception propagation")
def exceptions():
    _, namespace = compiled("def f(x):\n    return -x\n")
    try:
        namespace["f"]("unsupported")
    except TypeError:
        return
    raise AssertionError("unsupported operand must still raise TypeError")


@case("side effect evaluated once")
def effects():
    _, namespace = compiled("calls=[]\ndef g():\n    calls.append(1)\n    return 3\ndef f():\n    return -g()\n")
    require(namespace["f"]() == -3 and namespace["calls"] == [1], "wrong operand evaluation")


@case("explicit scope and unchanged module statements")
def selection():
    source = "K=-3\ndef f():\n    return +4\ndef g():\n    return +5\n"
    original = ast.parse(source)
    tree, namespace = compiled(original, ["g"])
    require(ast.dump(tree.body[0]) == ast.dump(original.body[0]), "module statement changed")
    require(ast.dump(tree.body[1]) == ast.dump(original.body[1]), "nonselected function changed")
    require(isinstance(tree.body[2].body[0].value, ast.Constant), "selected function not optimized")
    require(namespace["K"] == -3 and namespace["f"]() == 4 and namespace["g"]() == 5, "scope values changed")


@case("empty scope")
def empty_scope():
    source = "def f(x):\n    return -x + +3\n"
    require(ast.dump(optimize(source, [])) == ast.dump(ast.parse(source)), "empty scope changed the tree")


@case("input tree is independent")
def independent_tree():
    original = ast.parse("def f():\n    return +3\n")
    before = ast.dump(original, include_attributes=True)
    result = optimize(original)
    require(ast.dump(original, include_attributes=True) == before, "original tree mutated")
    result.body[0].name = "renamed"
    require(original.body[0].name == "f", "returned tree shares mutable source nodes")


@case("default scope includes all top-level functions")
def all_functions():
    tree, namespace = compiled("def f():\n    return +1\ndef g():\n    return +2\n")
    require(all(isinstance(node.body[0].value, ast.Constant) for node in tree.body), "default scope incomplete")
    require((namespace["f"](), namespace["g"]()) == (1, 2), "default values changed")


@case("async function scope")
def async_function():
    tree, namespace = compiled("async def f():\n    return +4\n", ["f"])
    require(isinstance(tree.body[0].body[0].value, ast.Constant), "selected async function not optimized")
    coroutine = namespace["f"]()
    try:
        coroutine.send(None)
    except StopIteration as completed:
        require(completed.value == 4, "async return changed")
    else:
        raise AssertionError("unexpected suspension in literal-return coroutine")
    finally:
        coroutine.close()


@case("invalid selection and input remain rejected")
def invalid_inputs():
    for source, names in (("def f():\n    return 1\n", ["missing"]),
                          ("def f():\n    return 1\n", "f"), (42, None)):
        try:
            optimize(source, names)
        except ValueError:
            continue
        raise AssertionError("invalid input or selection was accepted")


@case("incident report agrees with captured builds")
def report():
    actual = json.loads(Path("reports/incident.json").read_text(encoding="utf-8"))
    require(isinstance(actual, dict) and isinstance(actual.get("builds"), list), "report must contain a builds list")
    rows = actual["builds"]
    require(all(isinstance(row, dict) and isinstance(row.get("capture"), str) for row in rows), "each build needs a capture handle")
    by_capture = {row["capture"]: row for row in rows}
    require(len(by_capture) == len(rows) and set(by_capture) == {r["capture"] for r in EXPECTED_REPORT["builds"]},
            "report must cover each emitted capture exactly once")
    for expected in EXPECTED_REPORT["builds"]:
        row = by_capture[expected["capture"]]
        detail = "observed comparison is incomplete or incorrect for " + expected["capture"]
        require(row.get("changed_functions") == expected["changed_functions"], detail)
        change = row.get("first_change")
        require(isinstance(change, dict) and change.get("function") == expected["first_change"]["function"], detail)
        for field in ("before", "after"):
            text = change.get(field)
            require(isinstance(text, str), detail)
            require(ast.dump(ast.parse(text.strip(), mode="eval")) ==
                    ast.dump(ast.parse(expected["first_change"][field], mode="eval")), detail)


failures = []
for name, function in CASES:
    try:
        function()
    except Exception as error:
        failures.append(name)
        print("FAIL " + name + ": " + type(error).__name__ + ": " + str(error))
print(str(len(CASES) - len(failures)) + "/" + str(len(CASES)) + " contract cases passed")
if failures:
    raise SystemExit(1)
