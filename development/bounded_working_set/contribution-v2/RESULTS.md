# Corrected-host parser contribution: closed development attempt

The host delivered usable feedback and Qwen used work_on three times, but it saved
no tests or documentation. Eight accepted actions cost 160,354 generated tokens
and 177.407 model-request minutes. This is not a demonstrated improvement in task
completion. The correct starting library and all ten candidate files are unchanged.

The reviewer requested a graceful stop after examining C06/C07. Qwen repeatedly
treated partial current source as a partial serialized historical result, inferred
that editing might require complete files, and replaced useful regions with three
whole-file requests. The host returned broad prefixes, releasing the parser loop,
test tail and documentation exceptions. C08 had already been sent; it completed
normally before closure. This is an adaptive operator stop, not exhausted allowance,
a natural termination failure, or proof that Qwen could never recover.

| Call | Action | Input tokens | Generated tokens | Request seconds |
|---|---|---:|---:|---:|
| C01 | work_on: two sources, three saved results | 3,425 | 534 | 35.172 |
| C02 | read tests onward | 22,771 | 14,314 | 941.000 |
| C03 | search library | 23,789 | 20,724 | 1,373.531 |
| C04 | work_on: replace with seven ranges and check | 23,351 | 24,538 | 1,627.625 |
| C05 | read test helper | 22,762 | 25,320 | 1,675.172 |
| C06 | search tests | 23,803 | 21,298 | 1,411.625 |
| C07 | work_on: three files requested from start | 23,281 | 30,151 | 2,028.906 |
| C08 | search library | 22,781 | 23,475 | 1,551.375 |
| Total | Eight accepted acquisitions | 165,963 | 160,354 | 10,644.406 |

The loop took 10,715.562 seconds (178.593 minutes). Eight of 24 requests were sent;
16 remain unused in this consumed attempt. No check, edit, submission or correction
cycle was attempted. The old full-task check remains failed on the unchanged
candidate; its earlier library subchecks are historical evidence, not new checks.

Every complete thinking/final response and actual result was directly reviewed,
with the following actual input inspected. C01–C07 results reach the next decision;
C08's result is constructed/admitted but has no subsequent model recipient because
of the stop. C08 recognizes partial pages and a usable fragment anchor, qualifying
any claim that the earlier eligibility misunderstanding persists unchanged.

[VERIFICATION.json](VERIFICATION.json) reconstructs all 71 native inputs/trials,
replays all eight actions and verifies 221 frozen sources, 563 sealed artifacts
and three private runtime files locally. No incomplete response, silent retry,
runtime failure, automatic evidence eviction or rejected operation occurred.

This is reused-task development with Qwen-selected groups, not a controlled
comparison with the old host or a fresh capability task. The supplied compact and
broad-state qualification groups remain engineering feasibility evidence. The
separate [native fragment edit](native-edit-002/RESULT.json) fits at 23,639 tokens;
it adds only a diagnostic blank line and is not Qwen work or task progress.

Retain the corrected host while completing the [focused follow-up](FOLLOWUP_PROPOSAL.md).
No new presentation or reasoning policy is adopted from this run alone.
