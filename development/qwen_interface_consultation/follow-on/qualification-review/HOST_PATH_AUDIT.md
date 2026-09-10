# Host path audit

The new bounded runner leaves the consumed initial runner, design-preparation
helper, and shared host source unchanged. Its execution identity is pinned by
[the package manifest](../package/PACKAGE_MANIFEST.json) and both stage logs.
It freezes seven fresh system/user requests before completion exposure. The
qualification stage re-renders Q1–Q3 and requires byte-identical native prompts
and matching counts before sending Q1. Preparing a request is recorded separately
from starting or receiving a completion.

Direct inspection of the live request confirms thinking on/xhigh, seed 42,
the specified thinking sampler, every output/reasoning limit at -1,
cache_prompt=false, and no tool or response-format channel. Native startup
confirms 66/66 GPU layers, 56,576 context, q4_0 K/V, and no speculative decoder
implementation. The trained model's MTP-related metadata does not mean MTP was
enabled. The portable launch is retained in the chained runtime-prepared record;
private machine paths and full startup logs remain local with sealed hashes.

Native prompt-cache machinery exists, but both endpoint cached_tokens and
timings.cache_n are zero. The 36,096-token prompt count agrees across native
preparation, live usage and independent offline tokenization. No previous answer
or thinking was fed to Q1. Normal stop, exact raw response custody and separate
thinking/final byte equality were verified before evaluating correctness.

The monitor starts before server load and samples every 200 ms. All 584 saved
rows are complete; 544 report 339 MiB free. The first low sample occurs about
one second after Q1 starts, and low values persist through its last generated
tokens. The minimum before dispatch was 563 MiB. The difference demonstrates
why loading and tokenization alone did not qualify inference. The record does
not isolate CUDA graph allocation, another process, or a particular runtime
component as its cause.

After Q1's valid completion, the next dispatch checks the accumulated stage
minimum and raises the specified capacity stop. There is exactly one started,
received and completed call. Q2/Q3 have saved prepared inputs but no completions;
D1–D4 remain in the package. The owned server and monitor terminate, the port
is free, and the final memory sample returns to the pre-load 11,773 MiB free.
No retry, model switch, lowered threshold, smaller input, reasoning cap,
context shift or tool execution is present in this path.

The host enforced the frozen stop correctly. The selected runtime allocation
failed its reserve criterion. This audit earns capacity revision; it does not
earn a change to the information store or a diagnosis of model comprehension.
The design gate rejects this incomplete qualification before loading a runtime.
The review decision records null results for unexposed Q2/Q3, not fabricated
passing scores or model failures.

