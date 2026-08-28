# Experiment 003 results and decision

## Executive result

The verbatim Phase B pointer transmitted useful task-progress signal but did not make 25k reconstruction succeed.

Neither condition completed either fresh task. `T25-M` mostly restarted Phase A and hit context capacity. `T25-P` oriented toward Phase B in both tasks, acquired the governing source/observation, and used far less source-context in the source case—but still never patched.

The result is a partial positive for explicit progress state and a clear negative for sufficiency under the frozen reasoning-off actor.

## Outcomes

| Geometry | T25-M | T25-P | Paired interpretation |
|---|---|---|---|
| governing source | reread three completed ledgers; capacity stop | opened target, redundantly reread one ledger, acquired correct policy; capacity stop | pointer substantially improved orientation/economics but did not eliminate plan restart |
| historical observation | reopened correct observation, then restarted ledgers; capacity stop | opened target, reopened correct observation, then reread target six times; call exhaustion | pointer eliminated Phase A source restart, but evidence did not convert into action |

Hidden correctness is 0/2 for each condition because no branch mutated the Phase B target.

## Pass-criterion assessment

| Criterion | Source T25-P | Observation T25-P |
|---|---:|---:|
| avoid Phase A restart | fail: one completed ledger reread | pass |
| targeted governing source via P0 | pass | n/a |
| reopen exact historical observation | n/a | pass |
| mutate/check/submit within 25k | fail | fail |
| preserve hidden correctness | fail | fail |

The intervention therefore fails its prospective promotion gate.

## Token economics

Source continuation cumulative prompt tokens:

- `T25-M`: 35,580 across three HTTP calls;
- `T25-P`: 16,965 across three HTTP calls;
- reduction: 18,615 tokens, or 52.3%.

The source pointer overhead was only 168 tokens on the first request. It paid for itself economically, even though the branch remained incomplete.

Observation continuation:

- `T25-M`: 19,452 prompt tokens across four calls before capacity;
- `T25-P`: 24,874 prompt tokens across eight small calls;
- pointer overhead: 179 tokens on the first request.

The higher `T25-P` total came from six redundant target reads, not from the pointer or observation body. Its maximum single prompt remained only 3,870 tokens.

## Research decision

### Retain

Retain these architectural elements:

- exact external custody;
- P0 readable structural orientation;
- exact source reads;
- exact observation handles and reopen;
- explicit task-progress state derived from mechanical stage completion;
- verbatim user-authored active-step text rather than host semantic summaries;
- one-shot capability removal after successful use.

The pointer earned retention as a continuity primitive because it changed behavior in the intended direction at low cost.

### Do not promote

Do not claim that the current 25k controller matches the 50k append-only control. Do not promote `T25-P` as sufficient. Do not add richer metadata, relationship inventories, summaries, or host-selected relevant facts in response to this result.

The model already located the right source and observation. More locator metadata would address the wrong bottleneck.

### Next earned diagnostic

The next highest-ROI study is a small reasoning-mode diagnostic, not another metadata experiment.

Use fresh sibling source and observation geometries and the retained `T25-P` reconstruction. Compare the current reasoning-off actor with a prospectively bounded reasoning-enabled actor while holding model, quantization, task, P0, exact custody, pointer, tools, and 25k ceiling fixed.

The diagnostic should ask only whether bounded reasoning changes the observed evidence-to-action transition:

1. acquire/reopen the required exact fact;
2. stop redundant reads;
3. construct a candidate/file-bound patch;
4. check and submit within budget.

A very small development uptake check should precede fresh measurement. If reasoning-on still loops after possessing all exact facts, the next design target is an explicit action-phase controller or reduced action surface—not more information.

## Goal-level status

The project has now established:

- P0 can reduce discovery work;
- exact observation reopening works across a real context reset;
- explicit progress state improves post-reset orientation;
- the reasoning-off actor can still fail after all required information is in context.

The original goal remains unmet: the 25k reconstructed actor has not matched a 50k append-only control. The unresolved capability is coherent evidence-to-action control after reset, not basic metadata comprehension or information availability.
