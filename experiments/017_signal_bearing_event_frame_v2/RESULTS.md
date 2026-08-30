# Experiment 017 Results and Decision

## Executive result

Signal-bearing event-frame V2 passes its offline capacity and exposed live
qualification.

The important result is not that Qwen could use an opaque handle. It is that a
small resident mechanical description told Qwen what had happened and what
exact payload was available; Qwen then opened the payload only when its content
was needed.

V2 is promoted as the event representation for a future fresh large-world
R50/X25 comparison. This development run is not that comparison.

## Offline capacity result

| Sixteen accepted patch events | All 16 payloads external | 15 external + one new maximum resident | X25 status |
|---|---:|---:|---|
| maximum-schema ASCII | 11,426 prompt tokens | 12,947 | pass |
| reasoning-compatible escaped controls | 11,590 prompt tokens | 15,027 | pass |

The worst complete one-new-event request consumes 18,039 tokens after the
512-token runtime allowance and 2,500-token output reserve, leaving 6,961
tokens below the 25,000-token ceiling. Exact R50/X25 request bytes remain
identical before externalization. The fully resident escaped case still reaches
authentic R50 pressure and fails closed, as intended.

## Live development result

| Case | Seed | Calls | Action path | Hidden | Checked/submitted |
|---|---:|---:|---|---:|---:|
| closure mint | 173205 | 2 | check → submit | pass | yes |
| closure mint | 223607 | 4 | reopen result → read → check → submit | pass | yes |
| stale sable | 173205 | 2 | check → submit | pass | yes |
| stale sable | 223607 | 2 | check → submit | pass | yes |
| historical action signal | 173205 | 6 | reopen event → read → rejected patch → accepted patch → check → submit | pass | yes |
| historical action signal | 223607 | 5 | reopen event → read → patch → check → submit | pass | yes |

Totals:

- 6/6 hidden passes;
- 6/6 public checks and submissions;
- 21 HTTP completions;
- 20 accepted actions and one mechanically rejected stale binding;
- zero retry, repair, rescue, capacity denial, parser failure, transport
  failure, or runtime accounting delta.

## The signal test

The exact marker `ARCHIVE-Z7` was absent from both initial historical-case
coding requests, endpoint requests, and rendered prompts. Each request exposed
only:

- accepted `patch`;
- target `archive/source.dat`;
- predecessor and successor bindings;
- external field names `old,new`;
- payload size/hash;
- address `EVT-0001`.

Both seeds explicitly reasoned that this event was the source of the removed
marker, selected `reopen_event(EVT-0001)`, recovered the exact old value, read
current `report.py`, used the recovered value in the patch, checked, and
submitted.

The handle did not provide the meaning. The resident event fields provided a
readable lead; the handle provided exact custody access.

## Closure and validity

All four donor branches reconstructed their outstanding obligations after
large bodies left context. Both stale-check branches used the resident candidate
bindings to reject the predecessor check as authority for the current candidate,
ran a new check, and submitted. Neither needed old stdout/stderr.

One closure branch reopened an exact observation result and reread the patched
file before closure. That was unnecessary but model-chosen. It demonstrates
that making exact evidence accessible does not guarantee that access will be
economical; it does not indicate missing signal.

## Decision

Promote V2 with this invariant:

```text
resident:
  event sequence
  action type and readable target
  acceptance/status
  predecessor/current/successor bindings
  range/continuation/check/terminal identity
  exact payload field names, size, hash, and access method

external exact custody:
  patch old/new
  source/result/check/diff bodies
```

An opaque handle must never be treated as model-facing metadata by itself.
Every handle needs enough mechanically grounded resident signal for the model
to decide whether opening the exact payload serves its current obligation.

Do not add a summary, relationship layer, ranking, embedding, cache
substitution, duplicate suppression, or semantic host routing.

## What is not yet established

Experiment 017 does not show that V2 improves fresh large-world performance.
The diagnostic explicitly instructed Qwen to reopen the historical payload,
and the donor cases were previously exposed. It also does not prove that every
resident field is individually necessary.

The remaining earned question is end-to-end viability:

> In a fresh large world with several authentic pressure transitions, does the
> same minimal controller preserve quality and closure when one signal-bearing
> event plane replaces resident chronology?

The next study should freeze V2 unchanged and compare fresh R50 versus X25
worlds. It should not add another representation feature. The comparison must
measure exact payload reopens, unnecessary confirmations, prompt economics,
current-candidate checks, closure, and hidden quality.

## Falsifiable hypotheses for the next study

1. **Progress hypothesis:** V2's resident structural fields will prevent the
   missing/split-progress failures seen before unified receipts.
2. **Demand-loading hypothesis:** X25 will reopen old action/result payloads
   only when their absent content is needed for a current decision.
3. **Validity hypothesis:** candidate/check bindings will continue to prevent a
   stale check or observation from authorizing current action.
4. **Economic hypothesis:** externalizing bodies will keep X25 below its
   request ceiling without causing enough reopen churn to erase the gain.
5. **Failure discriminator:** if X25 still fails after correctly identifying
   progress and evidence, the cause should be acquisition/closure policy rather
   than representation ambiguity.
