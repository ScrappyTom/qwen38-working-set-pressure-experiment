# Receipt-correction baseline: evaluator-only source audit

22 September 2026. Read the exact original task, all thirteen candidate files,
fixture construction, complete public checker, original specification and previous
results/host audit. Also inspected the historical emitted patch, final source,
submission and complete saved check output. No checker, model, native runtime or
task operation was executed. This document is outside runtime source closure and
actor inputs. It must not supply a diagnosis, location or repair during a live run.

## Task and independent invariant

The task reports incorrect stock quantities after receipt corrections. It requires
repairing reporting while preserving validation, latest-revision selection, duplicate
handling, void receipts and independent receipt contributions. Exact current source,
a public check on the final candidate and submission are required.

The README defines the full existing contract. A ticket is a stripped, case-sensitive
nonempty identity. Depot/item labels are stripped and uppercased. Revisions are
positive ASCII decimal integers; units are nonnegative ASCII decimal integers.
Whitespace and leading zeroes are allowed. Status normalizes to active/void. Every
row must validate, including a lower revision that will subsequently be ignored.

For each ticket, the highest accepted revision is current. An identical repeat of
the current revision is a no-op. A conflicting equal current revision raises
ValueError; a lower revision is ignored after validation. Different tickets remain
independent even when all other values match.

The reporting invariant after each accepted transition is:

`total[depot, item] = sum(units of the current active receipt for each ticket in that group)`.

Void receipts contribute zero. Zero-total groups are omitted. Final rows sort by
depot/item, and `latest_receipts` sorts selected receipts by ticket. This invariant
comes from the task, README and inspected implementation; it does not depend on
matching the reference patch or reusing the public check's expected data.

For an accepted update, remove the old active receipt's units from its old group
and add the new active receipt's units to its new group. This preserves the invariant
from the empty state. Ignored old arrivals and duplicates cause no transition, while
void/active changes naturally remove or restore contribution. This argument assumes
the inspected registry supplies its intended before/after records; it does not
claim arbitrary externally constructed Change objects are validated by Totals.

Sources: [TASK](../../../correction_investigation/TASK.txt),
[README](../../../correction_investigation/source/README.md),
[API](../../../correction_investigation/source/src/dispatchledger/api.py),
[records](../../../correction_investigation/source/src/dispatchledger/records.py),
[CSV](../../../correction_investigation/source/src/dispatchledger/ingest/csv_rows.py),
[fields](../../../correction_investigation/source/src/dispatchledger/ingest/fields.py),
[registry](../../../correction_investigation/source/src/dispatchledger/state/registry.py),
[contributions](../../../correction_investigation/source/src/dispatchledger/reporting/entries.py),
[totals](../../../correction_investigation/source/src/dispatchledger/reporting/totals.py).

## Concrete source defect

`summarize_csv` fully decodes/validates the stream, then feeds each receipt to the
registry and applies only non-null Change records. `contributions` already emits
the old active receipt with negative units and the new active receipt with positive
units. The defect is in Totals.apply: it calculates `bucket(change.after)` once and
routes both signed entries there. Subtraction is present; its destination is wrong
when depot or item changes.

For the checker sequence, X first contributes nine ALPHA/CABLE units and Y
independently contributes four. Correcting X to six BETA/SENSOR units should leave
four ALPHA/CABLE and six BETA/SENSOR. The original loop leaves thirteen in the old
group and routes negative nine plus six into the new group, producing negative three.
Changing the shared destination to the old group merely misroutes the new contribution.
Each signed entry must affect its own receipt's group, or an equivalent implementation
must preserve the same invariant.

The preparation BAD/PARTIAL/GOOD constants are evaluator-only examples. A model
repair need not match their bytes. Rewriting normalization, selection or contribution
generation is unnecessary to fix this defect and expands the independent review burden.

## Checker coverage and limits

The [original public checker](../../../correction_investigation/PUBLIC_CHECK.py)
contains 38 explicit behavioral cases, with no donor comparison or hidden grader:

- Two intermediate checks inspect exact decoded records and the selected current
  receipts for the same concrete correction sequence.
- Twenty-two report checks cover that sequence, single/independent receipts, quantity,
  depot and item changes, remaining independent contribution, multiple corrections,
  returning to a previous group, exact duplicates, older arrivals, voids and
  reactivation, zero units, correction to zero, normalization, sorted groups and
  an empty header-only stream.
