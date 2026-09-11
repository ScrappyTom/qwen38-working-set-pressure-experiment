# Execution receipt — ordinary working-loop pilot

The owner answered the concrete two-run / at-most-40-request execution question
with **“Proceed.”** The sole attempt completed L01 and L02 with 24 requests,
24 preserved responses, 24 accepted actions, two passing checks and two checked
submissions. No retry, resume, replacement or rescue occurred. The unused
allowance does not authorize another run.

## Identity and custody

Execution source: commit `d4056ff02c0d54c117be4044175dfd59610c0e26`.
The unchanged [specification](../SPEC.md) and prepared package govern execution;
their original pending-decision wording is historical, superseded by the
recorded owner instruction. No frozen input or source was changed in this run.

| Artifact | SHA-256 |
|---|---|
| Preparation/package manifest | `6c4ae13079c093c73b0b29ea7a830e66081e0344a0be088dc1dde3785b48ed93` |
| Preparation seal | `9197f9e3f366f9146c68dbbc0c42969edf3e292af298ddf4f6e911119ce8a080` |
| [Response seal](../run-001/RESPONSE_SEAL.json) | `cc3cf5d47d3fca38f9458964503ff9366f893e4e7ee4e5dfaf0bb5abeb9b27df` |
| Offline verification source | `2f56ec78d49fcb71ce32f13b0be967098f3a70a1829b113208266bf1d6168c75` |

The sealed inventory contains 344 public files, plus the seal itself. All 225
chained records, 51 frozen source/test/contract identities, 26 canonical payload
files and three local private runtime artifacts verified. The first record is
2026-09-11 01:14:57.592998 UTC and the last 02:09:52.189563 UTC, both September
10 in the owner's America/Denver timezone. Response-body review followed full
attempt closure and seal verification.

The [offline verifier](../../../scripts/verify_investigation_execution.py)
reconstructed all 24 actual requests from the evolving histories and replayed
all actions, exact returns, candidate states and session states. It checked
native rendered inputs against saved template results, token arrays, usage and
CLI counts, making 62 distinct text recounts including complete saved thinking
and final text. This replay uses the same executor implementation through a
separate verification path; it is not an independent implementation of tool
semantics or a substitute for direct review. See [VERIFICATION.json](VERIFICATION.json).

All 22 nonterminal results occur in the next actual sent input, not merely a
saved hypothetical request. The two submission results close their runs and
receive no later model turn. Every accepted response has one normal strict JSON
action with finish reason `stop`; endpoint cache use is zero. No prepared input
was withheld, no dispatch lacked a completed response, and no result was rejected.

## Actor and execution bounds

Qwen3.8-27B UD-IQ3_XXS, model SHA-256
`c0b7c3038681ed2e3040456c1dd45f9858b6c2290bed172c70388a94874f3eee`,
llama.cpp b10434 revision `7e4c0a96880dae4fc4268ad441f8a6446bd5460a`,
server SHA-256 `5f1f831bc21dcbff4ca40e05cb59dbcbc0802d20b2046540bbbf3bd45cd61610`.
The offline tokenizer hash is
`d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c`.
Machine-specific launch paths and private runtime logs stay local.

Both runs use q4_0 K/V, 56,576 physical context, no MTP, native thinking on,
xhigh and uncapped generation. All four request budget fields are -1. Sampler:
temperature 1, top-p .95, top-k 20, min-p 0, repetition 1 and zero frequency/
presence penalties. One slot, six threads, batch 256, ubatch 128, flash attention,
fit off, no context shift, full 66/66 reported layer offload; cache_prompt and
stream are false. L01 seed 104729 precedes independent L02 seed 130363.

Each run permits 20 actions including submission. Native input P plus the
32,768-token planning generation reserve must fit physical context, so P is
admitted only at or below 23,808. G is not an output cap. Initial P is 3,070;
actual peaks are 15,644 and 20,027. The largest output is 8,084 tokens; minimum
physical space remaining after a response is 29,275. No context boundary is
introduced or crossed. These observations do not qualify a 25k input contrast
or bound harder-work generation.

## Lifecycle and validation scope

GPU sampling produced 15,792 records, minimum free memory **316 MiB**, maximum
observed sampling gap 0.831 seconds. The owner-approved 350 MiB reference remains
advisory; this does not meet or rewrite the original historical hard threshold.
All recorded runtime checks match the frozen configuration, without observed
CUDA failure or truncation. Read-only slot checks during monitoring added no
model inference. Only the owned runtime and monitor were closed; shutdown and
the dedicated port becoming free are recorded and verified.

The active runtime record already normalizes the helper's legacy planning
metadata to the pilot actor and advisory policy. Direct record inspection and
verification found no difference from the active actor. An initial review
suspicion about stale logger metadata was resolved without a code change.

The 14 pilot-specific mocked preparation/execution checks passed during the
preceding preparation and were not rerun here; their pinned sources did not
change. This tranche adds the executed full offline evidence replay and direct
review of all 24 responses. Neither statement is a full repository suite claim.
The earlier 58 selected maintenance checks remain a separate historical result.
