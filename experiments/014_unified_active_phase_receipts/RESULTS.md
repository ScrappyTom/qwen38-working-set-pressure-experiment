# Experiment 014 results and decision

## Executive result

Experiment 014 is a valid positive result for the narrow receipt-presentation
question.

All eight final candidates passed hidden grading. `T25-UNIFIED` submitted 4/4
branches versus 3/4 for `T25-SPLIT`. In the one divergent pair, the split
condition ran eleven passing checks and exhausted its sixteen-call budget;
the unified condition numbered the first passing check as the next active-phase
receipt and submitted immediately.

The stale-check family passed its safety gate in all four branches: after a
patch changed candidate V1 to V2, Qwen ran a new public check bound to V2 before
submission. Unifying the receipt plane did not make an old valid check appear
current.

The supported conclusion is:

> One exact monotonic active-phase receipt sequence is preferable to a frozen
> receipt prefix plus unsequenced recent history. It removes an observed
> closure ambiguity while preserving exact result custody and validity
> bindings. It does not eliminate every redundant action.

## Formal outcomes

| Family / seed | Condition | Hidden | Submit | Calls | Prompt tokens |
|---|---|---:|---:|---:|---:|
| CLOSURE / 173205 | T25-SPLIT | pass | yes | 7 | 33,128 |
| CLOSURE / 173205 | T25-UNIFIED | pass | yes | 7 | 33,287 |
| CLOSURE / 223607 | T25-SPLIT | pass | no | 16 | 92,146 |
| CLOSURE / 223607 | T25-UNIFIED | pass | yes | 7 | 33,325 |
| STALE / 173205 | T25-SPLIT | pass | yes | 12 | 60,758 |
| STALE / 173205 | T25-UNIFIED | pass | yes | 11 | 57,139 |
| STALE / 223607 | T25-SPLIT | pass | yes | 11 | 55,795 |
| STALE / 223607 | T25-UNIFIED | pass | yes | 11 | 56,943 |

The non-submitted split candidate is hidden-correct. That establishes mutation
quality but does not convert the exhausted branch into a formal completion.

## Aggregate economics

Branch totals exclude shared prefixes because each exact prefix was executed
once and then forked.

| Condition | Calls | Prompt tokens | Completion tokens | Endpoint time | Hidden pass | Submit |
|---|---:|---:|---:|---:|---:|---:|
| T25-SPLIT | 46 | 241,827 | 22,488 | 1,659.4 s | 4/4 | 3/4 |
| T25-UNIFIED | 36 | 180,694 | 17,257 | 1,262.5 s | 4/4 | 4/4 |

Unified receipts reduced branch calls by 21.7%, prompt tokens by 25.3%, and
endpoint time by 23.9%. These aggregate effect sizes must be interpreted with
care: the avoided eleven-check loop accounts for most of the difference. In
the other three pairs, the call difference was 0, -1, and 0, and prompt-token
differences were +159, -3,619, and +1,148.

## Hypotheses

### H1 — A unified exact receipt sequence prevents the split-clock closure loop

Supported, with limited sample scope. The fresh closure seed 223607 split path
repeated the public check until exhaustion, while its paired unified path
submitted immediately after receipt sequence 6 recorded the passing check.
The other closure seed submitted in both conditions.

### H2 — Unified receipts preserve candidate-bound stale-check safety

Supported in all four stale-check branches. Every submission followed a
passing check bound to the repaired current candidate. No branch treated an
earlier predecessor check as sufficient after mutation.

### H3 — Unification removes redundant confirmation generally

Not supported. Both conditions repeated the initial V1 check before the first
receipt reconstruction. Both conditions also reread or rechecked in the second
stale seed after the current V2 check. Unified receipts fix progress identity;
they do not determine evidence sufficiency or optimal action policy.

### H4 — Exact result bodies need not remain resident in the receipt plane

Supported for these tasks. Mechanical receipts were sufficient for closure in
the decisive pair. One unified branch reopened a prior target result on demand;
the other branches did not need externalized bodies to reconstruct progress.

## Architectural decision

Promote the **unified active-phase receipt rule** into the minimal controller:

- every active-phase action/result pair, including a rejected attempt, receives
  one monotonic sequence identity before and after reconstruction;
- exact candidate/environment/check/file/range bindings remain attached;
- compact progress receipts remain resident within their bounded contract;
- large result bodies remain exact in external custody and reopenable on
  demand;
- recent full bodies may remain in history, but they do not form a second
  progress clock.

Retain the rest of the earned architecture unchanged: exact purpose/progress,
current world bindings, hierarchical readable P0, maximal exact paging,
identity-only observation directories, low bounded private reasoning, exact
tool effects, checks, submission, replay, and evaluator separation.

Do not add suppression, caching, semantic summaries, ranking, relationships,
embeddings, host-selected relevance, or more reasoning. Experiment 014 does
not earn those features.

## Remaining gaps

The project now has a coherent minimal recurrent controller, but Experiment 014
does not establish:

- arbitrary-scale receipt-ledger paging or very long active phases;
- strategic continuity where the model must preserve hypotheses or rejected
  alternatives rather than explicit user-authored phases;
- dense observation selection among many plausible current records;
- large-repository P0 search/expansion economics beyond the tested synthetic
  hierarchy;
- purpose revision after prior work has completed;
- reliability across other actors, domains, or reasoning profiles.

The next high-ROI move is not another receipt micro-optimization. Carry the
promoted exact controller into a broader long-horizon/larger-world build that
varies task geometry while leaving the controller fixed. Any new feature must
be earned by a repeated outcome-level failure in that work.

No automatic successor experiment is authorized by this decision.
