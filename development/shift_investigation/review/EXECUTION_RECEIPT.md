# Execution receipt — S01

The owner answered the concrete one-run / at-most-20-action execution question
with **Proceed**. The runner recorded that instruction before exposure. Historical
pending-decision text in the sealed preparation remains unchanged. Execution
started from pushed commit `db1cd210cfdf4b593d83075ac5de509e23b367b1` and consumed
one fresh S01 conversation, seed 161803, without retry, rescue or replacement.

| Identity | SHA-256 |
|---|---|
| [Prepared package](../preparation-001/PACKAGE_MANIFEST.json) | `f46919611cf06506d6e56a194ba0200e6b566b28fae8ec8df2c24c55951a14f7` |
| [Preparation seal](../preparation-001/PREPARATION_SEAL.json) | `177a932ada863eb7117de40cb5dc122337fe316dc631f1fb637eab500c214780` |
| [Response seal](../run-001/RESPONSE_SEAL.json) | `266a83c85a002f57b579d1752553975767eea299294c35fc8301017d07977abf` |
| Initial candidate | `b77c87956a3936ab169f80f5df55b4a2731b6015968fdebcb1e2a1095469c6ea` |
| Submitted candidate | `b05e48a5080daa02f4a2dcc57b8b6de6287370048237033a24382c8a9d165606` |
| Submitted daily.py | `3f759d7e31253b34e380e5b62daaa26f9f77e64d64042195dcb4d27bc4fee8c2` |

## Actor and allowance

Qwen3.8-27B UD-IQ3_XXS; model SHA-256
`c0b7c3038681ed2e3040456c1dd45f9858b6c2290bed172c70388a94874f3eee`.
llama.cpp b10434 revision `7e4c0a96880dae4fc4268ad441f8a6446bd5460a`;
server SHA-256 `5f1f831bc21dcbff4ca40e05cb59dbcbc0802d20b2046540bbbf3bd45cd61610`.
Q4_0 K/V, context 56,576, no MTP, thinking on/xhigh/uncapped, all four generation
budget fields -1. Temperature 1, top-p .95, top-k 20, min-p 0, repetition 1,
frequency/presence 0. One slot, cache_prompt false, full GPU offload, fit off,
no context shift, six threads, batch 256/ubatch 128, flash attention.

Exact native input P <= 23,808 reserves G=32,768 inside physical C=56,576.
G is not an output cap. No input was denied or shortened. Thinking was saved
separately and omitted from later requests; all ordered action/result payloads
remained resident. Actual model/server/tokenizer files and launch arguments were
verified locally; private paths and server logs remain ignored.

## Closed evidence and verification

The first/last chained records are 2026-09-11 05:07:12.842902 and
05:17:55.146143 UTC (September 10 locally). The run has **11 prepared, sent,
received and completed responses**, **106 chained records**, **160 sealed public
files**, **12 canonical payload files**, **67 frozen source identities**, and
three verified local-only runtime files. There is no partial or unexecuted response.

Inventory, aggregate digest, chain and closure were verified before direct model
response access. [The offline verifier](../../../scripts/verify_shift_execution.py)
then reconstructed every API request and resident history, compared native
rendering/tokenization, retokenized all 11 native inputs and both saved output
fields (33 distinct CLI recounts), and replayed every action through the actual
executor. Results, successors, session states, canonical payloads, check
opportunity, terminal state and every next-turn decision match exactly.
This is a separate verification path, not a second implementation of host semantics.

Direct input inspection additionally compared every changed field/new event in
the actual later inputs with their predecessors, verified the unchanged system
and request settings, and checked exact user-state inclusion in every native
prompt. It found the same episode annotation in all 11 inputs. All ten
nonterminal results are in the next **sent** input. The submit result is saved
without a following model call, as expected. Mechanical verification does not
certify the direct reading documented in the separate transcript audit.

All 24 public cases passed on action 10 and replayed identically offline. The
first target mutation follows complete exact target acquisition at action 6;
inspection verification found no invalid read or missing target interval. The
final candidate changes only daily.py and differs from the known-good oracle
bytes. No frozen source or preparation artifact changed during execution.
The ten focused preparation tests were already passed before approval; this
tranche does not claim a new full-suite run. A local verification precheck first
omitted PYTHONPATH and failed import, then passed with the documented environment;
this did not affect, retry or modify the live run.

## Runtime and costs

All pre/post-dispatch checks show the selected context, full offload, q4 K/V,
MTP disabled, no CUDA error and no truncation. Telemetry contains 2,994 samples;
maximum sampling gap .224 seconds; minimum free memory **335 MiB** under the
owner's accepted advisory policy. The 11,773 MiB maximum occurs during shutdown
and is not generation headroom. The owned server and monitor closed and the
dedicated port was free. No actor/runtime metadata mismatch was found.

Cumulative input: 68,794; generated: 8,781. Retokenized saved thinking/final text:
8,239/509, which are text counts rather than original generated-token segmentation.
Peak input: 10,543; minimum post-generation physical room: 44,579 tokens.
Model requests: 606.263 seconds; task-loop wall time: 612.250 seconds; recorded
response processing: .752 seconds. Request time is not tool-execution time.
Per-call values and all checks are in [VERIFICATION.json](VERIFICATION.json).
