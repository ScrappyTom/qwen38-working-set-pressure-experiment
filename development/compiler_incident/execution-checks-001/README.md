# Execution preparation checks

All commands used Python 3.12 with `PYTHONPATH=src`, `-B` and `-X utf8`. No live
model endpoint was contacted. Mocked responses are explicitly labeled throughout.

- `compiler-execution.txt`: 21 focused tests passed in 229.733 seconds. An earlier
  development invocation had also passed the then-existing 19 tests; its console
  was not retained as a separate file and is not added to the coverage count.
- `runtime-lifecycle.txt`: three tests passed after adding the final runner's
  shutdown-result guard: failed shutdown, sealed failure and reserved/unauthorized
  attempt prevention. Two repeat earlier tests; the third brings distinct passing
  coverage to 22. No other production code changed after the 21-test run.
- `shared-response-execution.txt`: the historical interface-comparison suite
  refused `setUpClass`, running zero tests. Its preparation still expects the
  earlier `src/working_set_exp/hierarchical_p0.py` identity, superseded by recorded
  maintenance. Preserve this unsuccessful invocation; it is not coverage, a new
  host defect or a reason to edit the consumed historical package.
- `rehearsal-console.txt`: the final frozen engine, real tools, exact prior native
  inputs and 34 mocked answers completed both cells in their opposite branch orders.
- `rehearsal-verification-console.txt` and `REHEARSAL_VERIFICATION.json`: a separate
  replay verified the exact input/output/state sequence and the rehearsal seal.

Reproducible source is in `tests/test_compiler_execution.py`,
`scripts/rehearse_compiler_execution.py` and
`scripts/verify_compiler_execution_rehearsal.py`. The latter two scripts deliberately
write new artifacts exclusively; do not rerun them over the sealed directories.
Synthetic-size tests isolate allowance and failure behavior; only the cache-matched
rehearsal uses the previously qualified native counts. Neither is model-performance
evidence or a new capacity qualification for generation.
