# Experiment 009 results and decision

## Executive result

Experiment 009 supplies the project's first replicated recurrent observation-
validity result.

Two of four T25 trajectories crossed two authentic 25k boundaries. In both,
Qwen compared exact candidate bindings, selected the current observation over
an older stale one, reopened the exact marker, made the exact hidden-correct
Phase-C repair, passed the public check, and submitted. Both final candidates
passed post-seal hidden grading.

The other two T25 trajectories produced correct Phase-B candidates and current
observations but failed before boundary 2 because of actor-selected acquisition
cost: one redundant target read caused a 25k denial, and one seed used seven
50-line bridge pages until the twelve-action budget expired.

All four C50 append-only controls made the correct Phase-B repair and passed
their checks, but none reached Phase C. Each hit the physical 50,176-token
context ceiling before `fork_ready`.

The result is therefore not simple parity. It is a bounded existence proof plus
a reliability finding:

> Exact purpose projection, readable P0, candidate-bound observation identity,
> and exact reopen can preserve current evidence through two authentic resets.
> The remaining failure mode is local acquisition economics, not stale-evidence
> confusion or missing semantic memory.

## Outcome table

| cell | C50 | T25 | current-versus-stale tested? |
|---|---|---|---|
| Alpha / 173205 | correct Phase B; physical capacity stop before fork | correct Phase B; one redundant read; 25k stop before fork | no |
| Beta / 173205 | correct Phase B; physical capacity stop before fork | crossed boundary 2; selected current `P4!!`; hidden pass; submitted | yes, pass |
| Alpha / 223607 | correct Phase B; physical capacity stop before fork | correct Phase B; conservative 50-line paging exhausted 12 calls | no |
| Beta / 223607 | correct Phase B; physical capacity stop before fork | crossed boundary 2; selected current `P4!!`; hidden pass; submitted | yes, pass |

Mechanical totals:

- 117 prepared invocations;
- 112 HTTP completion calls;
- 112/112 completed actions accepted;
- 14/14 model-visible checks passed;
- 0 retries, repairs, rescues, or evaluator reads before seal;
- 14/14 completed stage runs replayed;
- 2/2 submitted Phase-C candidates passed hidden grading;
- runtime token-accounting delta 0 on all calls;
- exact owned server shutdown verified.

## Primary gates

| gate | result |
|---|---|
| authentic T25 transition at boundary 1 | pass in 4/4 T25 paths |
| authentic T25 transition at boundary 2 | pass in 2/4 T25 paths |
| select current rather than stale observation after boundary 2 | pass in 2/2 reached paths |
| use exact reopened fact in mutation | pass in 2/2 reached paths |
| final public + hidden quality and submit | pass in 2/2 reached paths |
| never reactivate completed work | pass on all reconstructed requests/actions |
| exact candidate/check/version binding | pass |
| every T25 request admitted under 25k | pass; inadmissible prospective requests stopped before HTTP |
| no rescue or host-selected relevance | pass |
| recurrent success across both seeds | pass for Beta lexical sibling; not across both fixture siblings |
| completed C50/T25 quality parity | not testable; C50 physically stopped before Phase C |

## What Qwen actually did

The direct audit matters more than the terminal labels.

In both successful Phase-C contexts Qwen saw two probe identities for the same
target:

```text
old handle -> old candidate ID
new handle -> current candidate ID
```

There was no observation-body preview and no host stale/current label. Qwen's
private reasoning explicitly matched the current request candidate to the new
handle, called the old record stale, reopened the new exact body, extracted
`P4!!`, and used it in the patch. Observable actions followed that reasoning.

The Alpha failures occurred earlier. Qwen had already selected the correct
Phase-A observation, produced the correct Phase-B patch, passed the check, and
captured the new current observation. It then lost the transition to mundane
tool economics: duplicate confirmation in one seed and unnecessarily small
pages in the other.

Reasoning was enabled and capped at 512 private tokens. The traces make these
choices sufficiently clear; rerunning exposed cells with thinking on is neither
necessary nor valid. More reasoning is not the earned fix.

## Context and time economics

Post-fork C50 Phase B:

```text
27 calls
832,027 cumulative prompt tokens
2,596.3 endpoint-compute seconds
0/4 Phase-C entries
```

Post-fork T25 Phase B plus reached Phase C:

```text
48 calls
293,349 cumulative prompt tokens
1,719.2 endpoint-compute seconds
2 hidden-correct submissions
```

T25 used more calls because it continued further and because two paths were
inefficient. It nevertheless processed far fewer cumulative prompt tokens and
finished two trajectories that append-only C50 could not physically continue.

On the two Beta pairs, complete T25 used 65.2% and 61.1% fewer prompt tokens
than the corresponding already-incomplete C50 Phase-B paths. This supports the
controller's economic mechanism but is not a generalized effect estimate.

## Host validity

No host bug affected the outcomes. All checks were real and passing, all
bindings were exact, capacity denials occurred before HTTP, all runtime deltas
were zero, evidence sealed before evaluator access, and the exact owned server
exited.

The audit did find a legacy descriptive inconsistency in observation-directory
v1: combined multi-stage rows are not globally `sequence_ascending`, despite
that label, and a completeness field remains prefix-named after Phase B rows
are added. Candidate bindings and bodies were correct, and both actors selected
the right handle without relying on sequence. This must be corrected through a
new schema before reuse; historical v1 evidence remains immutable.

## Architecture decision

Retain:

- exact authorized purpose and active-phase projection;
- exact external custody and replay;
- current candidate/version/effect binding;
- readable P0 paths, symbols, signatures, ranges, and file sizes;
- identity-only candidate-bound observation directory;
- exact observation reopen;
- low server-bounded private reasoning;
- authentic pre-request capacity transitions.

Do not add:

- semantic summaries;
- relationship graphs;
- embeddings or learned retrieval;
- model-authored memory;
- host-selected relevance;
- richer metadata taxonomies;
- unrestricted reasoning.

Experiment 009 closes the semantic question that Experiment 008 left open:
when the actor reaches boundary 2, exact candidate bindings are sufficient for
current-versus-stale observation choice in both tested seeds.

## Next decision

Do not spend another large measured run repeating this exact geometry. The
highest-ROI follow-up is a small fresh tool-economics diagnostic:

```text
L0: current read(path, start_line, line_count)
L1: exact read(path, start_line) returning the largest bounded whole-line page
    plus a non-guessing continuation
```

Hold P0, task, candidate, actor, reasoning, action budget, and checks fixed.
Use custody-heavy fresh tasks where exact full reads are required. Test whether
removing the arbitrary page-size decision improves closure without increasing
cumulative prompt tokens or changing semantic information.

Before that diagnostic, introduce a prospectively versioned observation-
directory schema whose ordering and completeness labels are literally true.
That is a mechanical correctness fix, not a new representation feature.

If deterministic bounded reads improve closure, carry that minimal contract
into the next larger recurrent task. If they do not, the remaining issue is the
actor's confirmation/action policy and should be tested directly rather than
answered with more metadata.

Experiment 009 is closed as valid mixed measured evidence. Automatic successor
execution remains stopped at this decision boundary.

