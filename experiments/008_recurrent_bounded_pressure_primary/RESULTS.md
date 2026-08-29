# Experiment 008 partial results and decision

## Executive result

The complete primary study was interrupted by operator error, but the sealed
partial run contains the project's first genuine two-boundary success.

On E8-SOURCE seed 223607, T25 crossed two authentic 25k pressure boundaries,
reacquired the governing exact policy source after each reset, preserved phase
and candidate identity, passed the public and hidden checks, and submitted. No
summary, relationship graph, host-selected relevance, retry, repair, or rescue
was used.

The observation case did not reach its second boundary. T25 exhausted its
action budget after correctly reopening the old observation, mutating, and
probing the new candidate. C50 hit the physical 50,176-token limit before
`fork_ready`. Consequently, current-versus-stale observation selection after a
second reset remains untested.

## Completed evidence

| cell | condition | measured outcome | interpretation |
|---|---|---|---|
| E8-SOURCE / 173205 | C50 | final hidden pass, checked, submitted | successful append-only control |
| E8-SOURCE / 173205 | T25 | Phase B passed; no authentic second boundary | actor trajectory stayed below pressure |
| E8-OBSERVATION / 173205 | T25 | correct reopen/mutation/new probe; call budget exhausted | observation semantics worked; closure economics failed |
| E8-OBSERVATION / 173205 | C50 | correct reopen/mutation/new probe; physical capacity stop | append-only 50k did not finish Phase B |
| E8-SOURCE / 223607 | T25 | two authentic resets; final hidden pass and submit | recurrent source-continuity existence proof |
| E8-SOURCE / 223607 | C50 | Phase B passed; operator interruption in Phase C call 2 | incomplete, not an actor failure |
| E8-OBSERVATION / 223607 | both | unexposed | no behavioral evidence |

The run contains 87 completed calls, 89 prepared invocations, zero retries,
zero repairs, and zero rescues. All 87 completed prompts, outputs, private
reasoning fields, and results were directly reviewed.

## Primary gates

| gate | status |
|---|---|
| one T25 source trajectory preserves hidden quality through two boundaries | pass |
| completed work is not reactivated after either reset | pass on observed T25 resets |
| current candidate/check/version bindings remain exact | pass on completed actions |
| every T25 request remains within 25k | pass |
| no host-selected relevance or rescue | pass |
| recurrent success replicated across two seeds | not established |
| stale observation rejected in favor of current observation after boundary 2 | not reached |
| complete paired C50/T25 primary comparison | invalid due operator interruption/unexposed cell |

## What changed relative to Experiment 006

Experiment 006 proved one-boundary reconstruction for source and historical
observation continuity. Experiment 008 extends that evidence in one important
way:

```text
exact Phase A purpose and world
        -> authentic reset 1
        -> exact source reacquisition and Phase B mutation
        -> authentic reset 2
        -> exact source reacquisition and Phase C mutation
        -> check and submit
```

The minimal continuation object survived recurrence at least once. Persistent
semantic memory is therefore still unearned as an immediate requirement.

The experiment also identifies two limits that the one-boundary study could
not reveal:

1. pressure points depend on actual actor-created history, not only a scripted
   qualification trajectory;
2. call budgets and exact paging can prevent a second transition even when
   active token occupancy is small.

## Architecture decision

Retain the current architecture unchanged:

- exact authorized purpose and active-step projection;
- exact current candidate/version/effect custody;
- readable P0 paths, symbols, signatures, and ranges;
- model-selected ordinary exact source acquisition;
- identity-only observation directory plus exact reopen;
- server-bounded 512-token private reasoning;
- exact capacity guards and replay.

Do not add model-authored summaries, relationship graphs, embeddings, learned
retrieval, semantic compression, richer metadata, unrestricted reasoning, or a
new evidence tool. The observed failures do not earn them.

## Next highest-ROI study

Do not rerun the exposed cells. A full replacement four-cell primary would
spend most of its calls reconfirming the source mechanism already observed.

The narrow unresolved question is recurrent observation validity. The next
study should use fresh observation-only sibling tasks and two seeds. It should
hold the controller and actor fixed while prospectively ensuring that Phase B
has enough action headroom for:

- one redundant target read;
- one additional exact source page;
- patch, check, new probe, and `fork_ready`.

The second boundary must still arise from authentic required content, and each
run must expose both the stale pre-mutation observation and the current
post-mutation observation with exact bindings. The primary behavior is whether
the actor reopens and uses the current object after reset rather than relying on
the stale exact body.

This is a follow-up diagnostic, not a retroactive completion of Experiment
008. It requires fresh fixtures and a new authorization.

## Operational decision

Future monitoring must follow global progress and the current record chain.
No process intervention may be based solely on a file count scoped to an
earlier branch. This is a human-operations correction; it does not change the
measured controller.

Experiment 008 is closed as partial measured evidence. Automatic successor
execution remains blocked pending owner review of this decision.
