# Experiment 008 host-path audit

## Purpose

This audit asks the question that must precede model-performance diagnosis:

> For each apparent failure, what exact request did Qwen receive, what did it
> return, what did the host do next, and did a host rule or defect determine
> the recorded outcome?

The audit covers every non-success disposition in the sealed partial run and
the source paths that produced it. It is condition-aware and post-seal.

## Finding summary

| event | Qwen behavior | host behavior | classification |
|---|---|---|---|
| cell-01 T25 after Phase B | completed every required action, passed, issued `fork_ready` | withheld Phase C because the prospective request remained under 25k | frozen host gating/design limitation; not model failure |
| cell-02 T25 Phase B | correctly reopened J2@@, patched, checked, probed R8@@, then used remaining calls on required pages | stopped exactly at visible 12-call limit | model acquisition/budget-policy outcome under a valid host limit |
| cell-02 C50 Phase B | same correct semantic sequence, plus all required bridge reads | denied prospective call 10 before HTTP because 47,634 + 512 + 2,500 exceeded 50,176 | correct physical capacity stop |
| cell-03 T25 | reacquired source at two resets, patched, checked, submitted | admitted every request under 25k | genuine recurrent success |
| cell-03 C50 Phase C | read target; reasoning planned policy confirmation next | operator interrupted HTTP call 2 | operator integrity failure; not model outcome |
| cell-04 | none | never launched after interruption | unexposed; no evidence |

No completed model action was rejected. There were no stale candidate/file
bindings, malformed endpoint envelopes, protocol recoveries, checker crashes,
false public-check results, raw-response overflows, or runtime-accounting
breaches in the 87 completed calls.

## Host rule 1: T25 Phase C was withheld when pressure did not occur

The exact final Phase-B action in cell-01/T25 was:

```json
{"action":"fork_ready","expected_candidate_id":"bcca82d8..."}
```

The model-visible request showed seven of twelve Phase-B invocations used. Its
private reasoning stated that the public check had passed and `fork_ready` was
the remaining action. The host accepted it.

`run_middle()` then constructed the exact prospective Phase-C request. Because
that request was admitted under the 25k envelope, it assigned disposition
`second_boundary_not_reached`. The top-level runner only launches T25 Phase C
when disposition is `second_boundary_eligible`:

```python
condition == "T25" and middle.disposition == "second_boundary_eligible"
```

Therefore Qwen was never asked to perform Phase C in this branch.

This matches the frozen experiment's intent to measure an authentic second
reset, but it is not the behavior of a general 25k working-set controller. An
operational controller would continue with the admitted chronology and reset
only when a later request actually crossed the envelope. The current result
must say:

> second recurrent boundary absent; Phase C host-withheld

not:

> T25 failed to complete the task.

The sealed run cannot be changed. Future recurrent runners must either:

1. continue admitted work until the authentic pressure event occurs; or
2. classify the fixture/trajectory as boundary-not-instantiated without using
   noncompletion as a model-quality result.

The successor implementation now takes the first option. See
`HOST_V2_QUALIFICATION.md` and
`src/working_set_exp/recurrent_host_v2.py`. It continues admitted Phase-C work
and performs reconstruction only when the exact pre-request guard actually
denies a later request.

## Host rule 2: observation T25 exhausted a visible action budget

At call 12, Qwen saw:

```text
phase: B
continuation invocations: used 11, limit 12
current candidate: 4d8b57c0...
observations:
  OBS-0002 probe candidate 4e0601e8...  (J2@@ when reopened)
  OBS-0005 probe candidate 4d8b57c0...  (new current R8@@ body)
```

Its reasoning correctly enumerated the completed work and recognized that one
call remained while it still needed to finish `silk.py`, read `tulip.py`, and
call `fork_ready`. It used the last call to finish the already-started exact
`silk.py` page. The host then stopped because `calls == 12` and `fork_ready`
was false.

The limit was prospective, model-visible, symmetric, and correctly enforced.
The host did not hide an available call or reject a valid action. The observed
shortfall arose from Qwen's policy:

- it read the two-line mutation target twice;
- despite P0 exposing exact file line ranges, it chose 50-line pages for
  86-line files;
- it recognized the resulting budget impossibility only at the final call.

