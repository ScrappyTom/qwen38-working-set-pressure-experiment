# Saved-work continuation: execution receipt

The single attempt is closed with checked submission, without retry. The owner's
continuing instruction to work with Qwen as pilot and consultant is recorded in
the first receipt as the authorization basis for the prepared maximum-16-call
scope. The two phase limits remain eight; phase 1 uses two calls, phase 2 seven.
Unused allowance is not permission to reopen this consumed attempt.

## Identities and runtime

- Preparation commit: `63506f81d08c9670e6b37a920af889a2cae057ed`.
- Execution manifest SHA-256:
  `3377c287d7b12fc9ad84df22a6e70a89fac01a9fa1071bf5ec2e796be5781736`.
- Response seal SHA-256:
  `99055e218584b886244f7312a2fb6dde75859b1029c00331a613721b3cb827fe`.
- Actor: Qwen3.8-27B UD-IQ3_XXS; llama.cpp b10434,
  revision `7e4c0a96880dae4fc4268ad441f8a6446bd5460a`.
- Model SHA-256:
  `c0b7c3038681ed2e3040456c1dd45f9858b6c2290bed172c70388a94874f3eee`.
- Server SHA-256:
  `5f1f831bc21dcbff4ca40e05cb59dbcbc0802d20b2046540bbbf3bd45cd61610`.
- Physical context 56,576; q4_0 K/V; full GPU offload; no MTP; one slot;
  no context shift or prompt-cache reuse. Thinking enabled, xhigh; all four
  generation-budget settings remain -1.
- Seed 86028121; temperature 1, top_p .95, top_k 20, min_p 0,
  repeat penalty 1, presence/frequency penalties 0.
- Native-input ceiling 23,808; selected prospective generation reserve 32,768.
  The reserve is not a cap or a guarantee.

Private runtime paths/logs stay local. Verification checks their three sealed
files, actual launch arguments and runtime binaries. The final receipt confirms
owned-server shutdown and a free dedicated port. No truncation, CUDA failure,
unexpected transport stop or context exhaustion occurred.

## Model calls

| Call | Action | Native input | Generated tokens | Request seconds |
| --- | --- | ---: | ---: | ---: |
| C01 | Save first report entry | 15,278 | 5,844 | 362.172 |
| C02 | Check: malformed JSON | 16,099 | 261 | 50.625 |
| C03 | Reopen BUILD-A | 18,747 | 12,407 | 778.563 |
| C04 | Read current optimizer | 22,644 | 16,561 | 1,079.219 |
| C05 | Correct and complete report | 23,227 | 19,187 | 1,259.609 |
| C06 | Reacquire README | 23,583 | 8,689 | 582.312 |
| C07 | Reacquire original capture | 20,932 | 15,443 | 990.671 |
| C08 | Check: 26/26 passed | 21,346 | 21,913 | 1,421.937 |
| C09 | Submit checked candidate | 21,961 | 13,552 | 878.907 |
| Total | 9 completed actions | 183,817 | 113,857 | 7,404.015 |

Task-loop time is 7,417.829 seconds, including 3.609 seconds of recorded response
processing. The approximately 13.814-second difference from model-request time
also includes other loop work; it is not all tool execution. Request costs include
native prompt processing and generation, not just decoding. Peak input is 23,583;
peak output 21,913; minimum physical room after a response is 13,317 tokens.
These observations do not establish an output bound for harder work.

There are twelve non-model setup operations: the three replayed saved-proposal
operations, four initial acquisitions and five restart acquisitions. Fourteen
live rendering/tokenization preparations include five rejected-prefix inputs;
only nine completion requests are sent. Those setup/rendering operations are not
Qwen actions or additional behavioral successes. Heavy offline replay,
tokenization and larger-file probes ran after the model runtime closed.

The 35,825 GPU samples reach 267 MiB free, below the original 350 MiB reference
under the already accepted advisory policy. Maximum sampling gap is 0.766 seconds.
This records healthy completion at an observed low margin, not qualification of
the original target or of a different workload.

## Custody and replay

`VERIFICATION.json` verifies 322 sealed public files, 193 hash-chained records,
77 pinned source files, 138 canonical payload copies and the three local private
runtime records. All 21 operations replay exactly. All 14 prepared native inputs
are reconstructed byte-for-byte and independently counted with the pinned native
tokenizer. Every actual dispatch includes its newest tool result. Every raw
reasoning/final field, strict action, host result, candidate and session state
matches replay. This script supports custody; it does not certify direct reading.

The submitted candidate is
`d05c7ed89f9de61f67872faeb06c84688a02f68134eb40bbf5db889c6c08204b`.
The report SHA-256 is
`70134ded9f3d120a68f72ed16f94fcd14c93c12a60b003334753898ae0b8bbca`.
The accepted public check names that candidate, and submission reports its current
public-check flag true. All nonreport files match the starting saved repair.
