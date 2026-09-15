# Recovery contribution: saved work, no checked completion

The owner-directed attempt at frozen commit `feb7b62b` is closed after eight
requests and eight operations. Qwen saves three tests and a documentation addition,
requests no check, and makes no submission. Independent assessment of the unchanged
saved candidate finds one failing test, two failing documentation examples, and
incomplete exact-diagnostic assertions. Earlier work is preserved. The four unused
operations are closed; no coaching, retry, rescue or extra inference enters this run.

The host delivers all seven nonterminal results completely and retains the acquired
sources. The decisive implementation was never acquired. C04 recognizes that gap,
guesses the cross-section reference and weakens its diagnostic assertions. C08 then
uses that untested test assertion as evidence for the documentation. The wrong
expectation survives in saved work and spreads to a second artifact. This is a
concrete distinction between preserving an assertion and establishing its truth.

## Complete contribution and cost

This is uncoached development from the actual prior C05 checkpoint, selected by the
researcher and inheriting earlier assembly assistance. It is neither a fresh task
nor an autonomous end-to-end backport. The new seed, checkpoint, allowance and shared
reference prevent a causal comparison with the preceding full attempt.

Qwen3.8-27B UD-IQ3_XXS uses medium thinking, uncapped generation, q4_0 K/V, 56,576
physical context, no MTP and no prompt cache reuse. Seed is 961213; allowance is
eight requests/twelve operations. Effective wire and native settings were verified.

| Request | Input tokens | Generated tokens | Request seconds | Actual operation |
|---|---:|---:|---:|---|
| C01 | 4,829 | 571 | 39.156 | Read test imports and fixture header, lines 1–80 |
| C02 | 5,503 | 517 | 38.281 | Search tests for the exception name |
| C03 | 5,950 | 506 | 38.843 | Read nearby direct-construction pickle tests, 1750–1850 |
| C04 | 6,913 | 16,695 | 933.391 | Save three new tests; no requested check |
| C05 | 8,047 | 863 | 62.718 | Read docs 200–300; intended interpolation section is elsewhere |
| C06 | 8,769 | 2,198 | 135.235 | Search docs for the exception name |
| C07 | 8,936 | 1,844 | 116.906 | Read the actual exception entry, 1340–1406 |
| C08 | 9,508 | 5,463 | 314.578 | Save documentation; no requested check or later model call |

Totals: **58,455 input tokens, 28,657 generated tokens, 1,679.108 model-request
seconds (27.985 minutes), and 1,701.532 task-loop seconds (28.359 minutes)**.
C04 accounts for 58.3% of generation and 55.6% of request time. Its thinking mixes
useful test construction with repeated reconsideration of information it has not
obtained. Those percentages locate the cost; they do not classify every token as waste.

Peak sent input is 9,508, below the unchanged 23,808 ceiling. Peak input plus
generation is 23,608. Every response ends normally within the prospective 32,768
generation reserve. No capacity rejection, source eviction or pressure boundary
occurs. Sampled free GPU memory reaches 151 MiB under the accepted advisory policy,
without observed CUDA failure or truncation. This is not a comfortable-margin claim
or qualification of every future workload.

Preparation, postclosure checks and review are outside those loop costs. Reviewer
time and Codex inference were not separately metered. This attempt's lower descriptive
cost than earlier attempts is not evidence of a controlled efficiency improvement.

## What the model saw, did and received

| Actual information | Qwen's interpretation/action | Host outcome | Supported interpretation |
|---|---|---|---|
| Initial selected source is displayed in feedback; prior rejection reasons are complete, proposed code absent | C01 calls the separate source list empty and considers earlier capacity failures; reads a useful header | Exact header delivered; original selection retained | Some scope confusion remains, but this read is useful and no capacity obstruction occurs |
| C04 has imports, old pickle examples and a valid insertion anchor; no library implementation | It repeatedly considers `gone` versus `b:gone`, chooses `gone`, saves tests without checking | Exact guarded edit accepted and new source delivered | Unsupported expectation enters saved work; acceptance establishes the edit, not correctness |
| C08 sees those saved tests and new exact doc source; no applicable passing check | It cites its own `_check_exc(..., 'gone')` as verification of cross-section behavior | Documentation saves the same wrong expectation | The visible work product is being used beyond what has been established about it |
| C07/C08 show two/one requests and six/five operations, with the counting rule | Thinking plans read, edit, check and submit as if the extra operations supplied additional decisions | One read then one patch; normal request-limit closure | Request planning is wrong despite truthful allowance display; no rejected over-budget action is emitted |

