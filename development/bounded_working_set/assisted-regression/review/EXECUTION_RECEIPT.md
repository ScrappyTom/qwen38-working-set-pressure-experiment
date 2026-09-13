# Execution receipt

The owner approved the revised assisted recommendation. Preparation was published
at 506627f7; T01 review/T02 preparation at c70bfcaa; T02 review/T03 preparation at
cd641b0a; T03 review/T04 preparation at 56b44059. All four requests bind the same
227 source identities. Each prepared package includes its exact native input and
token count; subsequent packages preserve the actual preceding review, candidate,
state, dialogue and response-seal ancestry. Earlier attempts remain consumed.

Actor: Qwen3.8-27B UD-IQ3_XXS; q4_0 K/V; context 56,576; no MTP; thinking on,
xhigh, uncapped; seed 961207; temperature 1.0, top_k 20, top_p 0.95, min_p 0,
repeat penalty 1, presence/frequency penalties 0; cache off. Exact model, runtime
and tokenizer identities are in each plan/seal. The input ceiling is 23,808;
32,768 is a prospective generation reserve, not a cap or completion guarantee.

| Reply | Input | Generated | Request seconds | Operation | Minimum free MiB |
|---|---:|---:|---:|---|---:|
| T01 | 6,423 | 18,093 | 1,010.516 | patch accepted | 263 |
| T02 | 7,501 | 3,258 | 186.500 | patch accepted | 263 |
| T03 | 7,765 | 360 | 36.375 | check accepted; overall false | 265 |
| T04 | 8,183 | 5,273 | 298.657 | discussion only | 84 |
| Total | 29,872 | 26,984 | 1,532.048 | three operations | 84 |

Peak sent input: 8,183. Peak measured input: 8,611, including the unsent closing
discussion. Response processing totals 3.999 seconds, including native admission
and tool execution. Sum of owned-turn intervals is 1,665.273 seconds; the interval
from first turn preparation to final closure is 2,138.342 seconds and includes
intervening reviewer work and preparation. These are four separate owned runtime
lifecycles, not one uninterrupted autonomous loop or a controlled speed comparison.

VERIFICATION-01 through -04 verify all 127 sealed public run files, 100 chained
records, eight native inputs, three actual operation replays and discussion-only
closure. All twelve local private runtime files also match. The checker is rerun
offline for exact replay; that is not another Qwen invocation. Exact seal hashes
are in SESSION_MEASUREMENTS.json. Every full thinking/final response was directly
reviewed separately; mechanical verification does not certify direct reading.

All runtimes shut down normally and free the dedicated port. Full GPU offload,
context, q4 cache, no-MTP and cache-off checks match. No transport error, output
truncation, CUDA failure, retry or operator interruption occurred. T04 reaches
84 MiB free, with 103 samples below 100 MiB; the cause of reduced availability
is unestablished. The existing advisory policy remains unchanged, and this is
not a comfortable-margin claim or qualification for another workload.

The final candidate is
8b8079f15ab90ea4ed23ad18e68c2c5bb175c686f3ca578fcb812a1657314654;
the test fingerprint is
5099d5d0f9a05dfda745ee39f529278e7f1b8a97ad5deb32015fb04c54b7d4eb.
Only the test file differs from the starting candidate. The complete feedback
from each operation is present in its next actual model input, and the final
checked candidate remains unchanged through discussion closure. Four replies
are consumed; two are closed unused. Full backport status remains incomplete.
