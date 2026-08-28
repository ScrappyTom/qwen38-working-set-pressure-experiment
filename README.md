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
