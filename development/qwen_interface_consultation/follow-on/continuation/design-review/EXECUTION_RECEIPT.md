# Design consultation receipt — September 10, 2026

Four frozen requests D1–D4, four received responses, four normal completions,
zero executed tools or candidate mutations. Each was a fresh conversation at
seed 42. No retry, rescue, cross-call answer/thinking, cache reuse or configuration
switch. The owner-authorized Q2/Q3 plus D1–D4 continuation is now consumed.

| Evidence binding | SHA-256 |
|---|---|
| Original package | 0849ada30219dea7df4aa34511d69a1a7ea1cb560602e4f0ed65de77538ac33a |
| Original Q1 seal | a93fa65612977687ceaf2a9756ef9c65272e5ed401cec961acaa37dc050c3a71 |
| Continuation manifest | 8b01cf34945a9a7bbbd3a76fa1c4e1e4b2e13b934ad67c6ab9920e11ee315905 |
| Q2/Q3 seal | c5f6a1b7e74380c7e42b07e429e7a8ef2e5b88f42904b568327d1fc933411dcf |
| Direct qualification decision checked before D1 | 629a320f2ebec4b9cfe45f2ccd8d1d2fd9c01f64ae4ea80553e2815b859793b1 |
| D1–D4 response seal | 380a0f8016ab0b7406479041cb55c136b94a8b39aa32d676975d6558de93e2e0 |
| Design public-file aggregate | de246bab535c6b1f8abf1fc9614fada4cf1e9db3c4ae798e37727ee77c8f6fd6 |

Pinned Qwen3.8-27B UD-IQ3_XXS model SHA
c0b7c3038681ed2e3040456c1dd45f9858b6c2290bed172c70388a94874f3eee.
b10434 server SHA
5f1f831bc21dcbff4ca40e05cb59dbcbc0802d20b2046540bbbf3bd45cd61610,
revision 7e4c0a96880dae4fc4268ad441f8a6446bd5460a.
Tokenizer SHA d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c.

Runtime: 56,576 context, q4_0 K/V, full 66/66 GPU layers, fit off, one slot,
six threads, batch 256, microbatch 128, flash attention, no MTP or context shift.
Thinking on/xhigh, all generation/reasoning caps -1. Temperature 1, top-p .95,
top-k 20, min-p 0, repeat penalty 1, presence/frequency penalties 0. Native
template and prompt-cache disablement verified against actual requests/usage.
Private runtime paths/logs stay local with hashes in the seal.

| Call | Input | Combined output | Offline thinking text tokens | Offline final text tokens | Elapsed seconds |
|---|---:|---:|---:|---:|---:|
| D1 | 20,666 | 26,208 | 20,732 | 5,473 | 1,697.906 |
| D2 | 4,834 | 21,993 | 17,241 | 4,749 | 1,222.578 |
| D3 | 3,549 | 16,951 | 13,023 | 3,925 | 913.329 |
| D4 | 4,162 | 26,173 | 20,880 | 5,290 | 1,467.484 |
| Total | 33,211 | 91,325 | 71,876 | 19,437 | 5,301.297 |

Separate text retokenization is not the server's original token segmentation;
combined endpoint usage remains authoritative. Generation reserve exceedances
are D1 +5,728, D2 +1,513 and D4 +5,693. All outputs are complete and uncapped.

The 25,593 whole-device memory samples include 25,552 below the advisory 350 MiB
reference, from 07:53:18.712 through 09:21:40.361 Mountain time. Minimum 339 MiB;
final post-shutdown sample 11,773 MiB free. No recorded CUDA failure/truncation.
The owned server shut down and its port was free; monitoring continued through
shutdown. These measurements describe this GPU workload and sampled intervals.

The independent checker verifies 32 public files, 3 private files and 25 chain
records, plus original Q1 custody and 44 source identities. It checks exact
request/native bytes, native/endpoint/offline input counts, zero cached tokens,
exact separated response text and nonexecuting host results. Its identity and
shared verifier identity are in [VERIFICATION.json](VERIFICATION.json).

All four complete inputs/thinking/final responses and following host decisions
received [direct review](DIRECT_TRANSCRIPT_AUDIT.md). Twenty focused interface
tests passed before exposure; no full-suite rerun is claimed. The later matched
comparison remains unexecuted and requires its own concrete execution decision.
