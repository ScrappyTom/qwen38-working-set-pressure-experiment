# Compiler incident comparison results

One branch completed a correct repair and historical report with a passing check
and submission. Both smaller-input branches stopped without a contribution; the
second resident branch exhausted physical context without emitting an action.
The approved attempt is closed, sealed and fully reviewed, with no retry.

The strongest new host finding is that **eight accepted returns were removed from
the next sent input before Qwen could use their bodies**. The strongest separate
actor finding is that correct early analysis with all acquired evidence visible still
expanded into a 38,037-token unfinished response. Neither finding supports a
general condition-performance claim or an immediate wholesale refactor.

## Outcomes and cost

Shared prefixes are counted once. Rows below show only newly performed work;
trajectory action counts include the relevant shared prefix.

| Segment | Requests / executed actions | Total trajectory actions | Input tokens | Generated tokens | Request seconds | Peak input | Outcome |
|---|---:|---:|---:|---:|---:|---:|---|
| C01 shared | 6 / 6 | 6 | 42,057 | 7,959 | 509.079 | 13,549 | Fork at next full input 17,481 |
| C01 R23808 | 8 / 8 | 14 | 157,604 | 60,235 | 3,915.140 | 22,067 | Checked submission |
| C01 X16000 | 23 / 23 | 29 | 329,572 | 188,373 | 11,862.544 | 15,989 | Rejected patch, then input denied |
| C02 shared | 8 / 8 | 8 | 56,473 | 13,967 | 888.266 | 14,607 | Fork at next full input 18,539 |
| C02 X16000 | 20 / 20 | 28 | 283,644 | 143,782 | 8,866.502 | 15,971 | Acquisitions only, then input denied |
| C02 R23808 | 1 / 0 | 8 | 18,539 | 38,037 | 2,517.750 | 18,539 | Empty final, context exhausted |

Total actual cost is **887,889 input tokens, 452,353 generated tokens and
28,559.281 request seconds (475.99 minutes)**, including the incomplete response.
These request times exclude subsequent tool execution and are not completed-task
times. The [receipt](EXECUTION_RECEIPT.md) reports recorded wall/processing scope
without treating missing failed-response timings as zero.

C01 R restricts simplification to UAdd on exact int/float constants and preserves
other unary operations. Its report correctly identifies normal-only changes in
BUILD-A and normal plus Weibull changes in BUILD-B, with `-log(r)` → `log(r)` as
the first changed expression in both. The exact successor passes all 26 public
contract/report cases and is submitted:
`51da4d95fe0c35e34696055d8d6c3e59aac446554ec214d3e9e3dd5fe2855582`.
The result is bounded contract evidence, not a general proof of application correctness.

The first and only check has 20 actions available before and 19 after it.
There is no failed check or correction cycle. C01 X's only patch is rejected
because its guessed old text does not exist. C02 X never edits. Their next inputs
fail admission at minimum sizes 16,445 and 16,154, with three/four actions left.
Both candidates remain at the initial version. The actor never receives either
branch's final result in a further decision.

## What the complete transcripts establish

The [direct audit](DIRECT_TRANSCRIPT_AUDIT.md) covers all 66 complete thinking/final
fields and actual input/result transitions. Navigation, exact guards, historical
retrieval and successor checking work on exercised paths. Useful reacquisition
restores absent source or requirements in many X turns. C01 R also rereads an
unchanged report already visible, despite recognizing the applicability rule;
this is a different cost from absent-source recovery.

Later X acquisition can remove the evidence needed to combine results. In eight
transitions it removes even the newly returned body. Qwen often identifies this
absence accurately, but progressively explores unsupported source/incident guesses
and tries to infer readiness from the remaining action budget. C01 eventually
executes a guessed patch; C02 keeps acquiring. The evidence supports both host
delivery limitations and costly actor choices, not a blanket diagnosis of memory
failure or redundant retrieval.

C02 R009 has all eight acquired bodies resident. It correctly reconstructs the
report and a viable repair early, repeatedly weighs optional folding and further
inspection, and later invents a reversed `ast.copy_location` contract. That false
premise leads it to speculate about a different historical emitter/current
checkout. It exhausts all physical space without a final. No proposed patch,
read or self-described correction in that thinking was executed. The
[offline API fact check](LOCAL_API_FACTS.json) distinguishes these claims from
actual Python behavior; its facts were not supplied to the actor during the run.

Long thinking therefore has more than one observed setting: absent evidence and
shrinking allowance in X, and repeated reconsideration plus a false library premise
with evidence resident in R. These transcripts do not isolate the causal share of
model tendencies, xhigh, interface presentation or any one passage.

## Decision

Preserve the successful contribution and all adverse outcomes. Retain exact
custody, guards, the complete tool reference and consulted framing. **Do not rerun
this frozen comparison or launch another pressure task unchanged.** First qualify
usable result delivery and the accumulated-history input floor offline. Then use
a small neutral Qwen conversation to examine the actual interpretation before
settling any presentation change, as described in [next steps](NEXT_STEPS.md).

No host/representation/reasoning change or further live exposure is made here.
The [apparatus finding](APPARATUS_FINDING.md) preserves the limitations: two
development cells, unequal completion, no failed-repair recovery, no controlled
hypothesis reversal, immediate omission of thinking, and no qualified 25k envelope.
Retaining the presentation remains a possible outcome of the next consultation.
