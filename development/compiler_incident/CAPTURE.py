"""Run from the candidate source directory by the offline capture builder."""
import ast
import json
import sys

from compiler.api import optimize


source = sys.stdin.read()
original = ast.parse(source)


class FixedRandom:
    def random(self):
        return 0.5


def evaluate(tree, function):
    namespace = {}
    exec(compile(tree, "captured-calculation", "exec"), namespace)
    args = (0.01, 0.0, 1.0) if function == "_normal_dist_inv_cdf" else (FixedRandom(), 2.0, 2.0)
    try:
        value = namespace[function](*args)
        return {"kind": "returned", "type": type(value).__name__, "value_repr": repr(value)}
    except Exception as error:
        return {"kind": "raised", "type": type(error).__name__, "message": str(error)}


records = [{"record_kind": "parsed input module", "ast_dump": ast.dump(original),
            "reference_calls": {name: evaluate(original, name) for name in ("_normal_dist_inv_cdf", "weibullvariate")}}]
for build, functions, called in (("BUILD-A", ["_normal_dist_inv_cdf"], "_normal_dist_inv_cdf"),
                                  ("BUILD-B", ["_normal_dist_inv_cdf", "weibullvariate"], "weibullvariate")):
    emitted = optimize(original, functions)
    records.append({"record_kind": "emitted module", "build": build,
                    "compile_request": {"functions": functions}, "ast_dump": ast.dump(emitted),
                    "called_function": called, "observed_call": evaluate(emitted, called)})
print(json.dumps(records, sort_keys=True, separators=(",", ":")))
