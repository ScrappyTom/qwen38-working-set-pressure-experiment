# Implementation notes

The owner-approved coding direction and this folder's PLAN were published in
f655a1c6 before implementation. Frozen host modules, task adapters and the completed
run remain unchanged. No model call has been made for this extension.

CPU qualification001 passed seven cases and failed the selection-replacement case.
Direct inspection of the rejected operation found the review script used
`saved_results`, while the actual work_on schema requires `results`. The supplied
schema and earlier qualified route agree. Corrected the test request, not the
production host. The first source-copy attempt and qualification002 hit a Windows
path-length limit because the full repository-relative prefix was repeated inside
an already deep output directory. Qualification002 did not run any tests. Its
failure and exact pre-test sources remain in cpu-qualification-002. Snapshots now
use paths relative to this small package, with an explicit mapping in RESULTS.

The copy failure happened before the original test source was saved and before its
field-name correction. That source was reconstructed by reversing the exact two-line
test correction, and its SHA256 matched qualification001's recorded pre-change hash.
All original source bytes are now preserved alongside the failed RESULTS, including
the partial long-path copy. This correction concerns reviewer reproducibility;
no model or frozen run evidence was changed or reclassified.

The new projection uses the existing optional page setting and shared byte budget,
including the added recent-row bytes. It exposes only the actual last six operations,
preserves exact search pages and original applicability, and returns the old recovery
view exactly at the no-detail fallback. Ordinary rendering is unchanged. Existing
tool descriptions already describe bounded historical navigation without restricting
it to ordinary mode, so no new wording or response schema is introduced.
