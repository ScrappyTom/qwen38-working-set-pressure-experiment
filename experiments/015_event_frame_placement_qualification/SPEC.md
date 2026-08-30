# Experiment 015: Single Event-Frame Placement Qualification

## Question

Can the qualified active-phase progress information be presented once, in one monotonically ordered event frame, without causing an obvious behavioral regression relative to the current dual `history` plus receipt-ledger presentation?

This is a development-only placement qualification. It is not the proposed large-world context study and produces no population or promotion claim.

## Why this qualification is required

Experiment 014 earned one exact monotonically ordered active-phase progress plane. In its qualified implementation, new action/result pairs remain in append-only `history` while their mechanical receipt identities are also appended to `active_phase_receipt_ledger`. That duplicates recent progress and can change both token economics and model behavior.

The intended future comparison instead uses one event-frame renderer in both branches:

- resident-control: exact recent result bodies remain resident;
- externalization-treatment: old result bodies leave the active context behind exact sequence-bound reopen handles.

Before constructing that study, this qualification tests whether replacing the dual presentation with a single event frame causes an obvious live behavioral problem on already exposed sacrificial cases.

## Conditions

`D15-UNIFIED-DUP`

The exact qualified Experiment 014 reconstructed presentation: externalized receipt prefix plus recent exact history, with recent receipts also present in the ledger.

`D15-EVENT-FRAME`

One exact monotonically ordered event sequence. Each action/result identity occurs once. Structural result fields remain visible. Large result-body fields are either resident in that event or external behind the exact sequence-bound `RES-####` handle.

The event sequence does not rank information, declare semantic sufficiency, suppress reads, summarize results, or choose relevance.

## Development material

Two exposed Experiment 014 cases are mechanically advanced to a hidden-correct post-mutation Phase-B state with five real accepted tool effects:

- `E14-CLOSURE-MINT`
- `E14-STALE-SABLE`

The state is deliberately sacrificial. Its only purpose is to exercise interpretation of already-completed progress, current-candidate checking, and submission under the two placements.

## Schedule and execution

- two cases;
- two frozen seeds;
- both conditions per case and seed;
- eight branches total;
- one attempt per branch;
- zero retries, repairs, or rescue calls;
- at most five completion calls per branch;
- Qwen3.8-27B-AD-IQ2_S under the frozen runtime;
- server-enforced 512-token private reasoning;
- exact maximal source paging;
- dedicated port 18118;
- external evidence root `C:\e15-placement`;
- response seal before post-run hidden grading.

## Pass criteria

The offline boundary passes only if:

- package bytes reproduce exactly;
- the full executable closure verifies;
- every initial prompt is capacity-admitted;
- the event frame contains neither `history` nor a parallel receipt ledger;
- exact resident events reconstruct their action/result pair;
- external events expose exact identity and no result-body fields;
- all eight scripted branches check the current candidate and submit;
- every constructed candidate passes the donor hidden checker.

The live boundary is informative rather than a quality gate. Every saved coding request, rendered prompt, private reasoning record, assistant action, and tool result must be directly inspected. A bad development action remains evidence and receives no retry.

## Interpretation boundary

Success would justify freezing a common single event-frame renderer for a later fresh large-world comparison. It would not prove that placement never matters, that externalization is beneficial, or that the controller works at large scale.

Failure would diagnose the exact behavioral or apparatus issue before any fresh large-world fixture is constructed.

## Prohibited work

This qualification does not authorize:

- a fresh large-world bank;
- a 50k-versus-25k measured run;
- summaries, semantic memory, relationship graphs, ranking, embeddings, or host-selected relevance;
- caching, duplicate-read suppression, or automatic result substitution;
- retries, repairs, rescue calls, or automatic successor work.