Thinking was already enabled. The private trace makes the cause interpretable,
so a thinking-on rerun is unnecessary.

## Host rule 3: C50 physical capacity denial was correct

Cell-02/C50 completed nine Phase-B HTTP calls. The next exact request was
prepared with:

```text
offline rendered prompt: 47,634 tokens
private-reasoning allowance: 512
response allowance: 2,500
physical slot: 50,176
total prospective occupancy: 50,646
```

The guard denied the request before HTTP. Request-side custody and the
capacity record are present. Counting this as one prepared invocation and zero
HTTP completions is correct. The branch demonstrates append-only physical
exhaustion, not a host bug.

## Host rule 4: observation validity was mechanically available

After Phase-B mutation, both observation requests exposed the old and new
probe rows with exact candidate IDs. The current request separately exposed
the current candidate ID. Thus the actor could mechanically distinguish:

```text
old exact probe -> candidate 4e0601e8... -> stale after mutation
new exact probe -> candidate 4d8b57c0... -> current
```

The directory did not include a host-authored `stale: true` judgment. It
exposed exact bindings from which currentness is derived. That preserves the
non-semantic host boundary.

Neither branch reached Phase C, so the interface's sufficiency for actual
current-versus-stale selection remains an open hypothesis.

## Host failure: operator monitoring and interruption

The only actual integrity failure after launch was operator-caused. Monitoring
counted artifacts only under cell-02/C50. Once that branch capacity-stopped,
its count remained unchanged while the runner correctly advanced through
cell-03/T25 and into cell-03/C50. The unchanged scoped count was misdiagnosed
as one unbounded call.

Ctrl-C arrived during cell-03/C50 Phase C call 2. The host had already saved
the exact outbound request and rendered prompt. No response was accepted. The
server shut down and the evidence was sealed without resume.

The corrective tool is `scripts/monitor_live_run.py`. It reads every record
chain under an output root and reports the globally latest record and any
prepared invocation without an accepted result. On this sealed run it points
to `E8-SOURCE-S223607-C50-C02`, the actual interrupted call, rather than the
completed observation branch.

Both corrections are offline-qualified. The historical runner and sealed
evidence remain unchanged at their source commit.

## Hypotheses earned for the next study

### H1: exact purpose projection is sufficient across recurrent resets

Evidence: every observed reset reasoning trace named the correct active phase,
and no T25 branch reopened completed Phase-A archive work. The source seed
223607 completed after two resets.

Test: fresh observation-only recurrent cases; zero completed-stage
reactivation remains a primary gate.

### H2: candidate IDs alone are sufficient for stale-observation selection

Evidence: Qwen correctly used the Phase-A observation while it was current and
created a successor-bound observation. It never reached the competing-choice
state.

Test: after reset 2, expose both old and current rows exactly as now and require
the actor to reopen one before mutation. Do not add semantic `stale/current`
labels unless this test fails through demonstrated binding confusion.

### H3: observation recurrence is limited by action economics, not semantics

Evidence: the actor selected the right handle and values but lost calls to a
duplicate target read and conservative source paging.

Test: use fresh observation tasks whose unrelated required custody geometry
allows one redundant read and one additional source page while still producing
authentic pressure. Keep the observation interface unchanged.

### H4: P0 line ranges are understood but not consistently used as page sizes

Evidence: C50 requested exact whole-file line counts; T25 defaulted to 50-line
pages despite seeing the same P0 ranges.

Test: record page-size choice and full-read call cost prospectively in the next
fresh cases. Do not add another tool or prompt hint yet.

### H5: bounded reasoning is sufficient to diagnose the current failures

Evidence: the saved private traces explicitly explain the active phase,
governing source/observation, remaining actions, and—late in observation T25—
the exact call-budget impossibility.

Decision: no reasoning-on rerun is needed; reasoning was already on at a
server-enforced 512-token maximum. A different reasoning budget is only earned
if a future failure remains causally opaque after prompt/output inspection.

## Disposition

One host policy affected apparent outcome classification, and one operator
failure truncated the experiment. Neither changes the valid two-boundary T25
source success. The result documents must distinguish host-withheld,
capacity-denied, budget-exhausted, and actor-completed paths exactly.
