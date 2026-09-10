**Proposal: resume the project after Experiment 020**

Latest execution outcome: the owner accepted the observed 339 MiB margin and
the q4/56,576 continuation completed with monitoring under the
[continuation amendment](development/qwen_interface_consultation/follow-on/continuation/SPEC.md)
for Q2/Q3 and D1–D4 without rerunning Q1. Read the
[complete design audit and decision](development/qwen_interface_consultation/follow-on/continuation/design-review/RESULTS.md)
and [prepared signature comparison](development/qwen_interface_consultation/comparison/PREPARATION_REVIEW.md).
The original three-plus-four scope is consumed; the sixteen matched comparison
requests have zero completions. The 350 MiB reference remains advisory and
q4/49,152 was not selected. Original stop reports remain preserved evidence.

Repair measurement, consult the selected operating model using the existing interface, then test one fresh investigation whose explanation changes across context pressure. Retain exact custody, readable orientation, ordered progress, canonical recovery references, and candidate-bound actions and observations. Explicitly review model-facing metadata and tool design with Qwen; a bounded refactor may earn adoption through clearer operational decisions or demonstrated efficiency while preserving those guarantees.

The owner has directed proceeding with this plan, starting with offline measurement maintenance and interface-development preparation. This document is not a frozen successor specification; its bounded execution stages remain as described below. Experiment 020 is complete. Its sealed evidence and original scores remain historical records. The [September 9 review](PROJECT_REVIEW_2026-09-09.md), the subsequent transcript check, and the owner's model choices are the basis for this plan.

Progress is recorded in the [maintenance finding](maintenance/resume_after_020/FINDING.md). The owner-directed initial 16-response consultation is concretely defined in [its development specification](development/qwen_interface_consultation/SPEC.md) and prepared package. Any later design consultation, interface comparison, or substantive experiment requires its own concrete bounded preparation; the instruction to proceed is not an automatic successor policy.

Completed under this plan: the prospective measurement repairs, 42 selected passing tests, independent historical reanalysis, and the sole initial 16-response consultation. The [completed consultation decision](development/qwen_interface_consultation/RESULTS.md) retains the core and identifies concrete interface friction from all exact thinking and final outputs. All eight ordinary actions were accepted and replayed. The [informed-design follow-on](development/qwen_interface_consultation/FOLLOW_ON_PROPOSAL.md) initially stopped after correct Q1 at 339 MiB against its frozen 350 MiB minimum; [the sealed partial audit](development/qwen_interface_consultation/follow-on/qualification-review/RESULTS.md) is preserved. Under the subsequent owner amendment, Q2/Q3 passed and all four design responses completed and received full direct review. Qwen's preference for visible contracts is retained; concrete errors in its proposed state views prevent adopting them wholesale. No consumed response may be repeated. The focused interface suite now contains 25 passing tests; this is not a full-suite claim.

Capacity preparation remains material. The initial crowded diagnostics left only 582 and 892 physical tokens at q8/32k and reached 316 MiB free. At the selected q4/56,576, continuation qualification reached 335 MiB and design reached 339 MiB, completing normally under the owner's advisory memory policy. Three design outputs exceeded the earlier 20,480-token planning reserve; the next preparation uses 32,768, with generation still uncapped. All sixteen comparison inputs fit its 23,808-token input ceiling. These are development margins, not a qualified future 25k study allowance. The proposed fresh investigation has a reproducible failure and independently checked behavior, but its natural pressure opportunity is still unqualified.

The September 10 owner-supplied GPT Pro review established that complete tool requirements must be visible to the actor; Qwen should advise on how to present them. Explicit signatures remain the preferred first narrow comparison. A variant addressing retrieved-object scope instead needs evidence about predicted or subsequently interpreted contents, not just accepted actions. That review called for separate generation-room and 350 MiB GPU-reserve qualification at q4/56,576; the owner subsequently amended the numeric memory requirement as recorded above. The existing q8 design package remains unexecuted preparation. The [follow-on proposal](development/qwen_interface_consultation/FOLLOW_ON_PROPOSAL.md) preserves this planning basis and links the subsequent qualification and design evidence, without changing historical results or authorizing an automatic run.

