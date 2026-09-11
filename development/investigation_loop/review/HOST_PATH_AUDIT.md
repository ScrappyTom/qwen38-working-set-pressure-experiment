# Host-path audit — ordinary working-loop pilot

The host carried both runs through checked submission without an observed
implementation failure. Every accepted nonterminal result was stored exactly
and included in the next actual request. The audit nevertheless finds repeated
navigation and substantial reconstruction/framing effort during successful
paths. No broad metadata or memory change follows from that distinction.

## Actual inputs and successful operation

The [initial native prompt](../run-001/calls/L01-001-rendered-prompt.txt) contains
the complete forms, limits and effects, explicit pre-edit guard meanings, the
accurate scoped navigation explanation, numerical action allowances and the
prospective return contract. It contains no correction-sequence illustration.
Each fresh history begins empty; neither actor sees the other's trajectory.
The task appears in both `task` and `active_user_authored_step.text`, under a
`continuation` stage and ordered reconstruction notice.

The host reconstructs every subsequent request from exact action/results,
checks native admission before dispatch, preserves raw output before execution,
and executes one strict final action. Correct current bindings are visible in
the accepted patch result and subsequent request; check status is not inferred
from an old result. The actor uses the new candidate for each check and submission.
No check is forced by the host, and submission itself does not require a pass.
Both actors independently fulfill the task's current-check instruction.

The following links identify the actual input, complete response and exact
return for each finding; subsequent input links establish an offered and sent
turn. The corresponding `next_turn_decision` records in
[records.jsonl](../run-001/records.jsonl) distinguish the decision to reconstruct
from the later `invocation_started` record. Their `next_request_sent=false`
means it has not yet been sent at that record, not that continuation was withheld.

| Path | What Qwen actually saw | Thinking versus final action | Host return and next actual input | Interpretation |
|---|---|---|---|---|
| L01-002 | [Input](../run-001/calls/L01-002-endpoint-request.json) retains the complete first `src` directory result, alongside static root orientation. | [Response](../run-001/calls/L01-002-endpoint-response.json) goes back to exploring `src`; final repeats the identical page request. | [Return](../run-001/calls/L01-002-host-result.json) is byte-identical to the first result. Host consumes one allowance and sends [003](../run-001/calls/L01-003-endpoint-request.json), where the actor descends correctly. | Avoidable repetition with evidence resident. Static-root prominence may contribute; cause is not isolated. No paging-completion requirement is stated. |
| L02-001 and 003 | [Initial input](../run-001/calls/L02-001-endpoint-request.json) already lists the complete top level; [003](../run-001/calls/L02-003-endpoint-request.json) retains the discovered child path. | [001](../run-001/calls/L02-001-endpoint-response.json) notices `src` but chooses `tree(.)`; [003](../run-001/calls/L02-003-endpoint-response.json) even names the child but pages its parent again. | [001 return](../run-001/calls/L02-001-host-result.json) adds no new root fact; [003 return](../run-001/calls/L02-003-host-result.json) repeats 002 exactly. [002](../run-001/calls/L02-002-endpoint-request.json) and [004](../run-001/calls/L02-004-endpoint-request.json) are sent normally. | Root confirmation and mislocated parent acquisition, respectively. No evidence was externalized or unavailable. |
| L01-007/008 | [007](../run-001/calls/L01-007-endpoint-request.json) and [008](../run-001/calls/L01-008-endpoint-request.json) retain complete target source and unchanged candidate/file identity, plus the reference's applicability explanation. | Full [007](../run-001/calls/L01-007-endpoint-response.json) and [008](../run-001/calls/L01-008-endpoint-response.json) repeatedly question whether reading must be immediate, eventually recognize applicability, then search for callers and patch correctly. | [Search](../run-001/calls/L01-007-host-result.json) returns only the definition; [patch](../run-001/calls/L01-008-host-result.json) returns the exact successor. [009](../run-001/calls/L01-009-endpoint-request.json) includes it. | Read-age interpretation effort, without an actual redundant source read. Caller search supplies a scope fact. Do not assign the whole response cost to that uncertainty. |
| L01-009 | [Input](../run-001/calls/L01-009-endpoint-request.json) contains the successful source repair, governing sources and unchanged original incident text, but no subsequent failed reopen. | [Response](../run-001/calls/L01-009-endpoint-response.json) repeatedly questions whether its patch is the reported incident and whether work remains; final runs the correct current-candidate check. | [Check](../run-001/calls/L01-009-host-result.json) passes; [010](../run-001/calls/L01-010-endpoint-request.json) is sent with its exact evidence and submits. | Episode confusion recovered before a useful check. This is neither a recorded regression nor loss at pressure. |
| L02-012/013 | [012](../run-001/calls/L02-012-endpoint-request.json) contains the accepted patch/diff; [013](../run-001/calls/L02-013-endpoint-request.json) additionally contains successor source lines 88–158. No failure follows the repair in either input. | [012 response](../run-001/calls/L02-012-endpoint-response.json) initially equates its repair with the incident; [013](../run-001/calls/L02-013-endpoint-response.json) repeatedly questions whether the repair is complete or its own. Finals confirm changed source once, then check. | [012 return](../run-001/calls/L02-012-host-result.json) is a current partial read; [013 return](../run-001/calls/L02-013-host-result.json) passes. [014](../run-001/calls/L02-014-endpoint-request.json) is sent and submits. | Confirmation after mutation is separate from duplicate navigation. Persistent framing uncertainty is visible in thinking; no incorrect edit or repeated check occurs. |
| Both closures | [L01-010](../run-001/calls/L01-010-endpoint-request.json) and [L02-014](../run-001/calls/L02-014-endpoint-request.json) include the real passing output and current check binding. | Full [L01](../run-001/calls/L01-010-endpoint-response.json) and [L02](../run-001/calls/L02-014-endpoint-response.json) responses read the outcomes, consider another check, then reject it as unnecessary. | [L01](../run-001/calls/L01-010-host-result.json) and [L02](../run-001/calls/L02-014-host-result.json) submit the checked candidate; no later turn is offered because submission is terminal. | Correct evidence use and stopping. A contemplated redundant check is not an executed one. |

