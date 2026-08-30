# Experiment 020 Results and Decision

## Executive result

Experiment 020 is a clean positive ecological result for the assembled
controller.

Both R50 and X25 passed all four fresh owner-controlled trajectories:

- 4/4 hidden-correct candidates per condition;
- 4/4 passing public checks per condition;
- 4/4 submissions per condition;
- all required source/observation inspection completed before mutation;
- zero capacity, transport, or checker stop.

X25 reduced peak resident prompt size by 25–41% while preserving quality. It
did not reduce total processing cost: it used 12 more conceptual calls, and
its extra exact reacquisition made cumulative prompt tokens almost identical
to R50.

The strongest supported conclusion is:

> On these fresh owner-controlled repairs, the signal-bearing X25 decision
> frame preserved exact grounding and full task quality after authentic
> externalization. It traded lower peak context occupancy for additional
> evidence-acquisition turns rather than producing a general token-cost win.

Unlike Experiment 018, R50 remained physically executable. This run therefore
establishes reliability under externalization, not a new hard-context
capability crossover.

## Outcome table

| Cell | Family | Seed | R50 | X25 |
|---:|---|---:|---|---|
| 1 | import boundaries | 173205 | hidden pass, checked, submitted | hidden pass, checked, submitted |
| 2 | import boundaries | 223607 | hidden pass, checked, submitted | hidden pass, checked, submitted |
| 3 | verifier observation | 173205 | hidden pass, checked, submitted | hidden pass, checked, submitted |
| 4 | verifier observation | 223607 | hidden pass, checked, submitted | hidden pass, checked, submitted |

All eight branches honored the frozen pre-mutation inspection requirement.

## Aggregate economics

The following paired totals conceptually attach each shared prefix to both
conditions. The physical run made 106 calls because each prefix executed once.

| Condition | Trajectories | Conceptual calls | Prompt tokens | Completion tokens | Endpoint time | Hidden pass |
|---|---:|---:|---:|---:|---:|---:|
| R50 | 4 | 67 | 1,229,046 | 30,311 | 4,701,763 ms | 4/4 |
| X25 | 4 | 79 | 1,227,723 | 34,911 | 4,761,790 ms | 4/4 |

Relative to R50, X25:

- used 17.9% more calls;
- used 0.1% fewer cumulative prompt tokens;
- used 15.2% more completion tokens;
- used 1.3% more endpoint time.

The near-zero aggregate prompt difference hides strong paired variation:

| Cell | R50 calls | X25 calls | R50 prompt | X25 prompt | X25 prompt delta |
|---:|---:|---:|---:|---:|---:|
| 1 | 19 | 19 | 395,223 | 292,404 | −102,819 |
| 2 | 18 | 23 | 350,862 | 373,256 | +22,394 |
| 3 | 15 | 18 | 241,500 | 274,058 | +32,558 |
| 4 | 15 | 19 | 241,461 | 288,005 | +46,544 |

X25 was much cheaper when externalization removed a large resident prefix and
Qwen reopened only one governing source. It was more expensive when Qwen used
the smaller frame to trigger several conservative reacquisitions.

## Peak occupancy

| Cell | R50 peak prompt | X25 peak prompt | Reduction |
|---:|---:|---:|---:|
| 1 | 35,335 | 20,821 | 41.1% |
| 2 | 31,824 | 20,544 | 35.4% |
| 3 | 27,933 | 20,940 | 25.0% |
| 4 | 27,908 | 20,864 | 25.2% |

X25's minimum adjusted headroom ranged from 1,048 to 1,444 tokens, always
above the frozen 1,000-token reserve. R50's minimum headroom ranged from
11,829 to 19,256 tokens under the physical slot.

This is the clear X25 benefit: bounded peak occupancy and predictable
continuation headroom. Cumulative token savings are not guaranteed.

## Family-level result

### Source-heavy repair

Both conditions passed 2/2.

| Condition | Calls | Prompt tokens | Result reopens |
|---|---:|---:|---:|
| R50 | 37 | 746,085 | 0 |
| X25 | 42 | 665,660 | 2 |

