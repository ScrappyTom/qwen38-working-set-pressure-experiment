# Recognize delivered historical capture receipts

MINT001 directly exposes a reporting defect: exact legacy capture bytes appear in
complete saved-result pages, but imported_observations reports them absent. The
modern receipt recognizer is being used as though it described every preserved
representation. Retain original envelopes and exact archive; fix the projection.

1. Extend the bound-capture identity check to the preserved legacy envelope. Require
   accepted=true, a known original OBS handle, exact raw body, size and fingerprint.
   The body's original candidate binding is already validated by imported custody.
   Do not infer present validity from the word current inside old source text.
2. Reuse that one check for visibility and replacement of retained duplicate
   acquisitions. Require complete authenticated outer pages before inspecting their
   contents. Partial pages, wrong handles/bodies/bindings and incidental text remain
   insufficient. A capture supplies no source-edit or current-check authority.
3. Test the actual MINT C02/C03 state, modern and legacy receipts, corrupted/partial
   pages, release/restoration and authority. Qualify actual native inputs and the
   normal capture/retrieval transition. No model inference is needed for this fix.
4. Preserve SABLE preparation001 unexecuted. Declare and prepare successor002 under
   corrected source; keep task, world, seed, allowance, checker and reasoning fixed.
   Replay and inspect its full input before publishing and one uncoached run.

Do not rerun MINT merely to remove this harmless-on-observed-actions discrepancy.
Do not invent new account or retention policies. Historical results stay historical.
The governance lesson is that truthful presentation must recognize supported saved
representations, not silently make a newer transport format the definition of
what evidence is present. Availability and applicability remain separate facts.
