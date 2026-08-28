# Experiment 006: authentic bounded-reasoning pressure transition

## Question

Can the exact Qwen actor continue correctly after an authentic live chronology
crosses the 25k pressure boundary when reconstructed from exact custody, P0,
and a verbatim active-step pointer, compared with retaining the identical
chronology in a 50k append-only context?

## Conditions

- **C50-R1:** the complete exact pre-fork chronology remains active under the
  physical 50,176-token slot.
- **T25-R1:** a fresh active context contains the exact task, current candidate,
  current P0, latest accepted fork result, complete identity-only observation
  directory, verbatim frozen Phase B pointer, and exact fork binding. Older
  chronology remains externally custodied but is absent.

Both conditions use the same AD-IQ2_S actor, seed, sampler, tools, candidate,
P0, pending work, 2,500-token response allowance, and server-enforced maximum
of 512 private reasoning tokens per call. Private reasoning is separately
custodied and never enters later history.

## Fresh cases

Two actor-unexposed cases are frozen before execution:

1. **E6-SOURCE:** Phase B requires reacquiring a governing source constant
   through P0 and exact read.
2. **E6-OBSERVATION:** Phase B requires reopening an exact compatibility
   observation that is absent from source.

Each live shared prefix must perform its real Phase A work, mutate and check
the current candidate, accept `fork_ready`, produce an append-only next request
that fails the 25k guard, and remain admissible under 50k. No filler, duplicate
padding, constructed prefix, semantic summary, ranking, or host-selected fact
is permitted.

## Schedule and boundaries

- two live prefixes and four continuations;
- branch order alternates across cases;
- 12 prefix invocations and 8 continuation invocations maximum;
- one attempt per call; zero retry, repair, rescue, or cross-cell feedback;
- every prepared invocation and actual HTTP completion is counted separately;
- model outcomes continue; infrastructure or integrity failures stop execution;
- responses are sealed before evaluator access.

## Decision rule

The reconstruction controller earns a recurrent-boundary study only if both
T25-R1 branches:

- preserve hidden correctness relative to their matched viable C50-R1 branch;
- reacquire the exact governing source or observation before mutation;
- check and submit without exceeding 25k;
- exhibit no stale binding, retry, rescue, or host-selected relevance.

Economics, latency, excess reacquisition, and reasoning/action alignment are
reported even when quality passes. A failure is diagnosed from every exact
saved prompt, output, result, and private-reasoning record before any successor
is proposed.
