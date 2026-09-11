# Prospective result-return and navigation repairs

The two size failures in the owner-supplied review reproduce against the actual
checkout. Both are repaired prospectively. An offline attempt at the proposed
working loop also exposed a directory-navigation crash, now repaired narrowly.
No model inference occurred. The wording comparison stays closed: retain its
complete reference and accurate wording without claiming a performance benefit.

## Direct evidence and earned changes

[BASELINE_PROBES.json](BASELINE_PROBES.json) preserves admitted source, action,
attempted and actual return sizes, exact returned objects, before/after state,
canonical stored originals, externalized records and actual retrievals. These
are actual `Candidate`/`ToolExecutor`/storage-recording paths, not isolated copies
of their logic. The owner's external probe bundle was not available in this
checkout; this reproduction uses the description in the supplied review.

Each source below is 18,000 UTF-8 bytes, comprising 200 whole lines. Different
envelope metadata makes these sizes two bytes smaller than the quoted isolated
probe, without changing either failure.

| Source | Baseline read | Baseline historical access | Repaired first page and exact access |
|---|---|---|---|
| Ordinary text | Accepted, 18,560-byte result | Accepted, 18,960-byte wrapper | Same complete 200-line page and wrapper |
| Quote-heavy | 36,360-byte return rejected; error contains no source, but state credits lines 1–200 and complete reading | Only the small rejection was stored, not the source | 59 lines, 10,978-byte result, 21,739-byte wrapper; next line 60, not complete |
| Mixed quotes/text | Accepted, 20,560-byte result | 24,960-byte wrapper rejected | 175 lines, 18,035-byte result, 21,910-byte wrapper; next line 176, not complete |

The baseline gate probe supplies an independent passing-check flag solely to
isolate the reading obligation. It demonstrates that false read credit can open
the gate; it does not claim an actual check ran or a model received the source.

The repair constructs each complete result before crediting read coverage. A
read chooses the largest whole-line prefix within the existing raw-source limit
(18,000 bytes), complete-result limit (22,000), and exact saved-result wrapper
limit (22,000). The same fields report the actual range and continuation. EOF is
tested separately because its null continuation can be smaller than a preceding
numeric continuation. Adjacent/overlapping ranges still combine; a read beyond
EOF does not supply missing source. Empty-file acquisition remains distinct.

All newly admitted original results must fit their eventual canonical historical
wrapper. Repeated accesses keep the original address and bytes; they do not add
another storage wrapper. Imported observation/result/event payloads are checked
before advertising their handles. Existing oversized originals remain intact;
this repair rejects importing an unreachable payload rather than pretending it
can recover it. No chunk protocol, storage migration or silent truncation is
introduced. The [prospective return contract](RETURN_CONTRACT.md) must accompany
the full tool requirements in future actual inputs; frozen references remain
historical documents.

The stronger admission check made the same commit ordering necessary for edits,
checks, probes and terminal flags. An unrecoverable patch result leaves the
candidate and check flags unchanged. A checker may execute before its complete
result fails admission; this does not roll execution back or credit a new passing
observation. Offline checker execution and an accepted/delivered check result
remain separate facts. Rejected boundary, probe and submission results do not
commit their flags.

These changes can shorten large pages, add required read calls, and move input
occupancy. They are prospective behavioral changes, not merely relabeled metrics.
Successful return construction is not proof of inclusion in the next model input.
The integration review must inspect that delivery directly.

## Additional navigation defect

[NAVIGATION_BASELINE.json](NAVIGATION_BASELINE.json) records the exact failing
`p0_page` request for `src/addressable_information_layer` on the admitted donor.
Counting symbols unnecessarily rendered every child's outline; a 325-byte
`render_working_brief` signature in `renderer.py:23` exceeded the 240-byte outline
limit. Its `P0Error` escaped the tool dispatcher and aborted the scripted loop.

Directory counts now use parsed top-level nodes without rendering signatures.
The dispatcher returns a normal rejection for `P0Error`. The explicit outline
limit remains: an outline of that file is rejected, but directory discovery and
exact source reads work. Invalid Python still prevents a Python outline/count
page and returns a clear rejection; no source is invented or truncated. Tests
cover the actual donor, failed outline, subsequent exact read, malformed source
and invalid paging. This fixes the observed blocker without adding a new view.

## Verification and historical boundary

[VERIFICATION.json](VERIFICATION.json) records **58 selected passing checks**, no
failures/errors/skips, source/test identities, and exact W01–W08 compatibility
replays through the patched host. These are selected standard-library-compatible
tests, not a full-suite run; pytest is not installed. The return matrix exercises
eight source shapes in both read modes: quotes, backslashes, control characters,
CRLF, Unicode, blank lines, mixed and ordinary text. It stores each complete
page on disk, removes its body from the event view, retrieves the original twice,
checks canonical identity and immutability, and reconstructs all source bytes.
Boundary/rejection cases cover reads, legal edits, completed checks, imported
evidence, state flags and historical source applicability after edits.

[FINAL_PROBES.json](FINAL_PROBES.json) records the final host's exact first-page
returns. Earlier [REPAIRED_PROBES.json](REPAIRED_PROBES.json) and
[FOCUSED_TESTS.json](FOCUSED_TESTS.json) preserve the first repair stage before
navigation was fixed. Despite its filename, [FINAL_TESTS.json](FINAL_TESTS.json)
is the intervening unsuccessful test attempt: one new test incorrectly expected
one symbol in `renderer.py`; direct source inspection found eight. Correcting
that expectation required no production change. The final verification supersedes
that attempt; no exposed model cell was retried.

The historical source pin is `3faf24e9e4a525bff00ca00ac32549ca662735bf`.
All 100 public files in the wording response inventory and 69 chained records
verify. Its 48 source identities match that Git pin; only `tools.py` and
`hierarchical_p0.py` differ in today's source closure. All eight saved input
states/actions/results/successors replay identically under the patched host.
Private runtime binaries/logs and native tokenization were not reverified in
this maintenance pass. Historical reports, scores, inputs and seals are unchanged.

Old execution-closure loaders correctly reject today's edited source. Reproduce
old execution using the pinned commit; do not regenerate old closure manifests
against the repair. Small historical actions remaining compatible does not mean
all larger historical paths behave identically.

To reproduce new checks from the repository root, use Python 3.12 with `src` on
`PYTHONPATH`, and choose new output paths:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
py -3.12 -B -X utf8 maintenance/result_return_boundaries/probe_checkout.py --output <new-probe-output.json>
py -3.12 -B -X utf8 maintenance/result_return_boundaries/verify_checkout.py --output <new-verification-output.json>
```

## Next decision

The [scripted loop](../../development/investigation_loop/OFFLINE_FEASIBILITY.json)
completes ten actual tool operations from failing check through checked submission.
It is an oracle path, not model navigation or investigation evidence. Its genuine
failure diagnostic already identifies a stale map, so it is a useful integration
candidate with limited discovery value. Natural pressure and native task budgets
remain unqualified. The [next-step proposal](../../development/investigation_loop/PROPOSAL.md)
places ordinary multi-turn qualification before the main pressure study.

Governance now explicitly distinguishes historical acquisition from successor
inspection, constructed returns from actual delivery, and loss at a boundary
from rationale that was never carried beyond private thinking. The prospective
25k target is defined as input only, separately from physical generation space;
the current 32,768 reserve on 56,576 cannot yet produce that contrast. No new
memory mechanism, interface micro-test, model exposure or changed GPU policy
follows automatically from these repairs.
