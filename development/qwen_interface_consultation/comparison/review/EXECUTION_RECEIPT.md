# Execution receipt — reference comparison, sole attempt

The owner explicitly authorized: "Yes, execute the 16 requests" after being
asked about the prepared comparison's separate execution boundary. Execution
used the unchanged package from commit
77709f92a209a128089e231d8913992f2b718b3a and the separately frozen
[execution specification](../EXECUTION_SPEC.md) and manifest. There were sixteen
sent requests, sixteen received complete responses and sixteen executed actions.
No retries, continuations, diagnostic additions or extra model completions occurred.

Run preparation was recorded at 2026-09-10 17:49:12.993790 UTC; terminal closure
at 18:37:19.571006 UTC. All sixteen native requests were rerendered and matched
before the first completion. Each actual request uses a fresh system/user
conversation and freshly reconstructed, byte-checked candidate/session state.
No later response saw an earlier action or model output from this comparison.

## Identities and independent verification

- Prepared package manifest: f8fab01274a39d12acd24e544d81056d4000a3e1a81652cd05d631c8f5328ca5.
- Prepared seal: c6b78560328cfb86c3a9d3315002b35b493a416dae321218b08d1ebcb9c3f44b.
- Execution manifest: e7f37daba46951b2a9ec946c23c4a430d1aa8179dfbbf671e0f5ae77a333819f.
- Response seal: 6aa1c190aa3873a66c0fc1f9e3b609c69b9c39ffc707d022edf7c209c600d6ea.
- Post-seal verifier source: d24ba04d9973f7dd14bf5a105cf389746a8942db3fef81b11e4ca39b2bdb75e4.

[Independent verification](VERIFICATION.json) passed: 196 sealed public files,
three local private-runtime files, 133 chained records, 46 execution source
identities, all sixteen offline/native/endpoint input-token matches, exact
thinking/final extraction from raw replies, normal finish and zero cache reuse.
Each final action was parsed and replayed on the original fresh state; actual
result and after-candidate/session bytes match. Every before-state matches the
original prepared snapshot. Shutdown and the free dedicated port are recorded.
The verifier ran after the terminal seal and made no completion requests. It
does not itself certify direct transcript review; that is documented separately.

The final frozen execution code passed the focused interface suite: 33 tests,
including eight execution tests for frozen-source/schedule enforcement, native
mismatch before dispatch, once-only execution and fresh state, accepted failing
checks and rejected actions, incomplete/invalid response custody, unexpected
executor failures, transport partial custody and refusal to restart. Endpoint
and runtime doubles were used; these tests are not model evidence or a full-suite
claim. Preparation's earlier 25-test result and all previous reports remain intact.

## Fixed runtime and observed capacity

Actor: Qwen3.8-27B UD-IQ3_XXS. Model SHA-256:
c0b7c3038681ed2e3040456c1dd45f9858b6c2290bed172c70388a94874f3eee.
llama.cpp b10434, revision 7e4c0a96880dae4fc4268ad441f8a6446bd5460a;
server SHA-256 5f1f831bc21dcbff4ca40e05cb59dbcbc0802d20b2046540bbbf3bd45cd61610.
Offline tokenizer SHA-256:
d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c.

Both conditions use q4_0 K/V, 56,576 physical context, full GPU offload, fit off,
one slot, no MTP and no context shift. Native thinking is on/xhigh, with all
request/server reasoning and generation limits -1. Sampler: temperature 1.0,
top-p 0.95, top-k 20, min-p 0, repetition 1.0, presence/frequency penalties 0.
There are six threads, batch 256, ubatch 128 and flash attention. Prompt caching
is disabled, and every endpoint response reports zero cached tokens.

The prospective generation reserve is 32,768, admitting at most 23,808 input
tokens; it is not an output cap. Maximum input is 20,389, leaving 36,187 for
uncapped generation. Maximum observed output is 10,648 (C15), and minimum
remaining physical space after completion is 30,062 (C03). No reserve exceedance,
CUDA error or truncation was observed. This is not a qualified 25k study budget.

