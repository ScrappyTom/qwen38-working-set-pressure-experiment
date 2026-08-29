# Experiment 008 direct transcript audit

## Scope and method

- reviewer: Codex, primary project agent;
- review mode: condition-aware post-seal direct audit;
- actor: Qwen3.8-27B AD-IQ2_S;
- reasoning: enabled for every completed call, server maximum 512 private
  tokens, not retained in subsequent active chronology;
- sampler: temperature 0.7, top-p 0.8, top-k 20, min-p 0.0,
  presence penalty 1.5, repeat penalty 1.0;
- response allowance: 2,500 tokens;
- active envelopes: 50,176 total for C50 and 25,000 total for T25;
- exposed seeds: 173205 and 223607.

All 87 completed model calls were directly reviewed. That review covered the
exact coding request, rendered prompt, assistant action, separately custodied
private reasoning, tool result, candidate binding, and endpoint usage. The
machine-readable `TRANSCRIPT_INDEX.json` binds every reviewed call to the
hashes of those artifacts. Stage candidates were reconstructed from sealed
snapshots and hidden-graded only after sealing.

## What the reset controller exposed

At each T25 reset the actor received:

- the exact original three-phase task;
- the exact active user-authored phase and exact completed-phase list;
- the exact current candidate and candidate-derived P0 directory;
- the latest accepted boundary action/result;
- current tool and invocation limits;
- an identity-only directory of externally custodied observations;
- explicit candidate/version bindings and staleness status;
- notice that older chronology remained external but was absent.

It did not receive a semantic summary, relationship graph, task-aware rank,
host-selected relevant fact, model-authored memory, or retention declaration.

## Cell 01: E8-SOURCE, seed 173205

### Shared Phase A

The actor completed the required setup coherently:

```text
begin
read archive/alder.py
read archive/birch.py
read policy/channel.py       -> CHANNEL_STEM = "topaz-"
read stage/ready.py
patch completed_groups()
check prefork: pass
fork_ready
```

The private reasoning tracked the active phase, the three required full reads,
the stage mutation, and the boundary transition. It acquired the governing
source fact before boundary 1.

### C50 Phase B and Phase C

Phase B retained the complete Phase-A chronology:

```text
read dispatch/token.py
read bridge/coral.py
read dispatch/compose.py
patch dispatch/token.py using policy.channel.channel_stem()
read bridge/drift.py
read bridge/elm.py
check public: pass
fork_ready
```

The actor did not reread `policy/channel.py`; it used the exact fact already in
history and chose a source-linked implementation. Phase C then performed:

```text
read dispatch/badge.py
patch dispatch/badge.py using policy.channel.channel_stem()
check public: pass
submit
```

The final candidate passed hidden grading. This is a successful append-only
control, but it processed very large prompts: Phase B peaked at 39,556 tokens
and Phase C at 40,921.

### T25 Phase B

After boundary 1 the actor immediately oriented to Phase B and reacquired only
the governing source and task-connected files:

```text
read policy/channel.py
read dispatch/token.py
patch using CHANNEL_STEM
read bridge/coral.py
read bridge/drift.py
read bridge/elm.py
check public: pass
fork_ready
```

It did not restart Phase A or reread the archive files. The reasoning stated
the active phase and remaining closure actions accurately, and observable
actions followed that plan.

This branch did not enter Phase C because the exact actor-created Phase-B
history was too compact to produce an authentic second 25k denial. Its peak
prompt was 15,757 tokens. The scripted qualification path had crossed the
second boundary, but the live actor's smaller line requests and compact tool
results changed the actual occupancy.

This is neither a behavioral failure nor a recurrent success. It reveals that
a task whose boundary depends on the actor's own acquisition footprint may
fail to instantiate the intended pressure point for an efficient trajectory.

## Cell 02: E8-OBSERVATION, seed 173205

### Shared Phase A

The actor completed setup and created the exact historical observation:

```text
begin
read archive/hazel.py
read archive/maple.py
read archive/oak.py
read stage/ready.py
patch completed_groups()
check prefork: pass
probe runtime              -> J2@@
fork_ready
```

The probe result was bound to the pre-Phase-B candidate and preserved as an
exact reopenable observation.

### T25 Phase B

The actor's first post-reset action reopened the right observation:

```text
reopen OBS-0002            -> J2@@, current for the Phase-B candidate
read runtime/nameplate.py
read runtime/nameplate.py  -> redundant second read
patch with J2@@
check public: pass
probe runtime              -> R8@@, bound to the new candidate
read bridge/pearl.py in two pages
read bridge/reed.py in two pages
read bridge/silk.py in two pages
```

This is positive evidence for version-bound observation handling before the
second boundary. The actor reopened the exact candidate-valid old result when
it was still the governing Phase-B fact, mutated, checked, and then obtained a
new result bound to the successor candidate.

It nevertheless exhausted the twelve-call Phase-B budget before reading
`bridge/tulip.py` and issuing `fork_ready`. The reasoning eventually noticed
that only one invocation remained and two required operations were still
needed, but that recognition came after the redundant target read and
conservative page choices had already consumed the budget.

