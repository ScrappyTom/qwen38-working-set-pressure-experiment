# Experiment 010 apparatus finding

## Disposition

The eight-cell measured run is valid for its narrow acquisition-granularity
question. No host, transport, parser, checker, capacity, custody, replay, or
runtime-accounting defect affected an outcome.

The exact run used Qwen3.8-27B-AD-IQ2_S, llama.cpp b10434, two frozen seeds,
reasoning enabled with the qualified 512-token private allowance, one attempt
per cell, and zero retries, repairs, rescues, or cross-cell history.

## Mechanical validity

- 61 prepared invocations produced exactly 61 HTTP completions.
- All 61 assistant actions were strict JSON, accepted, and executed.
- Every path completed both mechanically required full-file reads.
- All eight `prefork` checks passed.
- All eight paths reached accepted `fork_ready`.
- All eight final candidates passed post-seal hidden grading and matched the
  prospectively known-good candidate identity for their fixture.
- All eight exact action/result histories re-executed under their frozen L0 or
  L1 read semantics.
- Every runtime prompt-accounting delta was zero.
- Response evidence was sealed before evaluator truth was read.
- The owned server process terminated and dedicated port 18112 was released.

The response seal is SHA-256
`8f6c704beb5ed822c22924659e7ae85f0bc4923d9d8656429d5fe0eb4eaa6af6`.

## Model-facing isolation

The paired conditions received the same task, candidate, P0 directory, action
budget, sampler, seed, checks, and reasoning policy. The only intended
behavioral difference was the read contract:

- L0 accepted `path`, `start_line`, and actor-selected `line_count`.
- L1 accepted `path` and `start_line`, then returned the largest exact
  contiguous whole-line page fitting the frozen bound.

Direct inspection of the saved second-turn coding requests confirmed the same
task, candidate identity, invocation budget, history, P0, and non-read tools.
The L1 result retained exact file/candidate hashes, returned line range,
`complete`, and non-guessing `next_start_line`.

## Non-causal limitations and wording issue

The inherited prefix runner labels a successful short path
`pressure_boundary_not_eligible` because its original caller expected a later
25k fork. In Experiment 010 this is not a failure status. Every such path had
already passed its check and received an accepted `fork_ready`. Results use
`closed` rather than the inherited pressure label. The misleading label did
not alter any model-visible byte or host decision.

The hidden checker intentionally tests the same small target property as the
public checker. Hidden grading therefore confirms candidate identity and
post-seal evaluator separation, but is not a broader semantic test.

The ledger bodies are not needed to infer the numeric answer; complete reads
are task-required and mechanically gated. This is deliberate: Experiment 010
isolates physical transfer granularity, not whether the content is semantically
necessary.

The observation-directory v2 correction was qualified offline but was not
model-visible in these cells. Historical v1 evidence remains unchanged.

## Contamination boundary

No apparatus defect requires reclassification or rerun. The run may support
claims about exact page fragmentation, call/token economics, duplicate exact
reads, and closure under this small geometry. It may not support claims about
recurrent 25k reliability, repository-scale paging, semantic evidence use, or
duplicate-read prevention.
