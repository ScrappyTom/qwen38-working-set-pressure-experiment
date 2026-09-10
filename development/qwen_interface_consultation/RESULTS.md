# Initial interface consultation — results and design decision

Complete: all 16 responses finished normally, were sealed, and were directly
reviewed. All eight ordinary actions were accepted and independently replayed.
Retain the core and proceed to bounded model-informed interface design before
the fresh investigation. No refactor is adopted by this initial consultation.

## What the ordinary actions establish

The selected Qwen3.8-27B IQ3_XXS actor can use the existing interface on these
development states. All eight ordinary responses produce valid, accepted
actions with the relevant exact guards or recovery handles. This is evidence
about one decision per invocation, not eight completed coding tasks.

| What Qwen saw | Seed 42 action | Seed 314159 action | What the host did next and interpretation |
|---|---|---|---|
| Complete current source returning 1; task asks for 2 | Check current candidate | Patch to return 2 | The check runs and correctly fails on 1; the patch changes the exact source. Neither invocation receives a continuation. A baseline check is not automatically waste. |
| Passing check on A followed by edit to B | Check B | Check B | Both actual checks pass and bind to B. Historical success is not treated as a new check on B. |
| External old/new patch payload; only source lines 7–8 visible | Reopen EVT-0001 | Reopen EVT-0001 | Exact prior action content returns; current source remains unchanged and earlier lines remain unread. Useful retrieval is not replay of the edit. |
| Eleven completed reads; four external result bodies and seven visible bodies | Reopen RES-0001 | Reopen RES-0002 | Exact saved source returns with its metadata; no new read, edit, or check occurs. Both distinguish completed reading from current visibility. |

The original E020 presence-flag mistake is not repeated in these crowded-state
actions. That is a development observation under different weights, template,
and reasoning settings, not a controlled explanation of the historical result.
The exact prompts, thinking, final responses, and resulting states are reviewed
in [the direct transcript audit](DIRECT_TRANSCRIPT_AUDIT.md).

## What a passing action conceals

Thinking reveals repeated uncertainty about argument names absent from the
rendered prompt, confusion between a resource illustration and a required
check-first workflow, and difficulty identifying what byte counts measure.
Several responses eventually reach a correct final action after prolonged
deliberation. The final-output grammar constrains key names and SHA shape;
it does not mean the full signatures were visible during that deliberation.

The explanatory responses preserve the core predecessor/version,
saved-access, and partial-read distinctions. They also expose real limits:
the model sometimes predicts that a retrieval returns the extracted-field
object whose hash/size is displayed, whereas the tool returns the full saved
result. All four `reopen_result` explanations make that object-scope error,
while correctly distinguishing recovery from new execution. It sometimes
conflates task obligations or host scheduling with tool
rejection rules. Independent offline probes confirm the actual return object
and show that guarded patching does not enforce prior reading.

These findings earn a narrow interface design review. They do not establish
lost evidence, faulty version guards, or a need to replace the host's memory.
The host implementation and the presentation of its guarantees need separate
judgments. See [the host-path audit](HOST_PATH_AUDIT.md) for the exact distinctions.

## Retained and deferred decisions

Retain the exact stores, ordered events, stable recovery handles, current and
predecessor bindings, and separation between retrieving historical evidence
and executing new work. No representation variant has been adopted. Complete
the [prepared informed-design consultation](FOLLOW_ON_PROPOSAL.md) before
selecting at most one comparison variant. Its four exact requests currently
have zero completion calls; Qwen preferences have not yet been collected.

| Design topic to keep | Why it is earned | Evidence needed for adoption |
|---|---|---|
| Explicit model-visible tool signatures | Thinking repeatedly guesses keys while the final grammar requires them | A matched ordinary-action comparison preserves correct guards and useful choices, with a meaningful benefit after counting added prompt cost |
| Resource wording separated from action instructions | The ideal correction-cycle illustration is repeatedly read as check-first policy | Less mistaken workflow interpretation or unnecessary work without changing budgets or imposing a new stopping policy |
| Scope of payload hashes, byte counts, and recovered objects | Correct field hashes sit beside handles for larger saved-result objects | Correct prediction of actual retrieval contents and reduced ambiguity with full custody preserved |
| Navigation and page/whole-file status | Root incompleteness and a page's EOF flag require extra interpretation | Clearer decisions about necessary source acquisition without suppressing legitimate reads |
| Alternative names or grouping suggested by Qwen | The owner explicitly requested model-informed design; preferences remain uncollected | Preserve the original suggestion, map it to actual host semantics, then test the concrete proposal rather than accepting vocabulary preference alone |

A variant may change names, grouping, or which internal custody details are
displayed. It is a model-facing intervention even when storage is unchanged.
Do not bundle a new memory operation, semantic ranking, reread suppression,
or a host policy change into that comparison. Those remain deferred until a
separate task need earns them. The next comparison uses neutral fixture IDs
in both conditions because the initial descriptive labels cued some answers.

## Capacity and the substantive next task

Uncapped xhigh reasoning makes generation reserve material: completed outputs
already include 15,363 tokens, and one crowded response leaves only 582 tokens
of the 32,768 physical context. The 8,192-token development admission margin
is not a qualified future reserve. The prepared design prompt leaves less room
than one observed crowded answer used. Resolve that before exposure, using
the owner's q4/56,576 option if preparation selects a larger capacity. Preserve
the q8 evidence and match runtime/KV/context across any comparison pair.

The largest ordinary-action output is 13,346 tokens on a 2,215-token input;
the 15,363-token output is explanatory. Keep those modes separate when
qualifying a future action-generation reserve. Neither a small development
maximum nor the diagnostic maximum establishes a guaranteed bound for harder
coding work. Any reserve and its resulting change to the 25k admission target
must be explicit before the substantive comparison.

The [fresh investigation probe](../../maintenance/resume_after_020/INVESTIGATION_GEOMETRY.json)
reproduces a new stale-map failure and distinguishes it from extraction error,
but has not established a natural pressure opportunity. A short correct path
may finish early. It is not ready to freeze as the substantive continuity
experiment; qualify another credible investigation if necessary, without
padding or prescribing a complete reading list. No fresh-task model run has
occurred.

## Completed accounting and limits

| Mode | Input tokens | Generated output tokens | Invocation time |
|---|---:|---:|---:|
| Eight ordinary actions | 50,862 | 43,520 | 39.5 minutes |
| Eight diagnostics | 50,704 | 90,274 | 81.7 minutes |

The endpoint reports combined output. Separate offline retokenization counts
120,548 thinking-text tokens and 13,195 final-text tokens across both modes;
those text counts are not original generated-token segmentation. Full per-call
accounting and the qualification are in [the execution receipt](EXECUTION_RECEIPT.md).
Long deliberation is visible directly, but its entire cost cannot be assigned
to one field or to the host. Some thinking invokes an unsupplied verbosity
instruction; every such claim must be checked against the actual input.

All 178 sealed files and 66 chained records verify, and all 16 native prompt
counts match independent offline tokenization. The server closed and the port
is free. No truncation, CUDA/OOM error, or context shift is recorded. Sampled
whole-device free GPU memory reaches 316 MiB, below the profile's 350 MiB
target; finishing this workload does not qualify that reserve.

Exposed examples, one-action invocations, descriptive IDs, and diagnostic
questioning limit all claims. No new interface has been compared, no Qwen
design preference has yet been collected, and no fresh continuity task has
run. See [the apparatus finding](APPARATUS_FINDING.md).
