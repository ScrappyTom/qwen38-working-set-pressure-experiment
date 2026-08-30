# Experiment 015 Results and Decision

## Executive result

The development-only live placement qualification passed.

Both the qualified dual history/receipt presentation and the proposed single event frame produced 4/4 public-check passes, 4/4 hidden passes, and 4/4 submissions. Every branch required exactly two calls: check, then submit. The single frame caused no stale-check error, closure loop, duplicate acquisition, protocol failure, or model-visible confusion.

The result answers the narrow concern that moving progress into one plane might itself break Qwen's interpretation:

> Qwen can use one exact monotonic active-phase event frame to recognize completed work, validate current-candidate check state, and close correctly on these sacrificial cases.

It does not show that the current event encoding is cheaper. It was 10.62% more prompt-expensive than the compact legacy receipt presentation.

## Formal development outcomes

| Family | Seed | Condition | Hidden | Check | Submit | Calls | Prompt tokens |
|---|---:|---|---:|---:|---:|---:|---:|
| CLOSURE | 173205 | D15-UNIFIED-DUP | pass | pass | yes | 2 | 7,574 |
| CLOSURE | 173205 | D15-EVENT-FRAME | pass | pass | yes | 2 | 8,250 |
| CLOSURE | 223607 | D15-UNIFIED-DUP | pass | pass | yes | 2 | 7,574 |
| CLOSURE | 223607 | D15-EVENT-FRAME | pass | pass | yes | 2 | 8,250 |
| STALE | 173205 | D15-UNIFIED-DUP | pass | pass | yes | 2 | 7,684 |
| STALE | 173205 | D15-EVENT-FRAME | pass | pass | yes | 2 | 8,629 |
| STALE | 223607 | D15-UNIFIED-DUP | pass | pass | yes | 2 | 7,684 |
| STALE | 223607 | D15-EVENT-FRAME | pass | pass | yes | 2 | 8,629 |

## Aggregate descriptive economics

| Condition | Calls | Prompt tokens | Completion tokens | Reasoning bytes | Endpoint time | Hidden | Submit |
|---|---:|---:|---:|---:|---:|---:|---:|
| D15-UNIFIED-DUP | 8 | 30,516 | 3,897 | 11,973 | 260.5 s | 4/4 | 4/4 |
| D15-EVENT-FRAME | 8 | 33,758 | 3,405 | 9,703 | 242.3 s | 4/4 | 4/4 |

The event frame used 3,242 more prompt tokens (+10.62%), 492 fewer completion tokens (-12.63%), and 18.2 fewer endpoint seconds (-7.0%). Only the prompt increase should be treated as a strong mechanical finding. The completion and timing differences come from four exposed pairs and are confounded by the richer event contents.

## Hypotheses

### H1 — One event plane is sufficient for closure

Supported on the sacrificial cases. All four event-frame branches checked and submitted in two calls. Qwen explicitly used the sequence to mark earlier reads and mutation complete and sequence 6 to mark the current-candidate check complete.

### H2 — One event plane preserves stale-check safety

Supported on both seeds of the stale-check donor. Qwen identified the old passed check as predecessor-bound, ran a new check on the repaired current candidate, then submitted.

### H3 — Removing the dual presentation is automatically cheaper

Not supported by this encoding. The single frame was larger because it retained exact action arguments and structural results while the old externalized prefix used compact receipts. Removing cross-plane duplication does not guarantee a compact event schema.

### H4 — The dual presentation creates avoidable interpretive ambiguity

Weak qualitative support. One legacy seed explicitly described zero newly used calls versus five completed receipts as contradictory before resolving the reconstruction semantics. No event-frame branch expressed that ambiguity. It did not affect the final action in this small study.

## Architectural decision

Retain the one-progress-plane direction. Do not give a future 50k control both append-only history and a duplicate receipt ledger.

The next large-world comparison should use one common event renderer:

```text
R50 — resident event state, <=50k
      exact event identities and result bodies remain resident

X25 — externalized event state, <=25k
      same event identities and structural bindings;
      old exact result bodies move behind the same reopen handles
```

Before any externalization boundary, R50 and X25 must receive byte-identical requests. After pressure, the treatment is exact result-body residency, not placement in a different top-level prompt section.

This should not be reported as a pure `50k append-only chronology` comparison. It is a whole-controller comparison between resident and externally custodied exact event state. A raw append-only ecology could be reported separately later, but it must not be conflated with the causal body-residency treatment.

## Immediate next gate

Do one offline mechanical stress qualification before constructing fresh large-world fixtures:

- render the expected maximum active-phase event count;
- measure exact action, structural-result, resident-body, and externalized-body costs separately;
- prove R50 and X25 capacity envelopes;
- verify monotonically ordered identities and exact reopenability;
- verify that phase transition starts a new active ledger while older exact events remain in custody;
- leave the event schema unchanged if it fits.

Only if the exact stress proof fails may the representation be narrowed, for example by externalizing large action payload fields behind the same event identity. That change would require renewed offline and live placement qualification.

No additional live micro-ablation, suppression, caching, summary, relationship graph, ranking, embedding, or automatic successor is earned by Experiment 015.

## Scope

This was not fresh measured evidence. It used exposed donor cases and known-good constructed prefixes to qualify model interpretation. The supported promotion is the placement rule, not the observed 8/8 task quality or the small completion-time difference.
