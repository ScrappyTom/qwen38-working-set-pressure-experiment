# Execution receipt — eight-request wording comparison

The owner approved W01–W08 with **"I approve"** after the exact eight-request
execution question. That direction is preserved in the first run record.
Execution used commit 942e603479900b998f93e5d8bc581352d6d65a2b, the unchanged
preparation from 25789c6, and the separately frozen execution specification.
Eight requests were sent, eight complete responses received, and eight actions
executed, once each. E01–E04 remained offline regressions. There was no retry,
continuation, diagnostic addition, configuration change or extra completion.

The first record is 2026-09-10 21:49:24.123441 UTC; terminal closure is
21:54:47.869589 UTC. All eight actual native inputs matched their prepared
bytes/counts before any completion. Each request began from a freshly rebuilt,
byte-checked candidate/session and a fresh system/user conversation. No earlier
W response or action entered another W input. Runtime shutdown and port release
preceded the terminal seal and evaluator access.

## Custody and independent verification

| Artifact | SHA-256 |
|---|---|
| Prepared package manifest | b009fe4fdb2e0982c8cb1941791d622fb11cb05f84e80302481453234b4d2112 |
| Preparation seal | 57074b97fab747c939f689e36678f1088ad7b138a2ea2d6f5370c293586f29fe |
| Execution manifest | 6e763ce033deb5cbe2cd2c429b688e6d5c430efc3c30ac72bb89372caec3dd2a |
| Response seal | cabbc0b0eb92cc11d0a0f1ede059e11edabdd1ceb2914bb0effd864efa452718 |
| Independent verification | 71df352aeba9eb938932195f4c1c9136c7a60a8c711a8e2e2ef17725ec35458c |
| Post-seal verifier source | d2c82d48cac726e56aa788305ee95b59b2f68f0652bff4df5fb46b50b9024b2d |

[VERIFICATION.json](VERIFICATION.json), produced by the new offline
[verifier](../../../../scripts/verify_wording_execution.py), confirms 100 sealed
public files, three local private-runtime files, 69 chained records and 48
unchanged execution source identities. Previous closures still validate.
The seal itself is additional to its 100-file inventory. The original prepared
package, specifications, manifests, source and run artifacts were not edited.

Each response's complete thinking and final fields match the raw endpoint reply;
all finish normally, with one final action and zero cache reuse. Actual inputs
match preparation, endpoint usage and pinned offline tokenization. Independently
reversing the two declared edits restores each paired control exactly, including
the output schema, sampler, seed and every other request field. The four unique
native inputs repeat across seeds; seed is an endpoint setting, not prompt text.

Each actual final action was parsed and replayed on its original fresh host
state. Before-state, actual result, after-candidate and after-session match byte
for byte. Replay uses the frozen executor but not the live response handler;
it is a separate verification path, not a second implementation of tool semantics.
The verifier made zero model calls and does not certify direct reading; that is
documented in the [direct transcript audit](DIRECT_TRANSCRIPT_AUDIT.md).

The pre-execution revision passed fifteen focused checks: seven wording-runner
checks plus eight shared response-handler execution checks with mocked model
endpoints. The earlier preparation passed seven checks. These prior results are
preserved; execution source did not change and those tests were not rerun here.
This is not a full-suite test claim. The post-seal verifier was actually executed
against this completed evidence, including all eight action replays and recounts.

## Runtime and capacity

Actor: Qwen3.8-27B UD-IQ3_XXS, model SHA-256
c0b7c3038681ed2e3040456c1dd45f9858b6c2290bed172c70388a94874f3eee.
llama.cpp b10434, revision 7e4c0a96880dae4fc4268ad441f8a6446bd5460a;
server SHA-256 5f1f831bc21dcbff4ca40e05cb59dbcbc0802d20b2046540bbbf3bd45cd61610.
The pinned offline tokenizer is
d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c.

Both conditions used q4_0 K/V, 56,576 physical context, no MTP, all GPU layers,
fit off, one slot, no context shift, six threads, batch 256, ubatch 128 and flash
attention. Thinking was on/xhigh/uncapped in both launch and actual requests.
Sampler: temperature 1, top-p .95, top-k 20, min-p 0, repetition 1,
presence/frequency penalties 0. Cache reuse was disabled and reported zero.
Request seeds 1729 and 271828 superseded the server's default seed.

The prospective 32,768 generation reserve remained a planning allowance, not an
output cap. All live inputs fit the 23,808 admission ceiling; the largest was
3,906, leaving 52,670 physical tokens before generation. Largest output was
1,107 (W03); minimum remaining space after completion was 51,851 (W06).
No output exceeded the reserve. These small live inputs exercised no context
pressure and do not qualify the future 25k working-set budget. The prepared
20,410-token offline regression was not exposed to generation in this run.

Memory monitoring covered load through shutdown: 1,457 samples, minimum 339 MiB,
maximum/final 11,773 MiB free; nominal interval 200 ms, largest observed gap
224 ms. Health checks before dispatch and after each response passed. No CUDA
failure, truncation or physical exhaustion was observed. The 350 MiB reference
remained advisory under the already accepted owner amendment; the original Q1
threshold failure remains preserved. Private launch paths and logs remain local
and ignored, with hashes retained in the public seal.

## Actual per-request accounting

Input/output columns are endpoint counts. Thinking/final columns independently
retokenize the complete saved text fields without BOS or escape processing.
They are not original generated-token segmentation; the residual is not asserted
to be special-token overhead. Seconds measure the completion HTTP request,
including prompt processing and generation, excluding subsequent tool execution.

| Call | State / seed | Condition | Input | Output | Thinking text | Final text | Seconds | Physical tokens left |
|---|---|---|---:|---:|---:|---:|---:|---:|
| W01 | I3 / 1729 | Reference | 3,272 | 489 | 329 | 157 | 31.313 | 52,815 |
| W02 | I3 / 1729 | Wording | 3,293 | 382 | 224 | 155 | 26.031 | 52,901 |
| W03 | I3 / 271828 | Wording | 3,293 | 1,107 | 951 | 153 | 62.109 | 52,176 |
| W04 | I3 / 271828 | Reference | 3,272 | 447 | 291 | 153 | 29.360 | 52,857 |
| W05 | I4 / 1729 | Wording | 3,906 | 817 | 799 | 15 | 49.469 | 51,853 |
| W06 | I4 / 1729 | Reference | 3,885 | 840 | 821 | 16 | 50.610 | 51,851 |
| W07 | I4 / 271828 | Reference | 3,885 | 270 | 251 | 16 | 21.797 | 52,421 |
| W08 | I4 / 271828 | Wording | 3,906 | 224 | 206 | 15 | 19.719 | 52,446 |

Reference totals: 14,314 input, 2,046 output, 1,692 thinking-text, 342 final-text
tokens and 133.080 seconds. Wording totals: 14,398 input, 2,530 output, 2,180
thinking-text, 338 final-text tokens and 157.328 seconds. The candidate adds
21 input tokens per invocation, 84 across its four calls, without control padding.

All eight actions were accepted: four patches, two current-source reads and two
historical action-payload retrievals. No check or submission occurred. Each path
ended because the host offered no continuation. The eight-request authorization
is consumed; the attempt cannot be rerun, resumed or replaced.