This is an information-policy/call-budget failure, not metadata confusion.
The observation handle was chosen correctly and its body was used correctly.

### C50 Phase B

The append-only branch likewise reopened J2@@, patched correctly, passed the
public check, and probed the current R8@@ result. It read all four bridge files
in one request each by using their exact P0 line ranges. Before the final
`fork_ready` completion, however, the next complete request reached 47,634
prompt tokens; with 512 reasoning and 2,500 output tokens it exceeded the
50,176 physical slot and was denied before HTTP.

Thus neither observation branch reached boundary 2:

- T25 was stopped by the prospective action budget;
- C50 was stopped by physical append-only context capacity.

The frozen Phase-C question—choose the current R8@@ observation rather than
the available but stale J2@@ observation—was never behaviorally tested.

## Cell 03: E8-SOURCE, seed 223607

### Shared Phase A

The actor repeated the correct Phase-A structure and acquired `topaz-` from
the governing policy source. It did not need protocol recovery.

### T25 Phase B: authentic boundary 1 reconstruction

The first reset produced:

```text
read policy/channel.py
read dispatch/token.py
patch using CHANNEL_STEM
read bridge/coral.py
read bridge/drift.py
read bridge/elm.py
check public: pass
fork_ready
```

The actor again avoided completed Phase-A work. The final Phase-B request was
21,771 prompt tokens, and the next append-only Phase-C request failed the 25k
total gate once reasoning and output allowances were included. Boundary 2 was
therefore authentic.

### T25 Phase C: authentic boundary 2 reconstruction

After the second reset the actor performed:

```text
read policy/channel.py      -> reacquire current topaz- source fact
read dispatch/badge.py
patch with exact "topaz-"
check public: pass
submit
```

The private reasoning explicitly identified the active Phase-C target, the
need to reacquire the governing policy fact, and the required check/submit
closure. The external actions matched that plan. It did not reactivate Phase A
or Phase B, maintained current candidate bindings, passed the public check,
submitted, and passed the hidden grader.

The Phase-C prompt peaked at 12,241 tokens. This is the study's central valid
positive result: the same minimal controller crossed two real 25k boundaries
and reconstructed exact source continuity after each.

### C50 branch and interruption

C50 completed Phase B in seven calls, using the retained `topaz-` fact and a
literal patch, then read the Phase-C badge target. Its first Phase-C reasoning
correctly stated that it should reacquire/confirm the current policy source
before mutation. The operator interrupted the server during call 2, before an
assistant response was accepted.

The branch therefore cannot be used as a completed control for the successful
T25 trajectory. The interruption is not evidence about the actor's ability.

## Unexposed cell 04

E8-OBSERVATION seed 223607 was never sent to the actor. It contributes no
behavioral evidence and must not be inferred from the mechanically scripted
qualification.

## Cross-trajectory interpretation

### Purpose continuity

Purpose projection was consistently strong. After every reset, the private
reasoning correctly identified the active phase and did not restart completed
archive/stage work. This makes the exact active-step pointer empirically
load-bearing across a second transition, not merely a one-boundary convenience.

### Source continuity

Readable P0 continued to work as intended. The actor used familiar paths and
line ranges to reacquire exact source rather than navigating an opaque metadata
ontology. In the completed recurrent T25 trajectory it reacquired the same
governing source at both boundaries and correctly applied it to two different
mutations.

### Observation continuity

The actor understood the historical observation interface in Phase B. It
selected the correct handle, extracted the exact body, and then generated a
new candidate-bound observation after mutation. But the study did not reach
the point where old and new observations competed after boundary 2. Stale-
evidence selection remains untested, not failed.

### Planning and bounded reasoning

The 512-token private reasoning usually predicted the next observable action
and preserved the task stage, candidate, and remaining closure requirements.
It was most valuable at resets, where it translated the exact purpose pointer
and P0 into a short acquisition plan.

It was not optimal. The observation T25 branch reread a two-line target,
selected conservative source pages, and recognized its call-budget shortfall
only after it was unavoidable. C50 and T25 also chose different page sizes from
the same P0 information. The remaining bottleneck is local information and
budget policy, not protocol comprehension.

### Context economics

The completed recurrent T25 Phase C used a 12,241-token peak prompt. The source
C50 control reached 40,921 tokens in seed 173205. The observation C50 branch
physically stopped at a prospective 47,634-token prompt before Phase B closure.

These are not a complete paired economic estimate because no seed has both a
finished C50 and a finished recurrent T25 branch. They nevertheless show the
same mechanism seen in Experiment 006: resetting avoids repeatedly evaluating
large exact chronology, while append-only operation can exhaust even the 50k
slot before task closure.

## What the transcripts establish

They establish one clean recurrent source-continuity existence proof and show
that purpose projection remains effective over two authentic transitions.
They also expose two orthogonal limitations: recurrent pressure is trajectory-
dependent, and observation continuity can be blocked by action economics before
staleness is tested.

They do not establish a reliable success rate, C50/T25 parity, recurrent
observation selection, or a reason to add semantic memory.
