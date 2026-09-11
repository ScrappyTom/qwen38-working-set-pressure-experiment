# Results — ordinary working-loop pilot

**Both independent runs complete the full evidence-to-action loop.** Qwen finds
the relevant nested source, makes the same correct one-line repair, consumes
the actual edit result, checks the successor and submits it. L01 takes 10
actions; L02 takes 14. All 24 calls are sealed, replay-verified and directly
reviewed, including complete thinking and following host decisions.

This supports retaining the repaired host and complete tool reference for
further task work. It also exposes substantial deliberation and framing friction
that a passing submission alone would conceal. It does not establish continuity
across pressure or economical performance on a general investigation.

## Completed contribution and costs

Both change only `src/addressable_information_layer/patching.py`, line 112:

```diff
-    new_map = address_map
+    new_map = build_address_map(new_artifact)
```

The final candidate is
`23b5c17999963faf7453c68a6b537ae6c447555f77eb0a835bfa659ad47e89aa`.
The initial candidate is
`0f67505a0ad439530ae16095fac49db730b34ca253794657e06273420c2ba872`.
The task's public check passes its eight concrete assertions in each run:
application, exact extraction/current reopen, preserved neighbor, stale exact
reference rejection, another update/reopen and unchanged-content access. The
printed propagated map/version match is also true. Direct diff review confirms
unrelated source and the hash-protection implementation are unchanged. Matching
the donor is not used as the acceptance criterion.

| Measure | L01, seed 104729 | L02, seed 130363 |
|---|---:|---:|
| Submitted with current passing check | Yes | Yes |
| Calls/actions, of 20 allowed | 10 | 14 |
| First and only check | Call 9, pass | Call 13, pass |
| Actions remaining before / after check | 12 / 11 | 8 / 7 |
| Actual next turn after check | Sent; submits | Sent; submits |
| Cumulative native input tokens | 91,421 | 139,142 |
| Cumulative generated tokens | 17,501 | 31,725 |
| Peak native input tokens | 15,644 | 20,027 |
| Model-request seconds | 1,165.000 | 2,087.234 |
| Host response-processing seconds | 0.797 | 1.269 |
| Run wall seconds | 1,169.625 | 2,095.406 |

Total input is **230,563 tokens**, generation **49,226**, and model-request
time **3,252.234 seconds**. Run wall times are about 19.5 and 34.9 minutes for
this single-line repair task. These are two observed trajectories under one
configuration, not a treatment effect or dependable latency estimate. The
complete reference does not eliminate lengthy deliberation.

Request time excludes subsequent response handling. Response-processing time
includes validation, tool execution and custody, not just tool work. Run wall
time also includes per-turn reconstruction/rendering/admission; it is distinct
from whole-attempt runtime startup and shutdown. Saved-text recounts are 17,002 /
31,145 reasoning tokens and 468 / 538 final-text tokens; separate retokenization
is not the original generated-token segmentation. All metrics and per-call
details are in [VERIFICATION.json](VERIFICATION.json).

## What the transcripts establish

| What Qwen saw | What Qwen did | What the host did next | Interpretation |
|---|---|---|---|
| Scoped root/package pages and real search results, without a reading list | Descended to source; L02 also used a useful file outline | Returned exact requested structure/source and sent later turns | Useful navigation survives the clearer scope wording. |
| The preceding `src` child-path page still resident | Both runs requested that same parent page again | Returned identical evidence, counted the call and continued | Avoidable navigation, not a missing-memory event. |
| Exact source, current file/candidate identity and full required action forms | Used the actual helper semantics and pre-edit guards for the one-line repair | Returned the exact successor/diff and included it in the next request | Correct operational composition, beyond merely accepted JSON syntax. |
| Its own successful patch plus the unchanged original incident description; no failure after that patch | Repeatedly questioned whether the patch was the incident or an incomplete repair; L02 confirmed changed source, then both checked | Supplied current source where requested, executed a new current-candidate check and continued | Consequential interpretation effort despite ultimate success. No pressure externalization caused it. |
| The actual passing result for the unchanged current candidate | Used its diagnostic outcomes and submitted, declining contemplated rechecks | Accepted terminal submissions; no further model request | Useful evidence consumption and closure. |

