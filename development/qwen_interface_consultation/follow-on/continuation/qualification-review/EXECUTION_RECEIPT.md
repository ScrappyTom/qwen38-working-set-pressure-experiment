# Qualification continuation receipt — September 10, 2026

The owner authorized continuation at q4/56,576 with monitoring after the original
Q1 stop. Only Q2 and Q3 were sent here: two requests, two received responses,
two completed responses. Q1 remains its original once-only response. Zero design
calls had occurred when this qualification receipt was written.

| Binding | SHA-256 |
|---|---|
| Original package | 0849ada30219dea7df4aa34511d69a1a7ea1cb560602e4f0ed65de77538ac33a |
| Original Q1 seal | a93fa65612977687ceaf2a9756ef9c65272e5ed401cec961acaa37dc050c3a71 |
| Continuation manifest | 8b01cf34945a9a7bbbd3a76fa1c4e1e4b2e13b934ad67c6ab9920e11ee315905 |
| Q2/Q3 response seal | c5f6a1b7e74380c7e42b07e429e7a8ef2e5b88f42904b568327d1fc933411dcf |

The pinned Qwen3.8-27B UD-IQ3_XXS model, b10434 server and tokenizer identities
are those in the [original receipt](../../qualification-review/EXECUTION_RECEIPT.md).
The continuation manifest pins 44 execution-source identities. Runtime: q4_0
K/V, 56,576 context, 66/66 GPU layers, fit off, one slot, six threads, batch 256,
microbatch 128, flash attention, no MTP or context shift. Thinking on/xhigh,
all reasoning/output limits -1, seed 42, temperature 1, top-p .95, top-k 20,
min-p 0, repeat penalty 1, presence/frequency penalties 0. Cache reuse is disabled
and actual cached-token counts are zero. Exact private launch paths remain local
with verified hashes; portable launch and effective settings are in the chain.

| Call | Input | Combined output | Remaining physical tokens | Elapsed seconds |
|---|---:|---:|---:|---:|
| Q1, original run | 36,096 | 416 | 20,064 | 113.218 |
| Q2, continuation | 412 | 1,738 | 54,426 | 85.047 |
| Q3, continuation | 20,565 | 14,551 | 21,460 | 926.015 |
| Total processing across three calls | 57,073 | 16,705 | Not additive | 1,124.280 |

Separate offline text counts: Q2 1,683 thinking / 52 final; Q3 12,525 thinking /
2,023 final. These are retokenized text, not the server's original token
segmentation, and do not replace combined endpoint usage. Q2 prefill/generation
take 1.100/83.931 s; Q3 46.613/879.226 s. No speed comparison is inferred.

[Independent verification](VERIFICATION.json) checks the 18 public files,
three private runtime files and 15 chain records of this stage, plus the original
Q1's 15 public/three private files and 13 records. It verifies byte-identical
original requests/rendered inputs, native/endpoint/offline input counts, exact
separated reply bytes, zero cache reuse and nonexecuting host results. Its
[source](../verify_evidence.py) and shared verifier hashes are in the report.

The stage has 4,908 complete memory samples; minimum 335 MiB, with 4,457 below
the advisory 350 MiB reference. Q2's minimum before Q3 is 371 MiB. The process
and port close normally; the last sample has 11,773 MiB free. Full offload,
q4 K/V, context and disabled MTP match, with no CUDA failure or native truncation.

Twenty focused interface tests passed before continuation exposure, including
the five new amendment tests and the prior fifteen. This is not a full-suite
rerun. Original historical evidence, scores, source and consumed runners remain
unchanged; continuation control is separately identified.
