# Contribution coordination and spending controls

Implemented and qualified on CPU, October 9, 2026 (Denver). No GPU runtime,
native tokenizer, or model completion was started. The stopped unnamed-section
run and its incomplete work remain unchanged.

## What changed

The new opt-in session mixin accepts `select_contribution`: a model-authored
immediate objective plus an optional registered check scope. The request places
that purpose before the existing task state. It reports accepted edit count,
changed paths, and the selected check's actual candidate/definition applicability.
The objective lives in the ordinary operation archive; restoration derives it
from those records. It persists through work but does not carry a previous job's
objective into the new job. Retrieval of an older selection does not designate it.

This neither selects source nor grants editing authority, and a check remains an
observation rather than proof that the objective is complete. Selection costs one
operation and is optional. Accounts remain optional. The added operation, fields,
available scopes and costs are visible in the reference and output grammar.

The new runner adapter requires declared per-request, attempt-elapsed and
unchecked-edit elapsed limits. Only an actual current check in a declared scope,
under the current checker definition, clears the waiting-for-observation timer.
A failed check qualifies as an observation; an account assertion, retrieved check,
rejected check, stale result or objective change does not. Spending snapshots
retain elapsed time, including time since a snapshot if it is restored. Restoration
does not authorize resumption, and a loop cannot restart itself.

The loopback HTTP transport has an absolute deadline, including header waits and
trickling response bodies. A deadline preserves received bytes, produces no
operation from unfinished output, and leaves previously committed work intact.
The loop returns `spending_limit` without retry. It is designed to run inside the
existing owned-runtime context, which remains responsible for stopping the server.

These are spending controls, not a mechanism that forces the model to emit a final
action. Native rendering, checks and custody drain under their own limits; the
attempt limit is enforced at inference dispatch and during completion, not by
killing an already executing edit/check transaction. An accepted submission stays
accepted even if its closure accounting crosses the spending deadline. The actual
elapsed cost remains recorded.

## Evidence

| Qualification | Result and limit |
|---|---|
| 21 new tests | Selection/clear/history, job boundaries, applicability, source guards, capacity rejection, real CPU failure/correction/check/submission, serialized spending, request/scope binding, deadlines, preservation and no retry pass. |
| 46 existing focused tests | Uncoached loop (15), accounted contributions (11), decision interface (20) pass. These are regression checks, not another complete repository suite. |
| Three real saved states | Visible complete parser source, failed dispatch check, and released-source continuation qualify. Current work, source, accounts, history and sampler remain unchanged by adding purpose. The new selection survives serialized restoration. |
| Local HTTP probes | Complete response, HTTP error, delayed headers and continuously trickling output behave distinctly; the deadline retains the received prefix and terminates the client request. No Qwen server was used. |
| Existing source channel | Literal multiline replacement remains available through the extended decoder and generated grammar. Actual pinned decoder acceptance has not been tested for this extension. |

Final fixture outputs are in `cpu-final/`. `cpu-001/` and `cpu-002/` are retained
prepublication rendering drafts, superseded by the explicit operation-field and
job-boundary reference. They are not additional experiments or independent cases.
No capacity number from the constant CPU meter is a real token-fit result. Files
named `expected-native.txt` are constructed expectations, not runtime observations.

The three fixtures bind the actual historical inputs, complete response files,
effects, checkpoints and candidates. C17 restores its original wire exactly.
Older dispatch fixtures identify existing reference/extent-description changes
separately from this intervention; see [information-path review](INFORMATION_PATH.md).
The new objectives and fixture operations are researcher-chosen, never model
capability evidence. They do not supply the correct repair or silently fix the
incomplete parser task.

The initial fixture script failed on incorrect source-field names, an exact-input
assumption across an older reference revision, and use of the parent adapter for
the cumulative continuation. Those were qualification mistakes. The corrected
script uses actual returned extents and the actual saved-work adapter, and records
the baseline differences. Direct final-action review also corrected our initial
description of the C12 repair order. No historical result was rewritten.

## How this makes development more intentional

[CONTRACT.json](CONTRACT.json) states the question, fixed variables, exact fixtures,
outcomes and decisions. [Development method](../../../docs/DEVELOPMENT_METHOD.md)
requires evidence-path review before expensive inference and evaluates complete
coding contributions rather than successful reads, note counts or shorter output.
The new top-level guidance preserves the GPU stop and separates authorized CPU
development from model evaluation. Consultation stays outside active runs and is
used when it can resolve a concrete design question, not as a compulsory interview.

The candidate mechanism is explicit local purpose plus truthful progress facts.
It may help the model finish a bounded step before planning the whole task again.
It may instead add overhead or be unused. No productivity improvement is claimed.
Spending limits protect the owner from an open-ended attempt; reaching a limit
does not mean the feature is correct or that the model could not finish later.

## Integration and next gate

Use `ContributionCycleMixin` before the actual task session class. Construct
`run_contribution_cycle.Adapter` with the task, exact registered scopes, pinned
schema converter and declared limits; pair it with `SpendingControl` and the new
`Loop` inside the existing owned-runtime context. Bind these new source files in
a new preparation manifest. Do not reuse an old execution manifest or launcher
and call the configuration unchanged. There is deliberately no GPU launch CLI.

Before any separately authorized model attempt, qualify the actual template,
grammar/decoder, complete input admission, real cancellation/owned-server closure
and live budget values. Then compare one bounded coding contribution with model,
quant, sampler, account policy, source rules and cost controls held fixed. Count
the selection overhead. Retain the baseline if no benefit appears. Source
refocusing, multi-edit proposals and the ISTA quant remain separate candidates.

Reviewer effort for this development turn was not independently timed. The CPU
cases and reports do not quantify model savings or isolate a quantization cause.
