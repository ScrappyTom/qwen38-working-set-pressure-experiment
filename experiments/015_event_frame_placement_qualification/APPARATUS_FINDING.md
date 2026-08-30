# Experiment 015 Apparatus Finding

## Disposition

Valid development-only live placement qualification.

The run completed all eight authorized sacrificial branches with sixteen HTTP completion calls. There were no retries, repairs, rescues, capacity denials, parser failures, tool rejections, candidate-binding failures, checker failures, or server-lifecycle failures.

## Exact execution boundary

The live run used remote-synchronized preparation commit `0a41d22f67cbf8be3f37137df60ffbbcbc970882`, package `E15PKG-b0c062375dd05c1eaf360a34a4cd7dbc58df7674f085cb675ebd0ffbc38acfd1`, executable closure `6508aec8c1029a35e154874847f7d3bf11c5a655bc41b288467c837881d6e3eb`, authorization SHA-256 `6a6759f6467f72c247e020bec81d3c06754a5b7d4bf3b11e9d9cdce94deeef55`, and the frozen AD-IQ2_S actor/runtime.

Every first coding request, endpoint request, and rendered prompt matched its frozen package bytes before transport. Runtime and offline token counts matched on all sixteen calls. The dedicated server shut down and released port 18118.

## Response custody

The response tree was sealed before hidden grading. The seal is SHA-256 `2f83387e0ad24ecf96523f9ecbb88025c90fec72e4a374f57045b655198b6a7d`. All sealed files verify by path, byte length, and SHA-256. The external evidence root was copied byte-for-byte into `development_run`; the source and repository copies contained the same 1,396 files and 38,113,511 bytes at copy time.

Every branch contains:

- exact coding and endpoint requests;
- exact rendered prompt;
- raw endpoint response;
- exact assistant content;
- exact private reasoning output;
- strict parsed action;
- exact tool result;
- candidate snapshot and chained custody records;
- terminal branch summary and replay-verifiable record chain.

## No host defect affected behavior

Direct request and transcript review found no host defect that changed an outcome:

- both request placements contained the correct full task, active Phase-B step, completed Phase-A identity, current candidate, current P0 binding, observation identities, budgets, actions, and public check ID;
- each constructed event had the correct sequence, action, result binding, result size/hash, and resident/external status;
- the stale-check fixture preserved the old passed check as bound to predecessor candidate V1 and required a new current-candidate check on V2;
- every emitted check was executed against the stated current candidate and passed;
- every submit followed a passing current-candidate check;
- all eight terminal candidates passed post-seal hidden grading.

## Development-only limitation

These were already exposed donor cases mechanically advanced with known-good Phase-B mutations. This was intentional: the question was whether Qwen could interpret and close from the two progress placements, not whether it could discover the repair. The run cannot support a fresh-task quality or general efficiency claim.

The event representation also exposed exact action arguments and more structural result fields than the legacy compact receipt prefix. Therefore the two conditions were not a pure byte-for-byte placement ablation. That asymmetry did not invalidate the diagnostic comprehension question, but it prevents causal interpretation of the token, reasoning, or timing differences as placement effects alone.
