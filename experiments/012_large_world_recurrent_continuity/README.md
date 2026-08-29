# Experiment 012 — larger-world recurrent continuity

The exact measured run is complete, sealed, and valid. It is a negative result
for the frozen controller:

- C50 closed Phase B in 4/4 paths, then exhausted the physical 50,176-token
  context during Phase C;
- T25 produced a Phase-B-correct candidate in 4/4 paths but closed Phase B in
  0/4 because repeated in-phase resets hid compact progress receipts and caused
  duplicate exact acquisition;
- final hidden passes and submissions were 0/8;
- all 129 completed actions were accepted, all invoked checks passed, all token
  deltas were zero, and no retry/repair/rescue occurred.

The earned next requirement is a compact exact active-phase action/effect
receipt ledger with large evidence bodies externally custodied behind reopen
handles. No semantic summary, ranking, relationship graph, read suppression,
or automatic successor is authorized.

Read `RESULTS.md`, then `DIRECT_TRANSCRIPT_AUDIT.md`, `HOST_PATH_AUDIT.md`, and
`APPARATUS_FINDING.md`.
