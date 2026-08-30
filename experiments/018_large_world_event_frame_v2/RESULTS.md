# Experiment 018 Results and Decision

## Executive result

Experiment 018 is a valid mixed but materially positive end-to-end result.

The fully resident R50 event plane exhausted a 50,176-token physical context
in all four fresh trajectories before the actor could complete the long task.
The X25 controller continued every trajectory with a smaller 25,000-token
active envelope. It completed both candidate-bound observation tasks with
hidden-correct patches, passing checks, and submissions. It did not complete
either evolving-source task.

The strongest supported claim is:

> A single signal-bearing exact event plane can let this Qwen actor continue a
> fresh large-world task after the equivalent fully resident history can no
> longer fit, and can preserve enough grounding to reacquire a nonresident
> candidate-bound fact and use it in a checked hidden-correct mutation.

This is not yet a reliability claim. X25 succeeded in 2/4 trajectories, and
the successful geometry was one family under two seeds.

## Outcome table

| Family | Seed | R50 | X25 |
|---|---:|---|---|
| evolving source | 173205 | physical 50k stop, unchanged, hidden fail | reached failed check, diagnosed error, budget exhausted, hidden fail |
| evolving source | 223607 | physical 50k stop, unchanged, hidden fail | patched all targets, no check, budget exhausted, hidden fail |
| bound observation | 173205 | physical 50k stop, unchanged, hidden fail | hidden pass, public pass, submitted |
| bound observation | 223607 | physical 50k stop, unchanged, hidden fail | hidden pass, public pass, submitted |

Totals:

- R50: 0/4 hidden passes, 0/4 submissions, 4 physical capacity stops;
- X25: 2/4 hidden passes, 2/4 submissions, 0 capacity stops;
- 87 actual completions from 91 prepared invocations;
- zero retry, repair, rescue, rejected action, or runtime-accounting delta.

## Capacity and processing economics

R50's denied next requests required 55,139 prompt tokens in the source family
and 56,205 in the observation family before allowances. They could not be
issued inside the 50,176-token slot.

X25's maximum completed prompts ranged from 21,485 to 21,970 tokens. With the
512-token runtime allowance and 2,500-token output reserve, all remained under
25,000. The tightest admitted request had 18 tokens of remaining envelope.

| Condition | Conceptual trajectory calls | Cumulative prompt tokens | Hidden passes |
|---|---:|---:|---:|
| R50 | 30 | 705,818 | 0/4 |
| X25 | 71 | 1,116,835 | 2/4 |

These totals are not an efficiency win for X25. R50 processed fewer tokens
only because it was forced to stop earlier. The result is a capability
crossover under hard context constraints: X25 could continue and sometimes
finish work that R50 could not attempt further.

## What was learned about model-facing information

### 1. Readable signal plus exact custody works

The successful observation paths did not receive `HARBOR-K9` at the X25 fork.
They received readable observation identity, target, candidate binding,
size/hash, and an exact address. Both seeds selected the current candidate's
record, reacquired the exact body, used the marker in both patches, checked,
and submitted.

The lesson remains:

```text
handle alone = address, not information
readable type/target/status/binding = signal
handle + exact body = grounding
```

### 2. Exact presence does not guarantee integration

One source seed and one observation seed reread a completed ledger page even
though the visible event frame contained exact complete ranges. The frame was
truthful and sufficiently expressive; Qwen did not always integrate a long
list of events into a correct current-progress judgment.

This is a limit of merely presenting more exact metadata. Signal must be
readable at the decision point, not only technically present somewhere in a
large structure.

### 3. Exact reopen needs a canonical stable address

Both successful branches acquired the marker twice after the fork. One walked
a result-of-result handle chain. The other returned to the original observation
handle. Nothing was corrupted, but the generic custody representation made an
exact access operation produce a new competing address for the same payload.

The earned product-level correction is narrow: repeated access to one exact
body should retain one canonical source address and provenance. This does not
require ranking, caching, semantic summaries, or host-selected relevance.

### 4. Closure headroom is a first-class resource

The source task had an exact ideal path that could fit in eighteen actions. It
did not have room for one semantic correction or one duplicate acquisition.
Cell 01 used the public check to discover its mistake but could not patch,
recheck, and submit. Cell 02 lost the checking opportunity to one redundant
ledger read and an extra exact-source confirmation.

A viable long-horizon controller needs explicit reserve for verification and
correction, not merely admission of an ideal action path.

### 5. The source outcome is not pure continuity evidence

Both seeds read “use the exact current `active_prefix()` value” as a dynamic
function call. The checker expected a snapshot of the pre-change value. The
word “preserve” supports the checker, but the model's interpretation is
plausible and replicated. The 0/2 source result therefore mixes specification
clarity, semantic reasoning, and action economics. It should not be used as a
clean negative claim about the event frame.

## Decision

Retain the minimal architecture:

```text
exact authorized purpose
+ current candidate/resource state
+ readable P0 orientation
+ one monotonically sequenced signal-bearing event plane
+ candidate-bound observation identities
+ exact demand-loaded payload bodies
+ maximal bounded exact reads
+ 512-token ephemeral private reasoning
→ patch → check → submit
```

Do not add:

- semantic summaries;
- relationship graphs;
- embeddings or ranking;
- host-selected relevance;
- duplicate-read suppression;
- model-authored memory;
- unrestricted reasoning.

Experiment 018 has answered the immediate large-world viability question well
enough to stop representation micro-ablation. The architecture has a fresh
two-seed existence proof under authentic pressure. Its remaining limitations
are reliability and interface ergonomics, not absence of a viable mechanism.

Before ecological use, fix only the clearly earned implementation issue:
preserve a canonical exact payload address across reopen operations and make
the reopened source/provenance explicit. Qualify that mechanically; do not
claim it changes model capability without new behavioral evidence.

Then move to owner-controlled realistic work with clear acceptance semantics,
more action headroom for check/correction, and the same controller. The next
high-value evidence should come from varied real long-horizon tasks, not
another synthetic metadata feature comparison.

## What remains unproven

- reliability across independent source and observation geometries;
- strategic continuity for evolving hypotheses or rejected alternatives;
- scalable P0 paging in a real repository rather than generated distractors;
- dense observation selection among many current but differently relevant
  records;
- user revision of an active or parent objective;
- operation across more than one long active phase in an ecological task;
- generality beyond this actor, quantization, reasoning mode, Python domain,
  and action surface.

The completed study does prove something narrower and important: exact
external custody plus readable resident signal is not merely an attractive
diagram. It enabled correct grounded work after resident exact history had
become physically impossible.

