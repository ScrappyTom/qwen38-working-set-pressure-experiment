# Running notes

The first three-test CPU run had one fixture failure: it expected task text in the
historical mutable-state snapshot. Direct inspection shows task is configuration,
not a snapshot field. The replacement assignment is in session.task and the actual
view. Correct the test to inspect that input boundary; do not alter production
snapshot semantics just to satisfy the mistaken expectation. Preserve TESTS-001.
No model/native/check calls occurred in this failed test run.
