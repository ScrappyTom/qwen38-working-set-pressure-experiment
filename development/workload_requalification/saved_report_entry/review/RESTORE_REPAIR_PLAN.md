# Prospective checkpoint reconstruction repair

Publish this plan and the closed run result before changing implementation.
Existing owner direction covers this bounded offline apparatus repair. No further
model calls, runtime allocation or repeated owner approval are needed to diagnose
or qualify it.

## Earned problem

The d82cdc84 live continuation produced correct checked work, but its original
verifier failed at final checkpoint restoration. The only difference is canonical
ordering of the same `diffs` map: saved JSON keys `"2","8","16"` become integers
for runtime lookup. JSON sorting then compares lexical with numeric order. Root
reproduced the finding read-only against the actual final state. Accounting,
candidate, account, diff values, captures and recorded effects are unchanged.

The existing checkpoint test used only addresses 2 and 8. Other continuation
wrappers use the same conversion/comparison pattern; inspected two-digit-only
maps do not establish another failed run. Record the shared risk without silently
rewriting historical serializers, seals or arbitrary continuation implementations.

## Repair boundary

Interpret the declared numeric diff addresses consistently during restoration.
Prefer task-local typed normalization of the incoming map for the existing exact
reconstruction comparison, preserving the historical snapshot serializer and raw
bytes. Keep integer runtime lookup keys. Accept only canonical positive decimal
addresses, reject aliases/collisions, and cross-bind each diff address and value
to its corresponding accepted archived patch receipt. A self-consistent altered
map is not authenticated merely by roundtrip equality.

Do not change `canonical_json_bytes`, model requests, source eligibility, reply
grammar, candidate/check applicability, phase budgets or model settings. Do not
replace the assertion with broad permissive equality. If implementation proves
that serialization normalization is necessary instead, preserve the original byte
format for historical replay and explicitly identify the successor format.

## Qualification

Add a focused CPU regression crossing one- and two-digit patch addresses, including
the actual run's 2/8/16 map and closing account/submission. Verify exact checkpoint
and model-view restoration, integer live lookups, account provenance, candidate,
phase counters and archive access. Reject modified, missing, reassigned or aliased
diff entries. Retain existing capture, immutable-history and counter rejection
tests. No inference is necessary for this mechanical boundary.

Preserve the original verifier's failed attempt. Separately replay all recorded
public operations under the original frozen execution sources and qualify every
saved checkpoint using the repaired restorer. Bind both source sets explicitly.
Use only saved native measurements and saved observations; prohibit subprocess,
checker, model and new tokenization calls. Check all actual native inputs and
receipts, not only final candidate equality. A corrected restoration result must
be labeled prospective qualification, never an original source run.

Update running notes, the workload ledger and governance with the observed lesson:
serialized numeric-address maps require a stable typed interpretation; exact
roundtrip is distinct from receipt/custody authentication. Publish the repair and
qualification once these checks pass. Preserve the live success, original verifier
failure and all wider pressure/selection obligations. A model rerun is not earned
solely by a checkpoint decoder repair that leaves every prior working input and
recorded operation unchanged.