The post-edit uncertainty is the strongest finding. L02-012 initially calls its
own repair the accepted edit described by the task, then recovers. L01-009 and
L02-013 repeatedly question that same episode distinction and whether another
repair is needed. Those responses generate 4,337, 4,082 and 8,084 tokens,
respectively; their whole costs cannot be assigned to a single cause. Earlier
responses also spend substantial time rederiving the patch or questioning whether
unchanged exact source must be read immediately before editing.

Private thinking is omitted immediately; the source, old/new action, diff and
bindings remain. The duplicated incident text, generic continuation framing,
and candidate library's overlap with the operating host vocabulary are plausible
contributors. The transcript supports a concrete framing/reconstruction issue,
not a claim that a memory mechanism failed or would solve it.

L02's extra source read is of the **changed** file, lines 88–158. Keep it classified
as confirmation after mutation, separately from exact duplicate navigation or
absent-source recovery. Both final responses consider another check and correctly
decline it. No wholesale reread suppression is justified.

## Boundaries and decision

No check fails, action is rejected, input is withheld or response is truncated.
All 22 nonterminal results enter actual subsequent model calls. No externalization,
historical-retrieval action or context boundary occurs. Neither actor executes
the failing baseline before repairing. The source itself names a stale map and
the injected fault is conspicuous, so this is completed integration work, not a
demonstration of independent discovery or changing direction after new empirical
evidence rejects a hypothesis. The [apparatus audit](APPARATUS_FINDING.md)
preserves these limits.

Both runs use Qwen3.8-27B UD-IQ3_XXS, q4_0/56,576, no MTP, thinking on/xhigh/
uncapped with the frozen sampler and separate fresh histories. GPU free memory
reaches **316 MiB** under the owner's already accepted advisory policy, with
normal completion and no configuration change. The largest output is 8,084
tokens and minimum physical space after a response is 29,275. These outcomes
do not justify silently shrinking G=32,768. That reserve still limits input to
23,808, so the prospective 25k input contrast remains unqualified.

Close this two-run pilot and retain its complete evidence. Keep the return-path
repairs, exact records, version-bound operations, full reference and accurate
navigation/resource wording. No newly observed host implementation defect
requires a repair before the next preparation; that is limited to the inspected
paths, not a general host certification. Keep exact grouping and object-scope
ideas recorded; do not restart interface micro-tests or build a working account
solely because these successful responses are verbose.

The next work should be **offline selection of a fresh investigation outside
the agent/metadata domain**, with an observable symptom, plausible competing
explanations and accessible evidence that actually separates them. Use the
current representation initially. Describe the reported incident distinctly
from the actor's own working history, without supplying a diagnosis or required
next action. Inspect source, task, diagnostics and repeated evidence copies;
qualify navigation, the behavioral check and task-specific action/input/generation
allowances. Use a natural pressure opportunity if one exists; report its absence
instead of padding. A later live scope needs a concrete preparation and the
existing separate owner execution decision, not another governance layer.

Keep the owner's q8_0/32,768 preference as the primary capacity option when the
qualified workload and reserve fit, with q4_0/56,576 available when needed.
Choose and freeze one configuration before any new comparison. No MTP, silent
thinking cap, mid-run capacity switch or automatic successor is authorized.

Falsifiable questions for that preparation and later study:

1. With a clearly separated reported incident and working history, does Qwen
   still attribute its own accepted repair to the original incident or repeatedly
   doubt whether recorded work is its own? Score exact interpretations and
   actions, not just shorter output; this is not an instruction to rerun these cells.
2. After evidence rules out an explanation, does later action use that evidence
   or correctly reacquire/reconstruct it? Compare every relevant copy immediately
   before/after an actual boundary. Separate omitted private rationale from removed
   evidence and from present evidence used incorrectly.
3. Can useful investigation complete within its prospectively qualified native
   input, generation and action allowances? A stop before the meaningful pressure
   contrast is a capacity limitation, not a demonstrated continuity failure.

Companion products: [execution receipt](EXECUTION_RECEIPT.md),
[host-path audit](HOST_PATH_AUDIT.md), [apparatus finding](APPARATUS_FINDING.md),
[complete direct transcript audit](DIRECT_TRANSCRIPT_AUDIT.md), and
[decision](DECISION.json). No further model requests are authorized by these results.
