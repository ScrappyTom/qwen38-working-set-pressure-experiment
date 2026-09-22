# Bounded independent source review

22 September 2026. A separate read-only reviewer inspected the local task adapter,
report API, qualifier and tests against the original checker and shared capture/
decision interfaces. The reviewer ran no tests/checkers, made no edits and did
not audit the whole repository or certify native/model readiness.

The review found the original acceptance calculation retained, full suite
observation capture placed before reduction, correct original-parser comparison
meaning, explicit 1 MiB candidate allowance, reference isolation and source sealing.

Two boundary findings were addressed before closure:

- JSON-escaped unpaired surrogate strings could pass shape recognition and then
  fail UTF-8 projection. The local validator now declines these strings; raw
  captured output and actual execution status remain available. Qualification 003
  first exercises this case; 004 retains it.
- A failed structured report followed by exit zero could lose its explicit
  disagreement annotation when the satisfied execution row was filtered out.
  `reported_passed` and `report_execution_consistent` now survive at the top level
  alongside the actual exit-based `passed`. Qualification 004 exercises both
  disagreement directions without rewriting the execution outcome.

The reviewer read the corrections and IMPLEMENTATION.md afterward and reported
no remaining material concern within this bounded scope. The 20-test result and
executed qualifications are the implementation agent's evidence, not executions
independently repeated by the reviewer. Native decoding/admission, source discovery,
broad-selection recovery, completed work and model behavior remain open gates.

The parent subsequently reviewed the full adapter and identified the missing
runner diagnostic for an unexpected-success outcome without structured failure
traces. The implementation added that bounded exact fallback and corrected the
method/subtest count wording. Qualification 005 and the 21-test pass are recorded
in IMPLEMENTATION.md. This last case was requested by the parent, not independently
executed or re-reviewed by the read-only subreviewer above.
