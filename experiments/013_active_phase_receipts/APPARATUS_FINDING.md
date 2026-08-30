# Experiment 013 apparatus finding

## Disposition

Experiment 013 is a valid, sealed, and formally scorable comparison of the
frozen `T25-LATEST` and `T25-RECEIPTS` conditions.

The run completed all four shared prefixes and all eight branches. It made 148
prospective invocations, of which 134 reached the endpoint and 14 were denied
before HTTP by the exact 25,000-token guard. No retry, repair, rescue, or
cross-cell history occurred. Evaluator truth was opened only after the response
seal.

The response seal inventories 4,865 files with aggregate SHA-256
`d7d208b137d3855604eca91fc8f821ca3e411c1308faf42b9339bf43191741f8`;
the seal document itself has SHA-256
`80bd6f078570bdaac5dd6631aa9b7629db68678144615a715bd3cdbcb9957e09`.
The copied repository evidence is byte-identical to the external
`C:\e13-primary` evidence tree: 4,868 total files including the seal and
post-seal grade, 214,785,800 bytes, and zero per-file SHA-256 differences.

## Live-path integrity

- all 134 endpoint response IDs are unique;
- every completed call has its exact coding request, rendered prompt, endpoint
  request, endpoint response, assistant reasoning, assistant action, and tool
  result;
- every one of the 14 denied prospective calls retains exact pre-HTTP request
  and rendered-prompt custody;
- all twelve stage runs replay successfully;
- all runtime token-accounting deltas are zero;
- all model-visible public checks that were invoked passed;
- the owned llama.cpp server terminated, port 18116 was released, and shutdown
  verification passed;
- no measured call was retried or reclassified.

The owned server returned process code 1 after host-requested termination. This
is shutdown behavior, not a run failure: all cells, the response seal, port
release, and post-seal grading completed before the receipt was issued.

## The one rejected model action

One of 134 completed actions was mechanically rejected. In
`cell-03/T25-LATEST`, Qwen copied the current candidate ID and appended zeros,
so its first Phase-B patch was rejected as `stale candidate binding`. The exact
error entered model-visible history; Qwen reread the target, used the exact
current candidate ID, and produced the correct patch on its next mutation.

This was correct fail-closed host behavior and a recovered model error. It is
part of the measured trajectory, not an apparatus defect.

## Treatment fidelity

Both branches began from the same exact shared-prefix candidate, observations,
task, active Phase-B text, P0 root, actor, seed, call budget, tokenizer guard,
and tool contract within each cell.

The causal difference was preserved:

- `T25-LATEST` retained only the latest exact action/result pair at an in-phase
  reconstruction;
- `T25-RECEIPTS` externalized completed result bodies and exposed exact compact
  receipts for the externalized prefix, with exact bodies addressable through
  `reopen_result(handle)`.

No receipt contains semantic relevance, sufficiency, ranking, a recommended
action, or a result body. Repeated actions remained legal and were executed
normally.

## A real representation seam, not a hidden run defect

Direct transcript review found one important limitation in the frozen receipt
surface. After a reconstruction, the receipt ledger remained fixed at the
sequence externalized at that boundary. New actions appeared as complete
action/result pairs in ordinary `history`, not as new numbered receipt entries.

The request therefore presented one active phase through two exact progress
surfaces:

```text
numbered receipt ledger complete through sequence N
+
unsequenced post-reset ordinary history
```

The request contract named the second surface as post-reset history, so no
information was actually missing. However, the exact temporal union was only
implicit. In the observation case Qwen repeatedly saw a passed public check in
history yet treated the receipt ledger's unchanged `complete_through_sequence:
5` as evidence that the check had not been recorded. It reran the check until
the call budget ended.

This does not invalidate the measured comparison. It is behavior of the exact
prospectively frozen interface under test. It does limit the conclusion: this
version proves the value of compact progress receipts, but not the reliability
of a split ledger-plus-history presentation.

## Apparatus conclusion

No transport, checker, evaluator, candidate-binding, replay, response-seal, or
runtime-accounting defect affected the outcome. The primary comparison is
scorable.

The run did reveal an earned next interface question: whether one monotonically
sequenced exact receipt plane should cover both pre-reset and post-reset actions,
while full recent and externalized result bodies remain separately available.
That is a prospective representation change, not a reason to alter or rerun
this sealed bank.
