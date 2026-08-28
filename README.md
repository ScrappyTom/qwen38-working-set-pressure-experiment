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

