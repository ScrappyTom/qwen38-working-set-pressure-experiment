# Operational replies and an unintended end of work

22 September 2026. Read-only design review following receipt run-001 at
`76e078c4`. No implementation, runtime, model, native grammar test or checker was
executed for this review. The original attempt remains closed and unchanged.

Recommend an **opt-in task-execution reply contract** that requires an account
update, an operation, or both. Remove the discussion-only final form from that
contract's schema and actual decoder grammar. Preserve the existing consultation
and historical contracts. Continue the receipt contribution from its saved final
state with its five requests and five operations still consumed.

This corrects a lifecycle boundary. A prose description of intended work should
not double as an implicit instruction to abandon an unfinished execution task.
It does not guarantee useful selection, action completion or task correctness.

## Actual evidence

I directly inspected C05's full saved system/user input, thinking, final content,
decoded reply and host result, plus the final snapshots and runner/contract code.
This is not a fresh full review of C01-C04.

The actual system reference advertises four JSON forms, including
`{"discussion":string}`, and says: "Discussion alone ends the run; an
account-only reply records the account and continues." The task-specific system
instruction separately says to choose the next useful operation. Thus the
termination form is declared, not an accidental permissiveness introduced only
by validation.

The C05 user input gives an unfinished reporting repair, no check, empty selected
source, the current candidate, useful directory entries and the account identifying
README/source inspection as next work. It shows 20 requests remaining including
C05, and 67 remaining operations. The README address is visible in the root view
and recent tree result. No source bytes are claimed present. Input is 5,788 tokens;
the response generates 165 tokens and finishes normally with `finish_reason=stop`.
This is not an input-capacity, truncation or absent-address event.

C05's thinking ends with choosing to read README. Its entire final reply is:

```json
{"discussion":"I have the repo layout. Let me start by reading the README to understand the domain, then the source files under src/dispatchledger (ingest, reporting, state, records, api)."}
```

The host returns `discussion_only=true`, `executed=false`, and `operations=[]`.
The runner closes as `actor_stopped_without_operation`. There is no explicit
request to abandon the task, no operation to read README, and no checked
submission. We must not infer or execute the missing read from the prose or
thinking. The host followed its current contract correctly; that contract exposed
an unsuitable terminal path for this operational workload.

Final state has `requests_used=5`, `request_limit=24`, five archived operations,
`call_limit=72`, `starting_archive_length=0`, `submitted=false`, and
`delivery_blocked=false`. The starting and final candidate files are byte-identical.
C05 created no operation or account. The existing account remains from request 3.

## Where the behavior comes from

| Boundary | Inspected implementation | Relevant behavior |
|---|---|---|
| Declared forms | `accounted_contribution.operating_reference` | Discussion-only is explicitly terminal; account-only continues |
| Reply schema | `accounted_contribution.reply_schema`, through `operable_view` and `decision_view` | Four alternatives include the object containing only discussion |
| Native grammar | `repair_task.response_constraints` → `decision_view.reply_grammar` → `with_thinking` | Ordinary reply alternative 0 accepts a complete discussion-only object after the thinking delimiter |
| Decoder | `decision_view.decode_reply` | Parses final JSON or the literal SOURCE header/body; does not infer actions |
| Execution validation | Runner's task schema, then `AccountedSession.process_reply` using `session.reply_schema()` | Both currently accept discussion-only; zero requested effects yields `executed=false` |
| Lifecycle | `run_uncoached_contribution.Loop.invoke`/`execute` | Sets `no_operation` from that result and terminates |

The native final root also supports literal SOURCE replacement. That branch
already requires an operation and need not change. The thinking wrapper, model
effort, action rules, version guards, source prerequisites, checks and submission
requirements need no change for this defect.

## Smallest coherent correction

Use a new opt-in adapter rather than altering frozen task modules or the common
legacy default. The operational ordinary forms become:

```text
discussion + operation
discussion + account
discussion + account + operation
```

An account remains optional. An account-only reply remains a real recorded update
and consumes one operation; an empty account retains its documented clearing
meaning. This contract requires a recorded effect, not proof of useful progress.
Account-only repetition may still consume the finite allowance and should remain
observable, rather than being redescribed as success.

Minimal implementation seams:

1. A local schema helper deep-copies the existing decision reply schema and
   removes exactly the discussion-only alternative. Assert its expected shape
   and exactly one removal; preserve property order and all other fields/forms.
   Give the prospective contract an explicit identity. Do not weaken the action
   schema or silently filter unrelated forms.
2. A narrow converter wrapper can apply that same helper only to the existing
   `ordinary-reply` root supplied to `decision_view.reply_grammar`. Delegate all
   child rules and SOURCE-header construction unchanged to the pinned converter.
   This avoids copying the grammar builder or modifying shared/frozen modules.
   An optional explicit schema parameter in the common builder is another sound
   seam if needed, but a broad rewrite is unnecessary.
3. The task adapter's `reply_schema` and session subclass's `reply_schema` must
   return that same narrowed contract. The runner and operation processor both
   validate replies; changing only the model-facing schema would leave a mismatch.
4. Update the local operating-reference form list and lifecycle paragraph
   together. State that an execution reply records an account or requests an
   operation; discussion is explanation and is not a stop command. Keep the
   literal SOURCE instructions and explicit current-pass/submit requirements.
   Assert removal of the old terminal wording in the actual rendered system text.
