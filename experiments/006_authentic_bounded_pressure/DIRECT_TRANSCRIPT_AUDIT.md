# Experiment 006 direct transcript audit

## Scope and method

- reviewer: Codex, condition-aware post-seal review;
- actor: Qwen3.8-27B AD-IQ2_S;
- reasoning: enabled for every call, server maximum 512 private tokens;
- sampler: temperature 0.7, top-p 0.8, top-k 20, min-p 0.0,
  presence penalty 1.5, repeat penalty 1.0;
- response allowance: 2,500 tokens;
- active envelopes: 50,176 physical for C50 and 25,000 total for T25;
- seeds: 101031 and 141421.

All 42 exact coding requests, assistant actions, tool results, endpoint records,
and separately custodied private-reasoning artifacts were inspected. The
request audit checked candidate identity, history membership, P0, progress
pointer, observation handles, stage, invocation counts, and treatment status.
Terminal candidates were mechanically replayed and hidden-graded after the
response seal.

## What T25 actually received

Both T25 reset requests contained:

- the exact complete original two-phase task;
- `stage: continuation` and the verbatim prospectively frozen Phase B text;
- the exact current candidate, P0 paths, symbols, signatures, and ranges;
- the accepted `fork_ready` action/result as the sole active history item;
- the exact fork binding and remaining budgets;
- a complete identity-only directory of reopenable dynamic observations;
- explicit notice that older chronology was externally custodied but absent;
- ordinary exact tools, with no summary, ranking, relationship inventory, or
  host-selected relevant fact.

## E6-SOURCE shared prefix

The live actor followed the intended Phase A sequence without recovery:

```text
begin
read archive/aurora.py completely
read archive/boreal.py completely
read policy/route.py completely
read stage/ready.py
patch completed_groups()
check prefork: pass
fork_ready
```

Its private reasoning tracked the remaining required files, call budget,
candidate mutation, check, and boundary transition. The governing fact
`ROUTE_STEM = "nebula-"` was present in the exact prefix chronology.

### C50-R1

```text
read delivery/key.py
read delivery/render.py
patch using policy.route.route_stem()
check public: pass
submit
```

The model explicitly recalled `ROUTE_STEM = "nebula-"` from retained Phase A
history, inspected the target and dependent renderer, and chose a robust
source-linked implementation rather than duplicating the literal. It completed
in five calls. The candidate was not byte-identical to the evaluator's literal
known-good patch, but it was the same terminal candidate as T25 and passed the
hidden grader.

### T25-R1

```text
read delivery/key.py
read policy/route.py lines 195-197 around route_stem()
read policy/route.py lines 1-50 to resolve ROUTE_STEM
read delivery/key.py again
read delivery/render.py
patch using policy.route.route_stem()
check public: pass
submit
```

The first reasoning record correctly identified Phase B from the pointer and
located `route_stem()` through P0. The getter exposed an unresolved constant,
so the actor opened a bounded header page and recovered the exact value. It
then made the same source-linked patch as C50.

The second target read and renderer read were conservative and unnecessary,
but they remained small. The important behavior is that the actor did not
restart Phase A or reread the 11-kilobyte policy file. It converted readable
P0 ranges into bounded exact reacquisition and closed within 25k.

| source branch | calls | exact read bytes | prompt tokens | completion tokens | endpoint time | peak prompt |
|---|---:|---:|---:|---:|---:|---:|
| C50-R1 | 5 | 193 | 143,110 | 1,894 | 455.500 s | 29,289 |
| T25-R1 | 8 | 3,238 | 34,855 | 3,408 | 255.103 s | 6,175 |

T25 paid three reacquisition calls and more completion/reasoning output. It
still reduced cumulative prompt tokens by 75.6%, total prompt plus completion
by 73.6%, endpoint time by 44.0%, and peak prompt occupancy by 78.9%.

## E6-OBSERVATION shared prefix

The live actor used the one-shot capability exactly once:

```text
begin
probe session -> session_marker=K4::
read archive/cinder.py completely
read archive/delta.py completely
read archive/ember.py completely
read stage/ready.py
patch completed_groups()
check prefork: pass
fork_ready
```

The private reasoning preserved the marker throughout Phase A, but the T25
reset correctly removed that reasoning and the exact probe body from active
history. Its observation directory exposed only handle `OBS-0001`, action
`probe`, and readable target `session` plus exact custody bindings.

### T25-R1

```text
reopen OBS-0001 -> exact session_marker=K4::
read session/label.py
patch with K4::
check public: pass
submit
```

The very first post-reset reasoning record distinguished the probe handle from
the prefork-check and boundary handles. The first external action reopened the
right object. The second reasoning record extracted `K4::` from the exact body,
and the actor used it in the subsequent patch. This is direct temporal
reconstruction behavior, not inference from candidate source: the marker was
absent from the candidate.

### C50-R1

```text
reopen OBS-0001
read session/label.py
reopen OBS-0001 again
read session/wire.py
patch with K4::
check public: pass
submit
```

C50 had the original probe result in its active chronology but followed the
common instruction to reopen historical dynamic results. It then redundantly
reopened the same handle a second time and inspected the dependent wire file.
The reasoning knew the marker after the first reopen; neither later action was
needed for correctness. It nevertheless closed correctly.

| observation branch | calls | source read bytes | reopened bytes | prompt tokens | completion tokens | endpoint time | peak prompt |
|---|---:|---:|---:|---:|---:|---:|---:|
| C50-R1 | 7 | 196 | 440 | 202,813 | 3,104 | 683.249 s | 29,881 |
| T25-R1 | 5 | 69 | 220 | 14,546 | 2,201 | 144.036 s | 3,564 |

T25 used two fewer calls, reopened half as many exact bytes, reduced prompt
tokens by 92.8%, total prompt plus completion by 91.9%, endpoint time by 78.9%,
and peak prompt occupancy by 88.1%.

## Aggregate behavioral interpretation

| measure | C50-R1 | T25-R1 |
|---|---:|---:|
| hidden pass | 2/2 | 2/2 |
| checked and submitted | 2/2 | 2/2 |
| continuation calls | 12 | 13 |
| prompt tokens | 345,923 | 49,401 |
| completion tokens, including private reasoning | 4,998 | 5,609 |
| prompt plus completion | 350,921 | 55,010 |
| endpoint time | 1,138.749 s | 399.139 s |

T25 used one additional continuation call overall but reduced total
token-throughput by 84.3% and endpoint time by 64.9%. More importantly, both
reconstruction mechanisms were behaviorally real:

```text
source case:       P0 lead -> exact range -> exact governing value -> patch
observation case:  readable handle -> exact reopen -> recovered runtime fact -> patch
```

Bounded reasoning was not merely descriptive. Its stated plans predicted the
observable acquisition sequence in both T25 branches, and the actions followed
those plans through check and submission. Several traces remained repetitive
or ended near the server cap, so this result supports the frozen low bounded
mode—not unconstrained reasoning or a claim of optimal planning.

## Scope

This is two fresh geometries and one seed per geometry. It establishes an
existence proof under the exact actor/controller, not a broad reliability
estimate. It tests one boundary, not recurrent operation, repository-scale P0,
or semantic compaction.
