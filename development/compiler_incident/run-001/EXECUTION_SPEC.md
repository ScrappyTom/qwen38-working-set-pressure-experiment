# Compiler incident: proposed once-only execution

The owner directed preparing execution safeguards after offline task qualification.
This document freezes the proposed execution behavior. It does not record approval
to send Qwen completions. Prepare, test and bind this package before the separate
owner execution decision; do not reinterpret previous consumed authorizations.

## Fixed scope

Use the exact candidate, task, public checker and three observations sealed under
`preparation-001`, with package SHA256
`f63ec3dcb8115df53235f85acd3e4c644c16d7e3be46c9d1d0a7c2c675e2f3b2` and preparation-seal
SHA256 `35a53de9d8ca5a1811d842378d309f291035d11172791ead0d59b3ee99fe9480`.
The task review and verification are bound in the execution manifest. Preserve all
preparation files and source; the live loader does not call the oracle builder or
load the expected report into decision state. The sealed public checker remains
opaque to action selection and runs only when Qwen requests a check.

Propose two independent cells, C01 seed 49979687 and C02 seed 67867967. Each runs
one common prefix and, only at authentic input pressure, two continuation branches:
R23808 keeps bodies resident up to 23,808 native input tokens; X16000 externalizes
the oldest event-payload prefix only far enough to fit 16,000. C01 runs R then X;
C02 runs X then R. This fixed order is counterbalanced across the two seeds, not
adaptive to results. Complete one cell before starting the other.

Each complete trajectory has 32 actions including its common-prefix actions,
rejections, checks, retrieval and submission. If a prefix uses k actions, each
branch has 32-k remaining. Shared completions occur once, not twice. The absolute
stage ceiling is **128 completion attempts**, a conservative bound for four
32-action trajectories; shared work usually reduces the actual request count.
An attempt counts before dispatch, even if transport later fails. There is no
retry, continuation of a truncated answer, replacement seed, rescue dialogue,
automatic successor or budget extension. The whole attempt has one fixed run-001
directory reserved exclusively; a failed or empty reserved attempt cannot resume.

## Model, input and capacity

Keep Qwen3.8-27B UD-IQ3_XXS, llama.cpp b10434 / 7e4c0a96880dae4fc4268ad441f8a6446bd5460a,
q4_0 K/V, 56,576 physical context, no MTP, thinking on/xhigh/uncapped, unchanged
sampler, one slot, full GPU offload, fit disabled and prompt caching disabled.
Model/runtime hashes and the accepted advisory memory policy are in the manifest.
All four generation-budget request fields remain -1. G=32,768 is prospective
generation space, not a cap. A complete answer exceeding G can proceed only if
actual input plus reported generation fits physical context and other checks pass.
This package does not promise that difficult generation will fit.

Use the previously qualified request builder with the complete reference, accurate
resource/navigation wording and episode annotation. Do not add model-facing branch
names, ancestry text, selection advice, a working account or summaries. Keep fork
identity in exact custody records. A task report already written by the actor is
an ordinary artifact and an additional possible copy of evidence.

Before either cell receives a completion, reconstruct and natively render both
initial requests. They must match the sealed initial input's native bytes and
3,744-token count; only the outer sampling seed differs. Later inputs are counted
from the actual reconstructed state using the same server template and tokenizer.
Native rendering/tokenization requests are separate from model completions and
must be recorded, including unsuccessful admission trials and returned raw bytes.

The common prefix continues only while the next complete input fits 16,000. Its
first input above that limit is saved without a completion and creates the fork.
Copy exact candidate, check flags, reading state, ordered pairs, observations and
canonical payload maps. Assert byte-identical full requests before the residency
difference and verify that running one branch cannot change the common ancestor.

R23808 stops locally if its next input exceeds 23,808. X16000 begins with its last
externalized prefix, tries successive oldest-prefix counts and chooses the first
complete native input at or below 16,000. Both action and result payloads follow
the existing V3 rule; all readable signals remain. If even complete payload
externalization cannot fit, save that unsent input and stop that branch. Do not
restore old payloads automatically or choose them by meaning. Every new retrieval
must be Qwen's selected action. A branch capacity stop does not block its peer.
An input jump beyond the resident ceiling can still permit an X branch if it fits.

