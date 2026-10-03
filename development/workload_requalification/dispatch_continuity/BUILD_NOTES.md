# Running engineering notes

The published 9e933217 plan precedes implementation. No model calls yet.

The exact parent source and original class were inspected directly. Local probes
of the exact GH-30017 merged source reproduce stale virtual dispatch for both
union forms; a manual clear supplies a discriminating observation. These are
evaluator probes, not Qwen performance or an upstream issue-discovery claim.

The first CPU route (cpu-route-001) is preserved unsuccessful. The checker harness
omitted the upstream class's imported `itertools.permutations`, causing two
NameErrors among its 24 original methods. The source contribution, independent
feature checks and four reference regressions passed; this was an apparatus
error. Add the original imported helper to the execution namespace; do not
change upstream code/tests to satisfy the erroneous harness. Raw complete
observations and following model-facing views preserve both diagnostics.

Before that route, schema inspection corrected evaluator script argument names
(`expected_candidate_id`, `new`). No such invalid operation was executed or
attributed to Qwen. The production schema remains unchanged.

The documentation harness must bind the candidate module during example execution,
including `import functools` inside an example. Merely supplying a candidate
global before such an import would execute installed Python's library instead.
This is qualified explicitly; no successful example may stand in for current
candidate verification if it ran a different implementation.

The two job texts, fixed before exposure, deliberately allow a first contribution
to solve the later dynamic case already. Such a result remains useful and does
not require introducing a fault to manufacture recovery. Second-job source
release is declared evaluator intervention, not natural pressure.

Seven focused CPU checks now pass (1.722 seconds in the recorded console run).
Early unit attempts exposed test-fixture mistakes: omitted import bootstrapping,
missing historical observation directories, a representation-escaped diagnostic
comparison, and an attempted no-op edit where a changed edit was needed to test
authority. Production source guards and diagnostic text were retained. The
independent dynamic checker now compares actual stable return values before
function identity, so primary failure reports show the useful discrepancy rather
than only function memory addresses.

Native preparation001 qualified 44 forms, eight scripted decisions, 5,021 initial
tokens and a maximum 13,657-token next input, with zero completions and 367 MiB
minimum free GPU memory. Full initial input review found the inherited phrase
"original public checker" inappropriate for a new checker and especially the
later new job. Preparation001 remains exact, unexposed and superseded. A narrow
task reference now names this job's registered checker and the meaning of baseline
regression failure explicitly. Successor002 also binds the CPU fixture bytes used
by the transition tests and resolves inherited CLI paths before binding them.
No host-core or model/runtime policy changed. Requalify before exposure.
