# Observation custody and an operable recovery presentation

This opt-in development configuration implements the published plan at 5fe48c51.
Historical capture, result bounds and presentation remain the defaults used by
their original experiments. No stored historical input or result is rewritten.

## Observation boundary

`ObservationStore` runs checks in the existing isolated candidate arrangement and
writes captured stdout/stderr and an outcome record before constructing a report.
The run custody log records those exact files at that boundary. Outcome identity
includes candidate, checker bytes and scope. CHK references expose UTF-8-safe byte
pages; binary streams use explicit base64. Replay reads original observations instead
of re-executing a check and inventing new timestamps.

The limits are explicit: 1 MiB per stream, 128 MiB total observation storage and
30 seconds per checker. Storage admission occurs before process creation. Capture
termination and timeouts retain captured bytes, state their limitation and cannot
pass. A storage failure after process start stops with an incomplete observation
record; it does not pretend that execution was rejected before it happened.

The task checker now emits all its structured diagnostics. A derived report presents
the first real failure ahead of optional injected-fault details. Other diagnostics
remain in the preserved observation. A faulty formatter falls back to an executed
receipt and observation reference; a subsequent unexpected presentation exception
preserves the executed operation and stops. Legacy double-escaping wrapper limits
do not govern this check path.

## Recovery arrangement

`OperableSession` retains the selected source ranges and saved records when ordinary
feedback cannot fit or an acquisition meets a capacity obstruction. Its recovery
input shows the task, bindings, actual obstacle, bounded account prefix and a paged
selection inventory. Bodies remain designated and recoverable while omitted from
this input. Recent activity is omitted here; the exact archive is unchanged.

Read operations in recovery deliver temporary exact whole-line pages. Inspection
does not silently append them to the designated group. Edit authority is recomputed
from the input actually delivered; hidden designations, account prose and observation
pages cannot authorize source edits. Preceding-operation receipts follow the same
presentation policy, preventing them from silently reintroducing large bodies.

Search, outline, source and inventory results provide mechanically derived region
references. `work_on_exact` assembles complete identified regions and saved records
or rejects the whole replacement. Ordinary `work_on` retains exploratory paging.
Both must qualify the resulting ordinary presentation before exiting recovery.
An account can accompany either replacement in joint admission, preserving authorship
before acquisition while avoiding an unnecessary crowded intermediate input.

The host chooses the presentation arrangement, not semantic relevance. Region hashes
identify exact extents under a file fingerprint; they do not certify that the region
is sufficient. Search context is not automatically an entire function. The normal
source/check guards and declared edit checks remain. Accounts are optional, authored
understanding, with no host-generated semantic revisions.

## What remains unresolved

This configuration makes an operating recovery path possible under tested supported
limits. It does not guarantee good evidence selection, correct account meaning,
whole-task completion, or termination of uncapped generation. A pending-proposal
channel and new payload/reasoning formats are deferred. No action is recovered from
unfinished thinking. Native scripted feasibility and Qwen behavior remain separate.

The complete/check/correction evidence, including failed qualification attempts,
belongs beside this implementation. The separately frozen model attempt must be
reviewed through its actual inputs, full outputs, executed feedback and saved work.
