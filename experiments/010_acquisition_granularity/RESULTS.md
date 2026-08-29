# Experiment 010 results and decision

## Executive result

Deterministic maximal exact paging is a modest positive component result, not a
complete reliability fix.

Both L0 and L1 were hidden-correct and closed in all four cells. L1 reduced
ledger-read calls from 12 to 8, total calls from 32 to 29, and cumulative prompt
tokens from 212,414 to 202,821. It won call economics in three of four paired
cells. The one loss was an unchanged two-line target reread after bounded
reasoning stalled; it was unrelated to page fragmentation.

| Measure | L0 | L1 | Difference |
|---|---:|---:|---:|
| Hidden pass | 4/4 | 4/4 | equal |
| Check + `fork_ready` closure | 4/4 | 4/4 | equal |
| Total calls | 32 | 29 | L1 -9.4% |
| All read actions | 16 | 13 | L1 -18.8% |
| Ledger read actions | 12 | 8 | L1 -33.3% |
| Duplicate exact reads | 0 | 1 | L1 +1 |
| Prompt tokens | 212,414 | 202,821 | L1 -4.5% |
| Completion tokens | 9,021 | 8,630 | L1 -4.3% |
| Endpoint time | 952.1 s | 914.3 s | L1 -4.0% |

## Decision

L1 earns narrow promotion as the physical read primitive for one fresh
recurrent-pressure replication. The evidence supports moving the mechanical
question “how much exact contiguous content fits?” from the model to the host.
It does not support host-selected relevance, truncation, summarization, or
duplicate suppression.

This promotion is based on:

- quality and closure parity in every cell;
- three of four paired economic wins;
- deterministic removal of every ledger-page split;
- a simpler lower-arity action;
- no model confusion, parser issue, or replay defect.

L1 is not yet established as a reliable recurrent controller improvement. The
study stayed far below a pressure boundary, and its required file bodies were
not semantically load-bearing. Its next test must therefore be inside a fresh
two-boundary path where acquisition calls and active headroom are genuinely
scarce.

## Interpretation relative to Experiment 009

Experiment 009's seven-page noncompletion was not evidence that Qwen always
chooses tiny pages. Experiment 010 shows a variable policy: 500 in one path,
50→200 in another, 100→100→200 in a third, and 100+100 for both files in a
fourth. Qwen can estimate and adapt, but not reliably enough to spend a hard
budget on that physical choice.

L1 directly fixes the page-fragmentation class. It does not fix the second
Experiment 009 class—reading already-visible unchanged evidence again. The one
L1 duplicate in this run reproduces that separation cleanly.

The working architecture remains minimal:

```text
exact purpose/current world
        -> readable P0
        -> model chooses path + start
        -> host returns maximal exact bounded page
        -> model judges and acts
        -> exact check/effect custody
```

No relationship graph, semantic summary, embedding, ranking, declaration,
retention layer, or richer ontology is earned.

## Next study

Use L1 unchanged in a small fresh recurrent two-boundary study with the existing
T25 controller, current/stale observation bindings, and bounded reasoning. Do
not add duplicate-read handling yet.

The primary gate is whether paths that semantically know what to acquire now
reach mutation/check/closure within the hard 25k and action budgets. Track page
fragmentation and no-new-information acquisition as separate failure classes.
If duplicate exact reads remain the dominant loss after L1 removes physical
fragmentation, then—and only then—specify a narrow exact-result reference or
confirmation-policy diagnostic.

Experiment 010 makes no automatic successor authorization.
