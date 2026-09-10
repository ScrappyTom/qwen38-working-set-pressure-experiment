# Eight-request wording comparison: execution preparation

This specification binds execution safeguards to the unchanged package prepared
at commit 25789c6. The owner supplied GPT Pro's supportive review, which retained
the separate execution decision. That quoted recommendation is not owner approval.
Freezing this execution plan sends zero completion requests. Run W01–W08 only
after the owner explicitly approves this exact eight-request attempt; record
that direction in the first run record. No additional design round is proposed.

The [prepared specification](SPEC.md), [review](PREPARATION_REVIEW.md), exact
inputs and [independent verification](VERIFICATION.json) remain unchanged.
The manifest hash is b009fe4fdb2e0982c8cb1941791d622fb11cb05f84e80302481453234b4d2112;
the preparation seal is 57074b97fab747c939f689e36678f1088ad7b138a2ea2d6f5370c293586f29fe.

## Scope and invariants

Execute four matched pairs, in their prepared order:

| IDs in order | State | Seed | First → second condition |
|---|---|---:|---|
| W01, W02 | I3 | 1729 | reference → wording |
| W03, W04 | I3 | 271828 | wording → reference |
| W05, W06 | I4 | 1729 | wording → reference |
| W07, W08 | I4 | 271828 | reference → wording |

E01–E04 are offline input regressions and never enter this completion schedule.
Each request uses a newly reconstructed host state and a fresh system/user
conversation. One completed response permits at most one actual strict JSON
action. No continuation, corrective prompt, retry, rescue, diagnostic request
or addition to the schedule is permitted. Reserve run-001 once; any interruption
leaves an immutable complete or partial attempt, not a resumable cursor.

Keep Qwen3.8-27B UD-IQ3_XXS, pinned b10434, q4_0 K/V, 56,576 physical context,
no MTP, full GPU offload/fitting off, one slot, no context shift, thinking
on/xhigh/uncapped and the prepared sampler. Keep the 32,768 generation planning
reserve, 23,808 input ceiling, 14,400-second response timeout and 16 MiB transport
bound. Cache reuse is disabled. No runtime or prompt setting changes mid-run.

The 350 MiB memory reference remains advisory under the existing owner decision;
no new numeric floor or reconfirmation is introduced. Sample at 200 ms through
shutdown; require current telemetry before and after requests. Missing/stale
telemetry, runtime/CUDA/transport failure, context exhaustion, incomplete output,
native/accounting disagreement or cache reuse stops dispatch without retry.

## Execution and preservation

Use the separately frozen run_interface_wording.py. It reuses the existing
owned runtime, monitoring, strict response preservation and action-execution
helpers without editing their consumed source. Its manifest binds the original
package and seal, reviewed input scope, independent verification, exact eight
rows, exclusions, code, tests, runtime policy and this specification.

Before any completion, verify the package's files and private runtime identities,
record chain and preserved previous execution closure. Natively render and count
all eight scheduled requests again with the selected runtime; require exact
agreement with preparation. Before each dispatch, check source identities,
reconstruct its original candidate/session/request, apply only the prepared
presentation adapter, and require exact API request bytes. Record the actual
request and native input, candidate/session before dispatch and current health.

Preserve raw endpoint bytes before parsing. Preserve separate complete thinking
and final fields before validating finish reason, output channels, token/cache
accounting and telemetry. Only a valid complete final action reaches the existing
executor, once. Save its actual result and resulting candidate/session, including
changes preceding an unexpected executor exception. Preserve malformed envelopes,
incomplete final text and partial transport bytes as observed; do not repair them.

An accepted failing baseline check or rejected stale action remains a recorded
outcome. Neither triggers a corrective request. The comparison offers no next
turn after a failure; the original displayed fixture allowance is not an actual
live correction opportunity in this one-action study.

On completion or interruption, stop the owned server and memory monitor, verify
port release and hash-chain custody, and seal the public files and local-only
runtime identities before evaluation. Independent replay and direct transcript
review follow the seal. Never load evaluator truth into model input or a later
conversation. No model output from another W request enters any input.

## Review and next work

Produce the existing five reviews: execution receipt, host-path audit, apparatus
finding, complete direct transcript audit and results decision. Read every actual
input, full thinking, final action, exact result and following host decision,
including successful or recovered paths. Compare stated interpretation with the
operation performed; it is not proof of action causality. Check all supplied
copies of source/evidence before labeling access necessary or redundant.

The primary question is whether Qwen stops treating descriptive metadata as a
compulsory workflow while still taking useful, correctly bound actions. It is
not a requirement to check or navigate less, choose a particular next action,
or match the paired action. Identical actions can accompany different understanding;
different actions can both be useful. Report all four pairs before aggregates,
including input, generation, request time, interpretation and actual consequence.

If the reference controls do not reproduce the target confusion, report limited
sensitivity. Do not infer either efficacy or inefficacy from absence of an error.
These two edits form one package; four development pairs cannot isolate the
individual changes or establish whole-task efficiency. Keep complete tool
information regardless of the result.

The owner-supplied review recommends making a bounded presentation decision
after these responses and returning to multi-turn investigation work. Carry that
direction forward rather than automatically preparing another interface micro-test.
Any further interface study needs a new consequential finding that warrants it.
Accurate host-generated grouping remains recorded as a deferred option; exact
records and consequential interpretation/use must justify it. The next task still
needs credible natural context pressure and task-specific action/generation
allowances. Do not manufacture pressure with padding or a mandatory reading list.
