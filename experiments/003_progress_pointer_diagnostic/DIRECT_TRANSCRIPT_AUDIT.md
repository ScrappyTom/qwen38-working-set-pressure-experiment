# Experiment 003 direct transcript audit

## Review identity and mode

- reviewer: Codex, primary project agent
- date: 2026-08-28
- mode: condition-aware post-seal direct audit
- coverage: all 36 saved completion calls and all 39 prospective requests
- inputs inspected: exact coding requests, rendered prompts, append-only/reconstructed histories, P0 rows, observation directory, progress pointer, endpoint envelopes, raw assistant content, and tool results
- evaluator access: only after verifying the response seal

This is not a blinded review. It is a complete behavioral audit intended to explain what the exact actor knew, selected, acquired, and failed to do.

## What every reconstructed branch received

Both conditions received:

1. the exact full original two-phase task;
2. the exact current post-Phase-A candidate;
3. the latest accepted `fork_ready` response/result pair with `pending_stage: continuation`;
4. the current P0 directory of paths, symbols, signatures, and line ranges;
5. the complete directory of reopenable dynamic observations;
6. the exact continuation tool contract and remaining eight-call budget;
7. explicit notice that older chronology was externally custodied but absent;
8. no model-authored summary and no host-selected relevant fact.

`T25-P` additionally received a byte-exact frozen Phase B task component and the mechanically grounded facts `completed_protocol_stage: phase_a` and `active_protocol_stage: phase_b`. It did not receive the track prefix, probe body, expected patch, or evaluator truth.

The pointer cost 168 tokens on the source branch's first request and 179 tokens on the observation branch's first request.

## Shared prefix: E3-SOURCE

The actor followed the task cleanly:

| Call | Exact action | Prompt tokens | Result |
|---:|---|---:|---|
| 1 | `begin` | 956 | accepted |
| 2 | read all `cert/north.py` | 1,052 | exact, complete |
| 3 | read all `cert/south.py` | 10,871 | exact, complete |
| 4 | read all `cert/east.py` | 20,621 | exact, complete |
| 5 | read all `policy/track.py` | 30,405 | exact, complete; contained `TRACK_PREFIX = "gold-"` |
| 6 | read `staging/readiness.py` | 40,211 | exact, complete |
| 7 | patch readiness | 40,445 | accepted, exact bound candidate/file |
| 8 | check `prefork` | 40,917 | passed |
| 9 | `fork_ready` | 41,229 | accepted |

There were no duplicate reads, protocol errors, premature Phase B actions, or checker defects. The prefix reached an authentic pressure boundary in nine calls.

## E3-SOURCE / T25-M

First request knowledge included the exact full task, post-Phase-A candidate, accepted fork result, P0 entries for `publish/slug.py` and `policy/track.py`, and the two observation handles for the successful check and fork.

The actor nevertheless restarted Phase A:

1. read all `cert/north.py`;
2. read all `cert/south.py`;
3. read all `cert/east.py`;
4. prospective next request stopped before HTTP at 31,413 offline prompt tokens.

It never opened the Phase B target or governing policy in the reconstructed branch. The latest fork result alone did not function as a usable task-progress representation.

## E3-SOURCE / T25-P

The initial request differed only by the frozen verbatim pointer. Its behavior changed immediately:

1. read `publish/slug.py` completely;
2. redundantly read all `cert/north.py`;
3. read `policy/track.py` lines 1–230;
4. prospective patch turn stopped before HTTP at 22,061 offline prompt tokens.

The policy result was marked incomplete because two trailing function lines remained, but it included the load-bearing line `TRACK_PREFIX = "gold-"` and the `track_prefix` signature. Thus the model had both the exact flawed target and the exact governing value before the stop.

Qualitatively, the pointer transmitted substantial signal:

- it redirected the first action from a completed ledger to the Phase B target;
- it caused acquisition of the correct governing source;
- it cut cumulative executed-branch prompt tokens from 35,580 to 16,965 (52.3%);
- it lowered the stopped prospective request from 31,413 to 22,061 tokens.

