# Saved work and actual verification

The initial candidate is
`2921cbc8a115c86871a11f8eaea929c3d48a8e4d2bb2ca03bf48971c36cf15cd`.
The stopped candidate is
`4462a3bc4a867c1583abd1e1190e39f9d47fde0a94430c6dc370438d8929e8b7`.
The [exact additive patch](saved-contribution.patch) comes from those saved candidates,
not from private thinking. C11 is its only edit; it survives inspection and closure.

Only `Lib/test/test_urlparse.py` changes. Its saved SHA-256 is
`33ce8bfc9e6c253fd75de1f1b0aa79e1de6ad7d2c3b5cc0fcc0d73db2a448e53`.
The diff inserts 72 lines in one new method,
`UrlParseTestCase.test_port_access_boundary_and_errors`. All prior method source is
unchanged. All five other files, including library source and documentation, are
byte-identical to the starting candidate. `assess_run.py` records these comparisons.

## Useful coverage and missing requirement

The method obtains result objects through both urlsplit and urlparse. It covers
text and ASCII bytes for absent/empty ports, zero, 65535, 65536, negative values
and noninteger text, and text-only non-ASCII decimal digits. Construction occurs
outside the expected-error context; errors are expected when accessing `.port`.
Expected values, complete argument tuples and diagnostic strings agree with the
inspected implementation. The eventually correct empty-port expectation follows
the normalization source the model reacquired in C09.

The task also requires the **exact** exception class. `assertRaises(ValueError)`
accepts subclasses; the saved method adds no exact-type assertion. The fault checker
replaces ValueError with `DifferentValueError(ValueError)` while preserving arguments,
and the new test still passes. This is a concrete coverage defect, not a stylistic
preference or merely the absence of final submission.

## Executed result, not inferred correctness

The declared tests check CHK-0020 is bound to the saved successor and checker
`dcc3b97c061b78e64a7fe2f351d3a725aefbbffa129badca8a863f4295bc30eb`.
Its actual preserved output reports:

- 72 prior tests and 73 edited-suite tests pass, without skips or errors.
- The new method exercises every required path in the normal observation run.
- Six of seven injected faults are detected. Only `error_class` escapes.
- Existing work and documentation are preserved; overall `tests_passed=false`
  and `passed=false`.

Failing under `error_arguments`, `error_message`, `eager_validation`, `empty_port`,
`zero_port` and `maximum_port` is the desired detection result. Later missing paths
after an assertion stops one of those fault runs are not additional acceptance
requirements. An uncaught error under eager validation also counts as detection.
The checker does not require every mutation run to finish every access.

The full 8,402-byte stdout and empty stderr are preserved. Stdout SHA-256 is
`e07c08eb876cefc3093ea5f2d4474e8ca3dfc65ce8f702a6151dd429c34ff0fd`.
The post-run assessment reads this actual observation; it does not silently rerun
the checker or promote ordinary suite success into a task pass.

No new documentation examples or explanation were saved. No public-scope check
or submission occurred. C13's many private replacement drafts are not artifact
versions and were not executed or evaluated as proposed model work. This is useful
partial regression coverage, with a demonstrated missing requirement and unfinished
documentation, rather than a completed contribution.
