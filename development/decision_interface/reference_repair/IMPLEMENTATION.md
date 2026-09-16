# Displayed source references now resolve through refresh and merging

ReferenceSession is an opt-in subclass of the frozen feedback host. It resolves
current recovery regions through the same source renderer that supplies their
displayed extents, including EOF clamping. It also recognizes actual last-delivered
source references and rejects stale versions. Existing designated-selection,
historical-acquisition and rejected-anchor address handling remains inherited.
The complete preceding-input source guard and current candidate guard are unchanged.

The four new boundary tests cover refreshed edited regions, merged unchanged-file
regions, exact selection through a returned address, stale/unknown references,
undelivered current text and clamped extents. All 56 selected checks pass in
tests-003.txt. Tests-001 preserves the missing test-fixture constructor argument;
tests-002 establishes the four repaired fixtures before the selected regression run.

Qualification-002 replays thirteen actual replies without changing their wire inputs,
results or states. The resulting C14 input remains byte-identical. All four of its
displayed addresses round-trip. The actual C14 literal reply is applied without
rewriting its text; the existing declared non-EOF separator supplies one LF. The
real successor tests check passes, with all 72 independently targeted faults detected.
The new candidate is 389292f683634a48a33bb8abcd9d70953b885802d432816ca9d75c1ad4ce8fa6.
Documentation remains unchanged; this is not a completed task.

The exact next input is 22,260 tokens including all three receipts. The qualification
uses native rendering/tokenization and four measured inputs; it sends zero model
completions. The 35-record custody chain includes copied historical observation
bytes and the newly executed check. The runtime is closed before live preparation.

Preparation-001 exposed integer diff keys restored as JSON strings. Its failure,
earlier successful qualification and original adapter sources remain preserved.
The repaired adapter restores integer keys; qualification/preparation use new 002
folders. This repair changes checkpoint loading, not model-facing tool semantics.

The next exposure is the separately declared six-request/eighteen-operation
continuation. It reuses the public prefix and corrected feedback; it is neither a
fresh task nor an extension of the closed original allowance. No new reasoning,
transport, task, checker, selection policy or researcher-authored contribution is
introduced. Model-authored account text remains unchanged, including stale allowance
and pending-check language; current host allowance and verification are separate.

Remaining observed friction is preserved in the earlier audits: recovery inventory
versus displayed inspection scope still costs interpretation; a broad literal
replacement still requires copying substantial unchanged source. This narrow
resolver correction makes no causal claim about those costs or reliable completion.
