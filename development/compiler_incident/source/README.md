# Selected-function optimizer

`compiler.api.optimize(source, functions=None)` parses a Python module and returns
an independent optimized AST. With `functions=None` it processes all top-level
functions. With a sequence of function names it processes exactly those functions.
Unknown names are rejected. Nonselected functions and module-level statements
must retain their structure. The input syntax tree is never modified in place.

The small optimizer may simplify unary signs applied to numeric literals. It must
at least eliminate unary plus on exact built-in integer and float literals in
selected functions. It must preserve Python's values, types, exceptions and
operator dispatch everywhere else, including negative zero and user-defined
unary operators. Constant folding is optional for other cases when equivalent.

Historical input and emitted trees are available in the observation directory.
They are Python 3.12 `ast.dump` records with field names, excluding source-location
attributes. Each emitted tree describes a complete module, including functions
outside that build's selected scope. These captures precede the repair session;
changing this checkout does not change what those builds emitted.

Complete `reports/incident.json` using this structure:

    {"builds": [
      {"capture": "<emitted-tree handle>",
       "changed_functions": ["<function name>", "..."],
       "first_change": {"function": "<name>",
                        "before": "<original expression>",
                        "after": "<emitted expression>"}}
    ]}

Include every captured emitted build. Compare with the captured original tree.
List all top-level functions whose AST changed, in source order. Locate the first
expression whose node kind changed, traversing functions in source order and
their fields in normal Python AST order. Express its original and emitted forms
as ordinary Python expressions (equivalent parentheses/spacing are accepted).
This is the incident work product, not a claim that the repaired candidate was
used by the historical builds. The public check validates the optimizer contract
and the report; its report failures do not supply the missing incident facts.