The library, EVT-0073 proposal and other historical evidence remain accessible,
but Qwen selects none of them. Recovering that particular proposal was optional;
constructing different correct work would have satisfied the task. Neither
`work_on` replacement nor historical retrieval is exercised, so their availability
is not a behavioral demonstration of recovery or evidence assembly.

All acquired current source remains available, with zero duplicate current-source
lines in the sent inputs and no exact-source reacquisition. The refreshed saved test
class remains present through documentation work. Prior private thinking is omitted
immediately by the declared interface. The C04 uncertainty was not a retained public
account, and no later pressure transition removed its supporting implementation:
that implementation was never acquired in this attempt.

## Actual artifacts and verification

The unchanged final candidate is
`4fcb261b9c8d30ed0a10690a3db251d3b51f74e2a3698d2e29fbf4a294d8ad73`.
Only the test and documentation files change. Independent postclosure checking runs
the original 359 tests successfully with five skips; the edited 362-test suite has
one failure, five skips and no errors. The eight existing backport contract cases
pass. The new cross-section test expects `gone` where the actual lookup reports
`b:gone`. Basic and same-section Extended tests pass, but exact class, original
argument tuple and diagnostic expectations remain incomplete.

Executing the exact new documentation against the saved parser attempts sixteen
examples and finds two failures: a fabricated Basic error message and the same wrong
cross-section reference. Prose also incorrectly claims a `rawval` attribute exists.
These are independent reviewer assessments, never feedback supplied to Qwen. They
do not constitute an actor failed-check/correction cycle or repair the saved work.

All eight full reasoning and final responses, actual inputs, results and transitions
were directly reviewed. Exact replay verifies eight operations, nine native inputs,
152 custody records and 280 source identities. The ninth native input qualifies the
terminal edit's resulting view; it was not sent as a ninth model request. All seven
nonterminal results enter the next actual input. Runtime closes normally.

See [transcript audit](DIRECT_TRANSCRIPT_AUDIT.md), [host audit](HOST_PATH_AUDIT.md),
[artifact review](ARTIFACT_REVIEW.md), [execution receipt](EXECUTION_RECEIPT.md),
[apparatus finding](APPARATUS_FINDING.md), [metrics](METRICS.json), and
[exact verification](VERIFICATION.json). The three preparation tests and previous
88 selected host tests retain their separately recorded scope; no new full host
suite was run for this results-only review.

## Decision and next question

Retain the host for development. This trajectory establishes no new mechanical
defect requiring a patch, and no success claim for the latest explanation or recovery
extension. It does show that exact saved work can preserve and amplify an unsupported
premise. More archive capacity or another generic context reminder would not address
the demonstrated information gap on this trajectory.

Before settling any further presentation or operating-policy change, use a small
separate consultation on the actual C04-to-C08 transition: what independently supports
the reference value, what is merely asserted by the saved test, and what can one
remaining response actually execute? Preserve Qwen's initial interpretation before
source-checked clarification. Ask for an operational decision, not an invitation to
invent an interface. Retaining the interface is a valid consultation outcome.
No consultation or successor request is part of this consumed run.

Two falsifiable development hypotheses follow. First, under concrete inspection
Qwen may distinguish a newly authored expectation from observed behavior and select
actual source or a check to resolve it; if it continues to promote the assertion,
the problem survives making that relationship the explicit question. Second, it may
correctly explain the response forms but still fail to plan within them during task
work; consultation agreement alone would not resolve the operational issue. Any
later intervention must be declared, qualified and judged through completed checked
work, including the cost and preservation of earlier contributions. Do not silently
add checking, extend this allowance, supply coaching, or fix these actor artifacts.
