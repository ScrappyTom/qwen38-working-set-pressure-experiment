# Experiment 016 Results and Decision

## Executive result

The exact Experiment 015 event frame is not capacity-qualified for the planned
R50/X25 large-world comparison.

The problem is narrower than the earlier placement concern. Qwen already
showed that it can understand one event plane. The offline stress proof now
shows that this exact plane cannot always become small enough: old result
bodies can leave context, but large historical action payloads cannot.

No fresh large-world fixture should be constructed against V1.

## Exact results

| Sixteen accepted patch events | Resident prompt | Result bodies external | X25 after externalization | R50 after externalization |
|---|---:|---:|---:|---:|
| 512-character ordinary ASCII fragments | 32,553 tokens | 20,130 tokens | pass, 1,858-token total margin | pass |
| 170-character escaped-control fragments | 63,211 tokens | 35,516 tokens | **fail by 13,528 tokens** | pass |

The escaped-control action itself is not over the output envelope. Its maximum
is 1,853 tokens; adding the entire 512-token private reasoning budget reaches
2,365, still below the 2,500-token completion allowance.

Component inspection identifies the cause:

| Component | ASCII | Escaped control |
|---|---:|---:|
| Sixteen exact actions | 14,250 tokens | 29,565 tokens |
| Sixteen structural results | 3,141 tokens | 3,185 tokens |
| Sixteen externalized-result event records | 18,974 tokens | 34,398 tokens |

Externalizing a result removes its `diff`, output, content, or similar body.
It does not alter the action. In a patch event, exact `old` and `new` strings
remain resident forever.

## Interpretation

The ordinary ASCII case is useful context. It shows that V1 would probably
work on many familiar short-patch trajectories, but its remaining X25 margin
is already only 1,858 tokens on a small decision-frame base. That is not a
fixture-independent guarantee.

The escaped-control case is the decisive contract result. Control characters
are valid UTF-8 candidate content, valid schema strings, accepted by the real
patcher, and expensive under exact JSON tokenization. Sixteen such accepted
actions form a legal active phase. One legal counterexample is sufficient to
reject a positive capacity claim.

This is precisely why the project required a worst-case proof rather than
inferring safety from the small Experiment 015 trajectories.

## What remains valid

- Experiment 015's behavioral result remains valid: one event plane is
  comprehensible on the qualified development paths.
- Event sequencing, result identity, exact result custody, and phase-scoped
  sequence restart all pass.
- R50 and X25 guards fail closed.
- R50 can run resident until authentic physical pressure.
- The exact historical actions and results remain preserved externally.

## Architectural decision

Do not return to duplicate chronology plus receipts. Keep the one-event-plane
direction, but narrow the resident representation.

The next earned candidate should externalize large historical action payload
fields as well as result bodies. For patch events, the resident structure should
retain only mechanically useful progress/binding fields such as:

```text
action = patch
path
expected candidate/file binding
successor candidate/file binding
accepted status
exact event handle
exact pair size/hash
```

The exact `old`, `new`, and result body should remain in custody behind one
phase-scoped event handle. A low-arity exact `reopen_event(handle)` operation
is the cleanest candidate because it can return the original action/result pair
without summary, ranking, repair, or semantic host selection.

This is an earned representation narrowing, not a new metadata feature.

## Required next qualification

Before fresh large-world work:

1. specify an event-frame V2 candidate with structural action/effect fields and
   exact pair-payload custody;
2. prove the sixteen-event X25 reconstruction envelope offline, including at
   least one newly resident maximum event after reconstruction;
3. qualify exact `reopen_event` custody and replay;
4. repeat the small exposed live placement test because nesting/removing old
   action payload fields changes what Qwen sees;
5. only then freeze fresh R50/X25 fixtures.

No summary, cache substitution, duplicate suppression, relationship graph,
ranking, embedding, or semantic routing is earned.

## Provenance

This was an offline source/artifact qualification based on repository state
`60c833a55c115f095790a73841f12fa48276a7eb`. The generated proof is
`qualification_artifacts/CAPACITY_PROOF.json`; its artifact set is bound by
`qualification_artifacts/ARTIFACT_MANIFEST.json`.
