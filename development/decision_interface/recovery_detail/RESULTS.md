# Repairs and same-task reruns: incomplete contribution, two further host fixes

The owner-requested same-task attempt and separately frozen continuation are closed.
They did not complete the documentation or submit. The full reports are
[the original rerun](../feedback_repair/review/RESULTS.md) and
[the six-request continuation](../reference_repair/review/RESULTS.md).

The original rerun exposed the host rejecting its own refreshed source reference.
That resolver is repaired and qualified with the exact public correction: the
saved corrected tests pass all 72 independently targeted fault checks. This is
engineering replay, not a new live model edit. The following uncoached continuation
preserved those tests but saved no further file changes. It consumed 24.248
model-request minutes, in addition to the original attempt's 93.664 minutes.

The continuation exposed another host defect: recovery projection removed useful
patch-match addresses and a small account even after freeing ample input space.
That defect is now repaired offline. Both addresses and the full account fit at
6,757 tokens, and an exact-address source selection fits at 6,504. All 62 selected
tests pass. Exact replay verifies the actual public proposal, unchanged outcomes,
eight native inputs, 59 custody records and 357 source identities. See
[implementation and limits](IMPLEMENTATION.md) and [running notes](NOTES.md).

No additional model inference or check execution was added in this final repair.
The latest host fix is mechanically qualified; its effect on Qwen's completion
remains untested. Historical runs and consumed allowances remain unchanged.
