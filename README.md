# Qwen3.8 Single-Boundary Working-Set Experiment

This is the lean successor to the metadata working-set evidence repository.
The current program tests the original claim directly: whether
the same Qwen actor, using the earned P0 directory and server-bounded reasoning,
can continue correctly after exact chronology no longer fits a 25,000-token
active context.

The comparison is:

```text
same exact pre-fork trajectory
              |
       +------+------+
       |             |
 C50 append-only   T25 reconstructed
 <=50k            <=25k
```

Both branches retain exact external custody and the earned P0 readable
path/symbol directory. T25 receives no summary and no host-selected relevant
facts. It must reacquire exact source or prior observations itself.

See `experiments/008_recurrent_bounded_pressure_primary/SPEC.md` for the latest study,
`experiments/006_authentic_bounded_pressure/SPEC.md` for the successful first
authentic transition, and `experiments/002_single_boundary_reconstruction/SPEC.md`
for the original reasoning-off pressure attempt.

Experiment 006 completed successfully. Two fresh authentic prefixes crossed
the 25k boundary, and both reconstructed continuations reacquired their exact
governing source/observation, passed hidden grading, checked, and submitted.
See `experiments/006_authentic_bounded_pressure/RESULTS.md` and
`experiments/006_authentic_bounded_pressure/DIRECT_TRANSCRIPT_AUDIT.md`.

Experiment 007 is the earned recurrent-boundary test. It freezes two fresh
three-phase geometries and two seeds each. The same minimal controller must
cross two prospective 25k transitions, reuse or reacquire an unchanged source
fact, and distinguish a current candidate-bound runtime observation from an
older exact but stale one. No new metadata, summary, retrieval, or reasoning
feature is added. The offline scripted paths place the first transitions at
28,344/28,761 tokens and the second transitions at 22,091/22,086 prompt tokens;
all last pre-transition calls remain admitted under 25k.

Experiment 008 executed a fresh corrected recurrent study. An operator
monitoring error interrupted the primary run after 87 completed calls, so the
four-cell paired result is incomplete and will not be repaired or rerun. The
sealed evidence nevertheless contains the first genuine two-boundary T25
success: one source trajectory reacquired its governing exact fact after both
resets, passed hidden grading, checked, and submitted. The observation case
correctly handled candidate-bound observations in Phase B but did not reach
the second reset. See
`experiments/008_recurrent_bounded_pressure_primary/RESULTS.md` and
`experiments/008_recurrent_bounded_pressure_primary/DIRECT_TRANSCRIPT_AUDIT.md`.
The accompanying `HOST_PATH_AUDIT.md` distinguishes model actions from
host-withheld work, mechanical capacity denial, visible call-budget exhaustion,
and the operator interruption.

The corrected successor host is now qualified offline. It continues admitted
T25 work, reconstructs only at an actual pre-request pressure event (including
mid-phase), separates prepared calls from model completions, and uses a global
record-chain monitor. See
`experiments/008_recurrent_bounded_pressure_primary/HOST_V2_QUALIFICATION.md`.

Development live rehearsal is complete. From one exact 32k-token shared
prefix, C50 used retained chronology to make a hidden-correct repair and
submit, while T25 restarted the large Phase A reads and exhausted its 25k
envelope before acting. See
`experiments/002_single_boundary_reconstruction/DEVELOPMENT_REHEARSAL_RESULTS.md`.

The fresh measured run is also complete. Two of four prefixes reached an
eligible fork. C50 solved the observation pair while T25 ignored exact reopen
handles and exhausted its 25k envelope; both branches exhausted capacity in
the source pair after redundant reacquisition. The current no-summary T25
controller is not promoted. See
`experiments/002_single_boundary_reconstruction/RESULTS.md` and
`experiments/002_single_boundary_reconstruction/DIRECT_TRANSCRIPT_AUDIT.md`.

Experiment 003 tested the narrow earned remedy: a byte-exact user-authored
Phase B pointer, with no semantic host summary. The pointer materially improved
post-reset orientation and source economics, and the actor successfully reopened
an exact historical observation. It was not sufficient: the reasoning-off actor
still failed to mutate after acquiring the required facts. See
`experiments/003_progress_pointer_diagnostic/RESULTS.md` and
`experiments/003_progress_pointer_diagnostic/DIRECT_TRANSCRIPT_AUDIT.md`.

Experiment 004 tested the next narrow diagnostic. One source prefix exhausted
its call budget before either treatment was exposed. In the completed
observation pair, reasoning-off and reasoning-enabled Qwen both reopened the
governing historical result, made a hidden-correct repair, checked, and
submitted in five calls. Reasoning changed acquisition order and produced the
exact known-good patch, but did not improve success or call count and added
1,674 completion tokens and 88 seconds. The intended hard 512-token reasoning
cap was not enforced by the per-request llama.cpp field, so this is exploratory
reasoning-enabled evidence rather than a qualified bounded-reasoning result.
See `experiments/004_reasoning_transition_diagnostic/ATTEMPT1_RESULTS_DECISION.md`,
the direct transcript audit, and `docs/DONOR_AUDIT.md`.

A development-only follow-up moved the 512-token control to the llama-server
launch and verified an actual maximum of 511 private tokens. On the already
exposed source case, both modes remained hidden-correct, while bounded reasoning
used P0 ranges to reduce exact read content by 84.7% and cumulative prompt
tokens by 47.5%, at the cost of one call, 2,542 completion tokens, and 68
seconds. This earns a minimal fresh constructed-fork replication; it is not
itself measured evidence. See
`experiments/004_reasoning_transition_diagnostic/SERVER_BUDGET_DEVELOPMENT_FINDING.md`.

Experiment 005 is the earned fresh replication: two new source-reacquisition
geometries, exact mechanically constructed post-reset forks, and four frozen
R0/R1 branches. It removes live-prefix policy from the comparison and enforces
the 512-token private-reasoning limit at server launch. See
`experiments/005_bounded_reasoning_source_replication/SPEC.md`.

The replication is complete. Both modes produced hidden-correct code in both
cases, but bounded reasoning checked and submitted 2/2 while reasoning-off
closed only 1/2: its unnecessary large reacquisitions made the remaining check
request exceed 25k. Bounded reasoning reduced exact read content by 88.6%,
cumulative prompt tokens by 59.6%, and total prompt-plus-completion tokens by
55.6%, at the cost of two calls and 61 seconds. This earns a symmetric
reasoning-enabled C50/T25 authentic-boundary study. See
`experiments/005_bounded_reasoning_source_replication/RESULTS.md` and the direct
transcript audit.
