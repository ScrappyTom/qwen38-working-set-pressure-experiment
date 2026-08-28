# Experiment 002 measured apparatus finding

## Disposition

The measured lifecycle is valid as an exact execution of the frozen study.
The behavioral promotion gate fails. There was no transport, runtime, closure,
capacity-guard, custody, replay, server-lifecycle, or evaluator-separation
defect.

The response set was sealed before evaluator access:

- response files: 511;
- response aggregate SHA-256:
  `a1af26ba8c66c1ad18dd38a4684ffccce7c0df33efc18af82367059c18b8da89`;
- exact completion calls: 67;
- prospective calls: 70;
- retries, repairs, rescues: zero;
- server shutdown and port release: pass.

The sealed tree was copied from `C:\e2m-primary` into `mrun/` and all 511
file identities were verified. Action/result replay and candidate
reconstruction passed for every executed prefix and branch. Hidden grading was
opened only after the seal and replay.

## Model-quality outcomes are not apparatus failures

Two of four shared prefixes exhausted the frozen 14-call budget without an
accepted `fork_ready`. The runner preserved them as `prefix_incomplete`, did
not synthesize a fork, and continued to the next scheduled cell. This is the
prospectively specified handling of model-quality noncompletion.

Three continuation requests were denied before HTTP by their frozen context
guards: observation T25, source C50, and source T25. Each denied request and
admission decision is custodied, with no assistant response fabricated. These
are measured capacity outcomes.

## Treatment integrity

For each eligible fork, C50 and T25 bind the same exact task, seed, candidate,
P0 projection, prefix history hash, observation-directory hash, last prefix
record, and pending stage. C50 retains the complete prefix chronology. T25
receives a fresh context containing the original task, exact current world,
current P0, latest accepted fork action/result, and complete exact observation
directory. No semantic summary, host-selected relevant file, evaluator truth,
retry, or rescue entered either branch.

The exact frozen actor was Qwen3.8-27B-AD-IQ2_S with reasoning off. All 67
live calls reported the same prompt-token count as the offline tokenizer;
runtime accounting delta was zero throughout.

## Scope

The run supports conclusions about this actor, representation, task geometry,
and fixed action budgets. Because only two forks became eligible, it does not
provide four complete matched C50/T25 pairs and cannot support the planned
positive promotion claim. The incomplete prefixes themselves remain useful
evidence about long-horizon action budgeting.
