# Bounded parser continuation: stopped for a host restriction

The bounded host is implemented and qualified offline. Its first Qwen attempt
did **not** complete the saved parser contribution. Eight responses acquired
source and attempted recovery without saving tests or documentation. The reviewer
stopped during C09 after identifying repeatable host restrictions. This adaptive
stop is declared separately from the frozen natural-stop rules.

The clearest result is a capacity-policy error: the host withheld or rejected
small complete results that fit the declared input allowance because it required
reserved feedback room to remain unused after delivering feedback. C04's full
check fits at 23,348 tokens and C05's complete search at 22,838, both below 23,808.
The latter instead becomes status-only, then a 53-byte recovery prefix containing
no hit. These are actual saved native trials, not estimates.

Prospective corrections prepared in an isolated checkout make that reserve
spendable, restore file-filtered grouped history, and turn candidate-policy errors
into clean rejected edits. Two exact-state counterfactuals and 23 selected tests
qualify those host corrections offline. They do not establish what Qwen would do
after corrected feedback. The original run remains unchanged.

| Completed call | Input tokens | Generated tokens | Request seconds | Actual action |
| --- | ---: | ---: | ---: | --- |
| C01 | 3,384 | 213 | 17.953 | Root tree |
| C02 | 3,513 | 970 | 56.141 | Full library read |
| C03 | 16,097 | 9,325 | 571.547 | First test page |
| C04 | 22,774 | 18,844 | 1,233.844 | Check recovery rejected |
| C05 | 22,732 | 10,772 | 708.781 | Search; result withheld |
| C06 | 22,800 | 5,939 | 407.922 | Search-result header recovered |
| C07 | 22,784 | 5,956 | 409.766 | Next test read rejected |
| C08 | 22,776 | 9,828 | 649.265 | Check recovery rejected again |
| **Total** | **136,860** | **61,847** | **4,055.219** | **No saved contribution** |

Completed model requests cost **67.587 minutes**. Tool processing and admission
for those eight actions add 46.264 seconds. There is no normal final loop timer.
C09's 22,762-token input was sent, but its generated usage/time did not return;
the table excludes it. The attempt sent nine of its maximum 24 requests.
Minimum sampled GPU free memory was 272 MiB under the already accepted advisory
policy. No setting changed, and no observed CUDA or truncation error caused stop.
Concurrent brief offline CPU work makes these descriptive development timings,
not a controlled speed comparison.

The correct starting library, existing tests and documentation remain exactly
unchanged. The existing failed overall check still applies; there was no fresh
check or submission. Source retention succeeded mechanically, but Qwen never
executed work_on to select a smaller group, and no new atomic edit was tested by
the actor. Offline history scaling and edit/continuation success remain offline
evidence. The new run does not establish long-task capability.

Direct review finds both useful test reasoning and costly repeated speculation.
Qwen sometimes assumes absent earlier conversation persists and later treats a
53-byte exact page as if all 335 bytes were visible. Conversely, the prior search
query was actually absent from its recent summary, so its false reconstruction
of that query must not be called overlooking visible evidence. Delivery,
selection, interpretation and action completion remain separate questions.

All eight complete outputs were directly read. Independent verification checks
208 source identities, 497 sealed artifacts, 62 native preparations, all eight
actions/states and raw responses. The process-group stop bypassed normal closure;
the later [explicit stop receipt](EXECUTION_RECEIPT.md) preserves that limitation.
See [host findings](HOST_PATH_AUDIT.md), [artifact assessment](APPARATUS_FINDING.md),
[transcript audit](DIRECT_TRANSCRIPT_AUDIT.md) and [next steps](NEXT_STEPS.md).

Retain the archive and guards; correct the demonstrated admission defects before
more exposure. A small consultation should examine the specific visibility and
operation-identity misunderstandings. Then evaluate a completed saved contribution
under a newly declared package. Do not restart this attempt, spend its unused
allowance automatically, or describe the broader owner goal as achieved.
