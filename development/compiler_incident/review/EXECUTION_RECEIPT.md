# Execution receipt: compiler incident comparison

The owner-approved attempt ran once and stopped without retry. It preserved
66 requests/responses and executed 65 actions. C01 R23808 submitted checked work;
both X16000 branches reached input-admission stops; C02 R23808 exhausted physical
context before emitting its first continuation action. The entire attempt then
closed under the frozen incomplete-output rule. Unused allowance authorizes no
continuation, replacement cell, rescue or additional conversation.

## Identity and custody

- Owner instruction: “I approve”, bound in the custody record to the prepared
  two-cell, at-most-128-request scope, 32 actions per trajectory including shared work.
- Execution base: `5374c259be4b8bccf11e0729e7a9d9330b16445a`.
- Manifest SHA256: `c195b5c1ae0f0e234ba46f77d052fb86aa71ce8848d190d28a8b14612501d10d`.
- Package SHA256: `f63ec3dcb8115df53235f85acd3e4c644c16d7e3be46c9d1d0a7c2c675e2f3b2`.
- Response seal SHA256: `f8135f0fe20734fcbe90707a9bbe792fecee1acc89b315ce588f0dfc4c015cf5`.
- First/last custody records: 2026-09-11 22:54:18.417067 UTC /
  2026-09-12 06:53:18.734082 UTC. This interval includes preparation and closure.

[Offline verification](VERIFICATION.json) checked 1,570 sealed public files,
1,384 chained records, 71 pinned source files and 56 canonical payload files.
It reconstructed and retokenized all 129 prepared native inputs, including
withheld admission trials, and replayed all 65 actions against actual host code.
Candidate/session/check states and next decisions matched. It accounted separately
for the empty-final context-stopped response, with no executed action or successor.
Private runtime identities were checked locally; private runtime files remain ignored.

The new [execution verifier](../../../scripts/verify_compiler_execution.py) is
audit-only, outside the frozen source closure. It made zero completion requests.
It verifies observed-prefix fidelity, not correctness through an independent
implementation of the host. [Direct review](DIRECT_TRANSCRIPT_AUDIT.md) separately
read all 66 complete thinking/final fields, the full initial input and every later
changed input field/event/body, exact results and following decisions. Unchanged
copies were checked by exact reconstruction and identity, not semantic summaries.

## Execution and runtime

C01 used seed 49979687, with R23808 before X16000; C02 used seed 67867967,
with X16000 before R23808. Authentic forks followed 6 and 8 shared actions at
full-next-input sizes 17,481 and 18,539. Each shared prefix ran once. Branch clones
had identical candidate, history, checks and recovery maps before residency changed.

The frozen Qwen3.8-27B UD-IQ3_XXS and llama.cpp b10434 identities remained fixed:
q4_0 K/V, 56,576 physical context, no MTP, full offload, one slot, fit/context shift
off, prompt caching off, uncapped thinking/xhigh and all four generation budgets -1.
Sampling stayed at temperature 1, top-p .95, top-k 20, min-p 0, repeat penalty 1,
frequency/presence penalties 0. No model/interface setting changed between arms.

G=32,768 was planning room, not an output cap. C02 R009 consumed all 38,037 tokens
remaining after its 18,539-token input, with `finish_reason=length` and an empty
final. Its raw response and extracted text were saved before execution was
rejected. No action or state mutation occurred. C01 X029 also exceeded the reserve
(35,483 generated tokens) but fit its physical space and emitted an action.

Telemetry contains 138,533 samples, maximum observed gap 1.421 seconds, minimum
246 MiB free. The 11,716 MiB maximum includes shutdown and is not inference
headroom. The accepted 350 MiB reference stayed advisory. No CUDA failure was
observed; truncation was observed. Sampling was not an interrupting watchdog
inside a pending request. Owned shutdown was verified and the dedicated port
was free. No runtime remains running for this attempt.

## Accounting

Shared work counted once, all received responses consumed 887,889 input and
452,353 generated tokens, with 28,559.281 model-request seconds (475.99 minutes).
Separate text retokenization yielded 450,413 thinking and 1,742 final tokens;
these are not the original generation's segmentation.

The 65 executed-action responses account for 26,041.531 request seconds and
26.859 recorded processing seconds. The five completed segments total
26,189.157 wall seconds. The unexecuted response adds 2,517.750 request seconds;
its processing and completed-segment wall times were not recorded. Do not turn
missing timings into zero or describe the partial processing total as whole-host cost.
Native preparation/tokenization trials are preserved separately from model input
processing; 129 prepared inputs do not mean 129 completion requests.

Prior preparation's 22 focused passing checks and mocked rehearsal remain
engineering evidence. This tranche adds exact replay and transcript review;
it does not claim a new full-suite test run or alter any frozen result.
