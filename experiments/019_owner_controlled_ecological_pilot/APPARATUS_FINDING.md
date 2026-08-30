# Experiment 019 Apparatus Finding

## Disposition

Experiment 019 stopped on an infrastructure defect during the fourth saved
completion of cell 2. The frozen R50/X25 comparison is unscorable. There was
one attempt, no retry, repair, or rescue, and no branch was rerun.

The owned server shut down and released port 18121. The external run tree was
copied byte-for-byte into `measured_run`, then its 199 pre-evaluator files were
sealed before hidden grading. The seal aggregate is
`1defe11e2657e36f0804f76da5bfcb78df86cd2b166368afcdd0d3db8717e201`.

## Exact failure

Cell 2 call 4 returned HTTP 200, `finish_reason=stop`, a strict schema-valid
patch action, and a bounded accepted tool result. The action's `old` and `new`
fragments were byte-identical. The candidate implementation accepted that
no-op and therefore returned the unchanged candidate ID
`d2a57a0044458310fbe0b915eb88447b6f76b87dd511d68a0e31c29416342116`.

The candidate snapshot already existed at the content-addressed directory
`snap/d2a57a0044458310fbe0b915eb88447b`. `_save_candidate` attempted to write
the same exact files again and raised `FileExistsError` on `__init__.py`.

Two host defects combined to make this fatal:

1. a patch with identical `old` and `new` bytes was admitted as a successful
   mutation;
2. exact candidate-snapshot custody was not idempotent when execution revisited
   an already-custodied content identity.

The second rule is independently required even after rejecting no-op patches:
a later non-empty revert can legitimately return to an earlier exact
candidate. Content-addressed custody must accept an already-present identical
snapshot and fail only if bytes at that identity differ.

Both defects are corrected prospectively. No-op patches now return a bounded
tool rejection, and snapshot reuse verifies exact bytes before returning the
existing artifact identity. Regression tests cover both paths.

## Secondary reporting defects

The failure exposed two non-causal reporting defects:

- the stop receipt reported nine HTTP completions, although thirteen complete
  endpoint responses are present and verified;
- a shared-prefix trajectory that checked and submitted was labeled
  `shared_call_budget_exhausted`, because disposition was not updated when
  `state.submitted` ended the loop.

Future stop receipts count immutable request/response artifacts. Future
submitted prefixes use `submitted_before_first_boundary` with explicit
check/submission fields. Historical evidence remains unchanged.

## Evidence validity by plane

| Plane | Status |
|---|---|
| Authorization, bank, package, and prelaunch closure | Pass |
| Server ownership and shutdown | Pass |
| Strict endpoint transport | Pass for 13 saved calls |
| Cell 1 action/result record chain and replay | Pass, 29 records |
| Cell 1 public check and submission | Pass |
| Cell 1 post-seal hidden grade | Pass |
| Cell 2 calls 1-3 action/result chain | Preserved |
| Cell 2 call 4 request/response/reasoning/action/result | Preserved exactly; not appended to record chain |
| Response set sealed before evaluator access | Pass for partial tree |
| R50/X25 treatment comparison | Not reached; unscorable |
| Observation task | Not exposed |
| Canonical reopen identity in live behavior | Not tested |

Cell 2 call 4 is usable for direct behavioral and host-path diagnosis because
all seven call artifacts agree with the endpoint envelope. It is not a
completed action/result record because the exception occurred while attaching
the accepted patch's candidate snapshot.

## Design qualification finding

Cell 1 completed at a maximum server-reported prompt of 16,265 tokens, before
the first authentic 25k boundary. The task named all four files and stated both
required code semantics verbatim. It therefore tested grounded execution on
owner-controlled source, but not the resident-versus-externalized controller.

This is a fixture-design limitation. A future ecological fixture must prove
that its ideal correct path reaches an authentic boundary before completion,
using necessary work rather than padding, while retaining a full correction
cycle.

## Scope

Experiment 019 is neither a negative result for externalization nor a positive
ecological comparison. Its usable result is narrower: one exact owner-source
repair completed correctly; one model no-op exposed a bounded-error/custody
defect; and the intended treatment and observation mechanisms were not
reached. No automatic successor is authorized by this finding.
