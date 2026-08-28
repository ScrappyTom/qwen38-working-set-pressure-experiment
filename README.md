# Qwen3.8 Single-Boundary Working-Set Experiment

This is the lean successor to the metadata working-set evidence repository.
It tests the program's original claim directly: whether the same reasoning-off
Qwen actor can continue correctly after exact chronology no longer fits a
25,000-token active context.

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

See `experiments/002_single_boundary_reconstruction/SPEC.md`.

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
