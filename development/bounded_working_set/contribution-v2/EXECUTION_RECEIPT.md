# Execution and verification receipt

- Frozen source: 39b10965; maximum 24 new requests, seed 961207.
- Manifest: 63977f42d461e007acdf0ef94469b407f7c1b8a27acb72b910c107f4ae327338.
- Response seal: 70bf434163e9365d5eb0f9aac40d22675790747800492a25de18638bd3b0d17f.
- Actor: Qwen3.8-27B UD-IQ3_XXS; q4_0 K/V; 56,576 context; no MTP;
  thinking on, xhigh, uncapped; cache off. Input ceiling 23,808; prospective
  generation reserve 32,768. No run setting changed.
- Eight complete responses and accepted acquisitions; zero edits/checks/submissions.
  Sixteen requests unused; attempt consumed, no retry or rescue.
- Stop requested during C08 after direct C06/C07 review. C08 drained normally;
  operator_stopped closure, final state and exact stop reason preserved.
- 498 custody records; 563 sealed artifacts; 221 source identities; 71 native
  inputs/trials; eight deterministic action replays and raw response verifications.
- Three private runtime files verified locally and kept out of Git. Owned server
  and monitor closed; dedicated port free; no observed CUDA failure or truncation.
- Minimum sampled free GPU memory: 244 MiB over 51,725 samples, under the existing
  advisory policy. This does not pass the historical 350 MiB reference target.
- Input 165,963 tokens; generated 160,354; model requests 10,644.406 seconds;
  loop 10,715.562 seconds. Peak sent input 23,803. All outputs fit the selected
  planning reserve, which remains an allowance rather than an uncapped-generation
  guarantee.

[VERIFICATION.json](VERIFICATION.json) was produced after normal closure with zero
model requests. Every complete thinking/final response and actual result was also
directly reviewed; verification does not substitute for that review.

Thirty-seven selected checks qualified the implementation before this run; this
is not a fresh full-suite claim. Compact/broad scripted qualification, the original
visibility consultation, and the later diagnostic fragment probes are separate
development evidence and costs. None is added to the eight model actions or
presented as a completed parser contribution.