5. Continue using the unchanged exact final decoder. Its ordinary JSON parse is
   followed by the narrowed schema validation; its SOURCE path already validates
   a header containing an operation. No parser of intentions and no extraction
   from private thinking are warranted.

For valid operational replies, the existing runner's discussion-only stop branch
becomes unreachable. It can remain unchanged for historical/consultation users.
If an out-of-contract final nevertheless reaches Python, validation should preserve
the raw response and fail closed as a contract/runtime failure. It must not execute
a guessed action or certify that the actor deliberately chose to stop.

The system still has explicit checked submission, finite request/action limits,
capacity/runtime failure closure, and the existing graceful operator-stop path.
This bounded change does not introduce an implicit retry loop or a new general
actor-abandonment protocol. Such a protocol, if needed later, should be explicit
and distinguishable from explanatory prose.

## Why not accept discussion-only and request another response?

A prospective reject-and-continue policy could be made honest, but is larger here.
It needs a preserved protocol rejection, truthful next-input delivery without
overwriting operation feedback, request accounting, bounded repeated-invalid-reply
handling and new continuation semantics. It would spend another model request
after allowing an invalid operational result in the generation grammar.

Removing the currently advertised terminal alternative addresses the observed
path before that expenditure and preserves the existing execution semantics.
Retain the response as evidence if it is produced despite constraints; do not
retrospectively turn C05 into a rejection or give the old run another automatic
attempt. Neither choice can promise that Qwen will now select a useful action.

## Qualification required before a model continuation

Schema-only tests are insufficient because the actual request uses a grammar,
not `response_format`. Qualify the prospective task's exact wire grammar with
the pinned native machinery and already-open thinking template:

- The exact C05 final, generic discussion-only and an empty object are rejected.
- Ordinary action, account-only, empty-account clear and account-plus-action
  forms are accepted and decode without changing their intended bytes.
- Literal SOURCE with/without account remains accepted, including quotes,
  newlines, delimiter-looking source text and trailing newlines.
- Incomplete final text and thinking without a completed delimiter/final cannot
  execute; action-looking private text supplies no executable operation.
- Task and session schemas agree; the rendered reference has only the intended
  forms; legacy callers still accept their historical discussion-only form.

Use the existing decoder/native grammar qualification harness rather than a new
transport subsystem. Native grammar admission is not model behavior evidence.
A small scripted account/read sequence can verify lifecycle and accounting
without a checker; a new full application-check rehearsal is not necessary to
prove this form restriction. Preserve successful and rejected synthetic examples
separately from actual model replies.

## Continuation with the original finite opportunity

Create a separately named continuation from the exact sealed final candidate,
state and preceding feedback. Restore source/designation/account/history and
`starting_archive_length=0`; these five operations belong to the same contribution.
Do not feed a researcher-chosen read, repair or the private C05 draft as a pending
action. The changed contract, unchanged task and saved state are sufficient entry
material.

Preserve global `requests_used=5` of 24 and five used operations of 72. This leaves
**19 new requests and 67 operations**, without granting a fresh 24-request run.
Keep global request numbering so future account provenance cannot conflict with
the account already written during request 3.

The common Loop assumes `sent=0` and tests `session.requests_used == sent`; its
first-input seal comparison runs only when `sent==0`. A small local Loop subclass
can set `sent=5`, keep `MAX_REQUESTS=24`, and check the frozen initial input when
`sent` equals the inherited starting offset before delegating to `super().invoke`.
The comparison must include native/request/wire hashes and token count, exactly
as the ordinary first-call gate does. This preserves C06 onward filenames and
the existing request/operation processing. It does not require duplicating the
whole `invoke` method or changing the shared runner.

A local run/manifest/seal wrapper must explicitly distinguish:

- five inherited dispatches from new dispatches recorded in this folder;
- cumulative requests used from the new-folder count and its 19-request maximum;
- five inherited operations from new operations and the cumulative 72 limit;
- continuation-only timing/token totals from original-plus-continuation totals.

The common `execute` outcome's `sent_requests` becomes cumulative under an offset,
whereas record-derived seal counts cover this folder only. Name/document both
quantities; do not silently compare them as if they had the same scope. Replay
and report readers must also accept C06 as the first new call. Verify boundary
cases at request 24 and operation 72, plus inherited-offset first-input mismatch
and graceful stop, before launch. A local request reset with separate accounting
would require extra provenance translation and is less faithful to this saved
state, so it is not recommended here.

The original outcome remains `actor_stopped_without_operation`. Any eventual
continuation success belongs to the revised operational contract and reused
state, not a fresh autonomous start or a rewritten original result. No benefit
from this change is yet established.

## Evidence checks and limits

The complete C05 wire input, thinking, final, host result and three final snapshots
were checked against their size/SHA-256 entries in the original response seal.
The current inspected account/decision schema, decision session, thinking wrapper,
common runner and small-repair adapter match their run-manifest source hashes.
There are 109 original custody rows and five recorded dispatches; no hidden sixth
request is inferred. Candidate equality was compared directly.

This review diagnoses one concrete lifecycle defect. It does not attribute earlier
navigation choices to this form, establish broad model incapacity, or qualify a
general task-management policy. Implementation and prospective native qualification
remain to be performed after this design review.