But it did not fully suppress the old plan. The unnecessary `cert/north.py` read consumed roughly 9.8k additional next-turn tokens. Without that one restart, the exact scripted state machine proves the branch had enough room to read target, read policy, patch, check, and submit.

This is a mixed continuity result: the actor recognized Phase B but retained a competing urge to replay Phase A.

## Shared prefix: E3-OBSERVATION

The actor again followed the prescribed sequence:

| Call | Exact action | Prompt tokens | Result |
|---:|---|---:|---|
| 1 | `begin` | 886 | accepted |
| 2 | probe `negotiation` | 998 | accepted; `negotiated_prefix=R7|` |
| 3 | read all `cert/north.py` | 1,092 | exact, complete |
| 4 | read all `cert/south.py` | 10,803 | exact, complete |
| 5 | read all `cert/east.py` | 20,608 | exact, complete |
| 6 | read `staging/readiness.py` | 30,397 | exact, complete |
| 7 | patch readiness | 30,632 | accepted |
| 8 | check `prefork` | 31,110 | passed |
| 9 | `fork_ready` | 31,426 | accepted |

The one-shot capability worked as designed. After call 2, `negotiation` was absent from every later prefix request and response schema. The actor did not loop the probe.

## E3-OBSERVATION / T25-M

The control did not wholly ignore Phase B. It first reopened `OBS-0001`, which returned the exact probe body including `negotiated_prefix=R7|`. It then reverted to Phase A:

1. reopen `OBS-0001`;
2. read only line 1 of `cert/north.py`;
3. reread all `cert/north.py`;
4. read all `cert/south.py`;
5. prospective next request stopped before HTTP at 22,106 tokens.

This matters: task wording plus the observation directory were already sufficient to elicit exact historical-observation reacquisition. The control failure was not inability to discover or reopen the fact. It was failure to maintain the active Phase B plan after reacquisition.

## E3-OBSERVATION / T25-P

The pointer produced the intended first two information actions:

1. read the exact two-line `wire/header.py` target;
2. reopen `OBS-0001`, receiving the exact `R7|` prefix;

At that point the actor possessed every fact required for the patch and the read result supplied the exact candidate/file bindings required by the patch schema.

It then issued six more reads of the same two-line target (one used an oversized line count but returned the same exact complete file). All were accepted. It exhausted the eight-call budget without mutation.

There was no malformed JSON, rejected action, stale binding, missing capability, checker failure, truncation, or context pressure. The maximum prompt was only 3,870 tokens. This is therefore a clean evidence-to-action failure.

The repeated action is especially informative. The actor had previously produced correct bound patches in both shared prefixes. It can use the patch schema for direct local edits. What it failed to do here was synthesize an exact dynamic fact from one result with an exact source body from another result and commit to mutation under reasoning-off decoding.

## Cross-condition interpretation

### Signal transmitted

The pointer is not just extra text:

- Source first action changed from completed ledger to Phase B target.
- Source acquired the governing policy; the control never did.
- Observation first source action changed from completed ledger to Phase B target.
- Observation avoided all certification-ledger reads under `T25-P`.

### Signal insufficient

Neither pointer branch mutated. The two residual failure modes differ:

- Source: partial old-plan replay consumed the remaining context budget.
- Observation: all required evidence was present, but the actor entered a repeated-read attractor.

The first is a continuity/working-set policy defect. The second is an evidence-to-action control defect.

### What the result does not show

It does not show that exact reconstruction is impossible at 25k. The scripted qualification completed both geometries in five continuation calls. It does not show that P0 or observation handles lack value; the pointer branches used both correctly. It also does not show that a larger reasoning budget will solve the problem, only that a reasoning-mode diagnostic is now earned.

## Audit conclusion

The exact user-authored progress pointer improves orientation after reset and materially reduces wasted source acquisition. It is necessary-looking but not sufficient evidence for successful reconstruction with this reasoning-off actor.

The remaining bottleneck is no longer primarily “where is the fact?” It is “can the actor hold the current subgoal, combine exact facts already acquired, and move from reading to a bound mutation before spending the budget?”
