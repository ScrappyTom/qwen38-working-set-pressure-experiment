# Running implementation notes

The initial nine CPU tests pass. Four-worker verification hashes every file and
reduces the measured median from8.301s to4.237s in the counterbalanced1/4/4/1 local
probe. This is verifier I/O performance, not a predicted model or whole-loop gain.

An initial import probe failed before any runtime/model/check call: naming the new
module diagnostic_task.py shadowed the existing coherent_diagnostics module of
that name, causing a partially initialized module error through repair_task.
Renamed the new module continuity_task.py; do not alter the historical module or
conceal the failed apparatus probe. No experiment was exposed by that failure.

Twelve CPU checks now pass, including the actual failed-check state followed by
search, unchanged candidate/check applicability, exact fragment recovery, all
three live diagnostics and preservation of the old adapter. The overview fills
a bounded serialized-detail allowance by measured bytes rather than a fixed
one/two-diagnostic count; complete next-input admission remains the host's job.
Scope outcomes remain compact and visible. Native qualification is still pending.
