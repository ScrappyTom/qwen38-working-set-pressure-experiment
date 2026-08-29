# Recurrent host v2 offline qualification

## Disposition

The successor host corrects both operational issues found after Experiment
008 without changing or reclassifying the sealed evidence bytes.

It is qualified offline for integration into a fresh successor experiment. It
is not an authorization to expose an old or new measured fixture to the actor.

## Corrected behavior

### Continue admitted work

The old frozen runner launched T25 Phase C only when the first prospective
Phase-C request exceeded 25k. If the request remained admitted, it withheld
Phase C and ended the branch.

`run_t25_final_operational()` now starts Phase C in either valid Phase-B state:

- `second_boundary_eligible`: reconstruct immediately at the actual denied
  transition;
- `second_boundary_not_reached`: retain the admitted T25 active history and
  continue normally.

The second case is no longer recorded as model noncompletion.

### Reconstruct at the actual pressure event

If an admitted Phase-C chronology later crosses 25k, the exact pre-request
guard denies HTTP, the host creates a new exact boundary binding, projects the
latest accepted action/result and current world into a fresh context, and
continues the same active user-authored phase.

This is not a retry:

- no assistant response existed;
- the denied prepared-call identity remains in custody;
- no model-action budget is consumed;
- the successor request has a new call identity and an exact reconstruction
  binding;
- prepared invocations and HTTP completions are counted separately.

Only one recurrent Phase-C reset is permitted by this v2 primitive. A second
capacity denial after reconstruction stops fail-closed.

### Monitor global progress

`scripts/monitor_live_run.py` reads every record chain under the owned output
root. It reports the globally latest record and any latest prepared invocation
without an accepted action result. On the sealed partial run it identifies:

```text
E8-SOURCE-S223607-C50-C02
```

This is the actual interrupted call. It does not mistake the already-completed
cell-02/C50 branch for the active branch.

## Mechanical qualification

Two integration tests use the exact sealed cell-01/T25 Phase-B candidate,
history, and boundary binding:

1. admitted Phase C continues without a reset and reaches the exact expected
   successor, public check, and submission in five HTTP calls;
2. a synthetic pre-HTTP capacity denial at the same transition creates one
   reconstruction boundary, then reaches the same successor, check, and
   submission in five HTTP calls from six prepared invocations.

The global-monitor regression verifies 89 prepared invocations, 87 completed
actions, and the exact unmatched call from the historical partial run.

Repository qualification:

```text
29 tests
29 passed
0 failed
```

No endpoint request, llama.cpp server launch, GPU activity, model completion,
or measured-fixture exposure occurred during this correction.

## Unchanged boundaries

The following were not changed because the host-path audit did not identify
them as defects:

- P0 representation;
- observation-directory candidate bindings;
- 512-token private-reasoning cap;
- exact source/read semantics;
- public or hidden checkers;
- model-visible action budget;
- stale/current semantic policy;
- sealed Experiment 008 evidence and historical runner.

The observation call-budget outcome remains model policy under a valid frozen
limit. A fresh study may choose task geometry with prospective action headroom,
but must not retroactively enlarge the old branch budget.

## Integration requirement

Any fresh recurrent measured runner must call the v2 operational primitive,
include `src/working_set_exp/recurrent_host_v2.py` in its executable closure,
use the global monitor, and mechanically prove both the continuous and actual-
pressure transition paths before model exposure.