The first complete target read is delivered before mutation in both runs.
Inspection uses exact source and identity, not only path flags. L02's later
read starts at line 88; its page-complete flag does not imply a whole-file read.
Historical `complete_reads` survives the patch, and this audit does not treat
that bookkeeping as new inspection of changed successor bytes. Unchanged
`artifact_units.py` and `reopen.py` remain applicable across the candidate change.

## Return path, correction opportunity and limits

The largest source read returns 17,440 bytes; its complete result occupies
18,682 canonical JSON bytes. The repaired host admits it only after validating
the original and future exact-access wrapper. Exact originals are saved without
truncation; their next-input payloads reconstruct the recorded returns exactly.
Source analysis, mutation and later checks demonstrate use, not just delivery.
No live historical retrieval or adversarial oversized rejection occurs here;
the preceding offline boundary qualification is not relabeled as live evidence.

L01 first checks with 12 actions remaining before the check and 11 after;
L02 has 8 and 7. Both checks pass, both next requests are admitted and sent,
and both submit. The measurement's post-failure opportunity is null because no
failure occurs. Remaining actions are not a guarantee of future input admission;
this attempt simply has no capacity denial to interpret.

The main remaining issue is costly reconstruction despite resident evidence.
The unchanged incident wording, duplicate task locations, generic continuation
framing and overlapping candidate/host terminology are plausible contributors.
Immediate omission of private reasoning also removes the preceding explanation,
while retaining the facts needed to rebuild it. These factors are not isolated
by two seeds on one task, so no single mechanism is blamed or prescribed.

Keep exact host-generated grouping and explicit object scopes as deferred
presentation options. Future grouping must use actual records, and must not
invent progress, currentness or a repair rationale. The previous incorrect Qwen
examples do not disprove that option. This pilot earns attention to incident
versus work-history framing in a fresh task, not an additional isolated wording
comparison, global refactor or blanket reread suppression.
