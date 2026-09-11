# Dispatch Ledger

Dispatch Ledger accepts a sequence of receipt records and reports current units
by depot and item. The public API is `dispatchledger.api.summarize_csv(text)`;
it returns sorted dictionaries with `depot`, `item` and integer `units` fields.
`latest_receipts(text)` returns the selected receipt objects, sorted by ticket.

CSV has this exact header, in this order:
`ticket,revision,depot,item,units,status`. Each following row has six fields.
Tickets are nonempty, stripped, case-sensitive identifiers. Depot and item are
nonempty labels normalized by stripping whitespace and converting to uppercase.
Revision is a positive ASCII decimal integer; units is a nonnegative ASCII
decimal integer. Surrounding whitespace and leading zeroes are allowed. Status
is `active` or `void`, ignoring surrounding whitespace and letter case. Missing
or extra fields, empty identifiers/labels, invalid numbers and unknown statuses
raise `ValueError`. Invalid rows are rejected even if their revision is old.

Each ticket identifies one receipt. The highest revision wins, independent of
arrival order. An identical repeat of the same revision has no additional effect.
Two different records with the same ticket and revision raise `ValueError` when
that revision is current. A lower revision is ignored after validation.

An active selected receipt contributes its units to its depot/item pair. A void
selected receipt contributes nothing. Corrections may change any receipt field
except its ticket, including depot, item, units or status. Different tickets
contribute independently, even when their other fields match. Zero-total groups
are omitted; an empty input with only the header returns an empty report.

`examples/corrections.csv` is a small import sequence. The public check exercises
decoding, receipt selection and reports on separate examples and reports their
observed values. There are no third-party dependencies.
