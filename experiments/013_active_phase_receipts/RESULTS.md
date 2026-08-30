# Experiment 013 results and decision

## Executive result

Experiment 013 is a valid mixed-positive result.

Compact exact active-phase receipts solved the principal Experiment 012
failure. Both conditions produced hidden-correct candidates in all four cells,
but the receipt condition reached a passing public check in 4/4 branches versus
0/4 for the latest-result baseline, and submitted 2/4 versus 0/4. It used 14.3%
fewer Phase-B calls, 53.1% fewer Phase-B prompt tokens, and 31.2% less endpoint
time.

The remaining failure is narrower. In both observation branches, Qwen passed
the public check and then repeated it until the call budget ended. The model saw
every passing result but treated the receipt ledger—frozen at the last reset—as
the authoritative progress record and discounted newer unsequenced ordinary
history.

The supported conclusion is:

> Compact exact action/effect receipts are sufficient to preserve expensive
> pre-reset progress without resident result bodies. For reliable closure, the
> active phase needs one monotonically sequenced exact progress plane rather
> than a frozen receipt prefix plus a separate unsequenced recent history.

## Formal outcomes

| Geometry / seed | Condition | Hidden candidate | Public check | Submit | Phase-B calls | Counted reconstruction states |
|---|---|---:|---:|---:|---:|---:|
| SOURCE / 173205 | T25-LATEST | pass | no | no | 14 | 3 |
| SOURCE / 173205 | T25-RECEIPTS | pass | pass | yes | 10 | 2 |
| SOURCE / 223607 | T25-LATEST | pass | no | no | 14 | 3 |
| SOURCE / 223607 | T25-RECEIPTS | pass | pass | yes | 10 | 2 |
| OBS / 173205 | T25-LATEST | pass | no | no | 14 | 4 |
| OBS / 173205 | T25-RECEIPTS | pass | pass | no | 14 | 2 |
| OBS / 223607 | T25-LATEST | pass | no | no | 14 | 4 |
| OBS / 223607 | T25-RECEIPTS | pass | pass | no | 14 | 2 |

All eight final candidates pass the post-seal hidden grader. This establishes
mutation quality but does not retroactively turn non-submitted branches into
formal completions.

## Economics

Phase-B totals exclude the shared prefix because each exact prefix was run once
and then forked.

| Condition | HTTP calls | Prompt tokens | Completion tokens | Endpoint time | Resets including first boundary |
|---|---:|---:|---:|---:|---:|
| T25-LATEST | 56 | 507,348 | 23,466 | 2,315.0 s | 14 |
| T25-RECEIPTS | 48 | 238,019 | 21,484 | 1,593.3 s | 8 |

Relative to `T25-LATEST`, receipts reduced:

- calls by 8 / 56 (14.3%);
- prompt tokens by 269,329 / 507,348 (53.1%);
- completion tokens by 1,982 / 23,466 (8.4%);
- endpoint time by 721.7 seconds / 2,315.0 seconds (31.2%);
- counted reconstruction states by 6 / 14 (42.9%).

The observation receipt branches spent eighteen of their 28 calls on passing
checks—nine per seed. Even with that closure loop, they used fewer prompt tokens
than their latest-result counterparts because they did not repeatedly reacquire
large exact evidence.

## Hypotheses

### H1 — Compact exact receipts preserve pre-reset mechanical progress

Supported. All four receipt branches reconstructed the completed mutation and
both large reads, then reached the public check. None repeated the governing
observation, patch, or large read after the receipt boundary.

### H2 — Externalized exact result bodies can remain demand-loaded

Supported for these tasks. Across 24 externalized receipts, Qwen invoked
`reopen_result` once. The other three branches acted from receipt identity and
mechanical completion fields alone.

### H3 — No semantic host routing is required

Supported for reconstruction of pre-reset work. The host supplied no relevance,
sufficiency, or next-action judgment. Qwen correctly inferred what remained and
reached a valid check in every receipt branch.

### H4 — The exact v1 receipt surface is sufficient for reliable closure

Rejected. Two source branches submitted, but both observation branches entered
a repeated-check loop because the numbered ledger did not advance with new
post-reset effects.

### H5 — The latest full result is sufficient at large-world repeated pressure

Rejected again. All four latest-result branches produced correct code but lost
non-mutating progress across resets and exhausted the call budget before check
or submission.

## Architectural decision

The **receipt concept is promoted**. The exact Experiment 013 v1 split
presentation is **not promoted as a reliable controller**.

Retain:

- exact full task and active user-authored step;
- completed-step IDs;
- current candidate/version and exact boundary binding;
- remaining action/token budget;
- hierarchical readable P0;
- candidate-bound observation identities;
- compact exact active-phase action/effect receipts;
- exact result bodies in external custody with on-demand reopening;
- maximal exact paging;
- low bounded private reasoning;
- exact check, submission, replay, and evaluator separation.

Do not add:

- summaries;
- semantic ranking or routing;
- relationship graphs;
- embeddings;
- read suppression or cache substitution;
- more reasoning;
- host-selected next actions.

The narrowly earned revision is one monotonically sequenced mechanical receipt
ledger for **all** completed active-phase effects, including actions completed
after the latest reset. Full recent bodies may remain in a separate exact body
surface or behind the same reopen handles, but progress identity must not split
across two clocks.

This is not automatic successor authorization. A future study must use a fresh
bank and prospectively freeze how sequence identity, recent bodies, check
effects, and submission state are presented.

## Status against the project goal

Experiment 013 closes the most important large-world continuity gap from
Experiment 012:

```text
exact purpose + current world + P0 + latest result
    -> correct code, repeated acquisition, no closure

exact purpose + current world + P0 + compact receipts
    -> correct code, no repeated expensive acquisition, 4/4 passing checks
```

The remaining issue is no longer grounding in source or observations. It is
reliable transition from a verified effect to terminal closure when progress is
represented across a reset boundary.

That is a substantially narrower problem than long-horizon memory in general.

