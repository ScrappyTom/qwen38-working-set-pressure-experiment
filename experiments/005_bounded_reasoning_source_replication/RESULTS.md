# Experiment 005 results and decision

## Executive result

The fresh replication supports a narrow promotion of server-bounded reasoning
as part of the next managed-context controller.

Both modes produced hidden-correct terminal code in both cases. R1 checked and
submitted both; R0 checked and submitted one. In the second case, R0's
unnecessary large reacquisitions made its post-patch check request exceed the
25k envelope, while R1 retained enough headroom to check and submit.

## Aggregate comparison

| Measure | R0 | R1 hard-capped |
|---|---:|---:|
| Hidden-correct terminal candidates | 2/2 | 2/2 |
| Public-check pass and submit | 1/2 | 2/2 |
| Actual HTTP calls | 11 | 13 |
| Exact read content | 36,773 bytes | 4,207 bytes |
| Cumulative prompt tokens | 122,079 | 49,321 |
| Completion tokens | 832 | 5,273 |
| Prompt + completion tokens | 122,911 | 54,594 |
| Endpoint time | 308.998 s | 370.369 s |
| Largest prospective prompt | 22,103 | 5,340 |
| Private reasoning tokens | 0 | 4,413 |

R1 used two more HTTP calls and 61 seconds more endpoint time. It reduced exact
source acquisition by 88.6%, prompt tokens by 59.6%, total prompt-plus-completion
tokens by 55.6%, and peak prompt occupancy by 75.8%.

## Answer to the question

Yes, in these two fresh source-reacquisition geometries, hard-capped low
reasoning materially improved information selection and active-context economy.

The benefit was not richer semantic coding ability. It was disciplined use of
the already-earned P0 substrate:

```text
P0 symbol/range lead
        -> scoped exact getter read
        -> scoped exact constant read
        -> mutation
        -> check and submit
```

Reasoning-off instead used complete-file acquisition in both cases and, once,
drifted back into completed/irrelevant Phase A material. The actor still found a
correct patch, but too late to close inside 25k.

## Scope limits

- two cases and one seed per case are not a population estimate;
- the forks were mechanically constructed rather than reached by the live
  actor under authentic pressure;
- both cases used large Python sources with a getter and a top-level constant;
- reasoning increased latency and output tokens;
- R1 traces were repetitive and three calls hit or nearly hit the cap;
- this does not establish recurrent-boundary or repository-scale performance.

## Decision

Promote the following exact bundle into the next authentic pressure study:

- exact external custody;
- readable P0 path/symbol/signature/range orientation;
- verbatim user-authored current-step pointer;
- ordinary exact source and observation reacquisition;
- low private reasoning with a server-enforced 512-token maximum;
- private reasoning omitted from later model history;
- exact 25k pre-request guard.

Do not add semantic summaries, declarations, relationship inventories, or a new
evidence tool.

The next high-ROI experiment is no longer another short feature study. It is a
fresh authentic single-boundary comparison in which **both** branches use the
promoted reasoning/P0 controller:

```text
C50-R1: 50k append-only control
T25-R1: 25k reconstructed context with exact external custody
```

That isolates reconstruction from reasoning policy. Include at least one
governing-source case and one historical-observation case. Before execution,
fix receipt accounting so prepared invocations and actual HTTP calls are
reported separately. If one authentic boundary succeeds, proceed to recurrent
boundaries; if it fails, diagnose reacquisition policy from direct transcripts
before adding more representation.

