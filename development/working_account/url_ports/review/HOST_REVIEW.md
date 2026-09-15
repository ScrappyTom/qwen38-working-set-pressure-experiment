# Working-account and verification host review

This review concerns the opt-in configuration frozen at bbaf1c7a. The historical
ordinary protocol remains the default. Execution observations and final replay
are recorded below when the live attempt closes.

## Observed closure

The attempt is closed with an unchanged candidate. Three accepted source receipts
arrive exactly in C02–C04. A fourth response completes normally, but processing its
read raises the preserved `CapacityError` before committing any operation. Native
trials I0041/I0042 show 24,025 tokens for one new test line and 23,880 for rejection.
The input ceiling is 23,808. The prior input's successful fit did not guarantee
that even a rejection could be delivered on the next transition.

`_fit_pages` first tries preferred headroom, then the hard ceiling. The last
documentation acquisition spends that headroom, bringing C04 to 23,802. After a
new result or rejection becomes latest feedback, previous source feedback moves
into the selected-source representation and activity advances. Those layout costs
are included in the actual failed trials. Transactional rollback protects source
coverage and the candidate, but does not provide a model-visible recovery path.
This is a host interaction boundary, not a byte-store corruption or a claim that
the undelivered page was read. All four model responses, including the final one,
are preserved; no incomplete generation is being estimated.

The stopped-path replay verifies the complete seal, native/wire inputs, all
three committed operations, the precise terminal exception and final state.
The dedicated runtime closes normally through the runner's cleanup path.

## Division of responsibility

`AccountedSession` derives the current account from accepted `record_account`
operations. The original text, input candidate and producing request are retained.
Only the current account enters the ordinary decision view; every predecessor is
recoverable through its exact EVT action. Its RES is an acknowledgement, not a
duplicate account body. No hidden reasoning or discussion is promoted into an
account. Accounts may be wrong or stale; the host does not endorse them.

An accompanying operation runs only after its account has been accepted. Full
input admission measures the account without truncation or silent release of
selected evidence. A rejected account leaves its predecessor current and skips the
associated operation. The allowed sequence is reserved against the remaining
operation allowance before execution. Each response remains one model decision;
an account, edit and automatic check consume three actual operations.

The task declares a tests check after each accepted test-file edit and a public
check after each accepted documentation edit. Checks bind to the actual saved
successor and frozen checker bytes. All resulting receipts must reach the next
input. A failed check preserves the work. Scoped tests/examples passes do not
authorize submission; the current public pass is required. These are system
protections, so accepted submissions alone cannot establish the model independently
chose an adequate verification sequence.

The task makes the library the immutable behavioral authority. The checker
assesses non-target byte preservation, old test-method AST preservation and
insert-only documentation. This is a task/checking rule, not a host-level ban on
every possible library edit. The host still uses exact current-source eligibility
and guarded candidate/file identities for edits.

## Qualification and limits

Before the live request, 96 selected tests, nine native grammar cases, seven real
checker scenarios and two complete native-sized scripted routes passed. The direct
route uses six scripted requests/thirteen operations; the correction route uses
seven/sixteen and consumes a real failed check before correction. Neither makes
a model completion request. Source and exact-wire/custody checks are separate from
artifact correctness. Earlier unsuccessful qualification attempts remain preserved.

The actual older broad-reading state was also qualified. Its 23,413-token starting
input can deliver a partial 731/1,151-byte saved result at the hard 23,808 ceiling.
After researcher-selected narrowing, a new complete check and account fit. This
does not establish that Qwen will choose that narrowing or that every old result
fits completely beside a broad group.

The account-plus-check package is a declared change in system behavior. This fresh
task cannot isolate the account's benefit from checking policy, source availability,
task differences or the larger opportunity allowance. A correct account cannot
replace implementation evidence, actual execution or direct prose review. A failed
check can refute a proposed expectation without a later passing result; a pass
still establishes only what the executed checker covers.