Monitoring began before model load and continued through shutdown at a nominal
200 ms interval: 13,817 samples, minimum 327 MiB and maximum/final 11,773 MiB free.
The 350 MiB reference remained advisory under the accepted owner amendment,
with no new numeric stop floor. Fresh telemetry and runtime health were checked
before dispatch and before action execution. The runtime exited normally and
the dedicated port was free. The original below-threshold Q1 stop is preserved,
not relabeled as having passed its original target.

## Per-invocation accounting

Input and output are endpoint counts, with inputs independently recounted
offline from actual native prompts. Thinking/final columns count the saved text
fields separately offline without BOS; they are not original generated-token
segmentation and need not sum to the endpoint output. Request seconds measure
the completion HTTP call, including prompt processing and generation, excluding
subsequent local action execution and review.

| Call | State / seed | Condition | Input | Output | Thinking text | Final text | Request seconds | Physical tokens left |
|---|---|---|---:|---:|---:|---:|---:|---:|
| C01 | I1 / 42 | Legacy | 18,714 | 2,022 | 2,004 | 15 | 156.859 | 35,840 |
| C02 | I1 / 42 | Reference | 20,389 | 901 | 883 | 15 | 98.218 | 35,286 |
| C03 | I1 / 314159 | Reference | 20,389 | 6,125 | 6,051 | 71 | 405.687 | 30,062 |
| C04 | I1 / 314159 | Legacy | 18,714 | 6,205 | 6,131 | 71 | 402.500 | 31,657 |
| C05 | I2 / 42 | Reference | 4,557 | 646 | 628 | 15 | 42.578 | 51,373 |
| C06 | I2 / 42 | Legacy | 2,882 | 3,379 | 3,306 | 70 | 176.625 | 50,315 |
| C07 | I2 / 314159 | Legacy | 2,882 | 1,814 | 1,796 | 15 | 97.141 | 51,880 |
| C08 | I2 / 314159 | Reference | 4,557 | 485 | 467 | 15 | 34.438 | 51,534 |
| C09 | I3 / 42 | Legacy | 1,597 | 7,058 | 6,979 | 73 | 361.469 | 47,921 |
| C10 | I3 / 42 | Reference | 3,272 | 4,889 | 4,813 | 73 | 256.187 | 48,415 |
| C11 | I3 / 314159 | Reference | 3,272 | 637 | 481 | 153 | 39.000 | 52,667 |
| C12 | I3 / 314159 | Legacy | 1,597 | 1,198 | 1,120 | 73 | 62.875 | 53,781 |
| C13 | I4 / 42 | Reference | 3,885 | 926 | 908 | 15 | 55.125 | 51,765 |
| C14 | I4 / 42 | Legacy | 2,210 | 854 | 836 | 15 | 47.297 | 53,512 |
| C15 | I4 / 314159 | Legacy | 2,210 | 10,648 | 10,629 | 16 | 556.157 | 43,718 |
| C16 | I4 / 314159 | Reference | 3,885 | 925 | 907 | 15 | 55.281 | 51,766 |

Legacy totals: 50,806 input; 33,178 combined output; 32,801 thinking-text and
348 final-text tokens; 1,860.923 request seconds. Reference totals: 64,206 input;
15,534 combined output; 15,138 thinking-text and 372 final-text tokens;
986.514 request seconds. The reference is 7,013 UTF-8 bytes and adds 13,400
native input tokens across its eight calls, without control padding.

All sixteen actions are accepted: six reads, six checks (one passing, five
baseline failures), two saved-result retrievals, one patch and one outline page.
No saved-event retrieval or submission occurred. The sole run's authorization
is consumed. Private launch paths and runtime logs stay local and ignored, with
hashes in the public seal; public exact prompts and outputs remain preserved.
