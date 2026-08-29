# Experiment 012 results and decision

## Executive result

Experiment 012 is a valid negative result for the current large-world
controller.

Neither 50k append-only history nor the current 25k reconstructed frame
completed any four-phase task. C50 preserved enough in-phase progress to close
Phase B in all four branches, then physically exhausted its 50,176-token slot.
T25 used far fewer tokens, found the right evidence, and produced the correct
Phase-B mutation in all four branches, but after reconstruction it repeatedly
reacquired already-completed work and never closed Phase B.

The result isolates a specific missing capability:

> Current purpose, current candidate, P0, observation identities, and one exact
> retained action/result pair are not sufficient for repeated resets inside a
> large active phase. The controller also needs compact exact receipts for
> work already completed within that phase, while large evidence bodies remain
> externally custodied and reopenable.

This is not evidence for semantic summaries, relationship graphs, ranking,
embeddings, or read suppression.

## Formal outcomes

| Case / seed | C50 formal progress | T25 formal progress | Post-seal candidate characterization |
|---|---|---|---|
| SOURCE / 173205 | A, B complete; physical stop in C | A complete; B call budget exhausted | Both candidates pass B checker |
| SOURCE / 223607 | A, B complete; physical stop in C | A complete; B call budget exhausted | Both candidates pass B checker |
| OBS / 173205 | A, B complete; physical stop in C | A complete; fourth in-phase capacity stop | Both pass B; C50 also passes C checker |
| OBS / 223607 | A, B complete; physical stop in C | A complete; fourth in-phase capacity stop | Both pass B; C50 also passes C checker |

Terminal outcomes:

- final hidden passes: 0/8;
- submissions: 0/8;
- formal Phase-B completions: C50 4/4, T25 0/4;
- Phase-B-correct final candidates: C50 4/4, T25 4/4;
- Phase-C-correct final candidates: C50 observation paths 2/2;
- malformed/rejected actions: 0/129;
- failed model-visible checks: 0/8.

The phase-checker rows are post-seal diagnostics, not retroactive formal
completion. T25 never invoked its Phase-B check, and C50 observation paths never
invoked their Phase-C check.

## Economics

Across the four measured branches per condition:

| Condition | Prompt tokens | HTTP calls | Endpoint time | Maximum prompt |
|---|---:|---:|---:|---:|
| C50 | 1,598,786 | 47 | 5,072.8 s | 46,462 |
| T25 | 466,311 | 51 | 2,190.9 s | 13,401 |

T25 processed 70.8% fewer prompt tokens and used 56.8% less endpoint time, but
spent four more model calls and made less formal phase progress. The savings
therefore do not establish a successful managed controller at this scale.

C50's append-only history carried correct progress but grew until the next
request could not fit. T25 externalized chronology but repeatedly reconstructed
the same work. The two conditions expose opposite failure modes:

```text
C50: remembers progress, cannot keep fitting chronology
T25: fits bounded requests, cannot remember in-phase progress compactly
```

## What Qwen actually demonstrated

The terminal 0/8 hidden score should not be read as broad semantic failure.
Direct transcript review established that Qwen:

- used hierarchical P0 to find the policy source without scanning the large
  distractor world;
- correctly extracted `orbit-` and produced the intended name patch in both
  conditions and both seeds;
- correctly selected candidate-bound `OBS-0002`, extracted `A3::`, and produced
  the intended label patch in both conditions and both seeds;
- in both reached C50 observation Phase-C paths, selected current `OBS-0005`
  over stale `OBS-0002`, extracted `B6::`, and produced the intended header
  patch;
- tracked visible calls and remaining budget accurately;
- emitted only accepted, properly bound actions.

What it could not do was infer invisible read completion. A source read does not
change the candidate. Once its action/result disappeared from active history,
the model had no exact resident fact that the read obligation had been
satisfied. Repeating the read was epistemically conservative and economically
fatal.

## Hypotheses evaluated

### H1 — The earned minimal controller scales unchanged to repeated resets in a 160-file world

Not supported. All four T25 paths failed in Phase B despite producing the
correct Phase-B mutation.

### H2 — Hierarchical P0 can provide readable orientation without resident global inventory

Partially supported. Qwen used the compact root and scoped pages to locate the
policy source and avoided distractor modules. The task exposed many other paths
verbatim, so general unknown-target repository-scale navigation remains
untested.

### H3 — Candidate-bound observation identities remain understandable at scale

Supported in reached paths. Qwen selected `OBS-0002` correctly in Phase B and
selected current `OBS-0005` over stale `OBS-0002` in both C50 Phase-C paths.
T25 did not reach the later stale/current decision.

### H4 — Exact purpose and current-world reconstruction are sufficient without additional progress state

Rejected for phases that cross multiple resets. Those fields preserved the
obligation and correct world, but not which non-mutating obligations had
already been discharged.

### H5 — Low bounded reasoning is the main bottleneck

Not supported by these transcripts. Qwen articulated the correct fact, patch,
remaining obligations, and budget. The missing input was exact compact progress,
not more reasoning tokens.

## Newly earned architectural requirement

The next controller revision should add one exact, bounded, mechanically
generated **active-phase receipt ledger**. Each entry should contain only facts
already established by the host:

- action and readable target;
- candidate before/after or candidate validity binding;
- file/result/observation hash;
- exact returned range and `complete` for reads;
- accepted/pass status;
- exact body size;
- stable reopen handle for the externally custodied body.

The ledger must not state semantic relevance, sufficiency, conclusions, or the
next action. Qwen still decides whether a receipt is enough and whether to
reopen exact evidence.

The reset frame should not automatically retain a large full read body merely
because it happened to be the latest result. It should retain the compact
receipt and make the exact body demand-loadable. This is body externalization,
not suppression: a repeated Qwen request must still be honored prospectively.

## Falsifiable next hypotheses

1. **Receipt continuity:** Given the same first segment—correct patch plus two
   complete ledger reads—a reconstructed frame containing exact compact receipts
   will cause Qwen to proceed to check/probe/fork rather than repeat acquisition.
2. **Body separation:** Replacing the retained 14.4 KiB latest read body with a
   compact receipt and reopen handle will keep the first post-reset request far
   below 25k without changing available evidence.
3. **No semantic routing required:** Receipt fields alone, without host ranking
   or completion claims beyond mechanical action status, will be sufficient for
   the actor to reconstruct in-phase progress.
4. **Residual confirmation behavior:** If duplicate reads persist even when
   exact current receipts are visible, confirmation policy becomes an actor
   issue rather than a missing-state issue.
5. **P0 scaling remains separate:** A fresh case whose relevant source path is
   not strongly named in the task will be required before claiming general
   repository-scale localization.

## Decision

The current Experiment 012 T25 controller is **not promoted for large-world
recurrent use**. The smaller-world existence proof remains valid, but its
decision frame is incomplete when one active phase spans multiple pressure
resets.

Retain the rest of the architecture:

- exact authorized task and active user-authored step;
- completed phase IDs;
- exact current candidate/version;
- compact resource state;
- hierarchical readable P0;
- candidate-bound observation directory;
- maximal exact paging;
- low bounded private reasoning;
- exact external custody and replay.

Add only the earned active-phase receipt ledger and externalize retained large
bodies behind exact reopen handles. Qualify that change offline and on fresh
development material, then use a fresh sibling measured bank. Do not rerun this
exposed bank and do not add an automatic successor experiment.
