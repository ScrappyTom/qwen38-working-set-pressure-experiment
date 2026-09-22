# Running implementation notes

22 September 2026. Preserve these as development observations for governance.

- The original receipt C05 was accepted under a documented terminal prose form.
  Its absence of an operation did not express a clear request to abandon work.
  Correct the task lifecycle at schema, native grammar, visible contract and host
  validation together; never infer the missing operation from prose or thinking.
- The operational wrapper derives its forms from the existing schema and changes
  only the outer discussion-only alternative. Retained operations keep their
  existing argument definitions and source/check protections. A valid account-only
  update remains possible and is not automatically counted as useful progress.
- A continuation must preserve request provenance as well as candidate/history.
  Restoring five consumed requests while resetting the runner to zero would either
  violate its consistency guard or silently grant time and duplicate account
  request references. The isolated loop uses cumulative C06 onward and separately
  records new costs. First-input qualification also needs to run at that offset.
- Qualification check accounting must use preserved actual observations, not the
  number of successfully completed script labels. An operation may execute before
  its later feedback fails. Record starts lacking outcomes separately.
- The scripted reference repair remains outside the actor input. It proves the
  unchanged application/check route remains executable; it does not prove discovery
  or claim the actor would choose that route. The live continuation supplies no
  extra source, corrected account, repair or chosen next action.
- Keep this change separate from batched acquisition or custody-cost optimization.
  Their tradeoffs remain documented elsewhere and are not explanations for C05's
  documented prose-only termination.
- CPU-TESTS-002 preserves three synthetic transport failures caused by omitted
  explicit zero-cache fields and one wrong test expectation for the read payload's
  path (it is inside source). The fixtures were corrected after inspecting the
  production validator and actual CPU read result; production behavior was retained.
- Include the native grammar probe's pinned binary-identity JSON in the outer
  source closure, not only the native subpackage's internal binding list.
