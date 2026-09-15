# Actual saved tests and documentation

Reviewed the exact starting/final candidate files, both emitted patches, the task
contract, relevant parser implementation and actual checker behavior. The
[actual diff](ACTUAL.patch) is derived from those two candidates. No actor artifact
is edited or repaired during assessment.

The library and all other candidate files are byte-identical to the start. The test
and doc changes are insertions preserving earlier work, including the continuation
regression, transport tests and prior documentation. The final candidate is
`4fcb261b9c8d30ed0a10690a3db251d3b51f74e2a3698d2e29fbf4a294d8ad73`.

## New tests: useful paths, one wrong value, incomplete exact assertions

The three added methods obtain real lookup exceptions under explicit Basic and
Extended interpolation, including a missing cross-section option. The helper
checks option/section/reference and compares copied/deep-copied/pickled exception
state. The two passing methods exercise raw retrieval and successful resolution
after supplying the missing setting. These are meaningful behavior checks, not
merely direct exception construction or accepted output syntax.

The cross-section method asks for option r in section a whose value is `${b:gone}`.
Section b exists but gone does not. The actual Extended raise site passes
`":".join(path)`, so the exception reference is `b:gone`, while option/section remain
r/a. The new method incorrectly expects `gone` and fails before its transport,
raw and repaired-lookup assertions execute.

The source of that behavior is the saved Lib/configparser.py, lines 490–492;
the exception constructor at 267–275 preserves the supplied reference and stores
args as `(option, section, rawval, reference)`. That implementation was never in
Qwen's input during this attempt. The visible old direct-construction example
does not determine what the real raise site passes.

Additional contract omissions are visible directly in the new helper. isinstance
does not assert the exact class, and restored objects have no explicit exact-class
assertion. The original args are not compared with the tuple expected for the
lookup; restored equality only checks preservation. A truthy message is not an
exact expected diagnostic. Those omissions remain even in passing methods.

[ARTIFACT_CHECK.json](ARTIFACT_CHECK.json) is one independent postclosure invocation
of the unchanged public checker, never delivered to Qwen:

| Assessment | Actual result |
|---|---|
| Saved prior suite | 359 tests, five skips, no failures/errors |
| Edited suite | 362 tests, five skips, one failure, no errors |
| Existing backport contract | Eight cases pass |
| Three new methods under path instrumentation | One cross-section failure |
| Existing work preserved | True |
| Overall public check | False |

The path instrument's empty Extended transport set has a specific scope: it counts
Extended transport for references containing a colon. It does not mean that the
passing same-section Extended test skipped copying or pickle. Basic and same-section
Extended raw/resolved calls are also actually present. Do not replace direct source
reading with an overbroad interpretation of that aggregate.

All four restoration mutations produce failures, but the unmodified new suite already
has a failure. The reported traces additionally show the previously passing Basic
method failing on each mutated field, so there is useful fault sensitivity. This
does not turn the whole contribution or unexecuted cross-section transport into
qualified coverage. No historical or preparation score is revised.

## Documentation: two wrong outputs and one false attribute claim

The addition is placed under the exact exception directive and preserves adjacent
documentation. Its explicit interpolation policies, raw bypass, supplying the
missing setting and nested doctest layout are appropriate. Execution uses the exact
accepted C08 replacement text and the exact final parser, not a corrected example
or the review machine's standard-library parser.

[DOCUMENTATION_CHECK.json](DOCUMENTATION_CHECK.json) records sixteen attempted
examples with two failures:

1. Basic output invents a message beginning “There is no section named”. The actual
   diagnostic begins “Bad value substitution” and identifies option key, section sec,
   reference missing and raw value `val %(missing)s`. The saved source constructor
   establishes that message; the example's section in fact exists.
2. Extended cross-section output expects `r a gone`; the actual output is
   `r a b:gone`. This repeats the untested assertion in the new test class.

The prose also lists rawval as an exception attribute. It is an argument retained
in args[2], not an instance attribute. The recorded direct probe confirms
hasattr(error, "rawval") is false. The constructor supplies message, option,
section and reference. Supplying a constructor argument is not evidence of a
same-named stored attribute.

These examples were executed together as the saved addition supplies its common
import; this is not a full CPython documentation build. The raw and corrected lookup
examples succeed, but the incorrect outputs and attribute claim make the requested
documentation inaccurate. Mechanical detection of an added doc block would not
establish semantic quality; the frozen task already reserves direct review for it.

## Evidence and decision

[analyze.py](analyze.py) reconstructs the exact final candidate, computes the diff
and metrics, and performs the postclosure checker assessment. Its checker session
is isolated and adds no model feedback. [check_docs.py](check_docs.py) executes the
actual examples and records exact source bindings. Both outputs identify their
postclosure scope and zero model requests. Their write-once outputs are preserved.

The saved tests are a proposed contribution with partially useful coverage, not
independent evidence for their own expected values. C08 explicitly cites them as
verification; the same unsupported value then appears in documentation. Persistence
has worked mechanically while evidential status is misused. The next development
question concerns obtaining real support or verification before reusing a proposed
expectation, not correcting the library to satisfy the actor's mistaken tests.
