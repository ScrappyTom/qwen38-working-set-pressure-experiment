# Experiment 002 results and decision

## Executive result

The current 25k exact-reconstruction design is not promoted.

The experiment did not show that exact custody plus P0 is sufficient for this
reasoning-off actor to continue across a pressure boundary. The strongest
matched result went the other way: in the observation case C50 retained the
runtime fact and completed correctly, while T25 ignored five exact reopen
handles, restarted old source acquisition, and exhausted 25k before acting.

This is not a negative result about external memory in general. It isolates a
more specific missing capability: the actor needs an effective progress and
information-selection policy. Making exact history reopenable does not by
itself cause the actor to select the right working set.

## Mechanical outcomes

| fork | family | seed | prefix | C50 | T25 |
|---:|---|---:|---|---|---|
| 1 | source | 42 | incomplete at 14 calls | not created | not created |
| 2 | observation | 314159 | incomplete at 14 calls | not created | not created |
| 3 | observation | 42 | eligible | hidden pass, submitted | capacity stop, hidden fail |
| 4 | source | 314159 | eligible | capacity stop, hidden fail | capacity stop, hidden fail |

Across the four frozen scheduled forks, C50 produced one hidden-correct final
candidate and T25 produced none. Across the two eligible matched pairs, C50
was 1/2 and T25 0/2. The other two forks are not missing data; they are
preserved prefix noncompletion outcomes.

## Prospective decision rule

| requirement | result |
|---|---|
| at least 3/4 C50 branches pass | fail: 1/4 scheduled forks |
| T25 not lower than C50 and no matched regression | fail: observation pair regressed |
| both source T25 branches reacquire governing source before mutation | fail |
| both observation T25 branches reopen governing observation before mutation | fail |
| T25 requests remain within 25k or stop before HTTP; A25 stops | pass |
| no host-selected relevance, retry, repair, rescue, or hidden omission | pass |

The recurrent-boundary study and semantic digestion remain unauthorized.

## What was learned relative to the project goal

The project’s target is coherent operation when the world and chronology are
larger than active context. Experiment 001 earned the substrate side of that
architecture: exact external custody and a readable structural P0 directory.
Experiment 002 shows that substrate is necessary but not sufficient.

The missing layer is not more resident metadata. The actor had readable paths,
symbols, exact ranges, current candidate state, and exact observation handles.
It still restarted completed work. Conversely, when the exact governing fact
remained directly in C50 chronology and the actor transitioned to mutation,
it produced a correct patch.

The failure can be stated precisely:

```text
exact custody + readable location + mechanical boundary receipt
                           does not imply
correct progress inference + economical reacquisition policy
```

P0 remains earned as an orientation substrate. The no-summary T25 controller
is rejected as sufficient. No richer resident relationship or evidence layer
is earned by this result.

## Recommended next study

Do not repeat the same eight-branch run and do not add semantic summaries.
Run a small component diagnostic that changes only progress representation:

```text
T25-M  current mechanical reset
       full original task + stage=continuation + fork receipt

T25-P  same reset, custody, P0, tools, actor, and 25k envelope
       + an exact user-authored active-step field
       + mechanically marked completed protocol stage
```

The active step should be frozen as a separate exact part of the original task
before execution, not inferred or summarized by the host after observing the
trajectory. For these two-phase tasks it would contain the verbatim Phase B
instruction while preserving the full original task and constraints.

Also make completed one-shot capabilities mechanically unavailable: once an
exact probe has succeeded, repeated identical probe calls should be rejected
or omitted from the available action domain. That is capability-state hygiene,
not semantic relevance selection, and is directly earned by the seven- and
five-probe loops.

Use one source and one observation development geometry first. The diagnostic
passes only if T25-P:

- does not restart required Phase A reads;
- uses P0 to target the source fact in the source case;
- reopens the exact historical observation in the observation case;
- mutates, checks, and submits within 25k;
- preserves quality without host-selected evidence.

If explicit user-authored progress still fails, test a bounded reasoning mode
before designing richer memory. The present failures are dominated by action
selection and phase control, not missing metadata content.

## Final decision

Experiment 002 is complete as a valid negative capability study. Preserve all
evidence. Retain exact custody and P0. Do not promote the current reconstructed
controller to recurrent operation. Authorize only the narrow progress-pointer
diagnostic described above as the next highest-ROI question.
