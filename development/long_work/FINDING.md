# A concrete larger-source admission limit

The actual current implementation inventory contains 40 Python files and 602,261
bytes. Nine files fail the host's 24,000-byte per-file admission rule; none of the
40 violates the 512-byte line limit. This is a pre-model restriction, recorded in
admission-001.json. It is independent of Qwen's interpretation or task performance.

The isolated follow-up changes only the candidate module's file limit in its own
Python process, from 24,000 to 1,048,576, without editing the tracked host. All
other limits and the exact executor/recovery implementation remain unchanged.
The largest actual tested file is 47,907 bytes; the probe does not qualify every
file up to 1 MiB.

All 40 files are admitted. The actual host reads them in 56 whole-line pages,
stores each complete result and reopens every page exactly. Joined pages equal
the original bytes and complete coverage is recorded. One guarded comment edit
of the largest copied file succeeds; repeating that edit with predecessor guards
is rejected without changing the successor. The current public check compiles all
40 Python files. A saved pre-edit source page still reopens as the exact predecessor
after mutation. Total: 116 actual isolated operations, zero model calls.

This qualifies the tested paging, return-size, exact recovery, coverage and
version paths for these real larger files. It does not establish model admission
or delivery, useful navigation, application correctness, long-document handling,
unassisted selection or long-running work. The process-local limit is restored;
no active experiment or shared-host policy changes.

An explicit larger-file configuration is earned for the next preparation. Keep
the historical default and frozen runs reproducible. Its visible tool reference
must state the effective limits truthfully, and successor admission must use the
same selected policy. The separate long-history/input budget problem remains:
allowing larger source files does not bound resident event-signal growth.

The first ad hoc inventory probe caught ValueError instead of the actual
CandidateError (a RuntimeError subclass); its expected rejection therefore
printed uncaught. The saved inventory probe corrects the catch without changing
the host. The subsequent 116-operation qualification passes on its first run.
Exact results, pairs, source fingerprints and seal are in
[large-file-qualification-001](large-file-qualification-001/RESULTS.json).