The owner-authorized three qualification and four conditional design responses are now consumed, including the original retained Q1. The [earlier capacity revision](development/qwen_interface_consultation/follow-on/CAPACITY_REVISION.md) proposed q4/49,152 but was never selected or launched. The current sixteen-request comparison is its own prepared stage: an explicitly incomplete legacy control versus the source-checked visible reference, with identical state and output grammar. Its separate execution decision remains required by the follow-on proposal. No design rerun, broad refactor or fresh investigation is implied.

**Selected model and capacity options**

| Setting | Primary | Larger capacity option, if needed |
|---|---|---|
| Model weights | Qwen3.8-27B Unsloth Dynamic 3.0 UD-IQ3_XXS | Same exact artifact |
| Physical context | 32,768 tokens | Recorded tested allocation: 56,576 tokens, the approximately 55k option |
| K and V cache | q8_0 | q4_0 |
| MTP | Disabled | Disabled |
| Difficult-work reasoning | Native thinking on, xhigh, uncapped | Same |
| Externalization target | 25,000-token admission target, defined below | Same target unless a separately frozen question changes it |

Use the pinned `llama-cpp-b10434-cuda-13-3` runtime, revision `7e4c0a96880dae4fc4268ad441f8a6446bd5460a`, and model SHA-256 `c0b7c3038681ed2e3040456c1dd45f9858b6c2290bed172c70388a94874f3eee`. The profile source is [model-profiles](https://github.com/ScrappyTom/model-profiles/tree/b5ee42b47553c6882862665ca5a58dc0a921d8d0), specifically its IQ3_XXS profile, guide, and hardware overlay. Local executable/model paths remain in that repository's ignored `.local/handoffs/qwen38-iq3-q4-mtp.md`; do not copy machine-specific launch paths into committed experiment documents.

The primary full-offload preset is `32k-q8-full-gpu-350mib`, with automatic fitting disabled. Match the selected profile's embedded template, sampling, offload, and single-slot settings; remove speculative flags. Verify the effective client request as well as the launch command so the old harness does not silently restore its 512-token thinking budget or another generation cap. Low/medium effort and MTP are not part of this proposal.

The larger q4 configuration is an available preparation choice, not an automatic rescue. Its reported 55,779-token input result was simple retention with a tiny answer; hard reasoning near that occupancy is unvalidated. Select and qualify a capacity configuration before freezing a comparison. Both branches of any pair use the same KV type, physical context, reasoning policy, and runtime. Never compare q8 resident against q4 externalized and interpret the difference as externalization alone, or switch presets inside a measured trajectory.

**Resolve token accounting and history explicitly**

The old X25 guard admitted an exact rendered prompt plus fixed runtime/output allowances under 25,000 tokens. Its 512-token reasoning treatment is being replaced at the owner's direction. Reusing those constants would misstate the new allowance.

Proposed successor accounting: let P be the exact rendered input, A the verified runtime/template adjustment, G a prospective generation reserve covering reasoning and the final action, and C the selected physical context. Admit the resident branch while `P + A + G <= C`. Reconstruct the externalized branch by moving the oldest exact payload bodies out of residence until `P + A + G <= 25,000`. Use the same G in paired conditions. Determine G from saved exact outputs and the bounded development qualification below, freeze it before measurement, and report its value. If no usable reserve fits the primary configuration, decide on the larger q4 option during preparation.

Keep generation uncapped and context shifting disabled. G is an admission reserve, not a generation limit or a guarantee that every future response will fit. Consequently, 25k is a reconstruction/admission target here, not the old guarantee of a hard maximum on actual input plus output. Preserve the exact response and classify physical context exhaustion separately from an incorrect action. Report actual input, reasoning, final output, and remaining physical space independently. This budget definition must be explicit in the successor specification; do not present it as an unchanged replication of X25.

Proposed first-study history policy: continue storing private reasoning separately and omit it from subsequent decision frames. This keeps the controller's tested history policy while using the newly selected uncapped reasoning within each call. The model profile's preservation default does not settle what the client supplies in later history. Carrying reasoning forward would be an additional representation choice and should be chosen before the freeze, rather than inherited accidentally. No model-written memory or working-account action is added initially.

**1. Make the earned measurement repairs offline**

| Work | Concrete change and verification |
|---|---|
| Complete inspection | Correct `inspection_status` to require continuous coverage from the first line through actual EOF before the first accepted mutation, using exact source/version evidence. Test a missing middle, adjacent ranges, overlap, out-of-order reads, a real empty file, and an empty read beyond EOF. Keep page-to-EOF status distinct from whole-file coverage. |
| Acceptance semantics | Add a separately named post-hoc probe for `max_files=0` and qualify future checks at zero, one, larger limits, and the relevant inclusion boundaries. Test against the written contract independently of donor equivalence. Preserve the original frozen grades; report the additional R50/X25 difference separately. |
| Correction opportunity | Record calls remaining immediately before the first check and after each failed check, plus whether check/patch/recheck/submit opportunities remain. Measure this without changing action budgets, stopping behavior, or inserting new model-facing advice. |
| Lifecycle maintenance | Replace the stale pre-authorization absence assertion with an appropriately scoped current check; retain the actual authorization validation. Correct stale navigation text without rewriting historical decisions. |

Implement prospectively, with new analysis outputs and explicit code identities. Reproduce historical execution from its pinned commit; do not regenerate old executable-closure receipts against changed code. Run the focused regressions and an independently implemented line-coverage check on all eight saved Experiment 020 branches. The earlier review found no missing lines, and this repair should preserve that result. Persist the additional boundary findings as an addendum, not replacement scores.

Exit: corrected measurement is reproducible, the eight historical inspection outcomes remain explained, and the distinction between formal scores and additional contract tests is visible.

**2. Qualify the selected actor and review model-facing metadata and tools with it**

Prepare a small development package using exact saved requests, actions, results, and bindings. Verify runtime/model identities, exact prompt tokenization, uncapped reasoning-to-final separation, strict one-action output, capacity-stop custody, and isolated tool execution. Check the existing timeout/response-byte bounds against the selected configuration; record any necessary transport adjustment prospectively. Do not diagnose a client-imposed cutoff as model failure.

Use four development states:

| Example | Operational distinction to observe |
|---|---|
| Experiment 020 cell 1 X25, continuation call 3 | Eleven reads are complete; four result bodies exist but are external. The adjacent action payload is absent. Can the actor distinguish existence, current visibility, and completed work? Include the complete crowded request, not only a cleaned excerpt. |
| A saved passing check on candidate A followed by a patch producing B | Retrieving the old check does not execute a new check or establish that B passes. Observe the next action and the predicted effect of recovery. |
| A patch request with candidate/file preconditions | `expected_candidate_id` and `expected_file_sha256` bind the existing version. They are not the identity or fingerprint of an ideal corrected answer. |
| A historical patch and a partial source read ending at EOF | `reopen_event` reads saved action content without replaying the edit; reaching EOF does not imply that earlier source lines were read or are visible. |

Proposed initial consultation: four states, two prospectively fixed seeds (42 and 314159), one ordinary next-action response and one separately recorded diagnostic response per state/seed: 16 completions. Final exact requests and schedule are prepared before exposure. The diagnostic is an explanatory consultation, not a continuation of the measured coding protocol. Fresh sessions prevent assumptions or corrective teaching from leaking between examples.

Record the ordinary next action first, using the existing interface and task. Diagnostic questions come afterward in separate sessions so they do not prime that action. Ask what occurred, which version is involved, what is visible, and what a selected operation would return or change. Do not provide preferred names or architecture suggestions before the original interpretation is saved. All examples are development evidence, including those drawn from formerly measured transcripts.

The cited call-3 misreading was verified against its actual input and private output: Qwen described `result_body.present` as false although it was true; the adjacent `action_payload.present` was false. It recovered on call 4. Its valid retrieval was useful, so that episode alone does not prove avoidable cost.

**Explicit follow-on: Qwen-informed metadata and tool refactoring.** Review this before the fresh investigation and record a decision even if the existing interface is retained. The earlier conversational probe of Qwen 3.5 9B supplies useful hypotheses; the selected Qwen3.8-27B IQ3_XXS actor must provide its own interpretation and preferences under the chosen runtime. Begin with q8/32k and the existing representation.

After saving the unassisted actions and interpretations, ask Qwen how it would prefer the same facts and operations to be expressed. Consider what metadata is shown together or kept internal, visibility versus existence, completed reading, current versus historical evidence, and tool names, descriptions, arguments, and returned state. This review can propose a simpler model-facing interface, beyond renaming a few fields. Preserve exact internal records, stable references, ordered activity, version preconditions, the one-action protocol, and the separation of retrieval from execution. Any genuinely new operation or memory mechanism needs a separately demonstrated task need.

Complete tool argument requirements, accepted forms, binding meanings, and effects are required model-facing information. Verify them in the native rendered input, separately from the server's output grammar. Retaining familiar names or grouping remains an option; retaining the demonstrated omission is not the default for future work. A comparison against the explicitly under-specified legacy interface can measure the effect and cost of making signatures visible, but a speedup is not a prerequisite for supplying missing instructions.

Use a concrete observed ambiguity, unnecessary interface cost, or repeated operational mistake to motivate at most one small initial variant. Compare it with the existing interface in fresh sessions using matched states and actor settings, including complete crowded requests. Directly inspect the inputs, reasoning, actions, returned results, and resulting state; measure correctness, avoidable work, prompt/reasoning tokens, calls, and elapsed time. Record changed token cost and any movement of the pressure boundary. Design consultation and a variant comparison are a bounded follow-on package defined after the initial findings, not an implicit expansion of the proposed 16 completions.

Choose the comparison's observations to match the proposed repair. For explicit signatures, inspect argument guessing and correct guard-bearing actions while counting added input and generated output separately. For retrieved-object scope, valid handle selection is insufficient: use a prospectively specified content-prediction check against exact host retrieval, or a bounded continuation that can reveal how the returned result is interpreted. Freeze any changed request count before exposure; do not append diagnostics after seeing an outcome.

Adoption criterion: an observed operational benefit with the host's guarantees preserved. Repeatedly confusing a saved check with a new check can earn a correction; reliable decisions with fewer tokens or less unnecessary work can also justify a proposed improvement. A failure need not be manufactured before considering simpler presentation. Vocabulary preference or a fluent explanation alone is insufficient, and useful reacquisition is not automatically waste. This is a prospective recommendation for owner review under the existing approval boundary, not a change to Experiment 020's frozen rules. Treat an adopted interface variant as a qualified intervention and use the same variant in both subsequent pressure conditions.

Exit: a concise, directly audited interface decision recording the original interpretations, Qwen's suggestions, the guarantees retained, any exact proposed variant and comparison evidence, and an adopt/defer/retain decision. Keep deferred suggestions and their evidence requirements here so the metadata/tool refactoring question is not lost. Model preferences suggest designs; observed actions and consequences determine adoption.

**3. Prepare one fresh investigation**

Proposed task: diagnose a failure after editing an artifact and reopening one of its sections in an owner-controlled exact-content pipeline. A valid current operation unexpectedly fails content validation. The actor must reproduce it, repair the cause, preserve rejection of genuinely stale references, pass the public check, and submit.

This is a proposed task geometry, not a claim that a new production defect has been found. During offline preparation, pin and inspect a suitable owner-controlled source snapshot and construct a fresh fixture in the mutation-to-address-map refresh path. Do not reuse the exposed Experiment 019 inclusive-line/truncation faults, its summary-graph task, or Experiment 020's boundary/verifier faults.

For task construction and evaluation only, two plausible explanations are incorrect section extraction and an old address map being paired with updated content. Exact diagnostic evidence should establish that extraction from a correctly matched current unit is sound while the edit/update path leaves a stale association. Investigating propagation through the actual update and recovery paths should supply useful work after that distinction is established. Do not give these explanations, the solution path, or a mandatory complete reading list to the actor.

Use ordinary source discovery, reads, patching, and the existing public-check surface for exact reproduction output. Hidden checks independently cover the corrected current operation, continued rejection of old mismatched references, unchanged-content behavior, and another update. Any additional diagnostic operation would need its own demonstrated necessity; this proposal does not add one.

Admit the task only after offline inspection establishes a credible natural pressure opportunity and an executable correction-and-closure path under the actual file, line, patch, event, and resource bounds. Do not enlarge it with inert padding or compelled unrelated reads. If this candidate is too small, choose a different real investigation before freezing. If the actor nevertheless finishes before pressure or never needs to revise an explanation, record successful task work with continuity unexercised; do not manufacture a later boundary or require the actor to make an initial mistake.

Proposed primary schedule: one fresh task, two fixed seeds, paired resident/externalized conditions—four terminal branches—with each pair sharing one byte-identical live prefix until authentic pressure. Use the selected q8/32k configuration for all branches unless preparation prospectively chooses the larger q4 option for the entire comparison. The action budget and generation reserve come from qualification and are frozen before exposure; do not reuse the old 24-call limit without checking the actual task. No automatic retries, rescue, or successor.

The key question is whether the actor retains or correctly reconstructs the reason to investigate update propagation after evidence rules out extraction. It need not preserve verbatim reasoning or first commit to the wrong explanation. Before the run, state the observable implications of the evidence. Repeating a ruled-out diagnostic is only avoidable repetition when its relevant premises have not changed.

Measure task/hidden-check outcome, first-check outcome, actual correction opportunity, evidence selection, necessary reacquisition, avoidable repeated work, peak occupancy, and cumulative input/reasoning/final tokens and time separately. Audit every available copy of a fact in the task, source, observations, later results, and saved work before claiming memory use or information loss. Correct repair alone does not establish the claimed continuity mechanism; verbal explanation alone does not either.

**Owner decisions and boundaries**

The model, primary q8/32k configuration, optional approximately 55k q4 configuration, MTP exclusion, and uncapped xhigh difficult-work direction are already supplied. They do not need to be asked again.

The owner has authorized proceeding with the maintenance and initial consultation described here. The exact 16-request package and runtime settings have been prepared under the linked development specification before exposure. After the complete development audit, prepare any earned interface comparison and the qualified fresh task as concrete bounded packages. Present the frozen substantive comparison for its own execution authorization. If an owner instruction already explicitly covers an exact later boundary, retain that authorization rather than asking again.

Use the existing specification, receipts, response sealing, host-path audit, direct transcript audit, and results decision. Add no authorization framework or new governance schema. The first substantive experiment should establish whether the frozen foundation supports a changing investigation; later failures may earn a working account or another representation, but those mechanisms are not prebuilt by this proposal.

Every development and measured transcript review must inspect the actual prompt, separate thinking, final response/action, exact result, and next host decision for host defects and interaction friction, including recovered confusion and successful trajectories. Compare model interpretations with the actual supplied state before assigning cause or proposing a refactor. Preserve useful recovery as distinct from unnecessary work and record uncertain explanations as hypotheses. This requirement is also in `AGENTS.md` and `docs/ANALYSIS_GOVERNANCE.md`.