- Fourteen rejection checks cover conflicting current revisions, negative/fractional/
  non-ASCII units, zero/negative revisions, unknown status, empty identity/labels,
  missing/extra fields, invalid old-revision data and a wrong header.

Exact equality compares returned values with expected lists/dictionaries. Unlike
the shift mapping check, row order is observable and tested. Success requires no
failed case and exit zero. The initial input-sequence observation is not a 39th case.
Decoded/selected values can distinguish import or selection mistakes from reporting;
they are useful supplied diagnostics, not evidence of a repair the model discovered
without help.

Coverage remains finite. It does not exhaust arbitrary valid streams or compare
the incremental result after every arrival with independent full recomputation.
Case-sensitive ticket distinctions such as A versus a, conflicting equal *old*
revisions after a newer arrival, all invalid-number spellings, extreme integers,
all CSV quoting/newline forms and every void-to-void transition are not individually
covered. Source review must preserve their inspected existing semantics if edits
reach those components. Python equality alone also does not enforce exact runtime
numeric types in every expected-value comparison; preserve integer arithmetic.

Each ordinary case runs through an exception-catching helper, so it can record a
failure and continue. Import/setup failure or process interruption can still leave
partial output. The current host must not equate passing printed cases with a
complete passing checker execution. No documentation requirement or fresh tests
were added to the original task.

## Assess the saved contribution and actual loop

The final source review should confirm own-group subtraction/addition, independent
ticket preservation, zero-group removal, ordered rows and unchanged validation/
registry semantics. Compare every changed file, not just the target method. A
current public pass is necessary acceptance evidence but does not substitute for
this invariant and preservation review.

Audit the actual current-candidate check and subsequent submission separately from
host enforcement. Verify exact source eligibility before edits and inspect what
the actual edit feedback tells the following call. An applied diff establishes
the saved change, not its correctness or rationale. An account may preserve an
interpretation; it does not turn a guessed premise into executed evidence.

For acquisition, the key relationship crosses API, registry, signed contribution
construction and totals. A read that reveals subtraction already exists can
legitimately refine the diagnosis from missing removal to wrong routing. Reads of
previously unseen validation code may answer preservation questions even after
the repair is drafted; they should not automatically count as redundant work.
Judge repeated navigation against returned locations actually still visible.

Do not force a failed first repair, baseline check, optional account, historical
retrieval or pressure boundary. A direct correct source-led repair is valid. If
the new run does not exercise recovery or changing working sets, those broader
claims remain open.

## Original identity and prior exposure

The fixture contains thirteen files and 6,697 bytes. Original candidate:
`cb2c2d7e160c4c829b71ae1a033d34e1416224bfab84d57477857c94a731f349`.
Task SHA256: `7996e74e78899d9766749d06229418645fe66095bf5774fc1ab20fb178aacfbd`.
Public checker SHA256: `46841e0e6328588ca1cab0b87ccf35cc651ddfc9c9b13ce17b9dc2d9736d4854`.
Original totals.py SHA256:
`e1bf5143cbc452f69ef8358c5ccf91dcf7537520e7780eb6c64611c8cca24072`.

The previous R01 patch moves destination calculation inside the contribution loop.
The saved final source implements that change and preserves other files according
to the historical audit. Directly inspected saved check stdout has all 38 passing
cases, final passed status, exit zero and no stream truncation. The submission names
that checked candidate:
`3dce94985b28ebdae35c0bbf6be4d7db639503dc8319a32ffbe8727431e602b1`.
This review did not rerun that check, independently reverify the complete historical
seal or reproduce the separate GPT Pro review's broader property checks.

The old report records fourteen actions and 918.847 model-request seconds, with no
failed check or pressure boundary. That run used xhigh, seed 32452843, 24 single-action
requests and fully resident activity. The prospective regression uses medium,
seed 961221, 24 requests/72 operations, bounded navigation/change presentation and
current checked-submission enforcement. It is current-host workload requalification,
not an isolated treatment or speed comparison. A pass closes this entry only.

Historical evidence: [emitted patch](../../../correction_investigation/run-001/calls/R01-010-assistant-content.txt),
[actual check](../../../correction_investigation/run-001/calls/R01-013-host-result.json),
[final candidate](../../../correction_investigation/run-001/calls/R01-014-candidate-after.json),
[historical results](../../../correction_investigation/review/RESULTS.md).