X25 used 10.8% fewer prompt tokens despite five more calls. Most of that win
came from seed 173205. Seed 223607 used extra current-source confirmation and
split its patches, reversing the local economics.

### Observation/effect-heavy repair

Both conditions passed 2/2.

| Condition | Calls | Prompt tokens | Branch-local current-observation reopens |
|---|---:|---:|---:|
| R50 | 30 | 482,961 | 0 |
| X25 | 37 | 562,063 | 2 |

X25 paid 16.4% more prompt tokens and seven more calls. The observation
identity still did its semantic job: both X25 paths chose current `OBS-0002`,
never relied on stale `OBS-0001`, and used the exact current failure body in a
hidden-correct repair. The cost came from rereading or reopening source needed
to act after old bodies were external.

## What this says about the architecture

### The controller's core claim survives ecological use

The model can work from:

```text
exact task and current candidate
+ readable ordered event signal
+ candidate-bound observation identity
+ canonical exact payload addresses
+ demand-loaded exact evidence
+ 512-token bounded private reasoning
```

without resident full chronology. All four X25 trajectories demonstrate that
the frame retained enough signal to locate exact evidence and preserve quality.

### Externalization is a capacity mechanism, not automatically an efficiency mechanism

Experiment 018 established the capability crossover: R50 could no longer fit,
while X25 continued. Experiment 020 shows the other side. When R50 still fits,
resident exact bodies can reduce acquisition turns. X25 buys lower peak
occupancy and future executability, but the actor may repay some or all of
that saving through explicit reacquisition.

### Signal must be readable and decision-relevant

The current observation rows carried actionable signal:

- action/type;
- readable target;
- exact candidate binding;
- size/hash;
- canonical reopen address.

That let Qwen reject the older observation and select the current one. A bare
handle would not itself explain the choice. The experiment does not isolate
which readable field is individually necessary, so the whole earned row stays
frozen.

### Exact progress presence is not the same as actor confidence

The X25 event frame accurately recorded completed full reads. Qwen nevertheless
sometimes reacquired exact source before patching. This is not evidence for
more metadata. It is evidence that a capable model can rationally or
conservatively demand the body again when the resident signal establishes
occurrence but not the semantic details needed for action.

## Decision

Retain Earned Controller V1 with canonical payload identity unchanged.

No new model-facing representation feature is earned. In particular, do not
add:

- summaries or model-authored memory;
- relationship graphs;
- embeddings, ranking, or host-selected relevance;
- automatic duplicate-read suppression;
- cache substitution;
- more reasoning;
- a richer metadata ontology.

The current control policy remains:

> Keep exact payload bodies resident while they fit. At authentic pressure,
> externalize oldest bodies while retaining readable event identity and exact
> canonical access. Let the model decide what to reacquire.

Experiment 020 is sufficient to move beyond representation micro-experiments.
The next high-value work is broader ecological use of this frozen controller,
where failures can reveal whether remaining limits lie in P0 scale, strategic
continuity, dense observation choice, evolving user purpose, or actor action
economics. There is no automatic successor authorization.

## Remaining gaps

- only two task geometries and two seeds;
- both tasks use one owner-controlled Python package and injected defects;
- the task explicitly enumerates a complete audit set, reducing autonomous
  discovery demands;
- R50 never reached physical exhaustion in this run;
- no complex multi-phase hypothesis or rejected-alternative state crossed the
  boundary;
- observation choice involved one clearly older and one clearly current row,
  not a dense directory of current plausible observations;
- X25 operated with only about 1,000–1,400 adjusted tokens of minimum headroom;
- the result is specific to Qwen3.8-27B AD-IQ2_S, 512-token private reasoning,
  this sampler, Python, and this tool contract.

Those gaps should guide later real use. They do not undermine the completed
claim: the minimal signal-bearing controller preserved exact grounded quality
across all eight fresh ecological branches while materially reducing peak
resident context.

