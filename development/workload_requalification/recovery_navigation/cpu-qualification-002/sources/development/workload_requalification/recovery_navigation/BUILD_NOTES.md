# Implementation notes

The owner-approved coding direction and this folder's PLAN were published in
f655a1c6 before implementation. Frozen host modules, task adapters and the completed
run remain unchanged. No model call has been made for this extension.

CPU qualification001 passed seven cases and failed the selection-replacement case.
Direct inspection of the rejected operation found the review script used
`saved_results`, while the actual work_on schema requires `results`. The supplied
schema and earlier qualified route agree. Corrected the test request, not the
production host. The failed RESULTS and all hash-matching tested source bytes are
preserved under cpu-qualification-001. Later CPU attempts snapshot their own source
bytes before execution; this change concerns audit reproducibility, not behavior.

The new projection uses the existing optional page setting and shared byte budget,
including the added recent-row bytes. It exposes only the actual last six operations,
preserves exact search pages and original applicability, and returns the old recovery
view exactly at the no-detail fallback. Ordinary rendering is unchanged. Existing
tool descriptions already describe bounded historical navigation without restricting
it to ordinary mode, so no new wording or response schema is introduced.
