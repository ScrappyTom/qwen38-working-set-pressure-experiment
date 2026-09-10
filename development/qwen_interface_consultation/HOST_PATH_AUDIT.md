# Host-path audit: initial Qwen interface consultation

Complete. The sole frozen 16-response development run finished normally,
was sealed, independently verified, and directly reviewed in full. See
[DIRECT_TRANSCRIPT_AUDIT.md](DIRECT_TRANSCRIPT_AUDIT.md) and
[EXECUTION_RECEIPT.md](EXECUTION_RECEIPT.md) for review and custody evidence.

## What the host supplied and executed

The four prepared states come from actual tool executions: one exact saved
E020 request/replay, and three scripted small states. Each invocation rebuilds
its own candidate, observation/result/event stores, ordered pairs, read
coverage, check state, and submission state. Ordinary-action requests are
checked against the rebuilt state before exposure. Later invocations receive
neither earlier answers nor private reasoning. Repeated seeds use identical
rendered prompt bytes for each corresponding state/mode.

The native `/apply-template` output is saved before inference. Its token count
is compared with the actual endpoint usage before executing any action. Raw
endpoint bytes enter the artifact store and chained record before parsing.
The existing strict action parser and actual bounded executor process at most
one ordinary action. Diagnostic responses execute nothing. This consultation
does not offer a continuation after the resulting action. A repair/check that
has not yet happened must not be classified as failure to continue or submit.

The endpoint's `response_format` contains the existing action schema. The
ordinary rendered input contains short tool descriptions and action names,
plus any historical action examples, but no complete explicit signature list.
The final-output grammar requires candidate/file guard keys and constrains SHA
shape; it does not supply the particular candidate/file hashes. Calls 1 and 5
produce correct guard-bearing final JSON after reasoning proposes omitting
those keys. This mismatch is concrete interface friction that a check of JSON
validity alone would miss. It is not evidence that the host silently repaired
an emitted malformed action: the saved raw final response already has the keys.

## Findings supported by reviewed inputs and outputs

| Supplied fact or interface | Model interpretation/action | Actual host consequence | Interpretation |
|---|---|---|---|
| Complete source and short patch/check descriptions, without explicit signatures | Calls 1/5 repeatedly guess field names and whether bindings belong in the action | Call 1 runs an accepted failing baseline check; call 5 applies the exact intended repair | Useful/allowed actions coexist with avoidable-looking interpretation effort; test explicit signatures before quantifying an improvement. |
| `correction_cycle_reserved_by_fixture_design` describes check/patch/recheck/submit fitting an ideal path | Calls 1/3/4/5 debate or adopt it as a prescribed order | No host rule requires a preliminary check; no budget increase occurs | The field risks confusing resource description with policy. Its wording deserves a bounded comparison. |
| Root orientation lists the sole file, while repository completeness is false and generic instructions request P0 on incomplete views | Call 3 repeatedly considers extra orientation a mandatory prerequisite | It ultimately retrieves the useful old patch content | Availability versus mandatory navigation is unclear; no unused P0 call was actually executed. |
| Page ends at EOF but begins at line 7 | Calls 3/7 identify missing earlier source | Reopening history leaves read coverage at 7–8 | The distinction is recoverable; clearer page/whole-file labels remain a design hypothesis. |
| Source text, canonical field JSON, and complete action/result pair have different byte counts | Call 7 repeatedly interprets counts as possible hidden source/patch lengths and guesses `handle` versus `event_handle` | The correctly selected retrieval returns the exact 52-byte old/new payload; source remains unchanged | Metadata can be correct yet obscure what object a count describes. Test clearer scope or keeping irrelevant custody detail internal. |
| Passing check on A followed by accepted edit to B | Calls 2/6 request a new check on B | Both new checks pass and bind to B | No stale-check authorization failure occurs in these actions. |
| External exact bodies beside resident status/bindings in the crowded saved state | Calls 4/8 correctly distinguish visibility and completed reading, then retrieve RES-0001/RES-0002 respectively | Exact saved source returns; candidate/check state is unchanged | Useful recovery; no repeated false-presence claim or new execution masquerading as retrieval. |

The full transcripts retain errors and reconsiderations omitted by this compact
table. Correct action selection does not waive host/interface review. Statements
of rationale support interpretation hypotheses; they do not isolate causes or
measure what a changed interface would save.

