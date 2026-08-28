# Experiment 006 results and decision

## Executive result

The exact 25k reconstruction controller passed its first authentic live
pressure test.

Both T25-R1 branches matched their 50k controls on hidden correctness, public
check, submission, and terminal candidate identity within each pair. The source
branch reacquired its governing policy through P0 and bounded reads. The
observation branch reopened the correct historical runtime result on its first
post-reset action.

## Primary outcome

| family | C50-R1 | T25-R1 | T25 governing reacquisition |
|---|---|---|---|
| source | hidden pass, submitted | hidden pass, submitted | yes, before mutation |
| historical observation | hidden pass, submitted | hidden pass, submitted | yes, first action |

Every prospective quality requirement passed. There were no retries, repairs,
rescues, stale bindings, model-visible evaluator facts, or infrastructure
failures.

## Economics

Across the continuation branches:

| measure | C50-R1 | T25-R1 | T25 change |
|---|---:|---:|---:|
| calls | 12 | 13 | +1 |
| prompt tokens | 345,923 | 49,401 | -85.7% |
| completion tokens | 4,998 | 5,609 | +12.2% |
| prompt + completion | 350,921 | 55,010 | -84.3% |
| endpoint time | 1,138.749 s | 399.139 s | -64.9% |
| largest prompt | 29,881 | 6,175 | -79.3% |

The treatment paid for exact reacquisition but avoided repeatedly processing
the large Phase A chronology. The source treatment required three additional
calls; the observation treatment required two fewer because it avoided C50's
redundant reopen and dependent-source inspection.

## Answer to the project question

For these two fresh cases, yes:

> Exact external custody plus readable P0 orientation, a verbatim active-step
> pointer, ordinary exact acquisition, and hard-capped low reasoning allowed
> the same Qwen actor to continue correctly after its authentic chronology no
> longer fit the 25k active envelope.

This is the first direct positive evidence for the project's original
working-set goal. Earlier work established the pieces separately. Experiment
006 shows them operating together across a real boundary:

```text
authentic long chronology
          -> exact fork
          -> fresh bounded context
          -> model-selected exact reacquisition
          -> correct mutation
          -> check
          -> submit
```

## What is earned

Retain the exact bundle used here:

- exact external custody and replay;
- current candidate/version binding;
- readable task-independent P0 paths, symbols, signatures, and ranges;
- verbatim prospectively frozen active-step pointer;
- identity-only historical observation directory and exact reopen;
- ordinary bounded source tools;
- server-enforced 512-token private reasoning, excluded from later history;
- exact pre-request capacity guard;
- separate prepared-invocation and HTTP-completion accounting.

No semantic summary, declaration, relationship inventory, embedding/ranking,
or host-selected relevance is earned or needed by this result.

## What is not yet earned

- reliability beyond two fresh geometries;
- repeated pressure transitions;
- stable purpose and binding across several resets;
- repository-scale P0 paging;
- reconstruction after multiple intervening mutations/checks;
- semantic digestion or lossy compaction.

The C50 observation branch also demonstrates that retained chronology does not
guarantee optimal use: it reopened the same observation twice. The result is a
capability pass for T25, not proof that either controller is behaviorally
optimal.

## Decision

Promote the exact controller to a small fresh recurrent-boundary study. The
next study should hold the actor and controller fixed and require two pressure
transitions in one task, with current candidate/check bindings changing between
them. It should include both:

1. a source fact needed again after a later mutation; and
2. a dynamic observation whose validity is tied to a specific candidate or
   environment state.

Do not add new metadata or memory features before that test. The active
Experiment 006 authorization does not itself authorize recurrent live
execution; this result is the evidence for that next owner decision.