If Qwen submits or exhausts its allowance before pressure, report the common-path
outcome and create no branches. Never add padding, mandatory reading or another
action to manufacture a fork. An unchecked submission ends the trajectory as an
unchecked submission; the runner does not append a check on the model's behalf.

## Custody and failure handling

Save exact endpoint input and candidate/session snapshots before rendering. Capture
raw template and tokenization responses before parsing them. Save every complete
model response before extracting thinking/final content, validating or executing
an action. Retain partial HTTP response bytes when available and label them as
prefixes. Thinking remains separately preserved output and is never automatically
inserted into subsequent input. Final content must contain one strict JSON action.

Require one complete response choice, finish reason stop, the expected output
channel, exact native/endpoint input accounting, integer consistent token totals,
zero prompt-cache reuse and physical-context accounting. Validate the selected
action against the exact supplied output schema before invoking the tool. Wrong
keys, types or grammar bounds stop the attempt without executing that action.
In contrast, a structurally valid action rejected by ordinary tool semantics
creates its actual result, consumes one action and returns to Qwen normally.

After execution, save the actual result, successor state, all canonical original
payloads and the next-turn decision. Reconstruct each later event view from those
exact pairs and assert every resident body matches the corresponding actual
result. Successful tool construction is not itself proof of delivery: custody
distinguishes prepared, withheld and actually dispatched inputs. Record first-check
and post-failure remaining opportunity using the existing measurement function.
Do not treat an old check as current merely because its result was retrieved.

Verify source closure before rendering, after rendering, immediately before each
completion and after the saved response but before action execution. Check the
full preparation seal before and after the attempt. Source drift, malformed model
output, accounting mismatch, lost monitoring, runtime failure, incomplete output,
unexpected host exception or transport interruption stops the **entire attempt**;
do not run its remaining branches or second cell. Seal everything obtained so far.
Ordinary branch budget/capacity stops and terminal submissions are outcomes, not
exceptions that trigger retries or repairs.

Use the existing owned hidden server and 200ms GPU sampler on the dedicated port.
The accepted 350 MiB reference remains advisory; no renewed margin decision is
required. Check fresh telemetry (at most five seconds old) and runtime evidence
before and after preparation/response boundaries, before dispatch and before tool
execution. Sampling continues during inference; these checks do not constitute
an interrupting watchdog inside a pending HTTP request. A completed response is
saved before a post-response monitoring failure blocks execution. Retain the
existing transport timeout and byte bound. Always close the owned runtime and
record shutdown/port state in the final seal.

## Evaluation and separate decision

The runner and focused tests must qualify authentic forks, order counterbalancing,
exact state cloning, immutable ancestry, branch/cell isolation, actual result
delivery and canonical recovery, current-version checks, budget exhaustion,
capacity denial, early and unchecked submission, invalid responses, transport and
monitoring failures, source drift, frozen-source enforcement and once-only custody.
Use mocked completion endpoints and previously sealed native renders where inputs
match exactly. Such rehearsal is engineering evidence, not new Qwen performance.

After approval and eventual execution, seal responses before analysis, then directly
review every prompt, complete thinking, final action, actual result and following
host decision. Inspect all copies in source, observations, reports, patches and
check results before attributing continuity to storage or failure to information
loss. Distinguish omitted thinking, externalized evidence and misused available
evidence. The repair may be source-led; the historical report is the incident-
dependent contribution. Do not claim hypothesis reversal just because a pressure
boundary occurred. Preserve any shorter successful path that does not fork.

Report shared work once and branch work separately. Keep model-request input/output
totals, native preparation, model time, tool/host time, checks, opportunities,
necessary recovery and avoidable repetition distinct. Complete the existing five
audit products and bounded decision. A consequential misunderstanding may earn a
separate neutral conversation with Qwen afterward; it does not permit intervention
inside this frozen run. Retaining the interface remains a complete outcome.

Once the safeguards, rehearsal and manifest are ready, the owner can decide on
this exact two-cell, at-most-128-request scope. Freezing the manifest or passing
tests is not that approval. The run command requires the approved manifest hash
and a record of the separate owner instruction; do not supply one on the owner's
behalf merely to launch the prepared runner.
