# Successor checker qualified offline

Plan310eb24e was published before this implementation. The parent run and all
three earlier acceptance definitions remain unchanged. No new Qwen request or
runtime launch occurred for this qualification.

checker.py verifies the parent's exact checker hash, appends composition_check.py,
and returns a distinct definition. The added contract rejects drive components
at initial, dot-prefixed and interior positions; checks root/UNC/traversal forms;
and preserves accepted relative spelling through Windows component joining on
both same-drive and different-drive roots. Six relative controls produce twelve
native-join comparisons, beside twenty explicitly rejected forms. These are
finite contract cases, not comprehensive filesystem-security certification.

qualify_checker.py runs ordinary Python against fresh temporary copies of the
actual saved candidate and separately labeled evaluation variants:

| Variant | Actual outcome |
|---|---|
| Saved36e21200 | Fails on ./C:/outside.py while both older pass messages remain in stdout. |
| Evaluator reference | Passes the original, expanded and composition contracts. |
| Reference with broken timeout | Fails the original zero-timeout assertion. |
| Reference rejecting valid paths | Fails the original canonical-relative assertion. |

The full programs, four stdout/stderr pairs, reference source, exact identities
and execution environment are preserved in checker-cpu-001. The old saved
candidate is unchanged. Unsafe paths are never materialized; joining uses
PureWindowsPath without filesystem effects. The reference repair is engineering
assistance and must stay outside the next actor input. A reference pass is not a
Qwen result and does not close the real task.

The containment plan's first engineering step is complete. Still required before
another model attempt: the thin saved-work adapter, exact ancestor/candidate and
check restoration, rendered-input/native qualification, failure delivery and
current-pass closure route. Publish that package before the separately bounded
review-directed continuation. No automatic retry is running.
