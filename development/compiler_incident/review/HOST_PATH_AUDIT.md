# Host path audit: stored recovery versus delivered evidence

Exact custody, version guards and action replay worked on the observed paths.
The consequential limitation is later in the loop: the frozen admission rule
can externalize a newly returned payload before the next model input. Eight
accepted returns were absent from that next sent input. The actor often noticed
the absence correctly; an accepted retrieval record did not make its body usable.

## Construction, storage and next-input delivery

The previously repaired read path validates the complete result and its future
historical wrapper before committing read coverage. Saved results remain exact;
reopening does not execute a check or replay a patch. No read-construction or
historical-wrapper size rejection occurs here. This does not invalidate the earlier
return-boundary repair. It exposes a different boundary: successful construction
and exact retrieval do not establish delivery through input admission.

The runner reconstructs state and tries monotonically larger oldest-payload
prefixes until the native input fits X16000. The allowed prefix extends through
all action/result pairs, including the newest pair. It retains every event's
nonbody signals, identities, sizes and bindings. This behavior matches the frozen
algorithm; it is not source drift, a failed store or an unnoticed executor exception.

There are 64 actual result-to-next-sent-input joins, counting both fork successors.
Fifty-six retain the returned payload and eight do not. This is a join count,
not 64 unique responses or a general recovery success rate. The missing bodies are:

| Accepted return | Next invocation | Body removed before that input |
|---|---|---|
| C01 X022 | X023, prefix 22 | Original capture OBS-0001 |
| C01 X024 | X025, prefix 24 | Original capture OBS-0001 |
| C01 X027 | X028, prefix 27 | Original capture OBS-0001 |
| C01 X028 | X029, prefix 28 | README read |
| C02 X020 | X021, prefix 20 | Original capture OBS-0001 |
| C02 X023 | X024, prefix 23 | Original capture OBS-0001 |
| C02 X024 | X025, prefix 24 | Original capture OBS-0001 |
| C02 X025 | X026, prefix 25 | BUILD-A capture OBS-0002 |

For example, inspect [C02 X020's actual return](../run-001/calls/C02-X16000-020-host-result.json)
with [the following actual native input](../run-001/admission/C02-X16000-021-x020-native.txt).
The result is accepted, but all twenty bodies are external in that next input.
The [full next response](../run-001/calls/C02-X16000-021-assistant-reasoning.txt)
correctly says it has metadata without content and retrieves saved unary source.
Its previous explanation is also absent, because thinking is omitted immediately
in both conditions. No source, capture-body or report copy supplies the original
there. The stable handle survives; the requested body does not.

Earlier X turns do receive recovered bodies and use their content, but successive
large acquisitions displace counterparts and requirements. This is different from
the later eight cases where the newest body is not delivered at all. Neither is
equivalent to repeating a resident directory page or confirming changed source.

## Persistent signals also consume the working set

After C01 X029, even prefix 29 leaves 16,445 input tokens. After C02 X028,
prefix 28 leaves 16,154. Both exceed 16,000 with all payload bodies external.
The required nonbody state/history therefore sets a floor above the treatment's
limit. The next requests are withheld, with three/four actions still available.
Increasing the action limit alone would not admit those next inputs.

C01's rejected patch result and C02's final report read have no next sent input.
They are not examples of actor recovery after a failure. The terminal C01 R014
submission likewise has no next input by design. These three cases are separate
from the eight returns followed by an actual input lacking the body.

## Bindings and remaining opportunity

C01 R010 edits the acquired unary file with correct pre-edit candidate/file
guards. R012 writes the historical report on the successor; R013 checks that
candidate, passes 26 cases, and R014 submits it after receiving the actual check.
R011's report reread acquires no new report text: the prior report, guard and
unchanged-file applicability rule were already visible after a compiler-only edit.
The actor acknowledges that rule and rereads to be safe. This is a real redundant
confirmation, unlike X's recovery of absent report/source bodies.

C01 X029 names the correct current candidate/file fingerprint but invents an old
fragment absent from the file. The patch is rejected without mutation. A correct
guard does not make guessed source text correct. C02 X performs no mutation.
Historical reading is not promoted into inspection of changed successor content.

The sole first check has 20 actions before and 19 after it. Its allowance-only
correction-path flag is true; no failed check occurs, so after-failure correction
opportunity is null. Physical/input admission remains a separate constraint.
No failure recovery is demonstrated merely because three, four or twenty-four
actions remain at the respective stops.

## Boundary earned for prospective work

Before another pressure trial, qualify the complete action/result → admission →
next-decision path against accumulated nonbody history and the largest actual
returns. A newly returned body should either reach the next decision or produce
an explicit capacity outcome; accepted execution and delivery must stay distinct.
Requiring retention, changing the event view, or stopping earlier would change
experimental behavior and needs a separately identified prospective package.
No such policy was inserted into this run. Exact stored originals remain intact;
silent truncation, automatic semantic selection and blanket reread suppression
are not remedies established by these observations.