The P0 tension is in the host's actual wording, not an invented requirement
attributed solely to the model: the system instruction says to use P0 when the
repository view is incomplete, and `build_p0_root` always reports repository
incompleteness. Neither reading source nor an otherwise adequate root listing
clears that root flag. Clarifying when more orientation is needed is a
model-facing instruction intervention and must be qualified as such.

Call 9's diagnostic correctly interprets the predecessor candidate/file guards,
but includes missing exact-source inspection in its list of tool rejection
conditions. The rendered state calls inspection a requirement, while the
actual `_patch` implementation does not inspect read history. It validates
shape, candidate/file identities, exact unique old text, changed bytes, and
content/diff bounds. Distinguish the actor's instructed obligation from what
the tool enforces. This diagnostic statement caused no operation or rejection;
it supports clearer contract communication, not automatically adding a policy.

Calls 10 and 14 expose a related return-shape ambiguity. Both correct old-check
interpretations predict retrieval of the 42-byte stdout/stderr field payload.
The actual handle addresses the complete 434-byte original result, including
old candidate/check bindings. `event_frame_v3._payload_record` hashes extracted
fields; `capture_original_result_payload` saves the complete original result;
`_reopen_result` returns those saved bytes. The differing hashes are not lost
custody, but the model-facing grouping does not explain their different scope.
[HOST_PROBES.json](HOST_PROBES.json) saves the independent exact retrieval and
unchanged current state. Clarifying that relationship is earned; replacing the
storage or silently changing historical recovery semantics is not.

Calls 12 and 16 make the analogous prediction for a saved read: 10,164 bytes of
extracted-field JSON rather than the full 10,549-byte original read result
actually retrieved in call 4. Calls 11 and 15 also weigh the partial source
page's 45-byte field JSON against the 112-byte file. Call 11 eventually counts
the visible source correctly; call 15 retains the scope mismatch. The exact
source is 29 bytes, so subtracting 45 from the file size does not measure
missing source. Both still correctly identify lines 7–8 as an incomplete
whole-file read and describe historical patch retrieval as nonmutating.

Call 13's generic possible rejection list conflates call-limit or submitted
state with patch validation. The executor does not check those conditions in
the patch path; host scheduling determines whether a next invocation occurs.
The specific prefix/final-target restriction remains an actual tool check.
This is an explanatory overreach, not an observed rejected action or authority
bypass. Clarify the implemented contract rather than silently adding gates.

## Runtime and capacity boundary

The owned b10434 server uses the pinned IQ3_XXS weights, q8_0 K/V, 32,768
context, full GPU offload with fitting disabled, no MTP, one slot, native
thinking on/xhigh, and no output/reasoning cap. Context shifting is disabled.
The native prompt preflight's largest input is 18,732 tokens, leaving 14,036
physical tokens. Its required 8,192 generation-space margin is an admission
check, not an output limit or a qualified reserve for a later pressure study.

The server reports speculative decoding disabled and `n_predict=-1`.
Startup reports 66/66 layers offloaded. All 16 responses finish with `stop`,
all release records report `truncated = 0`, and no CUDA/OOM error or context
shift is recorded. The largest observed input plus output is 32,186 tokens,
leaving 582; the second crowded diagnostic leaves 892. The largest ordinary
output is 13,346 tokens, and the largest diagnostic output is 15,363. These
are development observations, not guaranteed future generation bounds.

Across 14,248 samples, whole-device free GPU memory ranges from 316 to 563 MiB.
The minimum is below the profile's 350 MiB target, so this workload does not
qualify that reserve. Desktop activity was not isolated; the samples do not
attribute changes in whole-device usage solely to the model. No preset switch,
output cap, retry, or rescue occurred.

All native prompt counts agree with actual endpoint usage and independent
offline tokenization. The response seal covers 178 files and 66 chained
records, and the eight ordinary actions replay exactly. The runner verified
owned server shutdown and a free dedicated port; a subsequent independent
check found the port free and no llama-server process. The final state is
completed development, with no incomplete generation or protocol stop and no withheld
continuation misclassified as an unanswered request. Presentation friction
and incomplete runtime-reserve qualification remain material limitations.
